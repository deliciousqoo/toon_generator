# Decision log

## D-0001 — Use this repository as the project source of truth

- Status: accepted
- Date: 2026-10-11
- Decision: Keep approved pipeline specifications, rules, prompts, workflows, and decision records in this repository.
- Reason: Project threads are useful for discussion, but repository files are easier to review, version, and reuse across future sessions.
- Impact: Thread conclusions must be reflected in repository files.

## D-0002 — Start with a single-account vertical slice

- Status: superseded by D-0013
- Date: 2026-10-11
- Decision: Validate one complete content flow before building the multi-account platform.
- Reason: The real inputs, approval gates, asset metadata, and failure cases need to be observed in practice first.
- Impact: This was the original sequencing decision. Its requirement to run real content before building a platform is superseded by D-0013; its caution against prematurely expanding to multi-account publishing remains relevant.

## D-0003 — Human approval remains a required gate

- Status: accepted
- Date: 2026-10-11
- Decision: AI may prepare drafts and recommendations, but the user approves the story, visual draft, polish result, and publishable output.
- Reason: Character identity, creative direction, rights, and final quality require accountable human judgment.
- Impact: Automation must stop at approval gates rather than publish or finalize autonomously.

## D-0004 — Separate project workstreams from the content state machine

- Status: accepted
- Date: 2026-10-11
- Decision: Treat threads and workstreams `00–09` as project work organization, while treating `idea` through `published` as the state machine for an individual content item.
- Reason: Governance, automation, and Git/platform work support production but are not content states. Separating them prevents a tooling task from being mistaken for a publishable content transition.
- Impact: Stage documents describe workstream inputs and outputs; every content item follows the production state machine and its own approval gates.

## D-0005 — Versioned artifact contracts are required at handoffs

- Status: accepted
- Date: 2026-10-11
- Decision: Each stage handoff must identify a versioned input and output artifact, minimum provenance, validation result, and the next consumer. Approved artifacts are immutable; corrections create a new version.
- Reason: Reproducibility and rollback require knowing which character bible, reference, prompt, workflow, tool, and human edit produced a result.
- Impact: Later stage schemas must carry stable content and artifact identifiers, version, state, owner, timestamps, source references, approval information, and provenance fields. Unknown values are recorded as unknown rather than inferred.

## D-0006 — Use explicit approval gates and named rework paths

- Status: accepted
- Date: 2026-10-11
- Decision: Require human approval at scope/bible, story, storyboard, visual draft, polish/refinement, and QA/rights/publication gates. A rejection returns the item to a named earlier state and creates a new version.
- Reason: Character identity, creative intent, rights, and final visual quality cannot be safely delegated to an automated pass/fail decision.
- Impact: Automation may prepare or validate a package but may not move an item through a human gate, mark it `approved`, or publish it autonomously.

## D-0007 — Scope creative configuration and assets to production projects

- Status: accepted; MVP validation scope clarified by D-0013
- Date: 2026-10-11
- Decision: Model each platform-managed production project as an independent container with its own project brief, account/content direction, primary character, audience, tone, target format, exclusions, references, character bible, series strategy, content items, and provenance. Identify project-owned records with a stable `project_id`.
- Reason: The platform must support multiple unrelated content projects without mixing their creative direction, reference material, character identity, or generated assets. The six project-brief fields are per-project configuration, not global platform settings.
- Impact: Stage specifications use `Project Brief` as the project-scoped input. Handoffs and artifact records carry `project_id`; cross-project reuse requires an explicit, traceable decision. The local single-user MVP preserves this boundary; hosted/multi-user expansion remains deferred.
- Clarification: The local MVP may use multiple synthetic project fixtures to demonstrate this isolation rule. This is not a hosted or multi-user expansion and does not permit real project data during `platform_build`.

## D-0008 — Keep specification work separate from actual project execution

- Status: accepted; mode transition clarified by D-0013
- Date: 2026-10-11
- Decision: Keep the repository in `specification_only` mode until the user explicitly requests a transition to actual project execution. During this mode, stage documents define abstract contracts and examples only; agents must not request, invent, or populate real project values or content.
- Reason: The pipeline and platform architecture must be reviewed independently of any one account, character, story, format value, or image-generation tool. Mixing execution questions into specification work causes premature assumptions and makes the contracts harder to evaluate.
- Impact: Agents ask only about pipeline, platform, schema, role, gate, validation, storage, provenance, and implementation decisions while in specification work. `next`, `queued`, and `completed` in the thread index describe workstream status and do not start production. D-0013 distinguishes synthetic-only `platform_build` from real `content_execution`; the transition instruction and exact approved inputs remain required before a real content item is created.

## D-0009 — Set the first production validation target to storyboard and AI draft

- Status: accepted
- Date: 2026-10-12
- Decision: Treat one Instagram toon project as the reusable boundary for its protagonist, optional supporting cast, references, and series direction. Run project setup once, then create episodes as content items identified by `content_id`. The first production validation target ends with a human-reviewed storyboard and AI visual draft, before retouch, QA, publishable export, or publication.
- Reason: The intended near-term result is an Instagram toon storyboard and draft. Panel count and layout vary by episode according to its request and permitted reference observations; a fixed format would not reflect the intended work.
- Impact: A short topic may receive a proposed story direction for human selection; an existing story or dialogue is preserved within the requested change scope. Storyboard review includes written cut decisions and low-fidelity visuals for the whole episode. The Stage 05 review package includes per-cut images and a composed episode preview, with G2/G3 decisions remaining human-owned. Stage 06 is a follow-up production extension; Stage 07–09 remain supporting/future workstreams. Current work remains `specification_only`; this decision does not authorize creating a real project or episode.
- Clarification: This refines D-0007's project-level `target format`: the Project Brief records supported format families and constraints, while an Episode Brief and its permitted references inform the exact episode layout. A concrete value still requires the applicable human decision.

## D-0010 — Use Level 1 storyboard roughs by default

- Status: accepted
- Date: 2026-10-12
- Decision: Use Level 1 beat thumbnails as the default visual fidelity for storyboard roughs. Keep the cut-by-cut written record complete enough to review the story at G2 and to let Stage 05 generate without guessing. Add visual detail only to specific cuts when a remaining ambiguity or complexity requires it.
- Reason: The user considers the simplest visual rough sufficient for the storyboard stage and wants to focus on the sequence before investing in drawing detail.
- Impact: This sets the default rough-visual detail, not the information required for G2 approval or the Stage 05 handoff. The examples, Stage 04 procedure, and operating guidance must distinguish sparse thumbnail art from complete written decisions. Higher-detail levels remain available for selected cuts.

## D-0011 — Keep first-slice manual editing focused on text and cut-level choices

- Status: accepted
- Date: 2026-10-12
- Decision: In the first platform slice, a human may revise storyboard dialogue and cut descriptions, choose among cut-level image candidates, and request regeneration for selected cuts. A general-purpose in-app image editor is outside the first-slice scope.
- Reason: The user wants concept, references, story, and ideas to flow through the pipeline into image drafts, with hands-on work concentrated on reviewing and refining the storyboard and drafts rather than editing raster images directly.
- Impact: Stage 04 must preserve human text edits as versioned storyboard revisions. Stage 05 must support per-cut candidate selection and regeneration while retaining prior runs and outputs. Drawing, direct pixel retouch, manual crop manipulation, and in-app balloon/text placement are not first-slice requirements. Existing G2/G3 human approval gates remain in force.

## D-0012 — Validate image-generation flow with a mock before provider calls

- Status: accepted
- Date: 2026-10-12
- Decision: The first local-platform workflow milestone uses a mock image-generation adapter and clearly labeled synthetic outputs without contacting an image provider. A later milestone adds one provider adapter and tests it with synthetic prompts and assets after the provider, credentials, data-transfer conditions, cost controls, and failure/retry behavior are specified.
- Reason: The app's storyboard, cut-selection, regeneration, versioning, and G3 review flow should be validated separately from external-service setup and behavior.
- Impact: Mock and provider adapters use the same generation request/result contract. The mock milestone makes no external generation calls. Provider validation may use synthetic data only and must record requests, outputs, and provenance. This decision does not authorize real project/content data or switch the repository out of `specification_only` mode.

## D-0013 — Build a personal local-first platform before real content production

- Status: accepted
- Date: 2026-10-12
- Decision: Build toward a single-user, local-first platform MVP for Stages 01–05 before creating any real Instagram toon project or episode. Validate the application first with synthetic project/episode fixtures and a mock image-generation adapter. A later milestone may add one image provider adapter and validate it only with synthetic prompts/assets after the provider, credential handling, data transfer, cost limits, and failure/retry behavior are specified.
- Reason: The user's goal is to create a platform and pipeline for personal work. They do not want to produce real creative work before that platform exists and has been reviewed.
- Impact: The first product validation is the local platform and its synthetic Stage 01–05 flow, not a real content vertical slice. Preserve project isolation, exact versions, provenance, and human G2/G3 decisions. Defer Stage 06 production work, advanced Stage 07 automation, hosted/multi-user operation, multi-account scheduling, and automatic publishing. Selecting this direction authorizes specification alignment only; implementation, external provider calls, and real-content execution each retain their own explicit start conditions.
- Clarification: D-0002 is superseded only as to sequencing. Its preference for evidence before broad multi-account/hosted expansion remains compatible with this decision. D-0008's real-content gate is retained but refined into separate `specification_only`, `platform_build`, and `content_execution` modes. D-0007's project isolation rule and D-0011/D-0012 remain in force. D-0014 confirms the local browser UI boundary; it does not choose the framework or local data store.

## D-0014 — Use a loopback-only browser interface for the personal MVP

- Status: accepted
- Date: 2026-10-12
- Decision: The MVP presents its user interface in a web browser on the user's own computer and accepts app connections only over the local loopback interface. It is not hosted and is not reachable from other devices or the public internet.
- Reason: The user prefers a web-page workflow, and browser-based storyboard and image-candidate review fits the intended use.
- Impact: This fixes the interface and network boundary only. The framework/runtime, local backend, metadata database, asset storage, and backup/restore approach remain open implementation decisions. The browser UI choice does not authorize cloud sync, provider calls, or real-content execution.

## D-0015 — Defer platform access from other computers until after the local MVP

- Status: accepted
- Date: 2026-10-12
- Decision: Keep the first platform MVP local to the user's own computer. Accessing the platform from another computer is a later milestone, not part of the MVP.
- Reason: The user chose to start with the recommended local MVP and consider remote platform access in a later phase.
- Impact: The MVP remains loopback-only as defined by D-0014 and must not be exposed to other devices or the public internet. This decision does not settle whether reference/media files or exported backups may use cloud sync; that remains a separate storage decision. Do not treat a cloud-synced folder as a shared live database without an explicit design and validation decision.

## D-0016 — Store MVP materials locally and provide backup-file export

- Status: accepted
- Date: 2026-10-12
- Decision: During the local MVP, keep active project metadata and binary materials on the user's PC and provide a way to export them as a backup file. Cloud synchronization is deferred to a later decision/milestone.
- Reason: The user chose local PC storage with backup-file export for the MVP, while keeping cloud synchronization for later.
- Impact: The MVP does not sync active project materials or a live database to cloud storage. Backup package contents, file format, integrity checks, destination handling, and restore procedure remain implementation-entry details. This sets the storage boundary, not the database technology or asset-store layout.

## D-0017 — Make project backups complete enough to restore the whole project

- Status: accepted
- Date: 2026-10-12
- Decision: An MVP project backup must be able to restore the complete project. Include project settings and materials, episode records and images, retained artifact versions, provenance, and human review/approval records.
- Reason: The user chose a complete project backup that includes settings, materials, images, version history, and review records.
- Impact: Backups preserve the project boundary and exact-version relationships; credentials and secrets remain excluded under existing rules. The package format, manifest, integrity verification, encryption, export destination, and restore/collision behavior remain to be specified.

## D-0018 — Restore a project backup as a separate copy

- Status: accepted
- Date: 2026-10-12
- Decision: Restoring a project backup creates a separate project copy and never overwrites existing project data.
- Reason: The user chose to preserve existing materials and restore the backup as a separate copy.
- Impact: Restore must preserve isolation between the source and restored project. The `project_id` allocation and source-to-restored lineage representation remain implementation-entry details; a conflicting identity must not cause an overwrite.

## D-0019 — Assign a new project ID to a restored copy

- Status: accepted
- Date: 2026-10-12
- Decision: A restored project copy receives a new `project_id`; the source project's original `project_id` is preserved as its lineage/source reference.
- Reason: The user chose to give the copy a new project ID while retaining the original ID as its source.
- Impact: The restored copy remains independently addressable and isolated from the source project. The exact field and manifest representation for the source-to-restored relationship, plus uniqueness validation, remain implementation-entry details.

## D-0020 — Require encryption for exported project backups

- Status: superseded by D-0023
- Date: 2026-10-12
- Decision: Every project backup exported by the local MVP must be encrypted before it is written as an export file.
- Reason: The user chose encryption for the complete project backup export.
- Impact: An unencrypted project backup export is not an acceptable MVP behavior. The encryption mechanism, key/passphrase handling, restore unlock flow, and lost-key recovery policy remain implementation-entry details. This decision applies to exported backups; encryption of active local storage remains open. Credentials and secrets remain excluded from backups.

## D-0021 — Use a user-set passphrase for each backup export

- Status: accepted for encrypted exports; scope clarified by D-0023
- Date: 2026-10-12
- Decision: The user sets a passphrase when exporting each backup and enters the same passphrase to restore it. If the passphrase is lost, that backup cannot be restored; no recovery or bypass path is provided.
- Reason: The user chose passphrase-based encryption and accepted that a lost passphrase prevents recovery.
- Impact: Never include the passphrase in the backup or write it to logs. Passphrase strength/validation, cryptographic format and key derivation, and secure handling during export/restore remain implementation-entry details. Active local-storage encryption remains a separate open decision.

## D-0022 — Use a desktop shortcut and per-export destination selection

- Status: accepted
- Date: 2026-10-12
- Decision: Start the local browser application from a desktop shortcut that opens the browser. Do not require an app-specific password to access active local project data; rely on the PC user account. Ask the user to choose the destination each time they export an encrypted backup.
- Reason: The user chose the simplest local launch, PC-account access for active materials, and explicit control of each backup file's location.
- Impact: The launcher must start the local service and open the browser. Active local data does not receive an additional app-level password layer. Backup exports use a save-location picker rather than a fixed folder. D-0023 determines whether each export is encrypted. This does not establish that full-disk encryption is enabled on the PC.

## D-0023 — Let the user choose encryption for each project backup

- Status: accepted
- Date: 2026-10-12
- Decision: For every project-backup export, ask whether to encrypt that export. Plain and encrypted backups are both supported. When encryption is selected, use the age passphrase-encryption format and offer a long generated passphrase plus strength guidance for a user-chosen passphrase. The user must enter the passphrase to restore an encrypted backup; a lost passphrase cannot be recovered. Never store or log the passphrase. Continue to exclude credentials and secrets from all backups.
- Reason: The user works alone on a local PC. Encryption is useful when a backup is moved to removable or otherwise less-trusted storage, but imposing a passphrase on every local backup adds friction and creates a permanent-loss risk.
- Impact: An export explicitly records whether it is plain or encrypted; the app must identify the format during restore and request a passphrase only for encrypted files. The UI clearly warns that a plain backup is readable by anyone with file access. D-0020 is superseded because encryption is optional per export. D-0021's passphrase and no-recovery rules apply only when encryption is selected. This does not add encryption to active local data.

## D-0024 — Adopt the local MVP technical and contract baseline

- Status: accepted
- Date: 2026-10-12
- Decision: Use a Python/FastAPI local service with a React + TypeScript frontend built by Vite; store metadata in SQLite and binary assets in a local per-user file store. Bind the browser application to loopback only and launch it from the accepted desktop shortcut. Define the minimum persisted Stage 01–05 handoff artifacts as versioned JSON Schema Draft 2020-12 contracts with a shared artifact envelope. Keep `project_id` and `content_id` semantics, artifact versions, schema versions, database versions, and backup package versions distinct. Use explicit migrations and fail closed on unsupported future versions. The detailed baseline is `docs/platform-technical-baseline.md`.
- Reason: The user accepted the proposed maintainable local web stack and storage/versioning baseline so the project can validate the complete synthetic Stage 01–05 flow before real content.
- Impact: The framework/runtime, database, asset store, formal minimum Stage 01–05 contract inventory, schema dialect, and migration boundary are no longer open implementation-entry choices. The minimum machine-readable schemas and synthetic fixtures are recorded under `docs/contracts/`; this does not formalize Stage 06–09 or the full Stage 07 harness. Runtime packaging versions are pinned at implementation time. This decision does not authorize code, provider calls, or real-content execution.

## D-0025 — Copy user-selected reference files into project storage

- Status: accepted
- Date: 2026-10-12
- Decision: When the user explicitly adds a local reference or media file to a project, copy it into the app-managed local asset store under that project's scope. Leave the original file unchanged. Do not automatically download or mirror reference material from the web. Record source/use metadata and an integrity checksum for the imported copy.
- Reason: A project-owned copy remains available if the original path changes and can be included in the complete project backup.
- Impact: Stage 01's no-bulk-download rule remains in force. Only an explicitly selected file with an adequate source/use basis is imported. Imported assets follow project isolation, versioning, backup, and the no-automatic-pruning rule in D-0026.

## D-0026 — Preserve local MVP history without automatic cleanup

- Status: accepted
- Date: 2026-10-12
- Decision: The local MVP does not automatically delete or prune project records, asset versions, generated drafts, review decisions, or audit history. The local MVP does not provide a whole-project deletion feature. Superseded records remain available as history.
- Reason: The user chose to preserve all versions and review records and defer project deletion rather than risk removing material or provenance automatically.
- Impact: Storage cleanup and project deletion are later decisions. Rights, privacy, or retention restrictions must be checked before importing or using a source; a restricted item is blocked from use and must not be kept contrary to its known conditions. This decision does not prevent a separately authorized item-level removal flow if later required; that flow must preserve a minimal non-sensitive audit/tombstone record where permitted.

## D-0027 — Start the synthetic local platform implementation

- Status: accepted
- Date: 2026-10-12
- Decision: The user's explicit request to proceed with implementation starts `platform_build` for the Stage 01–05 local MVP defined by D-0013–D-0026. Implement, install project dependencies, and validate with synthetic fixtures and a mock adapter.
- Reason: The user requested implementation after the entry specifications and product choices were recorded.
- Impact: Platform source, tests, local runtime and launcher are authorized. Actual project content, external image-provider calls, cloud synchronization, remote access, and publication retain their separate conditions. Platform acceptance is a later human decision supported by implementation evidence.

## D-0028 — Use offline schema validation and preserve restored review history

- Status: implementation baseline
- Date: 2026-10-12
- Decision: Use pinned `jsonschema` Draft 2020-12 validation with bundled schemas and format checks, and `pyrage` 1.4.0 for the accepted age passphrase format. Keep all runtime dependency pins in `requirements.txt` and frontend package/lock files. Restore remaps project-owned IDs and storage references, preserves original artifact/version and backup lineage, and marks copied reviews as historical evidence; current gates in the new project require a new human decision.
- Reason: Local validation must work without external schema fetches. Restoring a separate project copy must preserve reviews without silently inheriting approval authority under D-0007.
- Impact: Historical source reviews remain inspectable; restore does not overwrite records, create a current approval, or authorize real content. Dependency versions are implementation releases and remain distinct from artifact, schema, database, and package-format versions.

## D-0029 — Pause implementation for product-direction revision

- Status: accepted
- Date: 2026-10-13
- Decision: The user's product feedback requires a simpler, conversation-led creative workflow, a dedicated character-creation stage, story-first format selection, useful visual storyboards, immediate versioned feedback, and agent orchestration with bounded evaluation/revision as the preferred workflow model. Pause further implementation while the revised requirements are reviewed. The product-direction details and candidate-tool map are recorded in `docs/product-direction-revision.md`.
- Reason: The current interface and mock outputs do not provide useful story direction or image quality, and the user reports that the workflow is overly complex and unclear. The initial tool/technique recommendations were never connected to explicit adoption decisions before the project narrowed to a mock-first platform build.
- Impact: D-0027 records the earlier implementation authorization and work already performed; it does not authorize additional implementation during this review. Conflicting UX and output expectations in the prior MVP scope and Stages 01–05 are superseded by the revised direction once reviewed. Existing local storage, backup, isolation, and human decision boundaries remain in effect unless separately changed. No image plugin, model provider, agent framework, workflow engine, or external automation tool is selected by this decision. Resume implementation only after the user accepts a reconciled product scope.

## D-0030 — Require a pre-implementation decision pack

- Status: accepted
- Date: 2026-10-13
- Decision: Before implementation resumes, maintain one reviewable decision pack that maps every stage to its user flow, candidate plugins/open-source tools, AI techniques, human decision points, overall flowchart, and remaining choices. The pack is `docs/preimplementation-decision-pack.md`; its tool selections remain proposals until the user accepts them or a scoped evaluation supports a decision.
- Reason: The user asked to understand stage-by-stage use of tools and techniques, how the process will run, and which choices remain before starting implementation.
- Impact: D-0029's implementation pause remains in effect. Candidate names are not installed dependencies or provider authorization. Record unresolved data/location, model, hardware, license, agent-loop, and quality criteria before selecting dependent tools. Recheck current versions, compatibility, and licenses before any future integration.

## D-0031 — Set local-first execution and the first technical vertical slice

- Status: accepted as the current direction; implementation remains paused under D-0029
- Date: 2026-10-13
- Decision: Keep the application, project database, and source materials local, and prefer local inference. GPU/VRAM use is allowed. When quality, speed, or hardware makes it useful, a selected stage may use an external model; the user accepts its generation cost and transfer of the selected inputs. External workflows must disclose the provider, transferred input types, retention terms, and cost limits, and must not automatically upload every reference. Start technical validation with a Stage 04 story-to-storyboard vertical slice using a clearly labeled synthetic character fixture. Character creation remains a first-class requirement and must be available before the first real project episode. Use LangGraph first for this slice to validate persistent checkpointing and human pause/resume; simplify to an explicit Python state machine if the local persistence/recovery burden outweighs the benefit.
- Reason: The user prefers a local-only project setup while allowing GPU and conditional external generation when needed, and delegated the choice of an implementation starting slice. Stage 04 isolates the story/board feedback loop; the synthetic fixture allows harness behavior to be evaluated without bypassing the requirement for a dedicated character-design stage in real use.
- Impact: This resolves DQ-01's broad locality preference, the hardware/external allowance in DQ-03, and DQ-09's initial technical slice; LangGraph is the first-slice engineering choice for DQ-05, with a defined fallback. A GPU was observed on the current host, but D-0033 clarifies that it is not the target-machine baseline. Provider/model identity, target-machine profile, permitted data categories per provider, retention behavior, and numeric cost limits remain open. This decision does not resume implementation, authorize a provider API call, create real project content, or authorize publication; D-0029 remains active until the user accepts the reconciled scope and separately resumes implementation.

## D-0032 — Recommend quality and execution defaults for the next specification review

- Status: assistant recommendation; awaiting product-direction review
- Date: 2026-10-13
- Decision: For the first Stage 04 slice, use four bounded logical roles (story generator, storyboard planner, evaluator, deterministic validator), allow at most two targeted creative revisions after the initial draft, and retry one transient technical failure. Do not use a scalar quality score as an approval. The evaluator reports `blocker`, `revise`, or `optional improvement` issues tied to a beat/panel and cites the source requirement. Proposed character package: behavior/voice bible plus silhouette, proportions, palette, immutable identity cues, full-body front/three-quarter/profile/back views, six core expressions, and three characteristic acting poses. Treat these as a reviewable group of assets, not one crowded generated image; human correction remains available. Proposed image use: one rough per panel initially and one additional candidate only for a user-selected panel; never rerun the whole episode automatically. Keep local source/history, send only the selected task summary and explicitly selected images to an external provider, exclude secrets and unrelated references, and use only a paid tier whose published terms exclude training use. Stop if provider retention/transfer conditions or spend cannot be determined. Limit the first synthetic comparison to USD 5 total; set any real-episode cap after choosing the provider and seeing the first accepted cost estimate.
- Reason: These defaults prioritize useful feedback and controlled iteration while keeping the user in charge of creative selection. They reduce surprise transfer and runaway generation, and can be evaluated on a synthetic fixture before real-content execution.
- Impact: Proposed values narrow DQ-06–DQ-11 but are not recorded as user-approved product decisions. Gemini Nano Banana 2.1 and OpenAI GPT Image 2 are synthetic comparison candidates only. D-0033 supersedes the host-specific hardware assumption: compare local and external paths against a target machine selected for the project, which may be another PC. No provider call, content creation, code work, or implementation restart is authorized by this recommendation; D-0029 remains active.

## D-0033 — Keep image-generation hardware independent of the current PC

- Status: accepted user constraint; implementation remains paused under D-0029
- Date: 2026-10-13
- Decision: Do not set image-generation requirements or choose the local/cloud split based on the current PC. The project may be moved to another, higher-spec PC when local image generation benefits from it. Keep source code and specifications portable through Git; make setup, dependencies, and machine-specific configuration reproducible and avoid fixed machine paths. Keep secrets, model weights/caches, project records, source references, and generated media out of Git by default; their storage and transfer must be explicit. Evaluate local runtime requirements on the intended target machine(s), which are not selected yet.
- Reason: The user explicitly said hardware recommendations should not be based on the current computer and that using another PC through Git is acceptable if higher specifications are needed.
- Impact: The GTX 1650 observation is incidental host information, not a product constraint. DQ-03 now asks for target execution profiles; local image trials wait until the target machine is chosen. D-0033 itself did not authorize repository creation or push; the later project-wide push authorization is recorded in D-0034. Provider calls and implementation remain separately gated.

## D-0034 — Commit and push substantial work units project-wide

- Status: accepted user instruction; applies to all project workstreams
- Date: 2026-10-13
- Decision: At the end of each substantial, coherent, reviewable work unit, create a focused commit and push it to the current branch's configured upstream. Do not commit after every message or small edit. Commit titles use exactly one prefix—`[추가]`, `[수정]`, or `[삭제]`—followed by a concise description. Stage only paths in the work unit, inspect the staged diff, and perform relevant validation before committing. Push normally without rewriting history; if no upstream exists, the branch has diverged, or push is rejected, keep the local commit and report the issue. Exclude secrets, credentials, private project data, local databases, source references, model weights/caches, and generated media unless a specific storage/versioning decision allows them.
- Reason: The user asked for commits and pushes at larger task boundaries, requested a small Korean prefix set, and asked that this apply to the entire project rather than only this thread.
- Impact: This standing instruction applies across stages and threads. It authorizes normal pushes of completed project work units to the configured upstream; it does not authorize force-pushes, broad staging of unrelated work, or uploading excluded local/private assets.

## D-0035 — Resume the revised Stage 04 implementation with a delegated P0 baseline

- Status: explicit user implementation authorization; engineering defaults delegated to the assistant
- Date: 2026-10-14
- User instruction: “p0 기준을 권고안으로 정리하고 구현을 재개해”.
- Decision: Supersede D-0029's implementation pause for the revised Stage 04 synthetic technical slice. Apply and document the concrete P0 engineering baseline in `docs/p0-implementation-baseline.md`: minimal project intake, additive studio v2 contracts alongside unchanged legacy v1, a single conversational workspace, LangGraph with durable local checkpoints, four specialist roles supervised by one orchestrator, exact-version human story/format/storyboard review, append-only artifacts/events, targeted feedback routing, two automatic creative rewrites and one transient technical retry per bounded segment. Default the first supported text layout to explicit overlay; unsupported or unknown text modes block instead of silently changing. Technical fixture acceptance and model-backed creative quality are separate results.
- Reason: The user explicitly asked to turn P0 into recommendations and resume implementation after the scope and sequence had been explained. This authorizes routine engineering choices within that plan, including dependency installation and meaningful checks, without another restart question.
- Impact: `platform_build` is active for this work. A Stage 04 technical slice uses synthetic character/series fixtures and does not satisfy the independent character-creation prerequisite for actual episodes. Concrete provider execution, selected input transfer/retention, model/license, target machine, numeric spend and time limits remain P1; real projects/content remain P2. The prior broad local/GPU/external allowance is retained and must not be asked again. D-0032's P0 retry/role recommendations become engineering defaults through this delegation; its character-sheet quantities, model candidates and USD 5 proposal remain unevaluated recommendations. User-facing creative approval and publication remain human-owned. Apply D-0034 at coherent work-unit boundaries.

## D-0036 — Implement character-first conversational intake

- Status: accepted implementation direction
- Date: 2026-10-18
- Decision: The user's explicit request to implement the 2026-10-16 feedback starts the character-first revision. New projects develop character appearance/personality/desired feeling in one orchestrator conversation, review and revise an exact direction version, then proceed to actual visual candidates and a character sheet before episode creation. Simplify ordinary UI to current step/result/conversation/actions and show each completed implementation slice promptly.
- Reason: The user identified character creation and a reusable character sheet as the project's foundation and asked to apply the full staged input/review/correction experience observed in Meta Animated Drawings.
- Impact: This changes D-0031/D-0035's default product entry from the Stage04 technical slice to character direction. Existing Stage04/v1 fixtures remain separately accessible and do not become approved characters. First slice implements durable direction review only; visual candidates, actual sheets, reference image upload, image generation and v2 backup remain subsequent work. No generic implementation-restart question is required. Actual provider calls retain concrete P1 limits and content remains P2. The user requested optimal model/limit recommendations; the USD10/USD3 recommendations in docs/character-model-evaluation.md are proposals, not spend approval or active configuration. Apply D-0034's coherent-unit commit/push policy.

## D-0037 — Connect ChatGPT subscription usage without paid API fallback

- Status: accepted implementation and bounded connection test
- Date: 2026-10-18
- Decision: The user explicitly requested ChatGPT Pro usage in this local app, stopping at the usage limit and checking the real character dialogue step by step. Add this app's official OAuth/PKCE Sign in with ChatGPT connection and the public Responses route. Discover models for that signed-in account. Default character work to this subscription provider, retain the existing offline fixture only through an explicit engineering option, and keep LangGraph's designer/validator/evaluator/human review structure.
- Reason: Current official guidance supports subscription usage in personal projects that run locally. An API key and the earlier USD10 proposal are unnecessary for eligible text requests. The subscription route currently does not support image generation.
- Impact: OAuth account consent, token refresh, model selection and a durable usage-stop latch are local runtime concerns. No ambient API key, paid API fallback or automatic retry is permitted. Bound engineering acceptance to a fictional character, 40 attempted model calls per character project and 60 seconds per call; each turn has at most designer and evaluator calls. Preserve previous direction versions and user input on failures. Account/model changes invalidate unfinished work before new inference. Ask the user to complete actual browser sign-in/consent when needed; do not collect passwords or tokens in chat. Keep additional-credit continuation off in ChatGPT usage settings; the app cannot claim to have changed that account setting through an undocumented API. Image candidates, sheets, production content and publication remain separate scope.

## D-0038 — Implement visual candidate revision and character-sheet review

- Status: accepted implementation direction and image connection choice
- Date: 2026-10-18
- Decision: Implement confirmed direction → visual candidates → selected-candidate revision → chosen sheet coverage → visual sheet review/partial correction → exact-version confirmation. The user explicitly selected “Codex 이미지 생성 + 앱 반영”. Keep app-owned durable image requests, local image import, source lineage and review controls; execute the selected image requests using Codex's built-in image generation in this chat. There is no paid API fallback or unattended image provider in the app.
- Reason: The user asked to continue from the verified character conversation, inspect each result promptly and revise before completing the reusable character sheet. Current official SIWC limitations exclude hosted image generation, so its text connection cannot be presented as the image engine.
- Impact: Candidates and sheets consume the exact confirmed direction. Changing direction, candidate selection, coverage or a sheet component invalidates dependent current approvals while preserving history. A candidate selection is not final sheet approval. Coverage is chosen explicitly; D-0032's proposed view/expression/pose counts are not accepted minima. Validate project ownership, exact versions, decoded image contents and stored checksums before approval/handoff. Distinguish the recommended job prompt from an actually executed prompt; keep unavailable model/seed values unknown. Bound the first fictional engineering walkthrough to eight built-in image operations, with no automatic retry or provider fallback. User-facing final creative confirmation and production/publication authority are retained; UI QA is not production approval. Apply D-0034 after review and validation.

## D-0039 — Connect the confirmed character to conversational story and visual storyboard work

- Status: accepted implementation direction and fictional walkthrough material
- Date: 2026-10-18
- Decision: The user asked to connect the confirmed character sheet to story and storyboard creation, with conversational input, immediate previews, scoped corrections and separate confirmations at each step. Add an episode service alongside the legacy fixture run service. Pin the exact approved direction, selected candidate, sheet, component image IDs/checksums and human decision as an immutable character snapshot for every episode role and artifact. Use intent dialogue → story draft/review/correction → G1 → format choice/review → written board/cut correction → actual visual roughs/overview → human G2. The user chose the fictional seed-care story for first validation.
- Reason: The previous slice deliberately stopped before story workers because they read mutable current project data and were coupled to fixture retries and technical-only board reviews. Connecting them unchanged would lose the exact character basis and misstate visual quality.
- Impact: Keep the existing fixture paths and contracts. The new path uses the established Pro subscription connection with verified PNG sheet inputs, the shared existing project cap of 40 attempted specialist calls including earlier character calls, an additional 40-attempt episode cap, two role attempts per turn, 60 seconds per role and zero automatic inference retry/rewrite. The limits count failures and are reserved before network I/O; restart does not repeat an uncertain attempt. Use Codex image generation plus explicit local import for pre-G2 roughs, at most eight additional operations for the first fictional walkthrough. Preserve old artifacts, invalidate only dependent current approvals, and require exact-version human confirmation. Actual image pixels, declared prompt/source metadata and unavailable provenance remain distinct. This implements an episode drafting workflow; it does not grant Stage 05 execution, production/publication or rights approval. Apply D-0034 after validation.
- Runtime clarification (2026-10-18): The image tool rejected two six-reference requests during immediate argument validation, before producing or executing an image generation. Track those rejected submissions separately from actual built-in image executions; retain both records. The eight-image-operation bound remains unchanged. Use at most five actual image inputs, explicitly recording any unused sheet reference. This does not relax the subscription's attempted-call accounting, which always counts failed network attempts.
