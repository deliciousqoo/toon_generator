"""Character-pinned conversational episode contracts, independent of legacy fixtures."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .character_contracts import ImageProvenance


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Request(Contract):
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,120}$")
    expected_revision: int = Field(ge=0, strict=True)


class CreateEpisodeRequest(Contract):
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,120}$")
    expected_direction_version: str
    expected_sheet_version: str
    title: str = Field(default="새 이야기", min_length=1, max_length=120)


class TurnRequest(Request):
    stage: Literal["intent", "story", "storyboard"]
    message: str = Field(min_length=1, max_length=6000)
    expected_version: str | None = None
    target_ids: list[str] = Field(default_factory=list, max_length=8)
    edit_fields: list[str] = Field(default_factory=list, max_length=12)


class DecisionRequest(Request):
    action: Literal["confirm_story", "reopen_story", "confirm_format", "reopen_format", "confirm_board", "reopen_board"]
    expected_version: str


class FormatRequest(Request):
    expected_version: str
    cut_count: int = Field(ge=1, le=8, strict=True)
    layout: Literal["single_panel", "vertical_grid"]


class RoughJobRequest(Request):
    expected_board_version: str
    panel_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,120}$")
    instruction: str = Field(default="", max_length=3000)


class RoughUploadRequest(Request):
    expected_board_version: str
    provenance: ImageProvenance


class Intent(Contract):
    topic: str = Field(default="", max_length=3000)
    intended_emotion: str = Field(default="", max_length=1500)
    ending: str = Field(default="", max_length=2000)
    constraints: str = Field(default="", max_length=3000)


class IntakeDraft(Contract):
    intent: Intent
    assistant_message: str = Field(min_length=1, max_length=3000)
    next_question: str = Field(default="", max_length=1000)


class Beat(Contract):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,120}$")
    order: int = Field(ge=1, le=8)
    action: str = Field(min_length=1, max_length=2000)
    emotion: str = Field(max_length=1000)
    dialogue: str = Field(max_length=2000)


class StoryDraft(Contract):
    title: str = Field(min_length=1, max_length=120)
    premise: str = Field(min_length=1, max_length=3000)
    beats: list[Beat] = Field(min_length=1, max_length=8)
    payoff: str = Field(min_length=1, max_length=2000)
    assistant_message: str = Field(min_length=1, max_length=3000)


class Panel(Contract):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,120}$")
    order: int = Field(ge=1, le=8)
    beat_ids: list[str] = Field(min_length=1, max_length=8)
    scene: str = Field(min_length=1, max_length=1500)
    action: str = Field(min_length=1, max_length=1500)
    expression: str = Field(min_length=1, max_length=1000)
    dialogue: str = Field(max_length=2000)
    camera: str = Field(min_length=1, max_length=1000)
    composition: str = Field(min_length=1, max_length=1500)
    background: str = Field(min_length=1, max_length=1500)
    continuity: str = Field(min_length=1, max_length=1500)
    text_placement: str = Field(min_length=1, max_length=1000)


class BoardDraft(Contract):
    panels: list[Panel] = Field(min_length=1, max_length=8)
    assistant_message: str = Field(min_length=1, max_length=3000)


class Issue(Contract):
    code: str
    severity: Literal["warning", "blocker"]
    message: str
    target_id: str | None = None


class Evaluation(Contract):
    project_id: str
    episode_id: str
    version: str
    snapshot_fingerprint: str
    recommendation: Literal["ready_for_human", "revise", "blocked"]
    issues: list[Issue] = Field(default_factory=list, max_length=20)
    evidence: list[str] = Field(min_length=1, max_length=20)


class EpisodeState(Contract):
    schema_id: Literal["toon-episode-v1"] = "toon-episode-v1"
    id: str
    project_id: str
    title: str
    revision: int
    created_at: str
    current_stage: Literal["intent", "story", "format", "storyboard", "complete"] = "intent"
    status: Literal["awaiting_input", "awaiting_review", "blocked", "completed"] = "awaiting_input"
    character_snapshot: dict
    intent: Intent = Field(default_factory=Intent)
    next_question: str = "이 캐릭터로 어떤 이야기를 만들고 싶나요?"
    story: dict | None = None
    format: dict | None = None
    storyboard: dict | None = None
    confirmed_story_version: str | None = None
    confirmed_format_version: str | None = None
    approved_board_version: str | None = None
    messages: list[dict] = Field(default_factory=list)
    versions: list[dict] = Field(default_factory=list)
    evaluations: list[dict] = Field(default_factory=list)
    decisions: list[dict] = Field(default_factory=list)
    events: list[dict] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)
    rough_jobs: list[dict] = Field(default_factory=list)
    rough_assets: list[dict] = Field(default_factory=list)
    roughs: dict[str, str] = Field(default_factory=dict)
    provider: str
    fixture: bool
    engine: Literal["langgraph_sqlite"] = "langgraph_sqlite"
    generation_ready: Literal[False] = False
    usable_storyboard: bool = False
    calls_used: int = 0
    project_calls_used: int = 0
    pending_action: str | None = None
    mutation_blocked: str | None = None
