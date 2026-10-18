export interface CandidateRef { candidate_id: string; version: string }
export interface SheetComponent { id: string; label: string }
export interface VisualProvenance {
  source: 'codex_imagegen' | 'user_upload';
  model: string | null;
  workflow: string | null;
  prompt: string | null;
  seed: string | null;
  unknowns: string[];
  fixture: boolean;
}
export interface VisualAsset {
  id: string; project_id: string; sha256: string; byte_size: number;
  media_type: 'image/png'; width: number; height: number; url: string;
  provenance: VisualProvenance; source_asset_ids: string[];
}
export interface CharacterCandidate extends CandidateRef {
  direction_version: string; asset_id: string; feedback: string;
  parent_version: string | null; created_at: string;
}
export interface VisualJob {
  id: string; project_id: string;
  kind: 'candidate' | 'candidate_revision' | 'sheet_component';
  status: 'awaiting_image' | 'completed' | 'cancelled';
  direction_version: string; candidate_id: string; candidate_version: string | null;
  component_id: string | null; coverage_version: number;
  instruction: string; prompt: string; source_asset_ids: string[];
  asset_id: string | null; created_at: string;
}
export interface CharacterSheet {
  id: string; version: string; project_id: string; direction_version: string;
  candidate_ref: CandidateRef; coverage_version: number; coverage: SheetComponent[];
  components: Record<string, string>; created_at: string;
}
export interface CharacterVisualState {
  assets: VisualAsset[]; candidates: CharacterCandidate[]; jobs: VisualJob[];
  selected_candidate: CandidateRef | null; coverage: SheetComponent[];
  coverage_version: number; components: Record<string, string>;
  sheets: CharacterSheet[]; current_sheet_version: string | null;
  approved_sheet_version: string | null; decisions: Record<string, unknown>[];
}
export interface VisualMutation {
  request_id: string; expected_revision: number; expected_direction_version: string;
}
export interface VisualJobInput extends VisualMutation {
  kind: VisualJob['kind']; instruction?: string;
  candidate_id?: string; candidate_version?: string;
  component_id?: string; expected_coverage_version?: number;
}
export interface VisualSelectionInput extends VisualMutation { candidate_id: string; candidate_version: string }
export interface VisualCoverageInput extends VisualSelectionInput { components: SheetComponent[] }
export interface VisualComponentInput extends VisualSelectionInput { expected_coverage_version: number; asset_id: string }
export interface VisualSheetBuildInput extends VisualSelectionInput { expected_coverage_version: number }
export interface VisualSheetDecisionInput extends VisualMutation { expected_sheet_version: string }
