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


class CandidateRef(Contract):
    candidate_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,160}$")
    version: str = Field(pattern=r"^1\.0\.[1-9][0-9]*$")


class SheetComponent(Contract):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")
    label: str = Field(min_length=1, max_length=120)


class ImageProvenance(Contract):
    source: Literal["codex_imagegen", "user_upload"]
    model: str | None = Field(default=None, max_length=200)
    workflow: str | None = Field(default=None, max_length=200)
    prompt: str | None = Field(default=None, max_length=24000)
    seed: str | None = Field(default=None, max_length=200)
    unknowns: list[str] = Field(default_factory=list, max_length=20)
    fixture: bool = False

    @model_validator(mode="after")
    def bound_unknowns(self):
        if any(not item.strip() or len(item) > 1000 for item in self.unknowns):
            raise ValueError("출처의 미확인 항목을 짧게 기록하세요.")
        return self


class VisualAsset(Contract):
    id: str = Field(pattern=r"^image-[a-f0-9]{32}$")
    project_id: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    byte_size: int = Field(gt=0, le=32 * 1024 * 1024)
    media_type: Literal["image/png"] = "image/png"
    width: int = Field(gt=0, le=8192)
    height: int = Field(gt=0, le=8192)
    url: str
    provenance: ImageProvenance
    source_asset_ids: list[str] = Field(default_factory=list)


class VisualCandidate(CandidateRef):
    direction_version: str
    asset_id: str
    feedback: str = Field(max_length=3000)
    parent_version: str | None = None
    created_at: str


class VisualJob(Contract):
    id: str = Field(pattern=r"^visual-job-[a-f0-9]{32}$")
    project_id: str
    kind: Literal["candidate", "candidate_revision", "sheet_component"]
    status: Literal["awaiting_image", "completed", "cancelled"]
    direction_version: str
    candidate_id: str
    candidate_version: str | None = None
    component_id: str | None = None
    coverage_version: int = Field(ge=0)
    instruction: str = Field(max_length=3000)
    prompt: str = Field(max_length=24000)
    source_asset_ids: list[str] = Field(default_factory=list)
    asset_id: str | None = None
    created_at: str


class CharacterSheet(Contract):
    id: str
    version: str = Field(pattern=r"^1\.0\.[1-9][0-9]*$")
    project_id: str
    direction_version: str
    candidate_ref: CandidateRef
    coverage_version: int = Field(ge=1)
    coverage: list[SheetComponent] = Field(min_length=1, max_length=16)
    components: dict[str, str]
    created_at: str


class VisualState(Contract):
    assets: list[VisualAsset] = Field(default_factory=list)
    candidates: list[VisualCandidate] = Field(default_factory=list)
    jobs: list[VisualJob] = Field(default_factory=list)
    selected_candidate: CandidateRef | None = None
    coverage: list[SheetComponent] = Field(default_factory=list, max_length=16)
    coverage_version: int = Field(default=0, ge=0)
    components: dict[str, str] = Field(default_factory=dict)
    sheets: list[CharacterSheet] = Field(default_factory=list)
    current_sheet_version: str | None = None
    approved_sheet_version: str | None = None
    decisions: list[dict] = Field(default_factory=list)

    @model_validator(mode="after")
    def exact_lineage(self):
        ids = [asset.id for asset in self.assets]
        if len(set(ids)) != len(ids):
            raise ValueError("시각 자산 ID가 중복됩니다.")
        if len({job.id for job in self.jobs}) != len(self.jobs):
            raise ValueError("시각 작업 ID가 중복됩니다.")
        known_assets = set(ids)
        preceding = {}
        for asset in self.assets:
            if set(asset.source_asset_ids) - set(preceding):
                raise ValueError("원본 시각 자산을 찾을 수 없습니다.")
            if any(preceding[source].provenance.fixture for source in asset.source_asset_ids) and not asset.provenance.fixture:
                raise ValueError("개발용 원본의 출처 표시를 제거할 수 없습니다.")
            preceding[asset.id] = asset
        seen = {}
        for candidate in self.candidates:
            previous = seen.setdefault(candidate.candidate_id, [])
            if candidate.version != f"1.0.{len(previous) + 1}" or candidate.parent_version != (previous[-1] if previous else None):
                raise ValueError("후보 버전 이력이 올바르지 않습니다.")
            previous.append(candidate.version)
            if candidate.asset_id not in known_assets:
                raise ValueError("후보 이미지가 없습니다.")
        refs = {(candidate.candidate_id, candidate.version) for candidate in self.candidates}
        for job in self.jobs:
            if set(job.source_asset_ids) - known_assets or (job.status == "completed") != bool(job.asset_id):
                raise ValueError("시각 작업의 이미지 기록이 올바르지 않습니다.")
            if job.asset_id and job.asset_id not in known_assets:
                raise ValueError("완료한 시각 작업의 이미지가 없습니다.")
            if job.kind != "candidate" and (job.candidate_id, job.candidate_version) not in refs:
                raise ValueError("시각 작업의 정확한 원본 후보가 없습니다.")
            if job.kind == "sheet_component" and (not job.component_id or not job.coverage_version):
                raise ValueError("시트 작업의 구성 버전이 없습니다.")
        if self.selected_candidate and (self.selected_candidate.candidate_id, self.selected_candidate.version) not in refs:
            raise ValueError("선택한 정확 후보 버전이 없습니다.")
        if len({component.id for component in self.coverage}) != len(self.coverage):
            raise ValueError("시트 구성 ID가 중복됩니다.")
        if set(self.components) - {component.id for component in self.coverage} or set(self.components.values()) - known_assets:
            raise ValueError("시트 구성에 알 수 없는 이미지가 있습니다.")
        if [sheet.version for sheet in self.sheets] != [f"1.0.{index}" for index in range(1, len(self.sheets) + 1)]:
            raise ValueError("시트 버전 이력이 올바르지 않습니다.")
        for sheet in self.sheets:
            if (len({part.id for part in sheet.coverage}) != len(sheet.coverage)
                    or (sheet.candidate_ref.candidate_id, sheet.candidate_ref.version) not in refs
                    or set(sheet.components) != {part.id for part in sheet.coverage} or set(sheet.components.values()) - known_assets):
                raise ValueError("시트의 정확한 원본 버전이 없습니다.")
        if self.current_sheet_version and self.current_sheet_version not in {sheet.version for sheet in self.sheets}:
            raise ValueError("현재 시트의 정확 버전이 없습니다.")
        if self.approved_sheet_version and self.approved_sheet_version != self.current_sheet_version:
            raise ValueError("확인한 시트와 현재 시트 버전이 다릅니다.")
        return self


class VisualRequest(Contract):
    request_id: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_-]+$")
    expected_revision: int = Field(ge=0, strict=True)
    expected_direction_version: str = Field(pattern=r"^1\.0\.[1-9][0-9]*$")


class CandidateRequest(VisualRequest):
    candidate_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,160}$")
    candidate_version: str = Field(pattern=r"^1\.0\.[1-9][0-9]*$")


class VisualJobRequest(VisualRequest):
    kind: Literal["candidate", "candidate_revision", "sheet_component"]
    instruction: str = Field(default="", max_length=3000)
    candidate_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,160}$")
    candidate_version: str | None = Field(default=None, pattern=r"^1\.0\.[1-9][0-9]*$")
    component_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,80}$")
    expected_coverage_version: int | None = Field(default=None, ge=1, strict=True)


class VisualUploadRequest(VisualRequest):
    provenance: ImageProvenance


class CoverageRequest(CandidateRequest):
    components: list[SheetComponent] = Field(min_length=1, max_length=16)


class SheetBuildRequest(CandidateRequest):
    expected_coverage_version: int = Field(ge=1, strict=True)


class ComponentAttachRequest(SheetBuildRequest):
    asset_id: str = Field(pattern=r"^image-[a-f0-9]{32}$")


class SheetDecisionRequest(VisualRequest):
    expected_sheet_version: str = Field(pattern=r"^1\.0\.[1-9][0-9]*$")


class CharacterState(Contract):
    schema_id: Literal[SCHEMA_ID] = SCHEMA_ID
    project_id: str
    revision: int = Field(default=0, ge=0, strict=True)
    stage: Literal["direction", "candidates", "sheet", "complete"] = "direction"
    status: Literal["awaiting_input", "awaiting_review", "confirmed", "blocked"] = "awaiting_input"
    direction_confirmed: bool = False
    visual_ready: bool = False
    sheet_approved: bool = False
    visuals: VisualState = Field(default_factory=VisualState)
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
        if self.direction_confirmed and (not self.brief or self.stage == "direction"):
            raise ValueError("확인한 방향의 정확한 버전이 필요합니다.")
        if any(item.project_id != self.project_id for item in [*self.visuals.assets, *self.visuals.jobs, *self.visuals.sheets]):
            raise ValueError("다른 프로젝트의 시각 자료가 포함되어 있습니다.")
        if any(item.get("project_id") != self.project_id for item in self.visuals.decisions):
            raise ValueError("다른 프로젝트의 시각 결정이 포함되어 있습니다.")
        direction_versions = {brief.version for brief in self.versions}
        if any(item.direction_version not in direction_versions for item in [*self.visuals.candidates, *self.visuals.jobs, *self.visuals.sheets]):
            raise ValueError("시각 작업의 원본 방향 버전이 없습니다.")
        for sheet in self.visuals.sheets:
            source = next(item for item in self.visuals.candidates if item.candidate_id == sheet.candidate_ref.candidate_id and item.version == sheet.candidate_ref.version)
            if source.direction_version != sheet.direction_version:
                raise ValueError("시트와 원본 후보의 방향 버전이 다릅니다.")
        selected = self.visuals.selected_candidate
        if self.visual_ready != bool(selected) or self.sheet_approved != bool(self.visuals.approved_sheet_version):
            raise ValueError("시각 단계와 정확한 사람 결정이 일치하지 않습니다.")
        if self.direction_confirmed and bool(selected) != (self.stage in ("sheet", "complete")):
            raise ValueError("현재 시각 단계와 선택한 후보가 다릅니다.")
        if not selected and (self.visuals.coverage or self.visuals.components or self.visuals.current_sheet_version):
            raise ValueError("시트를 구성하기 전에 정확한 후보를 선택해야 합니다.")
        if selected:
            candidate = next(item for item in self.visuals.candidates if item.candidate_id == selected.candidate_id and item.version == selected.version)
            if not self.direction_confirmed or candidate.direction_version != self.brief.version:
                raise ValueError("선택한 후보의 원본 방향이 현재 방향과 다릅니다.")
        if self.sheet_approved:
            sheet = next(item for item in self.visuals.sheets if item.version == self.visuals.approved_sheet_version)
            if (not selected or self.stage != "complete" or sheet.direction_version != self.brief.version
                    or sheet.candidate_ref != selected or sheet.coverage_version != self.visuals.coverage_version
                    or sheet.coverage != self.visuals.coverage or sheet.components != self.visuals.components):
                raise ValueError("현재 시트의 원본과 확인한 정확 버전이 다릅니다.")
            if not any(item.get("kind") == "sheet_confirm" and item.get("actor") == "human"
                       and item.get("sheet_version") == sheet.version and item.get("direction_version") == sheet.direction_version
                       for item in self.visuals.decisions):
                raise ValueError("정확한 시트 버전에 대한 사람 확인 기록이 필요합니다.")
            selected_asset = next(item.asset_id for item in self.visuals.candidates if item.candidate_id == selected.candidate_id and item.version == selected.version)
            if any(asset.provenance.fixture for asset in self.visuals.assets if asset.id in {*sheet.components.values(), selected_asset}):
                raise ValueError("개발용 이미지는 실제 시트로 확인할 수 없습니다.")
        if self.stage == "complete" and not self.sheet_approved:
            raise ValueError("사람이 확인한 시트가 필요합니다.")
        if not self.direction_confirmed and (self.stage != "direction" or selected or self.sheet_approved):
            raise ValueError("방향 변경 뒤의 시각 결과는 다시 확인해야 합니다.")
        return self


QUESTIONS = {
    "appearance": "어떤 모습의 캐릭터를 만들까요? 외형이나 떠오르는 특징을 알려주세요.",
    "personality": "이 캐릭터는 어떤 성격인가요? 평소 행동도 함께 알려주세요.",
    "desired_feeling": "캐릭터를 볼 때 어떤 느낌이 들었으면 하나요?",
    "review": "정리한 방향에서 바꾸거나 더할 부분을 알려주세요.",
}


def unknown_fields(fields: dict) -> list[str]:
    return [key for key in ("appearance", "personality", "desired_feeling") if not fields.get(key, "").strip()]
