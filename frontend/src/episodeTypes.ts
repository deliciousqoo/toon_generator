import type { CharacterBrief, CharacterMessage } from './characterTypes';
import type { CharacterSheet, VisualAsset, VisualProvenance } from './characterVisualTypes';

export type EpisodeStage = 'intent' | 'story' | 'format' | 'storyboard' | 'complete';
export type EpisodeTurnStage = 'intent' | 'story' | 'storyboard';
export type EpisodeDecision = 'confirm_story' | 'reopen_story' | 'confirm_format' | 'reopen_format' | 'confirm_board' | 'reopen_board';
export interface EpisodeIntent { topic: string; intended_emotion: string; ending: string; constraints: string }
export interface EpisodeBeat { id: string; order: number; action: string; emotion: string; dialogue: string }
export interface EpisodeArtifact { artifact_id: string; version: string; project_id: string; episode_id: string; snapshot_fingerprint: string }
export interface EpisodeStory extends EpisodeArtifact { title: string; premise: string; beats: EpisodeBeat[]; payoff: string; assistant_message: string }
export interface EpisodeFormat extends EpisodeArtifact { story_version: string; cut_count: number; layout: 'single_panel' | 'vertical_grid'; rationale: string; text_mode: string }
export interface EpisodePanel {
  id: string; order: number; beat_ids: string[]; scene: string; action: string; expression: string; dialogue: string;
  camera: string; composition: string; background: string; continuity: string; text_placement: string;
}
export interface EpisodeBoard extends EpisodeArtifact { story_version: string; format_version: string; panels: EpisodePanel[]; assistant_message: string }
export interface EpisodeCharacterSnapshot {
  project_id: string; direction: CharacterBrief; sheet: CharacterSheet; assets: VisualAsset[];
  approval: Record<string, unknown>; fingerprint: string;
}
export interface EpisodeRoughJob {
  id: string; status: 'awaiting_image' | 'completed' | 'cancelled'; panel_id: string; board_version: string;
  instruction: string; prompt: string; source_asset_ids: string[]; snapshot_fingerprint: string; panel_fingerprint: string;
}
export interface EpisodeRoughAsset {
  id: string; project_id: string; episode_id: string; url: string; sha256: string; width: number; height: number;
  byte_size: number; provenance: VisualProvenance; source_asset_ids: string[];
}
export interface EpisodeVersion { kind: string; artifact: EpisodeStory | EpisodeFormat | EpisodeBoard; created_at: string }
export interface EpisodeState {
  schema_id: 'toon-episode-v1'; id: string; project_id: string; title: string; revision: number; created_at: string;
  current_stage: EpisodeStage; status: 'awaiting_input' | 'awaiting_review' | 'blocked' | 'completed';
  character_snapshot: EpisodeCharacterSnapshot; intent: EpisodeIntent; next_question: string;
  story: EpisodeStory | null; format: EpisodeFormat | null; storyboard: EpisodeBoard | null;
  confirmed_story_version: string | null; confirmed_format_version: string | null; approved_board_version: string | null;
  messages: CharacterMessage[]; versions: EpisodeVersion[]; evaluations: Record<string, unknown>[];
  decisions: Record<string, unknown>[]; events: Record<string, unknown>[];
  issues: { code: string; severity: 'warning' | 'blocker'; message: string; target_id?: string | null }[];
  rough_jobs: EpisodeRoughJob[]; rough_assets: EpisodeRoughAsset[]; roughs: Record<string, string>;
  provider: string; fixture: boolean; engine: 'langgraph_sqlite'; generation_ready: false; usable_storyboard: boolean;
  calls_used: number; project_calls_used: number; pending_action: string | null; mutation_blocked: string | null;
}
export interface EpisodeRequest { request_id: string; expected_revision: number }
export interface EpisodeCreateInput { request_id: string; expected_direction_version: string; expected_sheet_version: string; title?: string }
export interface EpisodeTurnInput extends EpisodeRequest { stage: EpisodeTurnStage; message: string; expected_version?: string; target_ids: string[]; edit_fields: string[] }
export interface EpisodeDecisionInput extends EpisodeRequest { action: EpisodeDecision; expected_version: string }
export interface EpisodeFormatInput extends EpisodeRequest { expected_version: string; cut_count: number; layout: EpisodeFormat['layout'] }
export interface EpisodeRoughJobInput extends EpisodeRequest { expected_board_version: string; panel_id: string; instruction?: string }
export interface EpisodeRoughUploadInput extends EpisodeRequest { expected_board_version: string }
