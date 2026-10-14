"""Additive Stage 01–04 contracts. Legacy v1 records are never migrated implicitly."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_ID = "toon-studio-contract-v2"
SCHEMA_VERSION = "2.0.0"


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceVersion(Contract):
    project_id: str
    artifact_id: str
    version: str
    role: str


class ProjectBrief(Contract):
    name: str = Field(min_length=1, max_length=120)
    audience: str = Field(default="", max_length=1000)
    series_direction: str = Field(min_length=1, max_length=3000)
    synthetic_confirmed: Literal[True]


class ReferenceUse(Contract):
    id: str
    project_id: str
    version: str
    purpose: Literal["character", "story", "composition", "dialogue", "format"]
    observations: list[str]
    not_to_copy: list[str]
    permission_status: Literal["synthetic_fixture", "unknown", "approved"]


class CharacterPackage(Contract):
    id: str
    project_id: str
    version: str
    identity_invariants: list[str]
    behavior_and_voice: list[str]
    sheet_artifact_id: str
    sheet_status: Literal["fixture", "missing", "pending", "approved"]
    conversation_history: list[dict] = Field(default_factory=list)
    revision_history: list[dict] = Field(default_factory=list)
    source_versions: list[SourceVersion] = Field(default_factory=list)
    approval_status: Literal["synthetic_fixture", "pending", "approved"]


class SeriesPackage(Contract):
    id: str
    project_id: str
    version: str
    direction: str
    editorial_filters: list[str]
    supported_formats: list[Literal["single_panel", "multi_panel"]]
    approval_status: Literal["synthetic_fixture", "pending", "approved"]


class Project(ProjectBrief):
    id: str
    schema_id: Literal[SCHEMA_ID] = SCHEMA_ID
    schema_version: Literal[SCHEMA_VERSION] = SCHEMA_VERSION
    created_at: str
    fixture_versions: list[SourceVersion]
    references: list[ReferenceUse]
    character_package: CharacterPackage
    series_package: SeriesPackage

    @model_validator(mode="after")
    def setup_project_boundary(self):
        owned = [*self.fixture_versions, *self.references, self.character_package, self.series_package,
                 *self.character_package.source_versions]
        if any(item.project_id != self.id for item in owned):
            raise ValueError("프로젝트 설정에 다른 프로젝트의 자료가 포함되어 있습니다.")
        return self


class Artifact(Contract):
    artifact_id: str
    version: str
    project_id: str
    content_id: str
    source_versions: list[SourceVersion]

    @model_validator(mode="after")
    def same_project(self):
        if any(s.project_id != self.project_id for s in self.source_versions):
            raise ValueError("다른 프로젝트의 원본 버전을 사용할 수 없습니다.")
        return self


class Beat(Contract):
    id: str
    order: int = Field(ge=1, le=8)
    action: str = Field(min_length=1, max_length=3000)
    emotion: str
    dialogue: str
    visual_purpose: str


class StoryArtifact(Artifact):
    understanding: str
    premise: str = Field(min_length=1, max_length=3000)
    narrative_intent: str
    beats: list[Beat] = Field(min_length=1, max_length=8)
    payoff: str
    feedback_applied: list[str] = Field(default_factory=list)
    provider: str
    fixture: bool


class FormatProposal(Artifact):
    story_version: str
    selected_format: Literal["single_panel", "multi_panel"]
    cut_count: int = Field(ge=1, le=8)
    rationale: str
    text_mode: Literal["overlay", "in_image", "mixed", "unknown"]


class Thumbnail(Contract):
    kind: Literal["developer_text_fixture"]
    description: str
    usable_storyboard: Literal[False]


class Panel(Contract):
    id: str
    order: int
    beat_id: str
    scene: str
    action: str
    expression: str
    dialogue: str
    camera: str
    background: str
    composition: str
    visual_purpose: str
    gaze_target: str
    pacing: str
    text_placement: str
    continuity: str
    thumbnail: Thumbnail


class StoryboardArtifact(Artifact):
    story_version: str
    format_version: str
    panels: list[Panel] = Field(min_length=1, max_length=8)
    feedback_applied: list[str] = Field(default_factory=list)
    usable_storyboard: Literal[False]
    fixture: bool


class Issue(Contract):
    id: str
    severity: Literal["blocker", "warning"]
    stage: str
    code: str
    message: str
    target_id: str | None = None


class Event(Contract):
    id: str
    at: str
    role: str
    stage: str
    message: str
    revision: int


class ArtifactVersion(Contract):
    kind: Literal["story", "format_proposal", "storyboard", "story_evaluation", "board_evaluation"]
    artifact_id: str
    version: str
    created_at: str
    summary: str
    artifact: dict


class Approval(Contract):
    id: str
    gate: Literal["G1", "FORMAT", "TECHNICAL_BOARD"]
    project_id: str
    run_id: str
    artifact_id: str
    version: str
    at: str
    actor: Literal["human"]
    scope: Literal["synthetic_technical_review"]


class EvaluationArtifact(Artifact):
    role: Literal["story_evaluator", "board_evaluator"]
    provider: str
    fixture: bool
    recommendation: Literal["revise", "ready_for_human", "blocked"]
    issues: list[Issue]
    feedback: str
    evidence: list[str] = Field(min_length=1)
    rubric_version: Literal["story-v1", "board-v1"]
    criteria: list[str] = Field(min_length=1)


class RunInput(Contract):
    idea: str = Field(min_length=1, max_length=20000)
    input_kind: Literal["idea", "anecdote", "script", "reference"] = "idea"


class ActionInput(Contract):
    action: Literal["approve_story", "approve_format", "approve_storyboard", "revise_story", "revise_storyboard", "reject", "retry"]
    expected_revision: int = Field(ge=1)
    feedback: str = Field(default="", max_length=5000)
    target_ids: list[str] = Field(default_factory=list, max_length=8)


class Run(Contract):
    schema_id: Literal[SCHEMA_ID] = SCHEMA_ID
    schema_version: Literal[SCHEMA_VERSION] = SCHEMA_VERSION
    id: str
    project_id: str
    revision: int
    created_at: str
    idea: str
    input_kind: str
    status: Literal["queued", "running", "awaiting_review", "blocked", "stopped", "completed"]
    current_stage: str
    current_role: str
    summary: str
    pending_action: str | None = None
    story: StoryArtifact | None = None
    format_proposal: FormatProposal | None = None
    storyboard: StoryboardArtifact | None = None
    issues: list[Issue] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    versions: list[ArtifactVersion] = Field(default_factory=list)
    approvals: list[Approval] = Field(default_factory=list)
    evaluations: list[EvaluationArtifact] = Field(default_factory=list)
    generation_ready: Literal[False] = False
    creative_quality_verified: Literal[False] = False
    technical_review_complete: bool = False
    retry_available: bool = False
    engine: Literal["langgraph_sqlite"] = "langgraph_sqlite"
    provider: str
    capabilities: list[str]
    limitations: list[str]


class StudioSchema(Contract):
    project: Project
    run: Run
    action: ActionInput


def studio_schema():
    """Export stable JSON schema for documentation and contract consumers."""
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": SCHEMA_ID,
            **StudioSchema.model_json_schema()}
