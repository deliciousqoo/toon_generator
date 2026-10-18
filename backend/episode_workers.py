"""Bounded episode roles sharing the application's own ChatGPT connection."""
import copy

from .episode_contracts import BoardDraft, Evaluation, IntakeDraft, StoryDraft


CREATIVE_OUTPUT_RULE = (
    "Never place internal project or episode IDs, hashes, version numbers, or workflow bookkeeping in creative fields, "
    "assistant_message, or next_question. Metadata is server-managed. Preserve only actual creative constraints in intent.constraints. ")


class SubscriptionEpisodeProvider:
    name = "chatgpt_subscription"
    fixture = False

    def __init__(self, connection):
        self.connection = connection

    def execution_identity(self):
        return self.connection.execution_identity()

    def _call(self, role, context, contract, instructions):
        clean = {k: v for k, v in context.items() if k != "_image_inputs"}
        return self.connection.call_structured(role, clean, contract, instructions, image_inputs=context.get("_image_inputs", []))

    def intake(self, context):
        return self._call("episode_orchestrator", context, IntakeDraft,
            CREATIVE_OUTPUT_RULE + "Extract the user's topic, intended emotion, ending and constraints into intent. Preserve known values unless explicitly changed. "
            "Do not invent events or identity facts. Ask at most one consequential next_question for missing information. "
            "If topic, intended_emotion and ending are all clear, leave next_question empty and briefly invite the user to draft the story. "
            "Do not propose a cut count or storyboard before human story confirmation. assistant_message summarizes known intent.")

    def story(self, context):
        return self._call("episode_story_writer", context, StoryDraft,
            CREATIVE_OUTPUT_RULE + "Draft an original short fictional story from the confirmed character snapshot and user's intent. "
            "Use concrete observable events, causal change and payoff. Respect personality, voice, identity invariants, avoid elements and abstract-only references. "
            "Use one to eight beats with stable IDs beat-1, beat-2 etc and consecutive order starting at 1. Do not propose panels or cut counts. "
            "Preserve supplied wording unless the user requested rewriting it. For a revision preserve every non-target beat and every field outside edit_fields exactly. "
            "When target_ids is nonempty, title, premise, payoff, all beat IDs and order must remain exactly unchanged. "
            "assistant_message briefly explains what changed and leaves human confirmation to the user.")

    def storyboard(self, context):
        return self._call("episode_storyboard_planner", context, BoardDraft,
            CREATIVE_OUTPUT_RULE + "Plan exactly format.cut_count ordered panels using the exact human-confirmed story and format. Map every story beat through beat_ids. "
            "Use stable IDs panel-1, panel-2 etc, consecutive order, readable distinct visual actions, expressions, framing, composition, background and continuity. "
            "The attached images are the approved character sheet; retain its design and identity. Dialogue is separate overlay, never generated inside artwork. "
            "Preserve story dialogue and meaning unless the user's scoped feedback explicitly requests a change. "
            "For scoped edits preserve all non-target panels byte-for-byte and every field outside edit_fields on target panels, including IDs/order/beat_ids. "
            "Return written instructions only; do not claim rough images exist or that G2 is approved. assistant_message summarizes the proposed change.")

    def evaluate(self, context):
        return self._call("episode_independent_evaluator", context, Evaluation,
            "Independently review the supplied draft against the immutable character snapshot, actual attached sheet images, intent, exact source versions, user feedback and edit scope. "
            "Check causal story progression, character action/voice/design fidelity, preserved wording, no distinctive reference copying, and for panels complete beat coverage and readable visual staging. "
            "A missing rough image is expected at this written planning stage and is not a draft blocker. Never creatively approve, infer rights, or publish. "
            "Return project_id, episode_id, version and snapshot_fingerprint exactly from context. Concrete issues and evidence only; ready_for_human means a human may review this draft.")


class FixtureEpisodeProvider:
    """Explicit engineering fixture used only by isolated tests/dev fixture mode."""
    name = "deterministic_episode_fixture"
    fixture = True

    def intake(self, context):
        value = copy.deepcopy(context["intent"])
        value.update(topic=context["message"], intended_emotion="친근함", ending="작은 발견")
        return {"intent": value, "assistant_message": "검증용 이야기 방향을 정리했습니다.", "next_question": ""}

    def story(self, context):
        previous = context.get("previous")
        if previous:
            result = {k: copy.deepcopy(previous[k]) for k in StoryDraft.model_fields}
            for beat in result["beats"]:
                if not context["target_ids"] or beat["id"] in context["target_ids"]:
                    for field in context["edit_fields"] or ["action"]:
                        beat[field] = context["message"]
            result["assistant_message"] = "지정한 이야기 부분을 수정했습니다."
            return result
        return {"title": "가상 씨앗 돌보기", "premise": context["intent"]["topic"],
            "beats": [{"id": "beat-1", "order": 1, "action": "작은 씨앗을 화분에 심는다.", "emotion": "호기심", "dialogue": "천천히 자라렴."},
                      {"id": "beat-2", "order": 2, "action": "물 한 방울을 주고 기다린다.", "emotion": "기대", "dialogue": "오늘은 어떨까?"},
                      {"id": "beat-3", "order": 3, "action": "돋아난 새싹을 발견한다.", "emotion": "기쁨", "dialogue": "작은 변화도 반가워."}],
            "payoff": "기다림 끝에 작은 변화를 발견한다.", "assistant_message": "검증용 이야기 초안입니다."}

    def storyboard(self, context):
        if context.get("previous"):
            result = {k: copy.deepcopy(context["previous"][k]) for k in BoardDraft.model_fields}
            for panel in result["panels"]:
                if not context["target_ids"] or panel["id"] in context["target_ids"]:
                    for field in context["edit_fields"] or ["action"]:
                        panel[field] = context["message"]
            result["assistant_message"] = "지정한 컷을 수정했습니다."
            return result
        beats = context["story"]["beats"]
        count = context["format"]["cut_count"]
        panels = []
        for index in range(count):
            assigned = [beat for n, beat in enumerate(beats) if min(n * count // len(beats), count - 1) == index]
            if not assigned:
                assigned = [beats[min(index, len(beats) - 1)]]
            panels.append({"id": f"panel-{index+1}", "order": index + 1, "beat_ids": [b["id"] for b in assigned],
                "scene": "작은 화분 앞", "action": " ".join(b["action"] for b in assigned), "expression": assigned[-1]["emotion"],
                "dialogue": " ".join(b["dialogue"] for b in assigned), "camera": "눈높이 중간 거리",
                "composition": "캐릭터와 화분이 함께 보임", "background": "흰 배경", "continuity": "확정 시트의 몸과 잎사귀 유지",
                "text_placement": "그림 아래 별도 대사 영역"})
        return {"panels": panels, "assistant_message": "검증용 글 콘티입니다. 실제 러프 이미지는 별도입니다."}

    def evaluate(self, context):
        return {"project_id": context["project_id"], "episode_id": context["episode_id"], "version": context["version"],
            "snapshot_fingerprint": context["snapshot_fingerprint"], "recommendation": "ready_for_human", "issues": [],
            "evidence": ["독립 역할과 사람 확인 경계를 검사하는 명시적 개발 fixture입니다."]}
