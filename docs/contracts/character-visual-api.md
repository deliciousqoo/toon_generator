# Character visual API (2026-10-18)

All paths below are relative to `/api/studio/projects/{project_id}/character`.
Every mutation returns the full `CharacterState`, inherits local CSRF protection,
and requires `request_id`, `expected_revision`, `expected_direction_version`.
The direction must already be confirmed. A repeated identical request ID returns
its saved response; changing its payload is a conflict. No endpoint calls an image
provider. Jobs wait for an image generated in Codex or supplied by the user.

## State additions

`stage`: `direction | candidates | sheet | complete`.
`visual_ready` and `sheet_approved` become booleans. `visuals` has defaults for old records:

```ts
interface CandidateRef { candidate_id: string; version: string }
interface Component { id: string; label: string }
interface Provenance {
  source: 'codex_imagegen' | 'user_upload'; model: string | null;
  workflow: string | null; prompt: string | null; seed: string | null; unknowns: string[];
  fixture: boolean;
}
interface VisualAsset {
  id: string; project_id: string; sha256: string; byte_size: number;
  media_type: 'image/png'; width: number; height: number; url: string;
  provenance: Provenance; source_asset_ids: string[];
}
interface Candidate extends CandidateRef {
  direction_version: string; asset_id: string; feedback: string;
  parent_version: string | null; created_at: string;
}
interface VisualJob {
  id: string; project_id: string;
  kind: 'candidate' | 'candidate_revision' | 'sheet_component';
  status: 'awaiting_image' | 'completed' | 'cancelled';
  direction_version: string; candidate_id: string; candidate_version: string | null;
  component_id: string | null; coverage_version: number;
  instruction: string; prompt: string; source_asset_ids: string[];
  asset_id: string | null; created_at: string;
}
interface CharacterSheet {
  id: string; version: string; project_id: string; direction_version: string;
  candidate_ref: CandidateRef; coverage_version: number; coverage: Component[];
  components: Record<string, string>; created_at: string;
}
interface VisualState {
  assets: VisualAsset[]; candidates: Candidate[]; jobs: VisualJob[];
  selected_candidate: CandidateRef | null; coverage: Component[];
  coverage_version: number; components: Record<string, string>;
  sheets: CharacterSheet[]; current_sheet_version: string | null;
  approved_sheet_version: string | null; decisions: Record<string, unknown>[];
}
```

## Mutations

- `POST /visual/jobs`: common fields plus `kind`, `instruction` (optional for initial candidate),
  `candidate_id`, `candidate_version` (required for revision and sheet jobs),
  `component_id` (required for sheet jobs), `expected_coverage_version` (required for sheet jobs).
  Initial candidate allocates its own ID. A revision retains its candidate ID and
  records a new version after upload. The returned job contains a self-contained
  prompt and the exact source image IDs to pass to Codex image generation.
- `POST /visual/jobs/{job_id}/image`: multipart `request` (JSON common fields plus `provenance`)
  and `file` (PNG/JPEG/WebP, at most 16 MiB). Decode, normalize to PNG, store immutable
  bytes and checksum. Completion adds a candidate version or replaces only the
  requested sheet component. Original uploads and external paths are not exposed.
- `POST /visual/select`: common fields plus `candidate_id`, `candidate_version`.
  Selection clears active sheet scope/components/approval, preserving all history.
- `POST /visual/coverage`: common fields plus `candidate_id`, `candidate_version`,
  `components: Component[]` (1–16 unique IDs, explicitly chosen by the human).
  Saves a new scope version and preserves unchanged matching components.
- `POST /visual/components/{component_id}/attach`: common fields plus
  `candidate_id`, `candidate_version`, `expected_coverage_version`, `asset_id`.
  Reuses the exact selected candidate image or a compatible existing component asset.
- `POST /visual/sheet/build`: common fields plus `candidate_id`, `candidate_version`,
  `expected_coverage_version`. Requires every selected component to have a present,
  checksum-valid image. Saves a new immutable sheet version; it remains unapproved.
- `POST /visual/sheet/confirm` and `POST /visual/sheet/reopen`: common fields plus
  `expected_sheet_version`. Confirmation is a human decision for that exact sheet
  and bible/direction. Fixture images cannot pass. Reopen keeps the current sheet
  and all images but clears approval immediately.
- `POST /visual/jobs/{job_id}/cancel`: common fields. Preserves the job and prompt.
- `GET /visual/assets/{asset_id}`: checksum-verified image bytes for this project.
- `GET /visual/sheet/export`: read-only ZIP of the exact approved direction bible,
  sheet JSON, approval/provenance metadata and checksum-verified PNG images,
  including the recursively referenced source images of the selected candidate
  and sheet components (unselected alternatives outside that source closure are omitted)
  (128 MiB total image limit). Requires the currently approved sheet.

Candidate changes, sheet component revisions and scope changes clear current sheet
approval immediately. Reopening direction clears active visual selections/scope,
but retains all candidates, images, jobs, sheets and decisions. Pending jobs become
cancelled. Restarts never execute an external image request or retry a completed upload.

Missing/corrupt active images fail closed on state read, image read, sheet approval
and any later run handoff. Unknown provenance stays explicit. A completed sheet does
not authorize story/image production or publication.
