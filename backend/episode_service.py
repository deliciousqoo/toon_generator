"""Durable, human-gated episode orchestration pinned to one approved character."""
import base64
import copy
import hashlib
import io
import json
import os
import re
import sqlite3
import threading
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from langsmith import tracing_context

from .character_visuals import VisualConflict, normalize_image
from .episode_contracts import (BoardDraft, CreateEpisodeRequest, DecisionRequest, EpisodeState,
    Evaluation, FormatRequest, IntakeDraft, Panel, Request, RoughJobRequest, RoughUploadRequest, StoryDraft, TurnRequest)
from .character_contracts import CharacterBrief, CharacterSheet, ImageProvenance, VisualAsset
from .episode_workers import FixtureEpisodeProvider, SubscriptionEpisodeProvider


def dump(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(dump(value).encode()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix):
    return f"{prefix}-{uuid.uuid4().hex}"


class EpisodeConflict(Exception):
    pass


class GraphState(TypedDict, total=False):
    project_id: str
    episode_id: str
    request_id: str
    draft: dict
    evaluation: dict
    issues: list[dict]


class EpisodeService:
    MAX_CALLS = 40

    def __init__(self, root, characters, provider=None):
        self.root = Path(root) / "studio" / "episodes"
        self.root.mkdir(parents=True, exist_ok=True)
        self.characters = characters
        self.provider = provider or (FixtureEpisodeProvider() if characters.provider.fixture else SubscriptionEpisodeProvider(characters.provider))
        self._db_lock, self._locks_lock = threading.RLock(), threading.Lock()
        self._locks = {}
        self.db = sqlite3.connect(self.root / "episodes.sqlite3", check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS episodes(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS episode_operations(project_id TEXT NOT NULL,episode_id TEXT NOT NULL,request_id TEXT NOT NULL,kind TEXT NOT NULL,request_hash TEXT NOT NULL,status TEXT NOT NULL,payload TEXT NOT NULL,PRIMARY KEY(project_id,request_id));
        """)
        self.db.commit()
        self.checkpoint_db = sqlite3.connect(self.root / "checkpoints.sqlite3", check_same_thread=False)
        self.checkpointer = SqliteSaver(self.checkpoint_db)
        self.checkpointer.setup()
        self.graph = self._build_graph()
        # A process cannot know whether an interrupted remote call completed.
        # Keep drafts/counters, release the operation only for a new explicit request.
        for pid, eid, rid, raw in self.db.execute("SELECT project_id,episode_id,request_id,payload FROM episode_operations WHERE status='pending'").fetchall():
            op = json.loads(raw)
            state = self._raw(pid, eid)
            state["revision"] += 1
            state.update(status="blocked", pending_action=None,
                issues=[{"code": "episode_interrupted", "severity": "blocker", "message": "이전 작업이 중단되었습니다. 완료 여부를 알 수 없는 모델은 자동 재호출하지 않았습니다.", "target_id": None}])
            self._save(state)
            op["response"] = state
            self.db.execute("UPDATE episode_operations SET status='interrupted',payload=? WHERE project_id=? AND request_id=?", (dump(op), pid, rid))
        self.db.commit()

    def close(self):
        self.checkpoint_db.close()
        self.db.close()

    def _lock_for(self, eid):
        with self._locks_lock:
            return self._locks.setdefault(eid, threading.RLock())

    def _raw(self, pid, eid):
        with self._db_lock:
            row = self.db.execute("SELECT project_id,payload FROM episodes WHERE id=?", (eid,)).fetchone()
        if not row or row[0] != pid:
            raise KeyError(eid)
        state = EpisodeState.model_validate(json.loads(row[1])).model_dump()
        if state["project_id"] != pid or state["id"] != eid or state["character_snapshot"]["project_id"] != pid:
            raise EpisodeConflict("이야기와 캐릭터의 프로젝트 경계가 맞지 않습니다.")
        self._validate_state(state)
        return state

    def _validate_state(self, state):
        """Persisted nested dictionaries remain a strict, same-project contract."""
        pid, eid, snapshot = state["project_id"], state["id"], state["character_snapshot"]
        try:
            if set(snapshot) != {"project_id", "direction", "sheet", "assets", "approval", "fingerprint"}:
                raise ValueError("snapshot keys")
            direction = CharacterBrief.model_validate(snapshot["direction"])
            sheet = CharacterSheet.model_validate(snapshot["sheet"])
            assets = [VisualAsset.model_validate(a) for a in snapshot["assets"]]
            if direction.project_id != pid or sheet.project_id != pid or any(a.project_id != pid for a in assets) or sheet.direction_version != direction.version:
                raise ValueError("snapshot boundary")
            asset_ids = {a.id for a in assets}
            if len(asset_ids) != len(assets) or set(sheet.components.values()) - asset_ids:
                raise ValueError("snapshot assets")
            if any(set(a.source_asset_ids) - asset_ids for a in assets):
                raise ValueError("snapshot source closure")
            if snapshot["approval"].get("kind") != "sheet_confirm" or snapshot["approval"].get("sheet_version") != sheet.version or snapshot["approval"].get("actor") != "human":
                raise ValueError("snapshot approval")
            if digest({k: v for k, v in snapshot.items() if k != "fingerprint"}) != snapshot["fingerprint"]:
                raise ValueError("snapshot hash")
            history = {}
            metadata_keys = {"artifact_id", "version", "project_id", "episode_id", "snapshot_fingerprint"}
            for record in state["versions"]:
                kind, artifact = record["kind"], record["artifact"]
                if kind not in ("story", "format", "storyboard"):
                    raise ValueError("artifact kind")
                if artifact["project_id"] != pid or artifact["episode_id"] != eid or artifact["snapshot_fingerprint"] != snapshot["fingerprint"] or artifact["artifact_id"] != f"{eid}-{kind}":
                    raise ValueError("artifact boundary")
                expected = f"1.0.{len(history.setdefault(kind, {})) + 1}"
                if artifact["version"] != expected:
                    raise ValueError("artifact lineage")
                if kind in ("story", "storyboard"):
                    contract = StoryDraft if kind == "story" else BoardDraft
                    extra = {"story_version", "format_version"} if kind == "storyboard" else set()
                    contract.model_validate({k: v for k, v in artifact.items() if k not in metadata_keys | extra}, strict=True)
                    if kind == "storyboard" and (artifact["story_version"] not in history.get("story", {}) or artifact["format_version"] not in history.get("format", {})):
                        raise ValueError("board source versions")
                elif (set(artifact) != metadata_keys | {"story_version", "cut_count", "layout", "text_mode", "rationale"}
                        or artifact["story_version"] not in history.get("story", {}) or type(artifact["cut_count"]) is not int
                        or not 1 <= artifact["cut_count"] <= 8 or artifact["layout"] not in ("single_panel", "vertical_grid") or artifact["text_mode"] != "overlay"):
                    raise ValueError("format source")
                history[kind][artifact["version"]] = artifact
            for kind in ("story", "format", "storyboard"):
                current = state[kind]
                if current and history.get(kind, {}).get(current["version"]) != current:
                    raise ValueError("current artifact changed")
            for evaluation in state["evaluations"]:
                value = Evaluation.model_validate(evaluation)
                if value.project_id != pid or value.episode_id != eid or value.snapshot_fingerprint != snapshot["fingerprint"]:
                    raise ValueError("evaluation boundary")
            preceding = set(asset_ids)
            rough_ids = set()
            for asset in state["rough_assets"]:
                ImageProvenance.model_validate(asset["provenance"])
                self._rough_asset(state, asset["id"])
                if asset["id"] in rough_ids or set(asset["source_asset_ids"]) - preceding or not re.fullmatch(r"[a-f0-9]{64}", asset["sha256"]):
                    raise ValueError("rough source lineage")
                if asset["board_version"] not in history.get("storyboard", {}):
                    raise ValueError("rough board source")
                source_panel = next((p for p in history["storyboard"][asset["board_version"]]["panels"] if p["id"] == asset["panel_id"]), None)
                if not source_panel or self._visual_fingerprint(source_panel) != asset["panel_fingerprint"]:
                    raise ValueError("rough panel source")
                rough_ids.add(asset["id"])
                preceding.add(asset["id"])
            job_ids = set()
            for job in state["rough_jobs"]:
                if job["id"] in job_ids or not re.fullmatch(r"rough-job-[a-f0-9]{32}", job["id"]) or job["snapshot_fingerprint"] != snapshot["fingerprint"] or set(job["source_asset_ids"]) - preceding or job["status"] not in ("awaiting_image", "completed", "cancelled"):
                    raise ValueError("rough job boundary")
                if job["board_version"] not in history.get("storyboard", {}):
                    raise ValueError("rough job board")
                panel = next((p for p in history["storyboard"][job["board_version"]]["panels"] if p["id"] == job["panel_id"]), None)
                if not panel or self._visual_fingerprint(panel) != job["panel_fingerprint"]:
                    raise ValueError("rough job panel")
                if (job["status"] == "completed") != (job.get("asset_id") in rough_ids):
                    raise ValueError("rough completed image")
                job_ids.add(job["id"])
            for asset in state["rough_assets"]:
                job = next(j for j in state["rough_jobs"] if j["id"] == asset["job_id"])
                if job.get("asset_id") != asset["id"] or job["source_asset_ids"] != asset["source_asset_ids"]:
                    raise ValueError("rough job lineage")
            panels = {p["id"]: p for p in (state["storyboard"] or {}).get("panels", [])}
            for panel_id, aid in state["roughs"].items():
                asset = self._rough_asset(state, aid)
                if panel_id not in panels or asset["panel_id"] != panel_id or asset["panel_fingerprint"] != self._visual_fingerprint(panels[panel_id]):
                    raise ValueError("current rough source")
            for key, kind in (("confirmed_story_version", "story"), ("confirmed_format_version", "format"), ("approved_board_version", "storyboard")):
                if state[key] and state[key] != (state[kind] or {}).get("version"):
                    raise ValueError("current confirmation")
                action = {"story": "confirm_story", "format": "confirm_format", "storyboard": "confirm_board"}[kind]
                if state[key] and not any(d.get("action") == action and d.get("version") == state[key] and d.get("actor") == "human" and d.get("snapshot_fingerprint") == snapshot["fingerprint"] for d in state["decisions"]):
                    raise ValueError("missing human decision")
            if state["usable_storyboard"] != bool(state["approved_board_version"]):
                raise ValueError("G2 state")
            if state["usable_storyboard"]:
                self._assert_board_sources(state)
                if state["fixture"] or set(state["roughs"]) != set(panels) or any(self._rough_asset(state, aid)["provenance"]["fixture"] for aid in state["roughs"].values()):
                    raise ValueError("G2 rough completeness")
        except (ValueError, KeyError, TypeError, StopIteration) as error:
            raise EpisodeConflict("저장된 이야기의 프로젝트·버전·원본 계약을 확인하지 못했습니다. 원본은 보존했습니다.") from error

    def _save(self, state, *, commit=True):
        state = EpisodeState.model_validate(state).model_dump()
        self._validate_state(state)
        with self._db_lock:
            self.db.execute("INSERT OR REPLACE INTO episodes VALUES(?,?,?)", (state["id"], state["project_id"], dump(state)))
            if commit:
                self.db.commit()

    def _snapshot(self, pid):
        package = self.characters.approved_visual_package(pid)
        state, sheet = package["state"], package["sheet"]
        selected = next(c for c in state["visuals"]["candidates"] if {"candidate_id": c["candidate_id"], "version": c["version"]} == sheet["candidate_ref"])
        ids = {*sheet["components"].values(), selected["asset_id"]}
        pending = list(ids)
        while pending:
            asset = self.characters._visual_asset(state, pending.pop())
            for source in asset["source_asset_ids"]:
                if source not in ids:
                    ids.add(source)
                    pending.append(source)
        assets = [copy.deepcopy(a) for a in state["visuals"]["assets"] if a["id"] in ids]
        for asset in assets:
            self.characters._read_visual_asset(state, asset["id"])
        approval = next(d for d in reversed(state["visuals"]["decisions"]) if d["kind"] == "sheet_confirm" and d["sheet_version"] == sheet["version"])
        result = {"project_id": pid, "direction": copy.deepcopy(state["brief"]), "sheet": copy.deepcopy(sheet), "assets": assets, "approval": copy.deepcopy(approval)}
        result["fingerprint"] = digest(result)
        return result

    def _assert_current(self, state):
        from .character_service import CharacterConflict, CharacterNotFound
        pinned = state["character_snapshot"]
        if digest({k: v for k, v in pinned.items() if k != "fingerprint"}) != pinned["fingerprint"]:
            raise EpisodeConflict("저장된 캐릭터 스냅샷의 체크섬이 맞지 않습니다.")
        try:
            current = self._snapshot(state["project_id"])
        except (VisualConflict, CharacterConflict, CharacterNotFound, ValueError, KeyError) as error:
            raise EpisodeConflict("캐릭터 시트 승인이나 이미지가 바뀌었습니다. 기존 이야기는 보존했습니다. 캐릭터 시트를 먼저 확인해 주세요.") from error
        if current["fingerprint"] != pinned["fingerprint"]:
            raise EpisodeConflict("캐릭터 시트가 이야기의 기준 버전과 달라졌습니다. 기존 이야기는 보존했으며 새 시트로는 새 이야기를 시작해 주세요.")

    def _project_calls(self, pid):
        with self.characters._db_lock:
            row = self.characters.db.execute("SELECT calls FROM character_provider_budget WHERE id=?", (f"chatgpt_subscription:{pid}",)).fetchone()
        return row[0] if row else 0

    def _public(self, state):
        state = EpisodeState.model_validate(state).model_dump()
        self._validate_state(state)
        result = copy.deepcopy(state)
        result["project_calls_used"] = self._project_calls(state["project_id"])
        result["mutation_blocked"] = None
        try:
            self._assert_current(state)
        except EpisodeConflict as error:
            result["mutation_blocked"] = str(error)
        return EpisodeState.model_validate(result).model_dump()

    def get_state(self, pid, eid):
        return self._public(self._raw(pid, eid))

    def list_episodes(self, pid):
        self.characters.get_state(pid)
        with self._db_lock:
            ids = [r[0] for r in self.db.execute("SELECT id FROM episodes WHERE project_id=? ORDER BY rowid DESC", (pid,)).fetchall()]
        return [self.get_state(pid, eid) for eid in ids]

    def _operation(self, pid, request_id):
        with self._db_lock:
            row = self.db.execute("SELECT episode_id,kind,request_hash,status,payload FROM episode_operations WHERE project_id=? AND request_id=?", (pid, request_id)).fetchone()
        if not row:
            return None
        result = {**json.loads(row[4]), "episode_id": row[0], "kind": row[1], "request_hash": row[2], "status": row[3]}
        if result["kind"] == "turn":
            try:
                base = EpisodeState.model_validate(result["base"]).model_dump()
                request = TurnRequest.model_validate(result["request"]).model_dump()
                self._validate_state(base)
                if base["project_id"] != pid or base["id"] != result["episode_id"] or request["request_id"] != request_id or request["expected_revision"] != base["revision"] or digest(request) != result["request_hash"] or result["version"] != self._next_version(base, request["stage"]):
                    raise ValueError("operation source")
            except (KeyError, ValueError, TypeError) as error:
                raise EpisodeConflict("보존된 대화의 프로젝트·요청·원본 범위를 확인하지 못해 실행을 중단했습니다.") from error
        return result

    def _replay(self, pid, eid, kind, request):
        op = self._operation(pid, request["request_id"])
        if not op:
            return None
        if op["episode_id"] != eid or op["kind"] != kind or op["request_hash"] != digest(request):
            raise EpisodeConflict("같은 요청 ID를 다른 입력이나 이야기에서 사용할 수 없습니다.")
        if op["status"] != "completed":
            raise EpisodeConflict("이전 요청이 중단되었거나 처리 중입니다. 자동으로 모델을 다시 호출하지 않습니다. 최신 결과에서 새 요청을 보내세요.")
        if op["response"].get("project_id") != pid or op["response"].get("id") != eid:
            raise EpisodeConflict("보존된 응답의 프로젝트나 이야기 경계가 맞지 않습니다.")
        return self._public(op["response"])

    def _save_op(self, pid, request_id, op):
        payload = {k: v for k, v in op.items() if k not in ("episode_id", "kind", "request_hash", "status")}
        self.db.execute("UPDATE episode_operations SET status=?,payload=? WHERE project_id=? AND request_id=?", (op["status"], dump(payload), pid, request_id))

    def create_episode(self, pid, request):
        request = CreateEpisodeRequest.model_validate(request).model_dump()
        with self._lock_for(pid), self.characters._lock_for(pid):
            previous = self._operation(pid, request["request_id"])
            if previous:
                return self._replay(pid, previous["episode_id"], "create", request)
            snapshot = self._snapshot(pid)
            if snapshot["direction"]["version"] != request["expected_direction_version"] or snapshot["sheet"]["version"] != request["expected_sheet_version"]:
                raise EpisodeConflict("현재 확인한 방향과 시트의 정확한 버전이 필요합니다.")
            state = EpisodeState(id=new_id("episode"), project_id=pid, title=request["title"], revision=0, created_at=now(),
                character_snapshot=snapshot, provider=self.provider.name, fixture=self.provider.fixture).model_dump()
            with self._db_lock, self.db:
                self._save(state, commit=False)
                self.db.execute("INSERT INTO episode_operations VALUES(?,?,?,?,?,?,?)", (pid, state["id"], request["request_id"], "create", digest(request), "completed", dump({"response": state})))
            return self._public(state)

    def _mutate(self, pid, eid, kind, request, mutate, binary=None):
        request = copy.deepcopy(request)
        if binary is not None:
            request["image_sha256"] = hashlib.sha256(binary).hexdigest()
        with self._lock_for(eid):
            replay = self._replay(pid, eid, kind, request)
            if replay is not None:
                return replay
            state = self._raw(pid, eid)
            if state["revision"] != request["expected_revision"]:
                raise EpisodeConflict("이야기가 바뀌었습니다. 최신 결과를 확인하고 다시 보내세요.")
            self._assert_current(state)
            mutate(state)
            with self.characters._lock_for(pid):
                self._assert_current(state)
                state["revision"] += 1
                with self._db_lock, self.db:
                    self._save(state, commit=False)
                    self.db.execute("INSERT INTO episode_operations VALUES(?,?,?,?,?,?,?)", (pid, eid, request["request_id"], kind, digest(request), "completed", dump({"response": state})))
            return self._public(state)

    def _identity(self):
        method = getattr(self.provider, "execution_identity", None)
        return method() if method else None

    def _context(self, op):
        state, request = op["base"], op["request"]
        stage = request["stage"]
        return {"project_id": state["project_id"], "episode_id": state["id"], "version": op["version"],
            "snapshot_fingerprint": state["character_snapshot"]["fingerprint"], "character_snapshot": state["character_snapshot"],
            "intent": state["intent"], "message": request["message"], "target_ids": request["target_ids"], "edit_fields": request["edit_fields"],
            "previous": state.get("story" if stage == "story" else "storyboard") if stage != "intent" else None,
            "story": state["story"], "format": state["format"], "dialogue": state["messages"][-20:], "_execution_identity": op["identity"]}

    def _config(self, eid, rid):
        return {"configurable": {"thread_id": "episode-" + digest([eid, rid])}, "recursion_limit": 8}

    def _call(self, pid, eid, rid, role, method, context):
        state = self._raw(pid, eid)
        self._assert_current(state)
        op = self._operation(pid, rid)
        if op["identity"] != self._identity():
            raise EpisodeConflict("ChatGPT 연결이나 모델이 바뀌었습니다. 현재 결과에서 새 요청을 보내세요.")
        if role in op["cache"]:
            return op["cache"][role]
        if op["inflight"]:
            raise EpisodeConflict("이전 모델 호출의 완료 여부를 알 수 없어 자동 재호출하지 않습니다.")
        reserve = 2 if role == "draft" and op["request"]["stage"] != "intent" else 1
        if state["calls_used"] > self.MAX_CALLS - reserve:
            raise EpisodeConflict("이 이야기의 시험 호출 한도에 도달했습니다. 이전 결과는 보관했습니다.")
        # The shared project reservation commits first. A crash can over-count an
        # attempt, but cannot escape the shared ceiling by creating new episodes.
        if self.provider.name == "chatgpt_subscription":
            with self.characters._db_lock, self.characters.db:
                key = f"chatgpt_subscription:{pid}"
                self.characters.db.execute("INSERT OR IGNORE INTO character_provider_budget VALUES(?,0)", (key,))
                used = self.characters.db.execute("SELECT calls FROM character_provider_budget WHERE id=?", (key,)).fetchone()[0]
                if used > self.MAX_CALLS - reserve:
                    raise EpisodeConflict("이 프로젝트의 Pro 시험 호출 한도 40회에 도달했습니다. 이전 결과는 보관했습니다.")
                self.characters.db.execute("UPDATE character_provider_budget SET calls=calls+1 WHERE id=?", (key,))
        state["calls_used"] += 1
        op["inflight"] = role
        op["events"].append({"role": method, "at": now(), "version": op["version"]})
        with self._db_lock, self.db:
            self._save(state, commit=False)
            self._save_op(pid, rid, op)
        images, bindings = [], []
        if not self.provider.fixture:
            snapshot = state["character_snapshot"]
            for index, aid in enumerate(dict.fromkeys(snapshot["sheet"]["components"].values()), 1):
                data = self.characters.visual_asset_bytes(pid, aid)
                images.append("data:image/png;base64," + base64.b64encode(data).decode("ascii"))
                asset = next(a for a in snapshot["assets"] if a["id"] == aid)
                bindings.append({"image_index": index, "asset_id": aid, "sha256": asset["sha256"],
                    "components": [part for part in snapshot["sheet"]["coverage"] if snapshot["sheet"]["components"][part["id"]] == aid]})
        result = getattr(self.provider, method)({**context, "sheet_image_bindings": bindings, "_image_inputs": images})
        self._assert_current(self._raw(pid, eid))
        if op["identity"] != self._identity():
            raise EpisodeConflict("응답 중 ChatGPT 연결이나 모델이 바뀌어 이번 결과를 적용하지 않았습니다.")
        with self._db_lock, self.db:
            op = self._operation(pid, rid)
            op["cache"][role], op["inflight"] = result, None
            self._save_op(pid, rid, op)
        return result

    def _draft(self, graph):
        op = self._operation(graph["project_id"], graph["request_id"])
        stage = op["request"]["stage"]
        method, contract = {"intent": ("intake", IntakeDraft), "story": ("story", StoryDraft), "storyboard": ("storyboard", BoardDraft)}[stage]
        value = self._call(graph["project_id"], graph["episode_id"], graph["request_id"], "draft", method, self._context(op))
        return {"draft": contract.model_validate(value).model_dump(), "issues": []}

    def _validate(self, graph):
        op = self._operation(graph["project_id"], graph["request_id"])
        state, request, draft = op["base"], op["request"], graph["draft"]
        stage = request["stage"]
        if stage == "intent":
            return {}
        records = draft["beats" if stage == "story" else "panels"]
        ids = [r["id"] for r in records]
        if len(ids) != len(set(ids)) or [r["order"] for r in records] != list(range(1, len(records) + 1)):
            raise EpisodeConflict("비트 또는 컷 ID와 순서가 중복되거나 끊겼습니다.")
        previous = state["story" if stage == "story" else "storyboard"]
        if request["target_ids"]:
            before = previous["beats" if stage == "story" else "panels"]
            if [r["id"] for r in before] != ids:
                raise EpisodeConflict("지정 부분 수정에서 ID나 순서를 바꿔 이전 결과를 보존했습니다.")
            if stage == "story" and any(draft[k] != previous[k] for k in ("title", "premise", "payoff")):
                raise EpisodeConflict("지정 부분 수정에서 이야기의 다른 결정을 바꿔 이전 결과를 보존했습니다.")
            for old, new in zip(before, records):
                allowed = set(request["edit_fields"]) if old["id"] in request["target_ids"] else set()
                if any(new[k] != v for k, v in old.items() if k not in allowed):
                    raise EpisodeConflict("요청한 대상이나 필드 밖의 내용이 바뀌어 이전 결과를 보존했습니다.")
        if stage == "storyboard":
            beat_ids = {b["id"] for b in state["story"]["beats"]}
            actual = {bid for panel in records for bid in panel["beat_ids"]}
            if len(records) != state["format"]["cut_count"] or actual != beat_ids:
                raise EpisodeConflict("콘티의 컷 수나 이야기 비트 연결이 확인한 원본과 맞지 않습니다.")
        return {}

    def _evaluate(self, graph):
        op = self._operation(graph["project_id"], graph["request_id"])
        if op["request"]["stage"] == "intent":
            return {}
        context = {**self._context(op), "draft": graph["draft"], "stage": op["request"]["stage"]}
        result = Evaluation.model_validate(self._call(graph["project_id"], graph["episode_id"], graph["request_id"], "evaluate", "evaluate", context)).model_dump()
        if any(result[k] != context[k] for k in ("project_id", "episode_id", "version", "snapshot_fingerprint")):
            raise EpisodeConflict("독립 평가가 현재 이야기·시트·산출물 버전과 맞지 않습니다.")
        issues = result["issues"]
        if result["recommendation"] != "ready_for_human":
            issues.append({"code": "evaluation_needs_revision", "severity": "blocker", "message": "검토에서 수정 의견이 남았습니다. 대화로 수정한 후 확인해 주세요.", "target_id": None})
        return {"evaluation": result, "issues": issues}

    def _review(self, graph):
        op = self._operation(graph["project_id"], graph["request_id"])
        response = interrupt({"episode_id": graph["episode_id"], "stage": op["request"]["stage"], "version": op["version"]})
        if response != {"confirm_version": op["version"]}:
            raise EpisodeConflict("현재 산출물의 정확한 사람 확인이 필요합니다.")
        return {}

    def _build_graph(self):
        graph = StateGraph(GraphState)
        for name, method in (("draft", self._draft), ("validate", self._validate), ("evaluate", self._evaluate), ("human_review", self._review)):
            graph.add_node(name, method)
        graph.add_edge(START, "draft")
        graph.add_edge("draft", "validate")
        graph.add_edge("validate", "evaluate")
        graph.add_conditional_edges("evaluate", lambda s: "done" if self._operation(s["project_id"], s["request_id"])["request"]["stage"] == "intent" else "review", {"done": END, "review": "human_review"})
        graph.add_edge("human_review", END)
        return graph.compile(checkpointer=self.checkpointer)

    def _next_version(self, state, kind):
        return f"1.0.{sum(v['kind'] == kind for v in state['versions']) + 1}"

    def _artifact(self, state, kind, value, version=None):
        result = {**value, "artifact_id": f"{state['id']}-{kind}", "version": version or self._next_version(state, kind),
            "project_id": state["project_id"], "episode_id": state["id"], "snapshot_fingerprint": state["character_snapshot"]["fingerprint"]}
        state["versions"].append({"kind": kind, "artifact": copy.deepcopy(result), "created_at": now()})
        return result

    def _invalidate_board(self, state):
        for job in state["rough_jobs"]:
            if job["status"] == "awaiting_image":
                job["status"] = "cancelled"
        state.update(storyboard=None, roughs={}, approved_board_version=None, usable_storyboard=False)

    def submit_turn(self, pid, eid, request):
        request = TurnRequest.model_validate(request).model_dump()
        with self._lock_for(eid):
            replay = self._replay(pid, eid, "turn", request)
            if replay is not None:
                return replay
            base = self._raw(pid, eid)
            if base["revision"] != request["expected_revision"]:
                raise EpisodeConflict("결과가 바뀌었습니다. 최신 버전을 확인해 주세요.")
            self._assert_current(base)
            stage = request["stage"]
            previous = base.get("story" if stage == "story" else "storyboard") if stage != "intent" else None
            if stage == "intent" and base["current_stage"] != "intent":
                raise EpisodeConflict("이야기 시작 후에는 이야기 수정으로 의도를 바꿔 주세요.")
            if stage == "story" and (not base["intent"]["topic"] or not base["intent"]["intended_emotion"] or not base["intent"]["ending"]):
                raise EpisodeConflict("이야기의 소재와 원하는 감정·마무리를 대화로 먼저 알려주세요.")
            if stage == "storyboard" and (base["confirmed_story_version"] != (base["story"] or {}).get("version") or base["confirmed_format_version"] != (base["format"] or {}).get("version")):
                raise EpisodeConflict("현재 이야기와 형식을 확인한 뒤 콘티를 만들 수 있습니다.")
            if (previous or request["expected_version"]) and request["expected_version"] != (previous or {}).get("version"):
                raise EpisodeConflict("수정할 산출물의 정확한 버전이 필요합니다.")
            records = (previous or {}).get("beats" if stage == "story" else "panels", [])
            allowed = {"action", "emotion", "dialogue"} if stage == "story" else set(Panel.model_fields) - {"id", "order", "beat_ids"}
            if len(request["target_ids"]) != len(set(request["target_ids"])) or not set(request["target_ids"]) <= {r["id"] for r in records} or not set(request["edit_fields"]) <= allowed or bool(request["target_ids"]) != bool(request["edit_fields"]):
                raise EpisodeConflict("수정할 대상과 필드를 현재 이야기에서 정확히 선택해 주세요.")
            version = self._next_version(base, stage)
            op = {"base": base, "request": request, "version": version, "identity": self._identity(), "cache": {}, "inflight": None, "events": []}
            with self._db_lock, self.db:
                self.db.execute("INSERT INTO episode_operations VALUES(?,?,?,?,?,?,?)", (pid, eid, request["request_id"], "turn", digest(request), "pending", dump(op)))
            state = copy.deepcopy(base)
            state["messages"].append({"id": request["request_id"] + "-user", "role": "user", "content": request["message"], "at": now(), "stage": stage})
            succeeded = False
            try:
                with tracing_context(enabled=False):
                    self.graph.invoke({"project_id": pid, "episode_id": eid, "request_id": request["request_id"]}, self._config(eid, request["request_id"]))
                    output = dict(self.graph.get_state(self._config(eid, request["request_id"])).values)
                self._assert_current(state)
                draft = output["draft"]
                if stage == "intent":
                    state.update(intent=draft["intent"], next_question=draft["next_question"], status="awaiting_input")
                elif stage == "story":
                    state["story"] = self._artifact(state, "story", draft, version)
                    self._invalidate_board(state)
                    state.update(title=draft["title"], current_stage="story", confirmed_story_version=None, confirmed_format_version=None, format=None,
                        next_question="바꾸고 싶은 부분을 알려주거나 이 이야기를 확인해 주세요.", pending_action="confirm_story")
                else:
                    old_board, old_roughs = state["storyboard"], dict(state["roughs"])
                    state["storyboard"] = self._artifact(state, "storyboard", {**draft, "story_version": state["story"]["version"], "format_version": state["format"]["version"]}, version)
                    self._invalidate_roughs(state, old_board, old_roughs)
                    state.update(current_stage="storyboard", approved_board_version=None, usable_storyboard=False,
                        next_question="컷을 확인하고 수정한 뒤 각 컷의 러프 이미지를 가져와 주세요.", pending_action="confirm_board")
                if stage != "intent":
                    state["evaluations"].append(output["evaluation"])
                    state["issues"] = output["issues"]
                    state["status"] = "blocked" if any(i["severity"] == "blocker" for i in output["issues"]) else "awaiting_review"
                else:
                    state["issues"] = []
                state["messages"].append({"id": request["request_id"] + "-assistant", "role": "assistant", "content": draft["assistant_message"], "at": now(), "stage": stage, "version": version})
                succeeded = True
            except Exception as error:
                from .chatgpt_provider import ChatGPTProviderError
                message = str(error) if isinstance(error, (ChatGPTProviderError, EpisodeConflict)) else "이번 작업을 처리하지 못했습니다. 이전 결과는 보존했습니다. 내용을 확인해 새 요청을 보내주세요."
                code = error.code if isinstance(error, ChatGPTProviderError) else "episode_execution_failed"
                state.update(status="blocked", pending_action=None, issues=[{"code": code, "severity": "blocker", "message": message, "target_id": None}])
                state["messages"].append({"id": request["request_id"] + "-assistant", "role": "assistant", "content": message, "at": now(), "stage": stage})
            # The character lock is held only for final validation and commit,
            # never while waiting on a provider. A simultaneous sheet reopen
            # cannot slip between the final check and artifact/decision save.
            with self.characters._lock_for(pid):
                if succeeded:
                    try:
                        self._assert_current(state)
                    except EpisodeConflict as error:
                        state = copy.deepcopy(base)
                        state["messages"].extend([
                            {"id": request["request_id"] + "-user", "role": "user", "content": request["message"], "at": now(), "stage": stage},
                            {"id": request["request_id"] + "-assistant", "role": "assistant", "content": str(error), "at": now(), "stage": stage}])
                        state.update(status="blocked", pending_action=None, issues=[{"code": "episode_snapshot_changed", "severity": "blocker", "message": str(error), "target_id": None}])
                current = self._raw(pid, eid)
                state["calls_used"] = current["calls_used"]
                state["revision"] = base["revision"] + 1
                op = self._operation(pid, request["request_id"])
                state["events"].extend(op["events"])
                op.update(status="completed", response=state)
                with self._db_lock, self.db:
                    self._save(state, commit=False)
                    self._save_op(pid, request["request_id"], op)
            return self._public(state)

    def _visual_fingerprint(self, panel):
        return digest({k: v for k, v in panel.items() if k not in ("dialogue", "text_placement")})

    def _invalidate_roughs(self, state, old_board, old_roughs):
        old = {p["id"]: p for p in (old_board or {}).get("panels", [])}
        state["roughs"] = {p["id"]: old_roughs[p["id"]] for p in state["storyboard"]["panels"] if p["id"] in old_roughs and self._visual_fingerprint(p) == self._visual_fingerprint(old[p["id"]])}
        if state["roughs"]:
            state["events"].append({"role": "visual_reuse", "at": now(), "version": state["storyboard"]["version"],
                "panel_ids": list(state["roughs"]), "reason": "Visual instructions are identical; dialogue and text placement remain separate overlays.", "source_board_version": old_board["version"]})
        for job in state["rough_jobs"]:
            if job["status"] == "awaiting_image":
                job["status"] = "cancelled"

    def _resume_review(self, state, stage, version):
        with self._db_lock:
            operations = self.db.execute("SELECT request_id,payload FROM episode_operations WHERE episode_id=? AND kind='turn' AND status='completed' ORDER BY rowid DESC", (state["id"],)).fetchall()
        for rid, payload in operations:
            op = json.loads(payload)
            if op["request"]["stage"] == stage and op["version"] == version:
                config = self._config(state["id"], rid)
                with tracing_context(enabled=False):
                    snapshot = self.graph.get_state(config)
                    if any(t.interrupts for t in snapshot.tasks):
                        self.graph.invoke(Command(resume={"confirm_version": version}), config)
                return

    def decision(self, pid, eid, request):
        request = DecisionRequest.model_validate(request).model_dump()
        def mutate(state):
            action = request["action"]
            kind = "story" if action.endswith("story") else "format" if action.endswith("format") else "storyboard"
            artifact = state[kind]
            if not artifact or artifact["version"] != request["expected_version"]:
                raise EpisodeConflict("확인할 산출물의 정확한 버전이 필요합니다.")
            if action.startswith("confirm") and any(i["severity"] == "blocker" for i in state["issues"]):
                raise EpisodeConflict("현재 수정 의견을 해결한 뒤 확인할 수 있습니다.")
            expected_stage = {"confirm_story": "story", "confirm_format": "format", "confirm_board": "storyboard"}
            confirmed_key = {"story": "confirmed_story_version", "format": "confirmed_format_version", "storyboard": "approved_board_version"}[kind]
            if action.startswith("confirm") and (state["current_stage"] != expected_stage[action] or state[confirmed_key] is not None):
                raise EpisodeConflict("이미 확인했거나 현재 단계가 아닌 산출물입니다. 수정 단계로 돌아간 뒤 진행해 주세요.")
            if action.startswith("reopen") and state[confirmed_key] is None:
                raise EpisodeConflict("아직 확인하지 않은 산출물입니다. 현재 결과를 수정해 주세요.")
            if action == "confirm_story":
                self._resume_review(state, "story", artifact["version"])
                state["confirmed_story_version"] = artifact["version"]
                self._invalidate_board(state)
                state["confirmed_format_version"] = None
                count = len(artifact["beats"])
                state["format"] = self._artifact(state, "format", {"story_version": artifact["version"], "cut_count": count,
                    "layout": "single_panel" if count == 1 else "vertical_grid", "text_mode": "overlay", "rationale": "확인한 이야기의 각 비트를 한 컷에 연결하는 제안입니다. 컷 수를 바꿀 수 있습니다."})
                state.update(current_stage="format", pending_action="confirm_format", next_question="이야기를 몇 컷으로 보여줄까요? 제안한 형식을 확인하거나 바꿔 주세요.")
            elif action == "reopen_story":
                state.update(confirmed_story_version=None, confirmed_format_version=None, approved_board_version=None, usable_storyboard=False, current_stage="story", pending_action=None)
            elif action == "confirm_format":
                if state["confirmed_story_version"] != state["story"]["version"] or artifact["story_version"] != state["story"]["version"]:
                    raise EpisodeConflict("현재 이야기 확인이 필요합니다.")
                state.update(confirmed_format_version=artifact["version"], current_stage="storyboard", pending_action=None, next_question="이 형식으로 컷별 콘티를 만들어 볼까요?")
            elif action == "reopen_format":
                state.update(confirmed_format_version=None, approved_board_version=None, usable_storyboard=False, current_stage="format", pending_action=None)
            elif action == "confirm_board":
                if state["fixture"]:
                    raise EpisodeConflict("개발용 결정론적 이야기·콘티는 실제 G2 창작 확인을 통과할 수 없습니다.")
                self._assert_board_sources(state)
                if any(j["status"] == "awaiting_image" for j in state["rough_jobs"]):
                    raise EpisodeConflict("요청한 러프 이미지를 반영하거나 작업을 취소한 뒤 확인해 주세요.")
                for panel in artifact["panels"]:
                    aid = state["roughs"].get(panel["id"])
                    if not aid:
                        raise EpisodeConflict("모든 컷의 실제 러프 이미지를 확인한 뒤 콘티를 최종 확인할 수 있습니다.")
                    asset = self._rough_asset(state, aid)
                    self._rough_bytes(state, asset)
                    if asset["panel_fingerprint"] != self._visual_fingerprint(panel):
                        raise EpisodeConflict("현재 컷과 러프 이미지 지시가 다릅니다.")
                    if asset["provenance"]["fixture"]:
                        raise EpisodeConflict("개발 fixture 이미지는 실제 시각 콘티로 최종 확인할 수 없습니다.")
                self._resume_review(state, "storyboard", artifact["version"])
                state.update(approved_board_version=artifact["version"], usable_storyboard=True, current_stage="complete", pending_action=None, next_question="확인한 콘티를 저장했습니다. 수정하면 새 버전으로 이어집니다.")
            else:
                state.update(approved_board_version=None, usable_storyboard=False, current_stage="storyboard", pending_action=None)
            state["decisions"].append({"id": new_id("decision"), "action": action, "version": artifact["version"], "actor": "human", "at": now(), "snapshot_fingerprint": state["character_snapshot"]["fingerprint"]})
            state["status"] = "completed" if state["usable_storyboard"] else "awaiting_review"
        return self._mutate(pid, eid, "decision", request, mutate)

    def save_format(self, pid, eid, request):
        request = FormatRequest.model_validate(request).model_dump()
        def mutate(state):
            current = state["format"]
            if not current or current["version"] != request["expected_version"] or state["confirmed_story_version"] != state["story"]["version"]:
                raise EpisodeConflict("현재 확인한 이야기와 형식 버전이 필요합니다.")
            if state["current_stage"] != "format" or state["confirmed_format_version"] is not None:
                raise EpisodeConflict("형식 수정 단계로 돌아간 뒤 구성을 바꿀 수 있습니다.")
            if (request["cut_count"] == 1) != (request["layout"] == "single_panel"):
                raise EpisodeConflict("한 컷은 단일 화면, 여러 컷은 순서형 화면을 선택해 주세요.")
            state["format"] = self._artifact(state, "format", {**{k: current[k] for k in ("story_version", "text_mode", "rationale")}, "cut_count": request["cut_count"], "layout": request["layout"]})
            self._invalidate_board(state)
            state.update(confirmed_format_version=None, current_stage="format", pending_action="confirm_format", issues=[])
        return self._mutate(pid, eid, "format", request, mutate)

    def _assert_board_sources(self, state):
        board = state["storyboard"]
        if (not board or state["confirmed_story_version"] != board["story_version"] or state["confirmed_format_version"] != board["format_version"]
                or (state["story"] or {}).get("version") != board["story_version"] or (state["format"] or {}).get("version") != board["format_version"]):
            raise EpisodeConflict("현재 확인한 이야기·형식에 연결된 콘티가 필요합니다.")

    def create_rough_job(self, pid, eid, request):
        request = RoughJobRequest.model_validate(request).model_dump()
        def mutate(state):
            self._assert_board_sources(state)
            board = state["storyboard"]
            panel = next((p for p in board["panels"] if p["id"] == request["panel_id"]), None)
            if board["version"] != request["expected_board_version"] or not panel:
                raise EpisodeConflict("현재 콘티의 정확한 컷을 선택해 주세요.")
            if any(j["status"] == "awaiting_image" and j["panel_id"] == panel["id"] for j in state["rough_jobs"]):
                raise EpisodeConflict("이 컷의 이미지 작업이 이미 대기 중입니다.")
            source_ids = list(dict.fromkeys(state["character_snapshot"]["sheet"]["components"].values()))
            source_roles = {aid: "identity_reference" for aid in source_ids}
            panel_index = next(index for index, item in enumerate(board["panels"]) if item["id"] == panel["id"])
            # Pin one actual preceding panel at request time. Its prop/layout
            # continuity must never override the approved character sheet or
            # replace the target panel's own action instructions.
            for earlier in reversed(board["panels"][:panel_index]):
                earlier_aid = state["roughs"].get(earlier["id"])
                if earlier_aid:
                    self._rough_bytes(state, self._rough_asset(state, earlier_aid))
                    source_ids.append(earlier_aid)
                    source_roles[earlier_aid] = "continuity_reference"
                    break
            if state["roughs"].get(panel["id"]):
                current_aid = state["roughs"][panel["id"]]
                self._rough_bytes(state, self._rough_asset(state, current_aid))
                source_ids.append(current_aid)
                source_roles[current_aid] = "edit_target"
            source_ids = list(dict.fromkeys(source_ids))
            prompt = ("Create one original Level 1 storyboard rough for the specified panel. Use the attached approved character sheet as identity references. "
                "Preserve body silhouette, proportions, palette and leaf. Show the exact observable panel action, expression, camera and composition. "
                "Do not copy external characters. No lettering, speech bubbles or captions; dialogue is added separately by the app. "
                "A continuity_reference is an earlier panel used only for prop design, layout direction and rendering style; never use it to change character identity or copy its action instead of the target action. "
                "When an existing rough is supplied as edit_target, preserve everything outside the requested change.\n"
                + dump({"character": state["character_snapshot"]["direction"], "panel": panel, "instruction": request["instruction"],
                    "source_roles": source_roles}))
            state["rough_jobs"].append({"id": new_id("rough-job"), "status": "awaiting_image", "panel_id": panel["id"], "board_version": board["version"],
                "instruction": request["instruction"], "prompt": prompt, "source_asset_ids": source_ids, "snapshot_fingerprint": state["character_snapshot"]["fingerprint"],
                "panel_fingerprint": self._visual_fingerprint(panel), "created_at": now()})
            state.update(approved_board_version=None, usable_storyboard=False, current_stage="storyboard", status="awaiting_review")
        return self._mutate(pid, eid, "rough_job", request, mutate)

    def cancel_rough_job(self, pid, eid, jid, request):
        request = Request.model_validate(request).model_dump()
        def mutate(state):
            job = next((j for j in state["rough_jobs"] if j["id"] == jid), None)
            if not job or job["status"] != "awaiting_image":
                raise EpisodeConflict("현재 대기 중인 이미지 작업이 필요합니다.")
            job["status"] = "cancelled"
        return self._mutate(pid, eid, "rough_cancel_" + jid, request, mutate)

    def _rough_path(self, state, asset):
        base = (self.root / "assets" / state["project_id"] / state["id"]).resolve()
        path = base / (asset["id"] + ".png")
        if not re.fullmatch(r"image-[a-f0-9]{32}", asset["id"]) or not path.resolve().is_relative_to(base) or path.is_symlink():
            raise EpisodeConflict("러프 이미지 저장 경로를 확인해야 합니다.")
        if os.name == "nt" and not str(path).startswith("\\\\?\\"):
            return Path("\\\\?\\" + str(path))
        return path

    def _rough_asset(self, state, aid):
        asset = next((a for a in state["rough_assets"] if a["id"] == aid), None)
        if not asset or asset["project_id"] != state["project_id"] or asset["episode_id"] != state["id"] or asset["snapshot_fingerprint"] != state["character_snapshot"]["fingerprint"]:
            raise EpisodeConflict("현재 이야기의 러프 이미지를 찾을 수 없습니다.")
        expected = f"/api/studio/projects/{state['project_id']}/episodes/{state['id']}/rough/assets/{aid}"
        if asset["url"] != expected:
            raise EpisodeConflict("러프 이미지 경로가 현재 이야기와 다릅니다.")
        return asset

    def _rough_bytes(self, state, asset):
        try:
            data = self._rough_path(state, asset).read_bytes()
        except OSError as error:
            raise EpisodeConflict("러프 이미지가 없습니다. 원본 파일을 복구해 주세요.") from error
        if len(data) != asset["byte_size"] or hashlib.sha256(data).hexdigest() != asset["sha256"]:
            raise EpisodeConflict("러프 이미지 체크섬이 달라졌습니다. 원본 파일을 복구해 주세요.")
        return data

    def rough_asset_bytes(self, pid, eid, aid):
        state = self._raw(pid, eid)
        return self._rough_bytes(state, self._rough_asset(state, aid))

    def upload_rough(self, pid, eid, jid, request, data):
        request = RoughUploadRequest.model_validate(request).model_dump()
        normalized, width, height = normalize_image(data)
        def mutate(state):
            self._assert_board_sources(state)
            board = state["storyboard"]
            job = next((j for j in state["rough_jobs"] if j["id"] == jid), None)
            if not job or job["status"] != "awaiting_image" or job["board_version"] != board["version"] or board["version"] != request["expected_board_version"]:
                raise EpisodeConflict("현재 콘티에 대기 중인 정확한 이미지 작업이 필요합니다.")
            panel = next(p for p in board["panels"] if p["id"] == job["panel_id"])
            if job["snapshot_fingerprint"] != state["character_snapshot"]["fingerprint"] or job["panel_fingerprint"] != self._visual_fingerprint(panel):
                raise EpisodeConflict("이미지 작업의 캐릭터나 컷 지시가 바뀌었습니다.")
            provenance = copy.deepcopy(request["provenance"])
            for field in ("model", "workflow", "prompt", "seed"):
                if not provenance[field] and field not in provenance["unknowns"]:
                    provenance["unknowns"].append(field)
            source_fixture = any(self._rough_asset(state, aid)["provenance"]["fixture"] for aid in job["source_asset_ids"] if any(a["id"] == aid for a in state["rough_assets"]))
            provenance["fixture"] = provenance["fixture"] or source_fixture
            aid = new_id("image")
            asset = {"id": aid, "project_id": pid, "episode_id": eid, "url": f"/api/studio/projects/{pid}/episodes/{eid}/rough/assets/{aid}",
                "sha256": hashlib.sha256(normalized).hexdigest(), "byte_size": len(normalized), "width": width, "height": height,
                "provenance": provenance, "source_asset_ids": job["source_asset_ids"], "snapshot_fingerprint": job["snapshot_fingerprint"],
                "panel_id": panel["id"], "panel_fingerprint": job["panel_fingerprint"], "board_version": board["version"], "job_id": jid}
            path = self._rough_path(state, asset)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as output:
                output.write(normalized)
            state["rough_assets"].append(asset)
            state["roughs"][panel["id"]] = aid
            job.update(status="completed", asset_id=aid)
            state.update(approved_board_version=None, usable_storyboard=False)
        return self._mutate(pid, eid, "rough_upload_" + jid, request, mutate, binary=data)

    def export_episode(self, pid, eid):
        with self._lock_for(eid):
            state = self._raw(pid, eid)
            self._assert_current(state)
            if not state["usable_storyboard"] or state["approved_board_version"] != (state["storyboard"] or {}).get("version"):
                raise EpisodeConflict("현재 콘티를 최종 확인한 뒤 내려받을 수 있습니다.")
            output = io.BytesIO()
            files = {}
            with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("episode.json", dump(state))
                selected_ids = set(state["roughs"].values())
                pending = list(selected_ids)
                by_id = {a["id"]: a for a in state["rough_assets"]}
                while pending:
                    for aid in by_id[pending.pop()]["source_asset_ids"]:
                        if aid in by_id and aid not in selected_ids:
                            selected_ids.add(aid)
                            pending.append(aid)
                rough_closure = [a for a in state["rough_assets"] if a["id"] in selected_ids]
                snapshot_assets = state["character_snapshot"]["assets"]
                if sum(a["byte_size"] for a in [*rough_closure, *snapshot_assets]) > 128 * 1024 * 1024:
                    raise EpisodeConflict("내려받을 이미지가 128MB를 넘습니다. 개별 이미지를 저장해 주세요.")
                for asset in snapshot_assets:
                    data = self.characters.visual_asset_bytes(pid, asset["id"])
                    name = f"character/{asset['id']}.png"
                    archive.writestr(name, data)
                    files[name] = asset["sha256"]
                for asset in rough_closure:
                    name = f"rough-sources/{asset['id']}.png"
                    archive.writestr(name, self._rough_bytes(state, asset))
                    files[name] = asset["sha256"]
                for panel in state["storyboard"]["panels"]:
                    asset = self._rough_asset(state, state["roughs"][panel["id"]])
                    data = self._rough_bytes(state, asset)
                    if asset["panel_fingerprint"] != self._visual_fingerprint(panel):
                        raise EpisodeConflict("콘티와 러프 이미지 지시가 달라졌습니다.")
                    name = f"roughs/{panel['id']}.png"
                    archive.writestr(name, data)
                    files[name] = asset["sha256"]
                archive.writestr("manifest.json", dump({"schema_id": "toon-episode-export-v1", "project_id": pid, "episode_id": eid,
                    "story_version": state["story"]["version"], "format_version": state["format"]["version"], "board_version": state["storyboard"]["version"],
                    "snapshot_fingerprint": state["character_snapshot"]["fingerprint"], "files": files}))
            return output.getvalue()
