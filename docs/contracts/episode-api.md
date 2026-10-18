# Character-pinned episode API v1

All routes below use `/api/studio/projects/{pid}`. The legacy `/runs` fixture is unchanged. Responses are `EpisodeState` in `backend/episode_contracts.py`; model-backed POSTs execute synchronously in FastAPI's worker thread. The UI keeps its request ID until a conclusive response and never retries a failed model call automatically.

| Method | Path | Request |
|---|---|---|
| GET | `/episodes` | `{episodes: EpisodeState[]}` response |
| POST | `/episodes` | `request_id, expected_direction_version, expected_sheet_version, title?` |
| GET | `/episodes/{eid}` | state, including immutable character snapshot |
| POST | `/episodes/{eid}/turns` | `request_id, expected_revision, stage: intent/story/storyboard, message, expected_version?, target_ids:[], edit_fields:[]` |
| POST | `/episodes/{eid}/decisions` | `request_id, expected_revision, action: confirm_story/reopen_story/confirm_format/reopen_format/confirm_board/reopen_board, expected_version` |
| POST | `/episodes/{eid}/format` | `request_id, expected_revision, expected_version, cut_count:1..8, layout:single_panel/vertical_grid` |
| POST | `/episodes/{eid}/rough/jobs` | `request_id, expected_revision, expected_board_version, panel_id, instruction?` |
| POST | `/episodes/{eid}/rough/jobs/{jid}/image` | multipart `request` JSON (`request_id, expected_revision, expected_board_version, provenance`) + `file` |
| POST | `/episodes/{eid}/rough/jobs/{jid}/cancel` | `request_id, expected_revision` |
| GET | `/episodes/{eid}/rough/assets/{aid}` | immutable PNG |
| GET | `/episodes/{eid}/export` | exact human-confirmed ZIP |

The first intent turn returns an updated `intent`, one `next_question`, and messages. Explicit story-stage turns draft/revise the story, preserving prior versions. `confirm_story` creates a proposed format but does not draft panels. Format editing creates new format versions; `confirm_format` enables an explicit storyboard-stage turn. Story and storyboard turns run a draft role plus an independent evaluator, at most two model attempts per turn. `edit_fields` scopes edits to named beat/panel fields; IDs outside `target_ids` remain byte-for-byte equal. Empty `target_ids` plus empty `edit_fields` requests a full draft/revision.

Every state has `character_snapshot` with `project_id, direction, sheet, assets, approval, fingerprint`. Assets retain `id,url,sha256` and provenance. Sources and output versions are server assigned. Every role/decision/commit checks that the current approved sheet still matches the pinned snapshot and that its images retain their checksums. Reads preserve old results and report `mutation_blocked` when approval has changed.

Story: `{artifact_id,version,project_id,episode_id,snapshot_fingerprint,title,premise,beats:[{id,order,action,emotion,dialogue}],payoff,assistant_message}`. Format: same metadata plus `{story_version,cut_count,layout,rationale,text_mode:overlay}`. Board: same metadata plus `{story_version,format_version,panels:[{id,order,beat_ids,scene,action,expression,dialogue,camera,composition,background,continuity,text_placement}],assistant_message}`. Versions are `1.0.N` independently per artifact kind. `versions` entries contain `{kind,artifact,created_at}`.

Rough jobs contain `id,status:awaiting_image/completed/cancelled,panel_id,board_version,instruction,prompt,source_asset_ids,snapshot_fingerprint,panel_fingerprint`. Imported assets contain `id,project_id,episode_id,url,sha256,width,height,byte_size,provenance,source_asset_ids`. `roughs` maps current panel IDs to asset IDs. Metadata uses the existing `ImageProvenance` contract. PNG/JPEG/WebP imports are decoded, normalized, bounded to 16 MiB source, and kept outside Git. The app never executes image prompts; Codex image generation plus import is explicit.

Each rough request pins sheet images as `identity_reference`, at most one nearest available preceding panel as `continuity_reference`, and its own prior rough as `edit_target` when present. Continuity references guide props, layout direction and rendering style only; they cannot replace the character identity or target action. Every pinned source is checksum-verified. Later changes to a preceding panel do not silently replace an existing job's source, and exports preserve superseded images still referenced by selected roughs.

Panel visual fingerprints exclude dialogue/text placement, permitting a dialogue-only revision to retain an existing rough with its exact lineage. Changed visual instructions invalidate only the affected panel's current rough. Human G2 confirmation requires current roughs for every panel and no pending rough job. `usable_storyboard` becomes true only for that exact confirmed board; `generation_ready` remains false because Stage 05 is outside this integration.

Shared Pro project budget is the existing `chatgpt_subscription:{pid}` 40 attempted calls, including character calls, plus 40 attempted calls per episode. Every attempt is reserved before network I/O; failures count. No automatic model retry, creative rewrite, paid API fallback or uncertain crash replay occurs.
