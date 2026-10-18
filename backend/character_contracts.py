"""Project-scoped character direction contracts; a direction is never a visual sheet."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


SCHEMA_ID = "toon-character-direction-v1"


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ReferenceObservation(Contract):
    label: str = Field(min_length=1, max_length=200)
    desired_traits: list[str] = Field(min_length=1, max_length=12)
    not_to_copy: list[str] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def bounded_notes(self):
        if any(not value.strip() or len(value) > 1000 for value in [*self.desired_traits, *self.not_to_copy]):
            raise ValueError("레퍼런스 관찰은 비어 있지 않은 짧은 특징으로 기록하세요.")
        return self


class DirectionFields(Contract):
    appearance: str = Field(default="", max_length=3000)
    personality: str = Field(default="", max_length=3000)
    desired_feeling: str = Field(default="", max_length=3000)
    voice: str = Field(default="", max_length=2000)
    identity_invariants: list[str] = Field(default_factory=list, max_length=20)
    avoid_elements: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def bounded_traits(self):
        if any(not value.strip() or len(value) > 1000 for value in [*self.identity_invariants, *self.avoid_elements]):
            raise ValueError("특징 목록은 비어 있지 않은 짧은 문장으로 기록하세요.")
        return self


class FieldUpdates(Contract):
    appearance: str | None = Field(default=None, max_length=3000)
    personality: str | None = Field(default=None, max_length=3000)
    desired_feeling: str | None = Field(default=None, max_length=3000)
    voice: str | None = Field(default=None, max_length=2000)
    identity_invariants: list[str] | None = Field(default=None, max_length=20)
    avoid_elements: list[str] | None = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def bounded_traits(self):
        if any(not value.strip() or len(value) > 1000 for value in [*(self.identity_invariants or []), *(self.avoid_elements or [])]):
            raise ValueError("특징 목록은 비어 있지 않은 짧은 문장으로 기록하세요.")
        return self


class TurnRequest(Contract):
    request_id: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_-]+$")
    expected_revision: int = Field(ge=0, strict=True)
    message: str = Field(min_length=1, max_length=3000)
    synthetic_confirmed: Literal[True]
    field_updates: FieldUpdates = Field(default_factory=FieldUpdates)
    references: list[ReferenceObservation] | None = Field(default=None, max_length=12)


class DirectionDecisionRequest(Contract):
    request_id: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_-]+$")
    expected_revision: int = Field(ge=0, strict=True)
    expected_version: str = Field(pattern=r"^1\.0\.[1-9][0-9]*$")


class CharacterBrief(DirectionFields):
    artifact_id: str
    project_id: str
    version: str = Field(pattern=r"^1\.0\.[1-9][0-9]*$")
    reference_observations: list[ReferenceObservation] = Field(default_factory=list, max_length=12)
    source_turn_ids: list[str] = Field(default_factory=list)
    provider: str
    fixture: bool


class CharacterIssue(Contract):
    code: str
    severity: Literal["warning", "blocker"]
    message: str


class DirectionDraft(Contract):
    fields: DirectionFields
    assistant_message: str = Field(min_length=1, max_length=4000)


class DirectionEvaluation(Contract):
    recommendation: Literal["ready_for_human", "revise", "blocked"]
    issues: list[CharacterIssue] = Field(default_factory=list, max_length=20)
    evidence: list[str] = Field(min_length=1, max_length=20)
    project_id: str
    version: str


class DialogueMessage(Contract):
    id: str
    role: Literal["user", "assistant"]
    content: str
    at: str
    version: str | None = None


class CharacterState(Contract):
    schema_id: Literal[SCHEMA_ID] = SCHEMA_ID
    project_id: str
    revision: int = Field(default=0, ge=0, strict=True)
    stage: Literal["direction", "candidates"] = "direction"
    status: Literal["awaiting_input", "awaiting_review", "confirmed", "blocked"] = "awaiting_input"
    direction_confirmed: bool = False
    visual_ready: Literal[False] = False
    sheet_approved: Literal[False] = False
    fixture: bool
    provider: str
    brief: CharacterBrief | None = None
    messages: list[DialogueMessage] = Field(default_factory=list)
    next_question: str
    question_field: Literal["appearance", "personality", "desired_feeling", "review"] = "appearance"
    unknowns: list[str] = Field(default_factory=list)
    issues: list[CharacterIssue] = Field(default_factory=list)
    can_confirm: bool = False
    versions: list[CharacterBrief] = Field(default_factory=list)
    decisions: list[dict] = Field(default_factory=list)
    events: list[dict] = Field(default_factory=list)
    evaluations: list[DirectionEvaluation] = Field(default_factory=list)
    active_request_id: str | None = None
    engine: Literal["langgraph_sqlite"] = "langgraph_sqlite"

    @model_validator(mode="after")
    def scope_and_gate(self):
        owned = [*self.versions, *([self.brief] if self.brief else [])]
        if any(item.project_id != self.project_id for item in owned):
            raise ValueError("다른 프로젝트의 캐릭터 방향이 포함되어 있습니다.")
        if any(item.project_id != self.project_id for item in self.evaluations):
            raise ValueError("다른 프로젝트의 캐릭터 평가가 포함되어 있습니다.")
        if [item.version for item in self.versions] != [f"1.0.{index}" for index in range(1, len(self.versions) + 1)]:
            raise ValueError("캐릭터 방향 버전 이력이 연속적이지 않습니다.")
        if self.brief and (not self.versions or self.brief != self.versions[-1]):
            raise ValueError("현재 캐릭터 방향과 보존된 정확 버전이 다릅니다.")
        if self.can_confirm and (not self.brief or self.direction_confirmed or self.unknowns
                                 or unknown_fields(self.brief.model_dump())
                                 or any(issue.severity == "blocker" for issue in self.issues)):
            raise ValueError("필수 입력이나 수정 사항이 남은 방향을 확인할 수 없습니다.")
        if any(item.get("project_id") != self.project_id for item in self.decisions):
            raise ValueError("다른 프로젝트의 사람 결정이 포함되어 있습니다.")
        if self.direction_confirmed and (not self.brief or self.stage != "candidates"):
            raise ValueError("확인한 방향의 정확한 버전이 필요합니다.")
        return self


QUESTIONS = {
    "appearance": "어떤 모습의 캐릭터를 만들까요? 외형이나 떠오르는 특징을 알려주세요.",
    "personality": "이 캐릭터는 어떤 성격인가요? 평소 행동도 함께 알려주세요.",
    "desired_feeling": "캐릭터를 볼 때 어떤 느낌이 들었으면 하나요?",
    "review": "정리한 방향에서 바꾸거나 더할 부분을 알려주세요.",
}


def unknown_fields(fields: dict) -> list[str]:
    return [key for key in ("appearance", "personality", "desired_feeling") if not fields.get(key, "").strip()]
