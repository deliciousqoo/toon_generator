"""Bounded character roles. Default is an honest input-preserving engineering fixture."""
import copy
import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx

from .character_contracts import DirectionDraft, DirectionEvaluation, DirectionFields


class DeterministicCharacterProvider:
    name = "deterministic_character_fixture"
    fixture = True

    def draft(self, context):
        fields = copy.deepcopy(context["previous_fields"])
        updates = context["field_updates"]
        summary = "입력한 내용을 방향 카드에 반영했습니다."
        if updates:
            fields.update(updates)
        else:
            target = context["question_field"]
            named_field = re.match(r"^(외형|성격|느낌|분위기|말투)\s*[:：]\s*(.+)$", context["message"], re.DOTALL)
            if named_field:
                target = {"외형": "appearance", "성격": "personality", "느낌": "desired_feeling",
                          "분위기": "desired_feeling", "말투": "voice"}[named_field.group(1)]
                fields[target] = named_field.group(2).strip()
            elif target == "review":
                # An ambiguous edit stays in the conversation; the fixture never guesses identity changes.
                summary = "의견을 대화에 기록했습니다. 방향 카드에서 수정할 항목을 선택해주세요."
            else:
                fields[target] = context["message"]
        return {"fields": fields, "assistant_message": summary}

    def evaluate(self, context):
        return {"recommendation": "ready_for_human", "issues": [],
                "evidence": ["입력 전달·수정 흐름을 검사하는 결정론적 fixture이며 독창성이나 창작 품질을 평가하지 않습니다."],
                "project_id": context["project_id"], "version": context["brief"]["version"]}


def validate_approval(approval, model):
    """A Stage 04 grant can never authorize character execution."""
    if (not isinstance(approval, dict) or approval.get("execution_authorized") is not True
            or approval.get("provider") != "ollama_character_local_json" or approval.get("model") != model
            or not model.strip() or approval.get("input_scope") != "synthetic_character_direction"
            or approval.get("endpoint") != "http://127.0.0.1:11434"
            or approval.get("allowed_roles") != ["character_designer", "character_evaluator"]
            or type(approval.get("max_calls")) is not int or not 1 <= approval["max_calls"] <= 48
            or type(approval.get("timeout_seconds")) not in (int, float)
            or not math.isfinite(approval["timeout_seconds"]) or not 0 < approval["timeout_seconds"] <= 120):
        raise ValueError("캐릭터 전용 합성 실행 허가·모델·역할·범위·로컬 주소·한도가 맞지 않습니다.")
    try:
        expiry = datetime.fromisoformat(approval["expires_at"].replace("Z", "+00:00"))
        if expiry.tzinfo is None or expiry <= datetime.now(timezone.utc):
            raise ValueError("expired")
    except (KeyError, TypeError, AttributeError, ValueError) as error:
        raise ValueError("캐릭터 실행 허가의 유효 기간이 없거나 만료됐습니다.") from error


class OllamaCharacterProvider:
    name = "ollama_character_local_json"
    fixture = False

    def __init__(self, model, *, approval, approval_key):
        validate_approval(approval, model)
        self.model, self.approval, self.budget_id = model, approval, approval_key

    def _call(self, role, context, schema, instructions):
        validate_approval(self.approval, self.model)
        prompt = (f"You are the independent {role} role in a synthetic local engineering test. "
                  "Reply in Korean with only JSON matching the supplied schema. Never approve character identity, "
                  "rights, images, sheets or publication. References contain abstract user-described feelings only; "
                  "never reproduce a reference character or infer ownership. Never invent missing decisions. "
                  "Preserve fields outside explicit field_updates and source project/version. " + instructions +
                  "\nJSON schema:\n" + json.dumps(schema, ensure_ascii=False) +
                  "\nContext:\n" + json.dumps(context, ensure_ascii=False))
        with httpx.Client(timeout=min(30, self.approval["timeout_seconds"]), trust_env=False) as client:
            response = client.post("http://127.0.0.1:11434/api/generate", json={
                "model": self.model, "prompt": prompt, "stream": False, "format": schema,
                "options": {"temperature": 0.2, "num_predict": 2200},
            })
            response.raise_for_status()
            if len(response.content) > 200_000:
                raise ValueError("캐릭터 응답 크기 한도를 초과했습니다.")
            return json.loads(response.json()["response"])

    def draft(self, context):
        return self._call("character_designer", context, DirectionDraft.model_json_schema(),
                          "Extract a compact character direction from user turns. Missing essential facts remain empty. "
                          "Do not claim to generate a candidate image or sheet. assistant_message is one short change summary; no question.")

    def evaluate(self, context):
        return self._call("character_evaluator", context, DirectionEvaluation.model_json_schema(),
                          "Assess only the supplied text: input fidelity, no invented identity, no direct reference copying, "
                          "and precise edit scope. Provide evidence. Use ready_for_human, revise or blocked; no human approval.")


def configured_character_provider():
    if os.environ.get("TOON_CHARACTER_ENABLE_OLLAMA") != "1":
        return DeterministicCharacterProvider()
    model = os.environ.get("TOON_CHARACTER_OLLAMA_MODEL", "")
    path = os.environ.get("TOON_CHARACTER_PROVIDER_APPROVAL_FILE", "")
    if not path:
        raise ValueError("캐릭터 전용 실행 승인 기록이 필요합니다.")
    try:
        raw = Path(path).read_bytes()
        approval = json.loads(raw)
    except (OSError, ValueError) as error:
        raise ValueError("캐릭터 실행 승인 기록을 읽을 수 없습니다.") from error
    return OllamaCharacterProvider(model, approval=approval, approval_key=hashlib.sha256(raw).hexdigest())


def validate_direction(brief, context):
    issues = []
    before = context["previous_fields"]
    updates = context["field_updates"]
    if updates:
        for key, value in before.items():
            if key not in updates and brief[key] != value:
                issues.append({"code": "outside_edit_scope", "severity": "blocker",
                               "message": "요청한 항목 밖의 캐릭터 설정이 변경됐습니다."})
                break
    if brief["reference_observations"]:
        issues.append({"code": "reference_review", "severity": "warning",
                       "message": "레퍼런스는 느낌을 이해하는 자료입니다. 독자 캐릭터의 유사성은 시각 후보 단계에서 확인해야 합니다."})
    # Validate the same normalized field contract independently of provider role execution.
    DirectionFields.model_validate({key: brief[key] for key in DirectionFields.model_fields})
    return issues
