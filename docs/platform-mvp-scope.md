# Personal local platform MVP scope

## Status

**2026-10-14 update:** D-0035 resumes implementation under the [P0 baseline](p0-implementation-baseline.md). The first new work unit is the Stage 04 synthetic orchestration slice and a simple conversational workspace. The Stage 01–05 capability list below describes the legacy prototype and future journey; it does not require rebuilding every phase simultaneously or prove creative acceptance. New studio v2 records coexist with legacy v1. Provider execution, real characters/episodes, and studio v2 complete backup/restore remain separately tracked prerequisites.

The original local-platform decisions in this document were accepted by D-0013 and implementation began under D-0027. On 2026-10-13, D-0029 paused further implementation for product-direction revision. Read [Product direction revision](product-direction-revision.md) and the [pre-implementation decision pack](preimplementation-decision-pack.md) first: their user flow, tool evaluation, and agent-orchestration requirements supersede conflicting user-facing requirements below. Existing storage, backup, project-isolation, and human decision boundaries remain unless changed separately. The current UI and mock creative outputs are prototype behavior, not product acceptance evidence.

## Goal

Build a platform for one person to manage Instagram toon projects and move an episode through Stages 01–05. Prove that the workflow, human review points, version history, and project boundaries work before using any real creative project data.

The accepted interface is a browser-based app that runs on the user's own computer and accepts app connections only from that computer over the loopback interface (`127.0.0.1`). A desktop shortcut starts the local app and opens it in a browser. Active project data and binary materials stay on the user's PC, without an additional app-specific password; access to active data relies on the PC user account (D-0022). The user can export a complete project backup containing settings, materials, episode images, retained versions, provenance, and human review/approval records. Each export explicitly offers plain or age-encrypted output; an encrypted export uses a generated or user-chosen passphrase that is required to restore and cannot be recovered if lost (D-0016, D-0017, D-0021–D-0023). The user chooses the destination for each export. Restore creates a separate project copy with a new `project_id`, preserving the source project's ID as lineage, and does not overwrite existing data (D-0018, D-0019). The accepted technical stack and minimum Stage 01–05 contract baseline are specified in [platform-technical-baseline.md](platform-technical-baseline.md) and D-0024. Cloud sync is deferred; no hosting vendor is selected.

## Included

- **Stage 01–03 — project setup:** organize project-scoped references and their source/use restrictions, a recurring character and identity constraints, and reusable account/series direction.
- **Stage 04 — story and storyboard:** accept either a short topic or a developed story; propose a story direction for a short topic, preserve supplied story/dialogue within the requested edit scope, produce Level 1 beat thumbnails by default, and record complete cut-by-cut text decisions for G2 review.
- **Stage 05 — image draft review:** create clearly marked synthetic per-cut candidates through a mock adapter, show a composed full-episode preview, let the user select a candidate, and regenerate only selected cuts while preserving prior versions.
- **Human controls:** the user may revise dialogue and cut descriptions, select image candidates, request selected-cut regeneration, and record G2/G3 decisions. The application and AI cannot approve creative, rights, final-quality, or publication decisions.
- **Local records:** preserve project/content IDs, exact input/output versions, provenance, validation results, and audit history. Keep each project's records isolated even when testing with more than one synthetic project fixture.
- **Local storage and backup:** keep active metadata and binary materials on the user's PC. Copy a user-selected local reference/media file into the app-managed project store and leave the original untouched; do not bulk-download web references. Preserve all versions and records without automatic pruning; whole-project deletion is outside the MVP. Export a complete project backup that can restore its settings, materials, episode records and images, retained versions, provenance, and human review/approval records. Each export explicitly asks whether to use age encryption; encrypted exports require a generated or user-chosen passphrase for restore, and a lost passphrase cannot be recovered. Plain exports are clearly labeled. Cloud sync is outside this MVP.
- **Minimum safety mechanics:** implement only the version checks, project-boundary checks, review holds, and retry/history behavior needed for Stages 01–05. This does not include the full Stage 07 automation harness.

## Excluded

- Real project briefs, account names, characters, references, stories, storyboards, images, or publication data during platform build.
- External image generation in the first implementation milestone. The mock adapter must be visibly labeled and must make no provider calls.
- Human retouch, pixel editing, crop manipulation, in-app lettering, optional AI refinement, QA/export preparation, and publication (Stage 06).
- Full Stage 07 automation, access to the platform from other computers (deferred by D-0015), hosted or multi-user operation, multi-account scheduling/permissions, cloud sync, automatic publishing, production LoRA training, and automatic competitor collection.

Cloud sync is deferred beyond the local MVP by D-0016. The MVP must not depend on a cloud-synced live database file; any later cross-device storage design must define conflict handling, recovery, and access controls. D-0017 fixes backup contents at the whole-project level; D-0018 and D-0019 require a separate restored copy with a new `project_id` and source lineage; D-0022 sets desktop-shortcut launch, no separate active-data password, and a per-export destination picker; D-0023 makes encryption an explicit per-export choice and applies passphrase/lost-key rules only to encrypted backups. D-0024 accepts the runtime, database, asset store, minimum schema contracts, and compatibility boundary. D-0025 requires an explicitly selected local reference/media file to be copied into project storage with its source/use basis and checksum; D-0026 keeps registered history without automatic pruning and leaves whole-project deletion out of the MVP. Package manifest fields and exact lineage representation are defined in [platform-technical-baseline.md](platform-technical-baseline.md). Credentials, secrets, and passphrases must not be included in backups.

## Image-provider milestone

One provider adapter may be considered after the mock workflow is accepted. Before its first call, the specification must identify the provider/model, credential handling, permitted synthetic data transfer, spend limits, timeout/failure/retry behavior, and provenance records. Provider validation uses synthetic prompts and assets only and requires a separate explicit authorization. It does not authorize real content.

## Platform acceptance

The local MVP is ready for a separate real-content decision only when review evidence shows that:

1. Project setup and Stage 01–03 records can be created and versioned using synthetic fixtures.
2. Stage 04 accepts both a short topic and a developed story; supplied story/dialogue is preserved outside the human-requested edit scope.
3. G2 review can be held, rejected, revised as a new version, and explicitly approved by the human.
4. The mock adapter creates labeled synthetic per-cut candidates and an episode preview without external calls.
5. The user can choose a cut candidate and regenerate selected cuts without erasing previous versions.
6. G3 review remains a human decision; generated output cannot self-approve or proceed to publication.
7. Exact versions, project/content scope, source restrictions, provenance, failures, and retries remain inspectable; cross-project reads/writes fail closed without an explicit grant.
8. The application is local-only, its test registry contains no real production records, and both plain and age-encrypted full synthetic project backups can be exported and restored. An encrypted backup requires its passphrase; a wrong passphrase or damaged file is rejected without changing project data. Either restore mode creates a separate copy with a new `project_id` and original ID as source lineage. Settings, imported materials, episode images, retained versions, provenance, and human review/approval records remain intact; the source remains unchanged, and credentials/secrets/passphrases are excluded. The original source file remains unchanged, no record is automatically pruned, and there is no project-deletion action.

Acceptance does not start real content production. The user must separately request that transition and provide approved project inputs.

## Work sequence and entry decisions

The original D-0027 build order below was written for the earlier product direction. D-0029 pauses that sequence. The current proposed order is the D-0031 Stage 04 synthetic vertical slice; this proposal still requires the revised scope and acceptance criteria to be accepted, followed by a separate explicit implementation-resume instruction.

1. **Reconcile the revised contracts:** resolve the Stage 01–04 record/schema gaps, use exact-version synthetic fixtures, and record the first-slice acceptance rubric. Runtime packaging versions are selected during implementation.
2. **Build only the local shell and fixture support needed by Stage 04:** keep project, character, strategy, and story inputs synthetic and version-pinned. This validates the orchestration slice; it does not replace the dedicated Stage 01–03 user-facing workflows.
3. **Build the Stage 04 story-to-storyboard slice:** verify story preservation, story selection, variable format proposal after story selection, readable visual roughs, cut-level edits, immediate versioned feedback, G1/G2 holds, and pause/resume behavior. A geometric placeholder can test layout plumbing but cannot satisfy storyboard visual-quality acceptance.
4. **Review workflow behavior and creative quality separately:** deterministic checks and mock runs prove contract/orchestration behavior only. Human review of the actual storyboard evidence decides whether the visual and narrative result is useful.
5. **Before real project episodes, provide the revised Stage 01–03 workflows, including the dedicated character-creation stage.**
6. **After the Stage 04 slice is accepted, implement Stage 05 with the mock adapter:** verify candidate selection, selected-cut regeneration, preview, provenance, and G3 holds. Provider validation remains a separate milestone requiring its own evaluation and explicit authorization.

The high-level storage boundary, whole-project backup contents, non-destructive restore, restored-copy ID rule, optional per-export encryption, launch method, active-data password choice, export destination workflow, stack, database, asset store, schema dialect, and minimum contract/version approach are set by D-0016–D-0024. The existing versioned envelope and synthetic fixtures are the baseline for compatibility review, not proof that the revised Stage 01–04 records already fit the schemas. Exact dependency/package versions are selected only after implementation is explicitly authorized. A specific image model provider is not needed for a Stage 04 orchestration-only slice; any model-based storyboard visual or image-generation run remains separately evaluated and authorized.
