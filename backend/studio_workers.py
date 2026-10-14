"""Bounded role workers; default fixtures do not claim creative AI output."""
import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Protocol

import httpx

from .studio_contracts import StoryArtifact, StoryboardArtifact


class TextProvider(Protocol):
    name: str
    fixture: bool

    def story(self, context: dict) -> dict: ...
    def evaluate_story(self, context: dict) -> dict: ...
    def storyboard(self, context: dict) -> dict: ...
    def evaluate_board(self, context: dict) -> dict: ...


class DeterministicFixtureProvider:
    name = "deterministic_fixture"
    fixture = True

    def story(self, context):
        """A transparent developer fixture, not an imitation of a story model."""
        previous = context.get("previous")
        feedback = context.get("feedback", "")
        if previous:
            draft = copy.deepcopy(previous)
            if feedback:
                draft["feedback_applied"].append(feedback)
                if feedback.startswith("대사:"):
                    draft["beats"][-1]["dialogue"] = feedback[3:].strip()
                elif feedback.startswith("행동:"):
                    draft["beats"][-1]["action"] = feedback[3:].strip()
                else:
                    draft["narrative_intent"] = f"합성 수정 fixture 메모: {feedback}"
            return draft
        idea = context["idea"]
        return {
            "understanding": f"입력 종류는 {context['input_kind']}이며 다음 합성 입력을 보존합니다: {idea}",
            "premise": idea,
            "narrative_intent": "합성 입력에서 시작·변화·마무리 데이터 전달과 사람 확인 흐름을 검증합니다.",
            "beats": [
                {"id": "beat-1", "order": 1, "action": f"입력의 상황 제시: {idea}", "emotion": "상황을 관찰함", "dialogue": idea if context["input_kind"] == "script" else "", "visual_purpose": "주인공과 시작 상황을 소개"},
                {"id": "beat-2", "order": 2, "action": "합성 주인공이 상황을 확인하고 잠깐 멈춤", "emotion": "고민함", "dialogue": "", "visual_purpose": "이전 상황에 대한 반응을 보여줌"},
                {"id": "beat-3", "order": 3, "action": "합성 주인공이 방향을 정하고 다음 행동을 준비함", "emotion": "결정함", "dialogue": "", "visual_purpose": "시작과 달라진 상태를 보여줌"},
            ],
            "payoff": "fixture의 마지막 상태를 확인합니다. 창작 이야기 품질은 아직 평가되지 않았습니다.",
            "feedback_applied": [], "provider": self.name, "fixture": True,
        }

    def evaluate_story(self, context):
        return {"recommendation": "ready_for_human", "issues": [], "feedback": "",
                "evidence": ["결정론적 개발용 평가 fixture이며 창작 품질을 검증하지 않습니다."],
                "source_versions": context["source_versions"]}

    def storyboard(self, context):
        return make_board(context["story"], context["format_proposal"], context["metadata"],
                          context.get("previous"), context.get("feedback", ""), context.get("target_ids"))

    def evaluate_board(self, context):
        return {"recommendation": "ready_for_human", "issues": [], "feedback": "",
                "evidence": ["컷 데이터의 기술 흐름 평가 fixture입니다. 시각 콘티·G2 검토는 미완료입니다."],
                "source_versions": context["source_versions"]}


class OllamaJSONProvider:
    """Opt-in loopback-only text adapter. No external upload and no image calls."""
    name = "ollama_local_json"
    fixture = False

    def __init__(self, model: str, *, approval: dict, approval_key: str):
        if not model.strip():
            raise ValueError("로컬 텍스트 모델 이름이 필요합니다.")
        self.model = model
        self.approval = approval
        self.budget_id = approval_key

    def _call(self, role, context, fields, instructions):
        # Each role uses its own request and rubric, never a generator self-score.
        prompt = (f"You are the independent {role} role for a synthetic local engineering test. "
                  f"Return only JSON fields {','.join(sorted(fields))}. Use Korean. "
                  "Never approve content or publication. Preserve exact source_versions supplied in context. "
                  "Never invent reference sources or character identity. " + instructions +
                  "\nContext:\n" + json.dumps(context, ensure_ascii=False))
        with httpx.Client(timeout=httpx.Timeout(min(30, self.approval["timeout_seconds"])), trust_env=False) as client:
            response = client.post("http://127.0.0.1:11434/api/generate", json={
                "model": self.model, "prompt": prompt, "stream": False, "format": "json",
                "options": {"temperature": 0.2, "num_predict": 2500},
            })
            response.raise_for_status()
            result = json.loads(response.json()["response"])
        if set(result) != fields:
            raise ValueError(f"텍스트 제공자의 {role} 응답이 계약과 다릅니다.")
        return result

    def story(self, context):
        result = self._call("story_generator", context, {"understanding", "premise", "narrative_intent", "beats", "payoff", "feedback_applied"},
            "Each beat has id,order,action,emotion,dialogue,visual_purpose. Keep original script/dialogue "
            "verbatim outside requested edit scope. Apply feedback precisely; preserve unaffected beats. "
            "Develop a concrete situation, character action, emotional turn and payoff.")
        return {**result, "provider": self.name, "fixture": False}

    def _evaluate(self, role, context, rubric):
        return self._call(role, context, {"recommendation", "issues", "feedback", "evidence", "source_versions"},
            rubric + " recommendation must be revise|ready_for_human|blocked. "
            "issues contain severity:blocker|warning,stage,code,message,target_id(null or exact beat/panel ID). "
            "Only recommend revise with concrete scoped feedback and evidence. Do not score hidden visual quality; "
            "these are written drafts. Evaluate the exact supplied artifact and versions.")

    def evaluate_story(self, context):
        return self._evaluate("story_evaluator", context,
            "Check concrete premise, causality, character invariants/voice, preserved original dialogue, "
            "ordered actions, emotional turn and payoff. Identify exact affected beats.")

    def storyboard(self, context):
        result = self._call("storyboard_planner", context, {"panels", "feedback_applied"},
            "Plan written cut data only. Every panel has id,order,beat_id,scene,action,expression,dialogue,camera,background,"
            "composition,visual_purpose,gaze_target,pacing,text_placement,continuity,thumbnail. "
            "thumbnail={kind:developer_text_fixture,description:readable planned visual,usable_storyboard:false}. "
            "Use exact existing panel IDs when revising; otherwise content_id-panel-order IDs. "
            "Preserve unaffected fields and panels. Dialogue-only edits must not alter action/pose/scene. "
            "Retain all story beats and exact story dialogue. Never claim these text notes are visual roughs.")
        return StoryboardArtifact.model_validate({**context["metadata"], **result,
            "story_version": context["story"]["version"], "format_version": context["format_proposal"]["version"],
            "usable_storyboard": False, "fixture": False}).model_dump()

    def evaluate_board(self, context):
        return self._evaluate("board_evaluator", context,
            "Check complete beat coverage, each panel's action/expression/staging/focal event, "
            "meaningful beat-to-beat change, dialogue readability, continuity, character invariants and intended pacing. "
            "Do not infer visual rough quality from text. Technical review can be ready while creative G2 remains pending.")


def configured_provider():
    # Explicit local opt-in is independent of any external/image execution gate.
    if os.environ.get("TOON_STUDIO_ENABLE_OLLAMA") == "1":
        model = os.environ.get("TOON_STUDIO_OLLAMA_MODEL", "")
        approval_path = os.environ.get("TOON_STUDIO_PROVIDER_APPROVAL_FILE", "")
        if not approval_path:
            raise ValueError("로컬 모델 활성화에는 P1 실행 승인 기록 파일이 필요합니다.")
        try:
            raw = Path(approval_path).read_bytes()
            approval = json.loads(raw)
        except (OSError, ValueError) as error:
            raise ValueError("P1 실행 승인 기록 파일을 읽을 수 없습니다.") from error
        if (not isinstance(approval, dict) or approval.get("execution_authorized") is not True or
                approval.get("provider") != "ollama_local_json" or approval.get("model") != model or not model.strip() or
                approval.get("input_scope") != "synthetic_stage04" or approval.get("endpoint") != "http://127.0.0.1:11434" or
                type(approval.get("max_calls")) is not int or not 1 <= approval["max_calls"] <= 48 or
                type(approval.get("timeout_seconds")) not in (int, float) or not 0 < approval["timeout_seconds"] <= 120):
            raise ValueError("P1 기록의 실행 허가·모델·합성 입력 범위·로컬 주소·호출/시간 한도가 맞지 않습니다.")
        return OllamaJSONProvider(model, approval=approval, approval_key=hashlib.sha256(raw).hexdigest())
    return DeterministicFixtureProvider()


def make_story(context: dict, provider: TextProvider, metadata: dict):
    return StoryArtifact.model_validate({**provider.story(context), **metadata}).model_dump()


def evaluate_story(story: dict, context: dict):
    """Independent deterministic evaluator, with no creative approval authority."""
    issues = []
    beats = story["beats"]
    if len({b["id"] for b in beats}) != len(beats) or [b["order"] for b in beats] != list(range(1, len(beats) + 1)):
        issues.append({"severity": "blocker", "stage": "story", "code": "beat_order", "message": "비트 ID와 읽기 순서가 중복되거나 끊겼습니다."})
    if context["input_kind"] == "script" and not context.get("feedback"):
        combined = "\n".join(b["dialogue"] for b in beats)
        if context["idea"] not in combined:
            issues.append({"severity": "blocker", "stage": "story", "code": "script_preservation", "message": "사용자가 준 스크립트를 수정 범위 밖에서 변경했습니다."})
    previous = context.get("previous_story")
    feedback = context.get("feedback", "")
    if previous and feedback.startswith(("대사:", "행동:")):
        allowed = "dialogue" if feedback.startswith("대사:") else "action"
        for key in ("understanding", "premise", "narrative_intent", "payoff"):
            if story[key] != previous[key]:
                issues.append({"severity": "blocker", "stage": "story", "code": "outside_edit_scope", "message": "국소 수정이 이야기의 다른 결정을 변경했습니다.", "target_id": previous["beats"][-1]["id"]})
                break
        if len(story["beats"]) != len(previous["beats"]):
            issues.append({"severity": "blocker", "stage": "story", "code": "outside_edit_scope", "message": "국소 수정으로 비트 수가 변경됐습니다."})
        else:
            for index, (before, after) in enumerate(zip(previous["beats"], story["beats"])):
                permitted = {allowed} if index == len(story["beats"]) - 1 else set()
                if any(after[key] != value for key, value in before.items() if key not in permitted):
                    issues.append({"severity": "blocker", "stage": "story", "code": "outside_edit_scope", "message": "요청한 필드 밖의 비트 내용이 변경됐습니다.", "target_id": before["id"]})
    if story["fixture"]:
        issues.append({"severity": "warning", "stage": "story", "code": "fixture_quality_pending", "message": "결정론적 개발 fixture입니다. 이야기 창작·품질 검증이 끝난 결과가 아닙니다."})
    else:
        issues.append({"severity": "warning", "stage": "story", "code": "human_quality_review", "message": "형식·입력 보존 검사만 수행했습니다. 이야기의 재미와 캐릭터 목소리는 사람이 검토해야 합니다."})
    return issues


def make_board(story: dict, proposal: dict, metadata: dict, previous=None, feedback="", target_ids=None):
    if previous:
        draft = copy.deepcopy(previous)
        draft.update(metadata)
        targets = set(target_ids or [p["id"] for p in draft["panels"]])
        for panel in draft["panels"]:
            if panel["id"] in targets:
                if feedback.startswith("대사:"):
                    panel["dialogue"] = feedback[3:].strip()
                elif feedback.startswith("행동:"):
                    panel["action"] = feedback[3:].strip()
                    panel["thumbnail"]["description"] = f"개발용 텍스트 fixture 행동 변경: {feedback[3:].strip()}"
                else:
                    panel["thumbnail"]["description"] = f"개발용 텍스트 fixture 수정 메모: {feedback}"
        draft["feedback_applied"].append(feedback)
        return StoryboardArtifact.model_validate(draft).model_dump()
    panels = []
    for beat in story["beats"]:
        panels.append({
            "id": f"{metadata['content_id']}-panel-{beat['order']}", "order": beat["order"], "beat_id": beat["id"],
            "scene": "합성 검증용 동일한 공간", "action": beat["action"], "expression": beat["emotion"],
            "dialogue": beat["dialogue"], "camera": "중간 거리에서 주인공의 행동 확인",
            "background": "새 캐릭터·브랜드·실제 자료 없는 합성 배경", "composition": "행동의 대상과 주인공을 같은 읽기 흐름에 배치",
            "visual_purpose": beat["visual_purpose"], "gaze_target": "현재 행동의 대상", "pacing": "한 비트의 변화가 읽힌 후 다음 컷으로 이동",
            "text_placement": "그림 밖 별도 overlay 영역", "continuity": "synthetic character fixture 1.0.0의 정체성 유지",
            "thumbnail": {"kind": "developer_text_fixture", "description": f"시각 콘티 필요: {beat['action']} / 표정: {beat['emotion']}", "usable_storyboard": False},
        })
    return StoryboardArtifact.model_validate({**metadata, "story_version": story["version"], "format_version": proposal["version"],
        "panels": panels, "feedback_applied": [], "usable_storyboard": False, "fixture": True}).model_dump()


def evaluate_board(board: dict, story: dict, proposal: dict, previous=None, feedback="", target_ids=None):
    issues = []
    if board["story_version"] != story["version"] or board["format_version"] != proposal["version"]:
        issues.append({"severity": "blocker", "stage": "storyboard", "code": "stale_source", "message": "콘티가 현재 확인된 이야기·형식 버전과 다릅니다."})
    beat_ids = {b["id"] for b in story["beats"]}
    panels = board["panels"]
    if (len({p["id"] for p in panels}) != len(panels) or
            [p["order"] for p in panels] != list(range(1, len(panels) + 1)) or len(panels) != proposal["cut_count"]):
        issues.append({"severity": "blocker", "stage": "storyboard", "code": "panel_order_count", "message": "컷 ID·순서·확인한 컷 수가 맞지 않습니다."})
    if {p["beat_id"] for p in panels} != beat_ids:
        issues.append({"severity": "blocker", "stage": "storyboard", "code": "beat_coverage", "message": "확인한 이야기의 모든 비트를 콘티에 연결해야 합니다."})
    for panel in board["panels"]:
        if panel["beat_id"] not in beat_ids:
            issues.append({"severity": "blocker", "stage": "storyboard", "code": "unlinked_beat", "message": "이야기 비트에 연결되지 않은 컷입니다.", "target_id": panel["id"]})
    if previous:
        targets = set(target_ids or [p["id"] for p in previous["panels"]])
        old = {p["id"]: p for p in previous["panels"]}
        for panel in panels:
            before = old.get(panel["id"])
            if not before:
                issues.append({"severity": "blocker", "stage": "storyboard", "code": "outside_edit_scope", "message": "수정 중 컷 ID를 새로 만들었습니다.", "target_id": panel["id"]})
                continue
            allowed = set()
            if panel["id"] in targets:
                if feedback.startswith("대사:"):
                    allowed = {"dialogue"}
                elif feedback.startswith("행동:"):
                    allowed = {"action", "thumbnail"}
                else:
                    allowed = set(panel)
            if any(panel[key] != value for key, value in before.items() if key not in allowed):
                issues.append({"severity": "blocker", "stage": "storyboard", "code": "outside_edit_scope", "message": "수정 대상·필드 밖의 컷이 변경됐습니다.", "target_id": panel["id"]})
    if proposal["text_mode"] != "overlay":
        issues.append({"severity": "blocker", "stage": "storyboard", "code": "unsupported_text_mode", "message": "이 텍스트 렌더링 모드는 구현되지 않았습니다. 자동으로 overlay로 바꾸지 않습니다."})
    issues.append({"severity": "warning", "stage": "storyboard", "code": "production_visual_rough_required", "message": "현재는 개발용 텍스트 fixture입니다. 합성 기술 흐름만 확인할 수 있으며 시각 콘티·창작 품질 검토 전에는 G2 승인과 이미지 생성이 불가능합니다."})
    return issues
