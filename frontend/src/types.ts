export type Pane = 'setup' | 'storyboard' | 'draft' | 'history' | 'backup';
export type Gate = 'RG' | 'CG' | 'SG' | 'G2' | 'G3';
export type Decision = 'approved' | 'rework' | 'rejected';
export interface Project {
  project_id: string; name: string; topic: string; synthetic: boolean; created_at: string;
  protagonist?: string; audience?: string | string[]; tone?: string | string[]; series_direction?: string;
  supported_formats?: string[]; exclusions?: string | string[];
  lineage?: { source_project_id: string; source_backup_id: string };
}
export interface Unit { unit_id: string; order: number; action: string; dialogue?: string; composition?: string; continuity?: string; rough_asset_id?: string; rough_asset_url?: string; [key: string]: unknown }
export interface Output { output_id: string; role: string; asset_id: string; unit_id?: string; status?: string }
export interface Artifact {
  artifact_type: string; artifact_id: string; version: string; created_at: string; state: string;
  content_id?: string; approval?: { status: string; gate?: string }; unresolved_risks?: string[];
  storyboard?: { units: Unit[] }; story?: { selected_story?: string; synopsis?: string; [key: string]: unknown };
  content_scope?: { format_decision?: { selected_format?: string; rationale?: string; [key: string]: unknown } };
  outputs?: Output[];
  review_package?: { per_unit_candidate_sets: { unit_id: string; candidate_output_ids: string[]; selected_output_id: string | null }[]; composed_preview_asset_id: string; selected_output_ids: string[] };
  references?: { reference_id?: string; source?: string | { origin?: string; filename?: string; asset_id?: string }; asset_id?: string; use_basis?: string; not_to_copy?: string[] | string; [key: string]: unknown }[];
  [key: string]: unknown;
}
export interface Asset { asset_id: string; url?: string; media_type: string; byte_size: number; sha256: string; content_id?: string; [key: string]: unknown }
export interface Review { gate: string; decision: string; notes: string; decided_at: string; actor: string; artifact_ref: { artifact_id: string; version: string }; [key: string]: unknown }
export interface Audit { event_id: string; action: string; occurred_at: string; actor: string; result: string; scope?: { record_id?: string; version?: string }; [key: string]: unknown }
export interface Episode { content_id: string; title: string; input_mode: string; created_at: string; status?: string; [key: string]: unknown }
export interface Proposal { id: string; title: string; story: string }
export interface ProjectSnapshot { project: Project; setup: { project_brief: Artifact; reference_research: Artifact; character_package: Artifact; account_strategy: Artifact }; episodes: Episode[]; records: Artifact[]; review_decisions: Review[]; audit_events: Audit[]; assets: Asset[] }
export interface EpisodeSnapshot { episode: Episode; brief: Artifact; proposals: Proposal[]; storyboard: Artifact | null; run: Artifact | null; run_stale?: boolean; assets: Asset[]; reviews: Review[]; history: Artifact[] }
export interface Bootstrap { mode: string; csrf_token: string; schema_version: string; projects: Project[] }
export interface ProjectInput { name: string; topic: string; protagonist: string; audience: string; tone: string; series_direction: string; supported_formats: string[]; exclusions: string; synthetic: true }
