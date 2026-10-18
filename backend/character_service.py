"""Durable character conversation: designer -> validator -> evaluator -> human review.

Each submitted turn owns an immutable operation and graph thread. Side-effect results are
cached before checkpoint replay; a direction decision never authorizes a visual sheet.
"""
import copy
import hashlib
import json
import re
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from langsmith import tracing_context
from pydantic import ValidationError

from .character_contracts import (QUESTIONS, CharacterBrief, CharacterState, DirectionDecisionRequest,
                                  DirectionDraft, DirectionEvaluation, DirectionFields, TurnRequest, unknown_fields)
from .character_workers import configured_character_provider, validate_approval, validate_direction


def now():
    return datetime.now(timezone.utc).isoformat()


def dump(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class CharacterConflict(Exception):
    pass


class CharacterNotFound(Exception):
    pass


class CharacterGraphState(TypedDict, total=False):
    project_id: str
    request_id: str
    brief: dict
    assistant_message: str
    issues: list[dict]
    evaluation: dict


class CharacterService:
    def __init__(self, root: Path, provider=None):
        self.root = Path(root) / "studio" / "character"
        self.root.mkdir(parents=True, exist_ok=True)
        self.provider = provider or configured_character_provider()
        self._db_lock = threading.RLock()
        self._locks_lock = threading.Lock()
        self._locks = {}
        self._closed = False
        self.db = sqlite3.connect(self.root / "directions.sqlite3", check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS character_states(project_id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS character_operations(project_id TEXT NOT NULL, request_id TEXT NOT NULL,
                kind TEXT NOT NULL, request_hash TEXT NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL,
                PRIMARY KEY(project_id,request_id));
            CREATE TABLE IF NOT EXISTS character_versions(project_id TEXT NOT NULL, version TEXT NOT NULL,
                payload TEXT NOT NULL, PRIMARY KEY(project_id,version));
            CREATE TABLE IF NOT EXISTS character_provider_budget(id TEXT PRIMARY KEY, calls INTEGER NOT NULL);
        """)
        self.db.commit()
        self._checkpoint_db = sqlite3.connect(self.root / "checkpoints.sqlite3", check_same_thread=False)
        self._checkpoint_db.execute("PRAGMA journal_mode=WAL")
        self.checkpointer = SqliteSaver(self._checkpoint_db)
        self.checkpointer.setup()
        self.graph = self._build_graph()
        with self._db_lock:
            pending = self.db.execute("SELECT project_id,request_id FROM character_operations WHERE status='pending'").fetchall()
        try:
            for pid, request_id in pending:
                with self._lock_for(pid):
                    try:
                        self._execute_turn(pid, request_id)
                    except (CharacterConflict, CharacterNotFound):
                        self._quarantine_operation(pid, request_id)
        except BaseException:
            self.close()
            raise

    def close(self):
        if not self._closed:
            self._closed = True
            self._checkpoint_db.close()
            self.db.close()

    def _lock_for(self, pid):
        with self._locks_lock:
            return self._locks.setdefault(pid, threading.RLock())

    def _validate_pid(self, pid):
        if not isinstance(pid, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,160}", pid):
            raise CharacterNotFound("캐릭터 프로젝트를 찾을 수 없습니다.")

    def _validated_state(self, raw):
        try:
            return CharacterState.model_validate(raw).model_dump()
        except ValidationError as error:
            raise CharacterConflict("저장된 캐릭터 계약을 지원하지 않거나 프로젝트 경계가 맞지 않습니다.") from error

    def ensure_project(self, pid):
        self._validate_pid(pid)
        with self._lock_for(pid), self._db_lock, self.db:
            if not self.db.execute("SELECT 1 FROM character_states WHERE project_id=?", (pid,)).fetchone():
                initial = CharacterState(project_id=pid, fixture=self.provider.fixture, provider=self.provider.name,
                                         next_question=QUESTIONS["appearance"],
                                         unknowns=["appearance", "personality", "desired_feeling"]).model_dump()
                self.db.execute("INSERT INTO character_states VALUES(?,?)", (pid, dump(initial)))
        return self.get_state(pid)

    def get_state(self, pid):
        self._validate_pid(pid)
        with self._db_lock:
            row = self.db.execute("SELECT payload FROM character_states WHERE project_id=?", (pid,)).fetchone()
        if not row:
            raise CharacterNotFound("캐릭터 프로젝트를 찾을 수 없습니다.")
        state = self._validated_state(json.loads(row[0]))
        if state["project_id"] != pid:
            raise CharacterConflict("저장된 캐릭터 프로젝트 경계가 맞지 않습니다.")
        return state

    def _operation(self, pid, request_id):
        with self._db_lock:
            row = self.db.execute("SELECT kind,request_hash,status,payload FROM character_operations WHERE project_id=? AND request_id=?",
                                  (pid, request_id)).fetchone()
        return None if not row else {"kind": row[0], "request_hash": row[1], "status": row[2], **json.loads(row[3])}

    def _replay(self, pid, kind, request):
        operation = self._operation(pid, request["request_id"])
        if not operation:
            return None
        if operation["kind"] != kind or operation["request_hash"] != hashlib.sha256(dump(request).encode()).hexdigest():
            raise CharacterConflict("같은 요청 ID를 다른 내용으로 사용할 수 없습니다.")
        if operation["status"] == "completed":
            response = self._validated_state(operation["response"])
            if response["project_id"] != pid:
                raise CharacterConflict("보존된 응답의 프로젝트 경계가 맞지 않습니다.")
            return response
        if operation["status"] != "pending":
            raise CharacterConflict("이전 요청의 계약을 지원하지 않습니다. 최신 상태에서 새 요청을 보내주세요.")
        if kind == "turn":
            return self._execute_turn(pid, request["request_id"])
        raise CharacterConflict("같은 요청이 처리 중입니다.")

    def _assert_revision(self, state, expected):
        if state["revision"] != expected:
            raise CharacterConflict("캐릭터 방향이 변경됐습니다. 최신 결과를 확인하고 다시 시도하세요.")

    def _record_operation(self, pid, kind, request, payload, status="pending"):
        self.db.execute("INSERT INTO character_operations VALUES(?,?,?,?,?,?)", (pid, request["request_id"], kind,
                        hashlib.sha256(dump(request).encode()).hexdigest(), status, dump(payload)))

    def _save_operation(self, pid, request_id, operation):
        payload = {k: v for k, v in operation.items() if k not in ("kind", "request_hash", "status")}
        self.db.execute("UPDATE character_operations SET status=?,payload=? WHERE project_id=? AND request_id=?",
                        (operation["status"], dump(payload), pid, request_id))

    def submit_turn(self, pid, request: dict):
        request = TurnRequest.model_validate(request).model_dump()
        self._validate_pid(pid)
        with self._lock_for(pid):
            replay = self._replay(pid, "turn", request)
            if replay is not None:
                return replay
            with self._db_lock, self.db:
                state = self.get_state(pid)
                self._assert_revision(state, request["expected_revision"])
                if state["direction_confirmed"]:
                    raise CharacterConflict("확인한 방향은 먼저 수정 단계로 돌아간 후 변경하세요.")
                if self.db.execute("SELECT 1 FROM character_operations WHERE project_id=? AND status='pending'", (pid,)).fetchone():
                    raise CharacterConflict("이 프로젝트의 이전 대화를 처리하고 있습니다.")
                version = f"1.0.{len(state['versions']) + 1}"
                self._record_operation(pid, "turn", request, {"request": request, "base_state": state,
                                       "version": version, "cache": {}, "events": [], "inflight": None,
                                       "provider": self.provider.name, "fixture": self.provider.fixture,
                                       "approval_id": getattr(self.provider, "budget_id", None)})
            return self._execute_turn(pid, request["request_id"])

    def _config(self, pid, request_id):
        thread_id = hashlib.sha256(f"{pid}:{request_id}".encode()).hexdigest()
        return {"configurable": {"thread_id": f"character-{thread_id}"}, "recursion_limit": 8}

    def _context(self, operation):
        state, request = operation["base_state"], operation["request"]
        previous = state["brief"] or DirectionFields().model_dump()
        fields = {key: copy.deepcopy(previous[key]) for key in DirectionFields.model_fields}
        references = request["references"] if request["references"] is not None else previous.get("reference_observations", [])
        return {"project_id": state["project_id"], "version": operation["version"], "message": request["message"],
                "previous_fields": fields, "question_field": state["question_field"],
                "field_updates": {key: value for key, value in request["field_updates"].items() if value is not None},
                "references": references,
                "dialogue": [{"role": item["role"], "content": item["content"]} for item in state["messages"][-30:]]}

    def _validate_operation(self, pid, request_id, operation):
        try:
            base = self._validated_state(operation["base_state"])
            request = TurnRequest.model_validate(operation["request"]).model_dump()
            if (base["project_id"] != pid or request["request_id"] != request_id
                    or request["expected_revision"] != base["revision"]
                    or operation["version"] != f"1.0.{len(base['versions']) + 1}"
                    or operation["provider"] != self.provider.name or operation["fixture"] != self.provider.fixture
                    or operation["approval_id"] != getattr(self.provider, "budget_id", None)
                    or operation["request_hash"] != hashlib.sha256(dump(request).encode()).hexdigest()
                    or not isinstance(operation["cache"], dict) or not isinstance(operation["events"], list)):
                raise ValueError("unsupported stored operation")
            # A valid old snapshot is still stale: reject it before graph replay or model calls.
            self._assert_revision(self.get_state(pid), base["revision"])
        except (KeyError, TypeError, ValueError, ValidationError, CharacterConflict) as error:
            raise CharacterConflict("보존된 대화의 계약·프로젝트·실행 범위를 확인할 수 없어 실행을 중단했습니다.") from error
        return {**operation, "base_state": base, "request": request}

    def _quarantine_operation(self, pid, request_id):
        with self._db_lock, self.db:
            self.db.execute("UPDATE character_operations SET status='quarantined' WHERE project_id=? AND request_id=?", (pid, request_id))
            try:
                state = self.get_state(pid)
            except (CharacterConflict, CharacterNotFound):
                return
            state.update(status="blocked", can_confirm=False, revision=state["revision"] + 1)
            state["issues"] = [{"code": "stored_operation_invalid", "severity": "blocker",
                                "message": "보존된 대화의 실행 범위를 확인하지 못했습니다. 이전 방향은 보존했으며 자동 실행을 중단했습니다."}]
            self.db.execute("UPDATE character_states SET payload=? WHERE project_id=?", (dump(state), pid))

    def _event(self, pid, request_id, role):
        with self._db_lock, self.db:
            op = self._operation(pid, request_id)
            if not any(item["role"] == role for item in op["events"]):
                op["events"].append({"role": role, "at": now(), "version": op["version"]})
                self._save_operation(pid, request_id, op)

    def _call(self, pid, request_id, role, method, context):
        self._event(pid, request_id, role)
        with self._db_lock, self.db:
            op = self._operation(pid, request_id)
            if role in op["cache"]:
                return copy.deepcopy(op["cache"][role])
            if op.get("inflight") and not self.provider.fixture:
                raise CharacterConflict("이전 모델 호출의 완료 여부를 확인할 수 없습니다. 자동 재호출하지 않습니다.")
            if hasattr(self.provider, "budget_id"):
                validate_approval(self.provider.approval, self.provider.model)
                self.db.execute("INSERT OR IGNORE INTO character_provider_budget VALUES(?,0)", (self.provider.budget_id,))
                used = self.db.execute("SELECT calls FROM character_provider_budget WHERE id=?", (self.provider.budget_id,)).fetchone()[0]
                if used >= self.provider.approval["max_calls"]:
                    raise CharacterConflict("캐릭터 전용 모델 호출 한도를 모두 사용했습니다.")
                self.db.execute("UPDATE character_provider_budget SET calls=calls+1 WHERE id=?", (self.provider.budget_id,))
            op["inflight"] = role
            self._save_operation(pid, request_id, op)
        result = getattr(self.provider, method)(context)
        with self._db_lock, self.db:
            op = self._operation(pid, request_id)
            op["cache"][role] = result
            op["inflight"] = None
            self._save_operation(pid, request_id, op)
        return result

    def _designer(self, state):
        pid, request_id = state["project_id"], state["request_id"]
        operation = self._operation(pid, request_id)
        context = self._context(operation)
        result = DirectionDraft.model_validate(self._call(pid, request_id, "character_designer", "draft", context))
        previous = operation["base_state"]["brief"]
        source_ids = [*(previous["source_turn_ids"] if previous else []), request_id]
        brief = CharacterBrief(**result.fields.model_dump(), project_id=pid, artifact_id=f"{pid}-character-direction",
                               version=operation["version"], reference_observations=context["references"],
                               source_turn_ids=source_ids, provider=self.provider.name, fixture=self.provider.fixture).model_dump()
        return {"brief": brief, "assistant_message": result.assistant_message}

    def _validator(self, state):
        self._event(state["project_id"], state["request_id"], "character_validator")
        context = self._context(self._operation(state["project_id"], state["request_id"]))
        return {"issues": validate_direction(state["brief"], context)}

    def _evaluator(self, state):
        pid, request_id = state["project_id"], state["request_id"]
        context = {"project_id": pid, "brief": state["brief"],
                   "request_context": self._context(self._operation(pid, request_id))}
        evaluation = DirectionEvaluation.model_validate(self._call(pid, request_id, "character_evaluator", "evaluate", context)).model_dump()
        if evaluation["project_id"] != pid or evaluation["version"] != state["brief"]["version"]:
            raise CharacterConflict("평가가 현재 프로젝트·캐릭터 방향 버전과 다릅니다.")
        issues = [*state["issues"], *evaluation["issues"]]
        if evaluation["recommendation"] != "ready_for_human":
            issues.append({"code": "evaluation_needs_revision", "severity": "blocker",
                           "message": "평가에서 수정할 부분이 남았습니다. 방향을 수정한 후 다시 확인하세요."})
        return {"evaluation": evaluation, "issues": issues}

    def _review(self, state):
        self._event(state["project_id"], state["request_id"], "human_review")
        response = interrupt({"kind": "character_direction_review", "project_id": state["project_id"],
                              "version": state["brief"]["version"]})
        if response != {"confirm_version": state["brief"]["version"]}:
            raise CharacterConflict("현재 캐릭터 방향 버전의 사람 확인이 필요합니다.")
        return {}

    def _build_graph(self):
        graph = StateGraph(CharacterGraphState)
        graph.add_node("designer", self._designer)
        graph.add_node("validator", self._validator)
        graph.add_node("evaluator", self._evaluator)
        graph.add_node("human_review", self._review)
        graph.add_edge(START, "designer")
        graph.add_edge("designer", "validator")
        graph.add_edge("validator", "evaluator")
        graph.add_edge("evaluator", "human_review")
        graph.add_edge("human_review", END)
        return graph.compile(checkpointer=self.checkpointer)

    def _execute_turn(self, pid, request_id):
        op = self._operation(pid, request_id)
        if op["status"] == "completed":
            response = self._validated_state(op["response"])
            if response["project_id"] != pid:
                raise CharacterConflict("보존된 응답의 프로젝트 경계가 맞지 않습니다.")
            return response
        op = self._validate_operation(pid, request_id, op)
        base = op["base_state"]
        state = copy.deepcopy(base)
        request = op["request"]
        state["messages"].append({"id": f"{request_id}-user", "role": "user", "content": request["message"],
                                  "at": now(), "version": None})
        try:
            config = self._config(pid, request_id)
            with tracing_context(enabled=False):
                snapshot = self.graph.get_state(config)
                if snapshot.values and (snapshot.values.get("project_id") != pid or snapshot.values.get("request_id") != request_id):
                    raise CharacterConflict("보존된 대화 체크포인트의 프로젝트 경계가 맞지 않습니다.")
                if not snapshot.values:
                    self.graph.invoke({"project_id": pid, "request_id": request_id}, config)
                elif snapshot.next and not any(task.interrupts for task in snapshot.tasks):
                    self.graph.invoke(None, config)
                values = self.graph.get_state(config).values
            brief = CharacterBrief.model_validate(values["brief"]).model_dump()
            state["brief"] = brief
            state["versions"].append(copy.deepcopy(brief))
            state["issues"] = values["issues"]
            state["evaluations"].append(values["evaluation"])
            state["unknowns"] = unknown_fields(brief)
            state["question_field"] = state["unknowns"][0] if state["unknowns"] else "review"
            state["next_question"] = QUESTIONS[state["question_field"]]
            state["can_confirm"] = not state["unknowns"] and not any(issue["severity"] == "blocker" for issue in state["issues"])
            state["status"] = "blocked" if any(issue["severity"] == "blocker" for issue in state["issues"]) else (
                "awaiting_review" if state["can_confirm"] else "awaiting_input")
            state["messages"].append({"id": f"{request_id}-assistant", "role": "assistant", "content": values["assistant_message"],
                                      "at": now(), "version": brief["version"]})
        except Exception:
            # Keep raw provider, validation and transport errors out of user state and logs.
            state["issues"] = [{"code": "character_execution_failed", "severity": "blocker",
                                "message": "이번 대화를 처리하지 못했습니다. 이전 방향을 보존했습니다. 입력을 확인해 다시 보내주세요."}]
            state["status"], state["can_confirm"] = "blocked", False
            state["messages"].append({"id": f"{request_id}-assistant", "role": "assistant",
                                      "content": state["issues"][0]["message"], "at": now(), "version": None})
        state.update(revision=base["revision"] + 1, direction_confirmed=False, stage="direction", active_request_id=request_id,
                     provider=self.provider.name, fixture=self.provider.fixture)
        with self._db_lock, self.db:
            current = self.get_state(pid)
            self._assert_revision(current, base["revision"])
            op = self._operation(pid, request_id)
            state["events"].extend(op["events"])
            state = self._validated_state(state)
            if len(state["versions"]) > len(base["versions"]):
                self.db.execute("INSERT INTO character_versions VALUES(?,?,?)", (pid, state["brief"]["version"], dump(state["brief"])))
            self.db.execute("UPDATE character_states SET payload=? WHERE project_id=?", (dump(state), pid))
            op.update(status="completed", response=state)
            self._save_operation(pid, request_id, op)
        return state

    def confirm_direction(self, pid, request: dict):
        return self._decision(pid, request, "confirm")

    def reopen_direction(self, pid, request: dict):
        return self._decision(pid, request, "reopen")

    def _decision(self, pid, request, kind):
        request = DirectionDecisionRequest.model_validate(request).model_dump()
        self._validate_pid(pid)
        with self._lock_for(pid):
            replay = self._replay(pid, kind, request)
            if replay is not None:
                return replay
            state = self.get_state(pid)
            self._assert_revision(state, request["expected_revision"])
            if not state["brief"] or state["brief"]["version"] != request["expected_version"]:
                raise CharacterConflict("현재 표시된 캐릭터 방향의 정확한 버전이 필요합니다.")
            if kind == "confirm":
                if not state["can_confirm"] or state["direction_confirmed"]:
                    raise CharacterConflict("필요한 입력과 수정 사항을 확인한 후 방향을 확정할 수 있습니다.")
                config = self._config(pid, state["active_request_id"])
                with tracing_context(enabled=False):
                    snapshot = self.graph.get_state(config)
                    if snapshot.next:
                        self.graph.invoke(Command(resume={"confirm_version": request["expected_version"]}), config)
                state.update(stage="candidates", status="confirmed", direction_confirmed=True, can_confirm=False,
                             next_question="캐릭터 후보 이미지를 연결할 준비 단계입니다. 시각 후보와 캐릭터 시트는 아직 완성되지 않았습니다.")
            else:
                if not state["direction_confirmed"]:
                    raise CharacterConflict("확인한 캐릭터 방향만 수정 단계로 돌아갈 수 있습니다.")
                missing = unknown_fields(state["brief"])
                blocked = any(issue["severity"] == "blocker" for issue in state["issues"])
                question_field = missing[0] if missing else "review"
                state.update(stage="direction", direction_confirmed=False, unknowns=missing,
                             can_confirm=not missing and not blocked,
                             status="blocked" if blocked else ("awaiting_input" if missing else "awaiting_review"),
                             next_question=QUESTIONS[question_field], question_field=question_field)
            state["revision"] += 1
            state["decisions"].append({"request_id": request["request_id"], "kind": kind, "actor": "human", "at": now(),
                                       "project_id": pid, "artifact_id": state["brief"]["artifact_id"],
                                       "version": request["expected_version"], "scope": "synthetic_character_direction_review"})
            state = self._validated_state(state)
            with self._db_lock, self.db:
                self._assert_revision(self.get_state(pid), request["expected_revision"])
                self.db.execute("UPDATE character_states SET payload=? WHERE project_id=?", (dump(state), pid))
                self._record_operation(pid, kind, request, {"response": state}, status="completed")
            return state
