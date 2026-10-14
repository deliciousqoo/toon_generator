export interface StudioSourceVersion {
  project_id: string;
  artifact_id: string;
  version: string;
  role: string;
}

export interface StudioProject {
  id: string;
  name: string;
  audience: string;
  series_direction: string;
  synthetic_confirmed: true;
  created_at: string;
  fixture_versions: StudioSourceVersion[];
}

export interface StudioProjectInput {
  name: string;
  audience: string;
  series_direction: string;
  synthetic_confirmed: true;
}

export type StudioInputKind = 'idea' | 'anecdote' | 'script' | 'reference';
export type StudioAction = 'approve_story' | 'approve_format' | 'approve_storyboard' | 'revise_story' | 'revise_storyboard' | 'reject' | 'retry';
export type StudioStatus = 'queued' | 'running' | 'awaiting_review' | 'blocked' | 'stopped' | 'completed';

export interface StoryBeat {
  id: string;
  order: number;
  action: string;
  emotion: string;
  dialogue: string;
  visual_purpose: string;
}

export interface StudioStory {
  artifact_id: string;
  version: string;
  premise: string;
  understanding: string;
  narrative_intent: string;
  beats: StoryBeat[];
  payoff: string;
  source_versions: StudioSourceVersion[];
  feedback_applied: string | string[];
  fixture: boolean;
}

export interface StudioFormat {
  artifact_id: string;
  version: string;
  story_version: string;
  selected_format: 'multi_panel' | 'single_panel';
  cut_count: number;
  rationale: string;
  text_mode: string;
}

export interface StudioPanel {
  id: string;
  order: number;
  beat_id: string;
  scene: string;
  action: string;
  expression: string;
  dialogue: string;
  camera: string;
  background: string;
  composition: string;
  visual_purpose: string;
  gaze_target: string;
  pacing: string;
  text_placement: string;
  continuity: string;
  thumbnail: { kind: string; description: string; usable_storyboard: boolean };
}

export interface StudioStoryboard {
  artifact_id: string;
  version: string;
  story_version: string;
  format_version: string;
  panels: StudioPanel[];
  feedback_applied: string | string[];
  usable_storyboard: boolean;
  fixture: boolean;
}

export interface StudioIssue { id: string; severity: 'blocker' | 'warning'; stage: string; code: string; message: string; target_id?: string }
export interface StudioEvent { id: string; at: string; role: string; stage: string; message: string; revision: number }
export interface StudioVersion { kind: string; artifact_id: string; version: string; created_at: string; summary: string; artifact: unknown }
export interface StudioRun {
  id: string;
  project_id: string;
  revision: number;
  status: StudioStatus;
  current_stage: string;
  current_role: string | null;
  summary: string;
  pending_action: 'approve_story' | 'approve_format' | 'approve_storyboard' | null;
  idea: string;
  input_kind: StudioInputKind;
  story: StudioStory | null;
  format_proposal: StudioFormat | null;
  storyboard: StudioStoryboard | null;
  issues: StudioIssue[];
  events: StudioEvent[];
  versions: StudioVersion[];
  engine: string;
  provider: string;
  generation_ready?: boolean;
  creative_quality_verified?: boolean;
  technical_review_complete: boolean;
  retry_available: boolean;
  capabilities: string[];
  limitations: string[];
  created_at: string;
}

export interface StudioProjectSnapshot { project: StudioProject; runs: StudioRun[]; current_run: StudioRun | null }
