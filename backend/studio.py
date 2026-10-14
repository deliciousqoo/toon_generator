"""Local durable Stage 04 orchestrator and its additive HTTP boundary."""
import copy
import json
import sqlite3
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

import httpx
from fastapi import APIRouter, HTTPException
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from langsmith import tracing_context

from .studio_contracts import ActionInput, EvaluationArtifact, FormatProposal, Project, ProjectBrief, Run, RunInput
from .studio_workers import configured_provider, evaluate_board, evaluate_story, make_board, make_story


def now():
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix):
    return f"{prefix}-{uuid.uuid4().hex}"


class StudioConflict(Exception):
    pass


class RunStopped(Exception):
    pass


class GraphState(TypedDict, total=False):
    run_id: str
    project_id: str
    idea: str
    input_kind: str
    revision: int
    story: dict
    format_proposal: dict
    storyboard: dict
    issues: list[dict]
    feedback: str
    target_ids: list[str]
    route: str
    entry: str
    automatic_rewrites: int
    previous_story: dict
    previous_storyboard: dict


class StudioService:
    MAX_NODES = 24
    MAX_SECONDS = 120
    MAX_AUTOMATIC_REWRITES = 2

    def __init__(self, root: Path, provider=None, *, background=True):
        self.root = Path(root) / "studio"
        self.root.mkdir(parents=True, exist_ok=True)
        self._db_lock = threading.RLock()
        self._locks_lock = threading.Lock()
        self._run_locks = {}
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="toon-studio")
        self._futures = {}
        self._closed = False
        self.background = background
        self.provider = provider or configured_provider()
        self.db = sqlite3.connect(self.root / "studio.sqlite3", check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, project_id TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS versions(run_id TEXT NOT NULL, kind TEXT NOT NULL, version TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(run_id,kind,version));
            CREATE TABLE IF NOT EXISTS provider_budget(id TEXT PRIMARY KEY, calls INTEGER NOT NULL);
        """)
        self.db.commit()
        self._checkpoint_db = sqlite3.connect(self.root / "checkpoints.sqlite3", check_same_thread=False)
        self._checkpoint_db.execute("PRAGMA journal_mode=WAL")
        self.checkpointer = SqliteSaver(self._checkpoint_db)
        self.checkpointer.setup()
        self.graph = self._build_graph()
        # Queued/running operations survive process exit. Human review remains paused.
        with self._db_lock:
            recovering = [json.loads(row[0]) for row in self.db.execute("SELECT payload FROM runs").fetchall()]
        for record in recovering:
            if record["status"] in ("queued", "running"):
                self._launch(record["id"])

    def close(self):
        self._closed = True
        self._executor.shutdown(wait=True)
        self._checkpoint_db.close()
        self.db.close()

    def _lock_for(self, rid):
        with self._locks_lock:
            return self._run_locks.setdefault(rid, threading.RLock())

    def _dump(self, value):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    def _raw(self, rid):
        with self._db_lock:
            row = self.db.execute("SELECT payload FROM runs WHERE id=?", (rid,)).fetchone()
            if not row:
                raise KeyError(rid)
            return json.loads(row[0])

    def _save(self, run):
        with self._db_lock:
            self.db.execute("INSERT OR REPLACE INTO runs VALUES(?,?,?)", (run["id"], run["project_id"], self._dump(run)))
            self.db.commit()

    def _patch(self, rid, **changes):
        with self._db_lock:
            run = self._raw(rid)
            run.update(changes)
            self._save(run)

    def _event(self, rid, role, stage, message):
        with self._db_lock:
            run = self._raw(rid)
            event = {"id": new_id("event"), "at": now(), "role": role, "stage": stage, "message": message, "revision": run["revision"]}
            self.db.execute("INSERT INTO events(run_id,payload) VALUES(?,?)", (rid, self._dump(event)))
            self.db.commit()

    def _activity(self, state, role, stage, message):
        rid = state["run_id"]
        run = self._raw(rid)
        if run.get("_cancel_requested"):
            raise RunStopped("사용자가 실행 중인 작업을 중단했습니다.")
        count = run.get("_node_count", 0) + 1
        if count > self.MAX_NODES or time.monotonic() > run.get("_deadline", time.monotonic() + self.MAX_SECONDS):
            raise RuntimeError("자동 실행의 단계 또는 시간 한도에 도달했습니다.")
        self._patch(rid, status="running", current_role=role, current_stage=stage, summary=message,
                    pending_action=None, _node_count=count)
        self._event(rid, role, stage, message)

    def _sources(self, state, *artifacts):
        sources = copy.deepcopy(self.get_project(state["project_id"])["fixture_versions"])
        sources.append({"project_id": state["project_id"], "artifact_id": f"{state['run_id']}-episode-input", "version": "1.0.0", "role": "episode_input"})
        for role, artifact in artifacts:
            sources.append({"project_id": state["project_id"], "artifact_id": artifact["artifact_id"], "version": artifact["version"], "role": role})
        return sources

    def _metadata(self, state, kind, sources):
        return {"artifact_id": f"{state['run_id']}-{kind}", "version": f"2.0.{state['revision']}",
                "project_id": state["project_id"], "content_id": state["run_id"], "source_versions": sources}

    def _archive(self, rid, kind, artifact, summary):
        with self._db_lock:
            saved = {"kind": kind, "artifact_id": artifact["artifact_id"], "version": artifact["version"], "created_at": now(), "summary": summary, "artifact": artifact}
            self.db.execute("INSERT OR IGNORE INTO versions VALUES(?,?,?,?)", (rid, kind, artifact["version"], self._dump(saved)))
            self.db.commit()
            # On checkpoint replay, immutable archived content wins.
            archived = json.loads(self.db.execute("SELECT payload FROM versions WHERE run_id=? AND kind=? AND version=?", (rid, kind, artifact["version"])).fetchone()[0])["artifact"]
            if kind in ("story", "format_proposal", "storyboard"):
                self._patch(rid, **{kind: archived})
            return archived

    def _cached_artifact(self, state, kind):
        with self._db_lock:
            row = self.db.execute("SELECT payload FROM versions WHERE run_id=? AND kind=? AND version=?",
                                  (state["run_id"], kind, f"2.0.{state['revision']}")).fetchone()
        return json.loads(row[0])["artifact"] if row else None

    def _issues(self, state, issues):
        records = [{"id": f"issue-{state['revision']}-{i}", "target_id": None, **issue} for i, issue in enumerate(issues)]
        self._patch(state["run_id"], issues=records)
        return records

    def _provider_call(self, state, method, context):
        for attempt in range(2):
            try:
                if self._raw(state["run_id"]).get("_cancel_requested"):
                    raise RunStopped("사용자가 실행 중인 작업을 중단했습니다.")
                if hasattr(self.provider, "budget_id"):
                    with self._db_lock:
                        self.db.execute("INSERT OR IGNORE INTO provider_budget VALUES(?,0)", (self.provider.budget_id,))
                        used = self.db.execute("SELECT calls FROM provider_budget WHERE id=?", (self.provider.budget_id,)).fetchone()[0]
                        if used >= self.provider.approval["max_calls"]:
                            raise RuntimeError("P1 기록의 제공자 호출 한도에 도달했습니다.")
                        self.db.execute("UPDATE provider_budget SET calls=calls+1 WHERE id=?", (self.provider.budget_id,))
                        self.db.commit()
                result = getattr(self.provider, method)(context)
                if self._raw(state["run_id"]).get("_cancel_requested"):
                    raise RunStopped("사용자가 실행 중인 작업을 중단했습니다.")
                return result
            except (httpx.TransportError, httpx.TimeoutException):
                if attempt:
                    raise
                self._event(state["run_id"], "orchestrator", self._raw(state["run_id"])["current_stage"],
                            "일시적인 로컬 연결 오류로 현재 역할 작업만 1회 재시도합니다.")

    def _evaluation(self, state, kind, role, context, structural_issues):
        archived = self._cached_artifact(state, kind)
        if archived:
            self._patch(state["run_id"], issues=archived["issues"])
            return archived, archived["issues"]
        sources = context["source_versions"]
        context = {**context, "rubric_version": "story-v1" if kind == "story_evaluation" else "board-v1",
                   "criteria": ["input_preservation", "causality", "character_continuity", "emotional_turn", "payoff"] if kind == "story_evaluation" else
                               ["beat_coverage", "action_expression_staging", "focal_change", "readability", "continuity"]}
        result = self._provider_call(state, f"evaluate_{'story' if kind == 'story_evaluation' else 'board'}", context)
        if result.get("source_versions") != sources:
            raise ValueError("평가 결과가 정확한 입력 버전을 가리키지 않습니다.")
        issues = self._issues(state, structural_issues + result["issues"])
        allowed_targets = {item["id"] for item in (context.get("story") or {}).get("beats", [])}
        allowed_targets.update(panel["id"] for panel in (context.get("storyboard") or {}).get("panels", []))
        if any(issue.get("target_id") and issue["target_id"] not in allowed_targets for issue in issues):
            raise ValueError("평가에서 현재 산출물에 없는 대상을 가리켰습니다.")
        if result["recommendation"] == "revise" and (not result["feedback"].strip() or not result["evidence"] or
                not any(issue.get("target_id") in allowed_targets for issue in result["issues"])):
            raise ValueError("자동 수정 추천에는 구체적인 근거·수정 의견·대상 ID가 필요합니다.")
        evaluation = EvaluationArtifact.model_validate({**self._metadata(state, kind, sources), "role": role,
            "provider": self.provider.name, "fixture": self.provider.fixture, "recommendation": result["recommendation"],
            "issues": issues, "feedback": result["feedback"], "evidence": result["evidence"],
            "rubric_version": "story-v1" if kind == "story_evaluation" else "board-v1",
            "criteria": ["input_preservation", "causality", "character_continuity", "emotional_turn", "payoff"] if kind == "story_evaluation" else
                        ["beat_coverage", "action_expression_staging", "focal_change", "readability", "continuity"]}).model_dump()
        evaluation = self._archive(state["run_id"], kind, evaluation, "정확한 산출물 버전의 독립 역할 평가")
        issues = evaluation["issues"]
        self._patch(state["run_id"], issues=issues)
        return evaluation, issues

    def _story(self, state):
        self._activity(state, "story_generator", "story", "이야기 역할이 합성 입력과 수정 범위를 정리하고 있습니다.")
        context = {"idea": state["idea"], "input_kind": state["input_kind"], "feedback": state.get("feedback", ""),
                   "previous": state.get("story"), "character_package": self.get_project(state["project_id"])["character_package"],
                   "source_versions": self._sources(state)}
        metadata = self._metadata(state, "story", self._sources(state))
        story = self._cached_artifact(state, "story")
        if not story:
            draft = self._provider_call(state, "story", context)
            from .studio_contracts import StoryArtifact
            story = StoryArtifact.model_validate({**draft, **metadata}).model_dump()
        story = self._archive(state["run_id"], "story", story, "이야기 초안 또는 수정본")
        self._patch(state["run_id"], format_proposal=None, storyboard=None)
        return {"story": story, "previous_story": state.get("story"), "format_proposal": None, "storyboard": None, "previous_storyboard": None}

    def _validate_story(self, state):
        self._activity(state, "validator", "story", "프로젝트 경계와 정확한 원본 버전을 검사하고 있습니다.")
        project = self.get_project(state["project_id"])
        if state["story"]["project_id"] != project["id"] or state["story"]["source_versions"] != self._sources(state):
            raise ValueError("프로젝트 또는 합성 원본 버전이 계약과 다릅니다.")
        return {}

    def _evaluate_story(self, state):
        self._activity(state, "evaluator", "story", "독립 검토 역할이 입력 보존과 비트 순서를 확인하고 있습니다.")
        context = {**state, "source_versions": self._sources(state, ("story", state["story"])),
                   "character_package": self.get_project(state["project_id"])["character_package"]}
        evaluation, issues = self._evaluation(state, "story_evaluation", "story_evaluator", context, evaluate_story(state["story"], state))
        blockers = [issue for issue in issues if issue["severity"] == "blocker"]
        rewrites = state.get("automatic_rewrites", 0)
        if evaluation["recommendation"] != "blocked" and (blockers or evaluation["recommendation"] == "revise") and rewrites < self.MAX_AUTOMATIC_REWRITES:
            # Creative reruns receive a new immutable version within a finite loop.
            return {"issues": issues, "automatic_rewrites": rewrites + 1, "revision": state["revision"] + 1000,
                    "feedback": evaluation["feedback"] or "형식 검사 보완: " + "; ".join(issue["message"] for issue in blockers), "route": "story"}
        if evaluation["recommendation"] in ("revise", "blocked"):
            issues = self._issues(state, [{**issue, "id": issue["id"]} for issue in issues] + [{"severity": "blocker", "stage": "story", "code": "evaluation_needs_human", "message": "독립 평가의 수정 요구가 남았습니다. 자동 재작성 한도를 넘어 사람이 수정 방향을 결정해야 합니다."}])
        return {"issues": issues, "route": "story_review"}

    def _format(self, state):
        self._activity(state, "storyboard_planner", "format", "확인한 이야기에 맞춰 컷 형식과 읽기 순서를 제안합니다.")
        count = len(state["story"]["beats"])
        proposal = FormatProposal.model_validate({**self._metadata(state, "format", self._sources(state, ("story", state["story"]))),
            "story_version": state["story"]["version"], "selected_format": "single_panel" if count == 1 else "multi_panel", "cut_count": count,
            "rationale": f"확인한 이야기의 {count}개 비트를 각 컷에 연결하는 합성 형식 fixture입니다.", "text_mode": "overlay"}).model_dump()
        proposal = self._archive(state["run_id"], "format_proposal", proposal, "이야기 확인 후 형식 제안")
        self._patch(state["run_id"], issues=[])
        return {"format_proposal": proposal, "issues": []}

    def _board(self, state):
        self._activity(state, "storyboard_planner", "storyboard", "확인한 이야기와 형식을 컷별 연출 데이터에 연결합니다.")
        context = {"story": state["story"], "format_proposal": state["format_proposal"],
            "metadata": self._metadata(state, "storyboard", self._sources(state, ("story", state["story"]), ("format", state["format_proposal"]))),
            "previous": state.get("storyboard"), "feedback": state.get("feedback", ""), "target_ids": state.get("target_ids", []),
            "character_package": self.get_project(state["project_id"])["character_package"]}
        board = self._cached_artifact(state, "storyboard") or self._provider_call(state, "storyboard", context)
        from .studio_contracts import StoryboardArtifact
        board = StoryboardArtifact.model_validate(board).model_dump()
        expected_sources = context["metadata"]["source_versions"]
        if (board["project_id"] != state["project_id"] or board["content_id"] != state["run_id"] or
                board["source_versions"] != expected_sources or board["story_version"] != state["story"]["version"] or
                board["format_version"] != state["format_proposal"]["version"]):
            raise ValueError("콘티 원본과 프로젝트·이야기·형식 버전이 정확한 입력과 다릅니다.")
        board = self._archive(state["run_id"], "storyboard", board, "시각 콘티 구현 전의 개발용 컷 데이터")
        return {"storyboard": board, "previous_storyboard": state.get("storyboard")}

    def _evaluate_board(self, state):
        self._activity(state, "evaluator", "storyboard", "컷별 이야기 연결·원본 버전·텍스트 모드·시각 콘티 준비 상태를 검사합니다.")
        context = {"story": state["story"], "format_proposal": state["format_proposal"], "storyboard": state["storyboard"],
                   "source_versions": self._sources(state, ("storyboard", state["storyboard"])),
                   "character_package": self.get_project(state["project_id"])["character_package"]}
        evaluation, issues = self._evaluation(state, "board_evaluation", "board_evaluator", context,
                                             evaluate_board(state["storyboard"], state["story"], state["format_proposal"],
                                                            state.get("previous_storyboard"), state.get("feedback", ""), state.get("target_ids")))
        rewrites = state.get("automatic_rewrites", 0)
        if evaluation["recommendation"] == "revise" and rewrites < self.MAX_AUTOMATIC_REWRITES:
            return {"issues": issues, "automatic_rewrites": rewrites + 1, "revision": state["revision"] + 1000,
                    "feedback": evaluation["feedback"], "route": "board"}
        if evaluation["recommendation"] in ("revise", "blocked"):
            issues = self._issues(state, issues + [{"severity": "blocker", "stage": "storyboard", "code": "evaluation_needs_human", "message": "독립 평가의 콘티 수정 요구가 남았습니다. 자동 수정 한도 이후 사람이 결정해야 합니다."}])
        return {"issues": issues, "route": "board_review"}

    def _review(self, state, stage):
        kind, action, gate = {"story": ("story", "approve_story", "G1"), "format": ("format_proposal", "approve_format", "FORMAT"),
                              "storyboard": ("storyboard", "approve_storyboard", "TECHNICAL_BOARD")}[stage]
        artifact = state[kind]
        blockers = [issue for issue in state.get("issues", []) if issue["severity"] == "blocker"]
        pending = {"stage": stage, "action": action, "artifact_id": artifact["artifact_id"], "version": artifact["version"]}
        self._patch(state["run_id"], status="blocked" if blockers else "awaiting_review", current_stage=stage, current_role="human",
                    summary="합성 기술 흐름을 확인할 수 있습니다. 시각 콘티·창작 품질은 미검증입니다." if stage == "storyboard" else "결과를 확인하고 수정하거나 다음 단계로 이어가세요.", pending_action=action)
        response = interrupt(pending)
        if response["stage"] != stage or response["artifact_version"] != artifact["version"]:
            raise StudioConflict("확인하려는 산출물 버전이 현재 대기 중인 버전과 다릅니다.")
        action_name = response["action"]
        if action_name == "reject":
            self._patch(state["run_id"], status="stopped", current_role="orchestrator", pending_action=None, summary="사용자가 작업을 중단했습니다. 결과와 이력은 보존됩니다.")
            return {"route": "stop", "revision": response["revision"]}
        if action_name in ("revise_story", "revise_storyboard"):
            self._invalidate(state["run_id"], "story" if action_name == "revise_story" else "storyboard")
            return {"route": "story" if action_name == "revise_story" else "board", "revision": response["revision"],
                    "feedback": response["feedback"], "target_ids": response["target_ids"], "automatic_rewrites": 0}
        if action_name != action or blockers:
            raise StudioConflict("해결되지 않은 blocker가 있거나 현재 단계에 맞지 않는 확인입니다.")
        self._approve(state["run_id"], gate, artifact)
        if stage == "storyboard":
            self._patch(state["run_id"], status="completed", technical_review_complete=True, pending_action=None, summary="합성 기술 흐름 검토 완료 · 시각 콘티/창작 품질 미검증")
        return {"route": {"story": "format", "format": "board", "storyboard": "stop"}[stage],
                "revision": response["revision"], "feedback": "", "target_ids": []}

    def _invalidate(self, rid, stage):
        run = self._raw(rid)
        kinds = ("story", "format_proposal", "storyboard") if stage == "story" else ("storyboard",)
        old = [run[k]["artifact_id"] for k in kinds if run.get(k)]
        # Approval records are immutable audit facts; current approval status derives from current exact artifact versions.
        self._event(rid, "orchestrator", stage, "수정으로 이후 단계의 현재 승인 효력이 해제되었습니다. 이전 산출물과 확인 기록은 보존합니다.")
        self._patch(rid, _invalidated_artifact_ids=old, technical_review_complete=False)

    def _approve(self, rid, gate, artifact):
        run = self._raw(rid)
        if not any(a["gate"] == gate and a["version"] == artifact["version"] and a["artifact_id"] == artifact["artifact_id"] for a in run["approvals"]):
            run["approvals"].append({"id": new_id("approval"), "gate": gate, "project_id": run["project_id"], "run_id": rid,
                                    "artifact_id": artifact["artifact_id"], "version": artifact["version"], "at": now(), "actor": "human", "scope": "synthetic_technical_review"})
            self._save(run)
            self._event(rid, "human", run["current_stage"], f"{gate}에서 정확한 버전 {artifact['version']}을 합성 기술 검토 범위로 확인했습니다.")

    def _build_graph(self):
        builder = StateGraph(GraphState)
        nodes = {"story": self._story, "validator": self._validate_story, "story_evaluator": self._evaluate_story,
                 "story_review": lambda s: self._review(s, "story"), "format": self._format,
                 "format_review": lambda s: self._review(s, "format"), "board": self._board,
                 "board_evaluator": self._evaluate_board, "board_review": lambda s: self._review(s, "storyboard")}
        for name, node in nodes.items():
            builder.add_node(name, node)
        builder.add_conditional_edges(START, lambda s: s.get("entry", "story"), {"story": "story", "format": "format", "board": "board"})
        builder.add_edge("story", "validator")
        builder.add_edge("validator", "story_evaluator")
        builder.add_conditional_edges("story_evaluator", lambda s: s["route"], {"story": "story", "story_review": "story_review"})
        routes = {"story": "story", "board": "board", "format": "format", "stop": END}
        for node in ("story_review", "format_review", "board_review"):
            builder.add_conditional_edges(node, lambda s: s["route"], routes)
        builder.add_edge("format", "format_review")
        builder.add_edge("board", "board_evaluator")
        builder.add_conditional_edges("board_evaluator", lambda s: s["route"], {"board": "board", "board_review": "board_review"})
        return builder.compile(checkpointer=self.checkpointer)

    def create_project(self, request: ProjectBrief):
        pid = new_id("project")
        sources = [{"project_id": pid, "artifact_id": f"{pid}-{role}", "version": "1.0.0", "role": role}
                   for role in ("project_brief", "reference_fixture", "character_fixture", "series_fixture")]
        project = Project.model_validate({**request.model_dump(), "id": pid, "created_at": now(), "fixture_versions": sources,
            "references": [{"id": f"{pid}-reference_fixture", "project_id": pid, "version": "1.0.0", "purpose": "story", "observations": ["개발용 합성 입력만 사용"], "not_to_copy": ["실제 작품·캐릭터·브랜드"], "permission_status": "synthetic_fixture"}],
            "character_package": {"id": f"{pid}-character_fixture", "project_id": pid, "version": "1.0.0", "identity_invariants": ["이름 없는 합성 주인공"], "behavior_and_voice": ["개발용 행동·목소리 fixture"], "sheet_artifact_id": f"{pid}-sheet-fixture", "sheet_status": "fixture", "approval_status": "synthetic_fixture"},
            "series_package": {"id": f"{pid}-series_fixture", "project_id": pid, "version": "1.0.0", "direction": request.series_direction, "editorial_filters": ["합성 기술 검증"], "supported_formats": ["single_panel", "multi_panel"], "approval_status": "synthetic_fixture"}}).model_dump()
        with self._db_lock:
            self.db.execute("INSERT INTO projects VALUES(?,?)", (pid, self._dump(project)))
            self.db.commit()
        return project

    def get_project(self, pid):
        with self._db_lock:
            row = self.db.execute("SELECT payload FROM projects WHERE id=?", (pid,)).fetchone()
        if not row:
            raise KeyError(pid)
        try:
            project = Project.model_validate(json.loads(row[0]))
            if project.id != pid:
                raise ValueError("프로젝트 등록 ID가 계약의 ID와 다릅니다.")
            return project.model_dump()
        except ValueError:
            # Stored records may include supplied material. Never expose Pydantic input details.
            raise ValueError("저장된 프로젝트 계약이 현재 앱과 호환되지 않습니다.") from None

    def list_projects(self):
        with self._db_lock:
            ids = [row[0] for row in self.db.execute("SELECT id FROM projects ORDER BY rowid DESC").fetchall()]
        return [self.get_project(pid) for pid in ids]

    def get_run(self, pid, rid):
        run = self._raw(rid)
        if run["project_id"] != pid:
            raise KeyError(rid)
        with self._db_lock:
            run["events"] = [json.loads(row[0]) for row in self.db.execute("SELECT payload FROM events WHERE run_id=? ORDER BY id", (rid,)).fetchall()]
            run["versions"] = [json.loads(row[0]) for row in self.db.execute("SELECT payload FROM versions WHERE run_id=? ORDER BY rowid", (rid,)).fetchall()]
            run["evaluations"] = [v["artifact"] for v in run["versions"] if v["kind"] in ("story_evaluation", "board_evaluation")]
        run["retry_available"] = run["status"] == "stopped" or (run["status"] == "blocked" and run.get("_failed", False))
        try:
            validated = Run.model_validate({k: v for k, v in run.items() if not k.startswith("_")})
            if validated.id != rid:
                raise ValueError("작업 등록 ID가 계약의 ID와 다릅니다.")
            return validated.model_dump()
        except ValueError:
            raise ValueError("저장된 작업 계약이 현재 앱과 호환되지 않습니다.") from None

    def list_runs(self, pid):
        self.get_project(pid)
        with self._db_lock:
            ids = [row[0] for row in self.db.execute("SELECT id FROM runs WHERE project_id=? ORDER BY rowid DESC", (pid,)).fetchall()]
        return [self.get_run(pid, rid) for rid in ids]

    def create_run(self, pid, request: RunInput):
        self.get_project(pid)
        rid = new_id("run")
        run = Run(id=rid, project_id=pid, revision=1, created_at=now(), **request.model_dump(), status="queued", current_stage="story",
            current_role="orchestrator", summary="이야기 작업을 준비하고 있습니다.", provider=self.provider.name,
            capabilities=["역할별 실행 상태", "정확한 버전 확인", "SQLite 체크포인트 재개", "범위별 수정", "원본·수정 이력 보존"],
            limitations=["합성 기술 검증만 허용", "전용 캐릭터 창작·시트 단계 미구현", "시각 콘티와 이미지 생성 미구현", "개발용 fixture를 완성된 AI 창작물로 승인할 수 없음", "v2 작업의 암호화 백업·멀티 PC 이동 미구현"]).model_dump()
        run.update({"_thread_id": rid, "_initial": {"run_id": rid, "project_id": pid, "idea": request.idea, "input_kind": request.input_kind,
                    "revision": 1, "automatic_rewrites": 0, "issues": []}, "_command": None})
        self._save(run)
        self._event(rid, "orchestrator", "story", "합성 이야기 작업을 생성했습니다. 창작 품질 검증은 별도입니다.")
        self._launch(rid)
        return self.get_run(pid, rid)

    def action(self, pid, rid, request: ActionInput):
        initial = self.get_run(pid, rid)
        if initial["status"] in ("running", "queued") and request.action == "reject":
            # The worker owns the run lock while executing; stop must not wait for a model response.
            with self._db_lock:
                raw = self._raw(rid)
                if raw["revision"] != request.expected_revision:
                    raise StudioConflict("결과가 갱신됐습니다. 현재 버전을 다시 확인해주세요.")
                if request.target_ids:
                    raise StudioConflict("중단 요청에는 컷 대상을 지정하지 않습니다.")
                raw.update(revision=raw["revision"] + 1, status="stopped", current_role="orchestrator", pending_action=None,
                           summary="중단 요청을 반영했습니다. 현재 호출이 반환되면 다음 역할을 실행하지 않습니다.", _cancel_requested=True, _command=None)
                self._save(raw)
                self._event(rid, "human", raw["current_stage"], "실행 중 작업을 중단했습니다." + (f" · {request.feedback}" if request.feedback else ""))
            return self.get_run(pid, rid)
        if initial["status"] in ("running", "queued"):
            raise StudioConflict("현재 작업이 진행 중입니다.")
        with self._lock_for(rid):
            run = self.get_run(pid, rid)
            if run["revision"] != request.expected_revision:
                raise StudioConflict("결과가 갱신됐습니다. 현재 버전을 다시 확인해주세요.")
            if run["status"] in ("running", "queued"):
                raise StudioConflict("현재 작업이 진행 중입니다.")
            action = request.action
            stage = run["current_stage"]
            if request.target_ids:
                valid = {p["id"] for p in (run["storyboard"] or {}).get("panels", [])}
                if action != "revise_storyboard" or len(set(request.target_ids)) != len(request.target_ids) or not set(request.target_ids) <= valid:
                    raise StudioConflict("현재 프로젝트·콘티에 없는 컷을 수정할 수 없습니다.")
            if action.startswith("revise_") and not request.feedback.strip():
                raise StudioConflict("바꿀 내용을 짧게 적어주세요.")
            if action == "revise_storyboard" and (stage != "storyboard" or not run["storyboard"]):
                raise StudioConflict("콘티가 나온 후 컷을 수정할 수 있습니다.")
            if action.startswith("approve_"):
                if run["pending_action"] != action or any(i["severity"] == "blocker" for i in run["issues"]):
                    raise StudioConflict("현재 단계의 blocker를 해결한 후 확인할 수 있습니다.")
            forked_rework = run["status"] == "completed"
            if forked_rework:
                if action not in ("revise_story", "revise_storyboard"):
                    raise StudioConflict("검토를 마친 작업은 수정 요청으로 새 버전을 만들 수 있습니다.")
                self._prepare_completed_rework(rid, run, request)
                stage = "story" if action == "revise_story" else "storyboard"
            elif action == "retry":
                if run["status"] not in ("stopped", "blocked") or not (self._raw(rid).get("_failed") or run["status"] == "stopped"):
                    raise StudioConflict("재시도할 실행 오류가 없습니다. 수정 요청으로 결과를 바꿔주세요.")
                self._prepare_retry(rid, run)
            elif run["status"] == "stopped" or not run["pending_action"]:
                raise StudioConflict("중단된 작업은 명시적인 재시도가 필요합니다.")
            raw = self._raw(rid)
            raw["revision"] += 1
            if action != "retry" and not forked_rework:
                kind = {"story": "story", "format": "format_proposal", "storyboard": "storyboard"}[stage]
                raw["_command"] = {**request.model_dump(), "stage": stage, "revision": raw["revision"], "artifact_version": run[kind]["version"]}
            raw.update(status="queued", current_stage=stage, pending_action=None, current_role="orchestrator", summary="요청한 작업을 이어가고 있습니다.")
            self._save(raw)
            self._event(rid, "human", stage, f"요청: {action}" + (f" · {request.feedback}" if request.feedback else ""))
        self._launch(rid)
        return self.get_run(pid, rid)

    def _prepare_completed_rework(self, rid, run, request):
        # A terminal graph cannot consume another interrupt response. Fork its exact frozen state.
        raw = self._raw(rid)
        snapshot = self.graph.get_state(self._config(raw))
        state = dict(snapshot.values)
        if not state.get("story") or (request.action == "revise_storyboard" and not state.get("storyboard")):
            raise StudioConflict("수정할 검토 완료 버전을 찾을 수 없습니다.")
        stage = "story" if request.action == "revise_story" else "storyboard"
        state.update(revision=run["revision"] + 1, entry="story" if stage == "story" else "board",
                     feedback=request.feedback, target_ids=request.target_ids, automatic_rewrites=0)
        self._invalidate(rid, stage)
        self._patch(rid, _thread_id=new_id(rid), _initial=state, _command=None, _failed=False, _cancel_requested=False)

    def _prepare_retry(self, rid, run):
        raw = self._raw(rid)
        if run["status"] == "stopped":
            snapshot = self.graph.get_state(self._config(raw))
            state = dict(snapshot.values)
            state.update(revision=run["revision"] + 1, entry={"story": "story", "format": "format", "storyboard": "board"}[run["current_stage"]], feedback="", target_ids=[], automatic_rewrites=0)
            self._patch(rid, _thread_id=new_id(rid), _initial=state, _command=None, _failed=False, _cancel_requested=False)
        else:
            self._patch(rid, _command=None, _failed=False, _cancel_requested=False)

    def _config(self, raw):
        return {"configurable": {"thread_id": raw["_thread_id"]}, "recursion_limit": self.MAX_NODES}

    def _launch(self, rid):
        if self.background:
            self._futures[rid] = self._executor.submit(self._drive, rid)
        else:
            self._drive(rid)

    def wait(self, rid, timeout=10):
        future = self._futures.get(rid)
        if future:
            future.result(timeout=timeout)

    def _drive(self, rid):
        with self._lock_for(rid):
            if self._closed:
                return
            raw = self._raw(rid)
            if raw.get("_cancel_requested"):
                return
            self._patch(rid, _node_count=0, _deadline=time.monotonic() + self.MAX_SECONDS)
            try:
                self.get_run(raw["project_id"], rid)
                self.get_project(raw["project_id"])
                config = self._config(raw)
                snapshot = self.graph.get_state(config)
                if not snapshot.values:
                    value = raw["_initial"]
                elif raw.get("_command"):
                    current_interrupts = [i.value for task in snapshot.tasks for i in task.interrupts]
                    command = raw["_command"]
                    if current_interrupts and current_interrupts[0]["stage"] == command["stage"] and current_interrupts[0]["version"] == command["artifact_version"]:
                        value = Command(resume=command)
                    else:
                        # A crash may occur after command checkpointing; continue committed work without reapplying it.
                        value = None
                else:
                    value = None
                # Environment-wide tracing opt-ins must not upload local project data.
                with tracing_context(enabled=False):
                    self.graph.invoke(value, config)
                    if value is None and raw.get("_command"):
                        # Projection can reach review just before its interrupt checkpoint is written.
                        # Establish that checkpoint first, then deliver the still-unconsumed exact command.
                        reached = self.graph.get_state(config)
                        pending = [i.value for task in reached.tasks for i in task.interrupts]
                        command = raw["_command"]
                        if pending and pending[0]["stage"] == command["stage"] and pending[0]["version"] == command["artifact_version"]:
                            self.graph.invoke(Command(resume=command), config)
                self._patch(rid, _command=None, _failed=False)
                self._event(rid, "orchestrator", self._raw(rid)["current_stage"], "체크포인트를 저장했습니다. 사용자 확인 지점에서 대기합니다." if self._raw(rid)["pending_action"] else "작업 상태를 저장했습니다.")
            except RunStopped:
                self._patch(rid, status="stopped", current_role="orchestrator", summary="사용자 중단 요청에 따라 이후 역할 실행을 멈췄습니다.", pending_action=None, _failed=False, _command=None)
                self._event(rid, "orchestrator", self._raw(rid)["current_stage"], "현재 호출 이후 실행을 중단했습니다. 명시적인 재시도가 필요합니다.")
            except Exception as error:
                # Internal exception text stays local; the API reports an actionable bounded failure.
                self._patch(rid, status="blocked", current_role="orchestrator", summary="작업 실행에 실패했습니다. 이전 결과를 보존했으며 이 단계만 재시도할 수 있습니다.", pending_action=None,
                            _failed=True, _error=f"{type(error).__name__}: {error}")
                self._event(rid, "orchestrator", self._raw(rid)["current_stage"], f"실행 오류: {type(error).__name__}. 자동 전체 재실행을 중단했습니다.")


def create_studio_router(root: Path):
    service = StudioService(root)
    router = APIRouter(prefix="/api/studio")
    router.service = service

    def call(function, *args):
        try:
            return function(*args)
        except KeyError:
            raise HTTPException(404, "현재 프로젝트의 작업을 찾을 수 없습니다.") from None
        except StudioConflict as error:
            raise HTTPException(409, str(error)) from None
        except ValueError:
            raise HTTPException(409, "저장된 데이터 계약이 현재 앱과 호환되지 않습니다. 원본은 보존했습니다.") from None

    @router.get("/projects")
    def projects():
        return {"projects": call(service.list_projects)}

    @router.post("/projects", status_code=201)
    def create_project(request: ProjectBrief):
        return service.create_project(request)

    @router.get("/projects/{pid}")
    def project(pid: str):
        selected = call(service.get_project, pid)
        runs = call(service.list_runs, pid)
        return {"project": selected, "runs": runs, "current_run": runs[0] if runs else None}

    @router.post("/projects/{pid}/runs", status_code=202)
    def create_run(pid: str, request: RunInput):
        return call(service.create_run, pid, request)

    @router.get("/projects/{pid}/runs/{rid}")
    def run(pid: str, rid: str):
        return call(service.get_run, pid, rid)

    @router.post("/projects/{pid}/runs/{rid}/actions", status_code=202)
    def action(pid: str, rid: str, request: ActionInput):
        return call(service.action, pid, rid, request)

    return router
