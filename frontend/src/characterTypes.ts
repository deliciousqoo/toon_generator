import type { CharacterVisualState } from './characterVisualTypes';

export interface CharacterReferenceObservation {
  label: string;
  desired_traits: string[];
  not_to_copy: string[];
}

export interface CharacterBrief {
  artifact_id: string;
  project_id: string;
  version: string;
  appearance: string;
  personality: string;
  desired_feeling: string;
  voice: string;
  identity_invariants: string[];
  avoid_elements: string[];
  reference_observations: CharacterReferenceObservation[];
  source_turn_ids: string[];
  provider: string;
  fixture: boolean;
}

export interface CharacterMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  at: string;
  version: string | null;
}

export interface CharacterState {
  schema_id: 'toon-character-direction-v1';
  project_id: string;
  revision: number;
  stage: 'direction' | 'candidates' | 'sheet' | 'complete';
  status: 'awaiting_input' | 'awaiting_review' | 'confirmed' | 'blocked';
  direction_confirmed: boolean;
  visual_ready: boolean;
  sheet_approved: boolean;
  visuals: CharacterVisualState;
  fixture: boolean;
  provider: string;
  brief: CharacterBrief | null;
  messages: CharacterMessage[];
  next_question: string;
  question_field: 'appearance' | 'personality' | 'desired_feeling' | 'review';
  unknowns: string[];
  issues: { code: string; severity: 'warning' | 'blocker'; message: string }[];
  can_confirm: boolean;
  versions: CharacterBrief[];
  decisions: unknown[];
  events: unknown[];
}

export interface CharacterFieldUpdates {
  appearance?: string;
  personality?: string;
  desired_feeling?: string;
  voice?: string;
  identity_invariants?: string[];
  avoid_elements?: string[];
}

export interface CharacterTurnInput {
  request_id: string;
  expected_revision: number;
  message: string;
  synthetic_confirmed: true;
  field_updates?: CharacterFieldUpdates;
  references?: CharacterReferenceObservation[];
}

export interface CharacterDecisionInput {
  request_id: string;
  expected_revision: number;
  expected_version: string;
}
