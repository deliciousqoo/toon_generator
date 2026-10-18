# Project instructions for toon_generator

## Project purpose

This repository defines a personal, local-first workspace for the Instagram toon pipeline. The existing Stage 01–05 synthetic/mock prototype is retained as a legacy baseline. The user resumed implementation on 2026-10-14 (D-0035). Build the revised Stage 04 synthetic technical slice under `docs/p0-implementation-baseline.md`, with the product journey in `docs/product-direction-revision.md`. Real project/content production remains separately gated.

The user authorized the character-first revision on 2026-10-18 (D-0036), based on the feedback of 2026-10-16. New projects start with a character conversation, direction review, visual candidates and a character sheet before episode work. Implement each UI/worker/persistence/revision slice together and show it in preview promptly. Keep the ordinary interface limited to the current result, conversation, step and necessary actions. The first slice is `docs/character-direction-guide.md`; it implements direction review, not visual candidate or sheet completion. Existing Stage 04 fixtures remain an explicit technical path at `?storyFixture=1`. Actual provider execution still requires its concrete P1 scope; never count a direction confirmation as sheet approval.

The user explicitly authorized connecting their ChatGPT Pro usage and testing the actual character dialogue on 2026-10-18 (D-0037). Use this app's own official Sign in with ChatGPT consent and public Responses route. Never extract another app's credentials, use an ambient API key, fall back to paid API billing, or automatically retry after a usage stop. Use a bounded fictional character for engineering acceptance, at most 40 attempted specialist calls per character project, 60 seconds per call, two role calls per turn. OAuth consent and account-specific model discovery determine the available connection; the API-budget proposal is not the default. Keep paid-credit continuation disabled in ChatGPT usage settings. Image generation is outside this integration's supported scope. The user requested this connection and test; do not request a generic provider-execution approval again.

The user authorized implementing visual candidate comparison/revision and character-sheet completion on 2026-10-18 (D-0038), and explicitly selected “Codex 이미지 생성 + 앱 반영”. The app prepares durable generation/edit requests and imports actual images; Codex's built-in image generation executes selected requests in this chat. Do not imply that the app's SIWC text token supports hosted image generation or that an unattended image worker exists. Keep paid API fallback disabled. The first engineering walkthrough uses the existing fictional direction, at most eight built-in image operations, and visibly records exact source versions and actual generation provenance (unknown values remain unknown). Candidate choice, coverage choice and final creative confirmation remain separate human decisions. Technical QA may exercise these controls on the fictional project; it is not production or publication approval. Store image binaries outside Git and preserve old versions on rework.

## Source of truth and authority

1. Approved specifications, character/account bibles, and recorded decisions are the source of truth.
2. A discussion thread is not an approval record by itself. Accepted conclusions must be reflected in repository files.
3. A human owns creative direction, character identity, rights decisions, final quality, and publication. AI may prepare drafts and recommendations, but may not self-approve or publish.
4. A production project is the isolation boundary for project-specific briefs, references, characters, content items, and provenance. Cross-project reuse requires an explicit decision and traceable source records.
5. A project owns its recurring protagonist and series direction. `content_id` identifies one episode; project-level reference, character, and strategy packages do not require it.

## Working rules

1. Do not overwrite an approved asset, prompt, workflow, or decision. Create a new version and keep the previous version traceable.
2. Every stage handoff identifies its `project_id`, input and output versions, owner, approval condition, validation, unresolved risks, and next consumer.
3. Store structured handoff data as JSON when a later stage needs to consume it. Use the stage specification for the schema and required fields.
4. Record model, workflow, prompt, seed, reference version, and tool versions for generated images whenever available. Missing provenance must be marked as unknown, not guessed.
5. Do not commit API keys, access tokens, private credentials, or personal data. Keep generated binaries out of Git until a storage and versioning policy exists.
6. External references may be analyzed for structure, composition, and patterns. Do not copy protected characters, text, panels, or distinctive artwork.
7. Do not claim that an output is complete or verified unless the relevant file, preview, test, or approval record was actually inspected.
8. Keep implementation details, decisions, and portfolio writing consistent with the work actually performed.
9. When changing an established rule, record the reason, impact, and affected artifacts in `DECISIONS.md`; supersede an old decision with a new entry instead of silently editing history.

## Operating modes

The repository entered `platform_build` through the user's explicit implementation request on 2026-10-12 (D-0027), paused for product-direction revision on 2026-10-13 (D-0029), and resumed through the user's explicit instruction on 2026-10-14 (D-0035): “p0 기준을 권고안으로 정리하고 구현을 재개해”. The current work may change application code, install implementation dependencies, define gated provider adapters, and validate the synthetic Stage 04 slice. Apply the delegated P0 engineering recommendations and record their rationale; do not ask again for implementation restart. Executing a provider call and using real content remain governed by P1/P2. The following rules apply whenever a workstream is in `specification_only` before its relevant explicit transition:

- define pipeline behavior, platform boundaries, contracts, approval gates, automation limits, recovery paths, storage, and provenance using abstract examples only;
- use `unknown`, placeholder values, or example IDs instead of requesting or inventing real account names, character names, content ideas, scripts, dialogue, storyboard panels, dimensions, model choices, or publication data;
- treat stage inputs and outputs as future execution contracts, not as a request to populate a real project now;
- treat `next`, `queued`, and `completed` in a thread index as workstream planning status, not as permission to start production;
- ask only questions about the pipeline, platform, schemas, roles, gates, validation, storage, provenance, and implementation choices while this mode is active.

The following modes are distinct:

- `specification_only`: edit specifications and abstract examples only.
- `platform_build`: resumed by D-0035 for the revised Stage 04 technical slice. Use synthetic fixtures, visibly identify deterministic workers and developer thumbnails, and never report them as AI creative-quality evidence. Provider adapter code may be implemented, but actual calls require the relevant P1 configuration and execution scope. Real project/content values remain prohibited.
- `content_execution`: after platform acceptance and a separate explicit user instruction, use approved real project inputs to produce an actual episode. Platform implementation, a completed stage, or synthetic acceptance does not imply this transition.

Neither choosing the platform direction nor changing a stage index starts code or content production. Never infer a mode transition from a stage number, a completed specification, or a `next`/`queued`/`completed` label.

## Git rules

- Check `git status` before editing and keep unrelated user changes intact.
- Apply the project-wide work-unit commit policy in D-0034: when a substantial, coherent work unit is complete and reviewed, commit it and push it to the current branch's configured upstream. Do this at work-unit boundaries, not after every message or small edit.
- Use exactly one of these Korean title prefixes: `[추가]`, `[수정]`, or `[삭제]`, followed by a concise description. Choose the prefix for the main purpose of the commit; split unrelated work into separate commits.
- Before committing, inspect status and the full staged diff, stage only paths belonging to that work unit, and perform the relevant validation. Do not use broad staging as a shortcut when unrelated or untracked work exists.
- Push the resulting commit to the existing configured upstream without rewriting history. Never force-push. If the push is rejected, the upstream is missing, or the branch has diverged, preserve the local commit and report the blocker instead of trying a destructive or history-rewriting workaround.
- Do not use history-rewriting or destructive commands to discard work unless the user explicitly asks for it.
- Review the diff and run the relevant validation before calling a change complete. A clean working tree is not itself proof of correctness.
- Never commit secrets, credentials, personal data, or large binary assets without an explicit repository decision.

## Document conventions

- Project rules live in this file.
- The operating model and artifact contracts live in `docs/01-operating-rules.md`.
- Stage specifications live under `docs/stages/` and follow the required stage template.
- Cross-cutting decisions live in `DECISIONS.md` and are append-only in spirit: new decisions explain changes to earlier ones.
- Reusable prompts and workflow definitions live under `workflows/` when they are introduced.
- Use repository-relative paths in documents, stable IDs for content and versions, and explicit dates for approvals and decisions.
- Keep project setup (reference, character, and series direction) reusable across episodes. Select each episode's format from its request and permitted structural reference observations; ask a human when they are unclear or conflict.
- A storyboard specification uses Level 1 beat thumbnails by default, with cut-by-cut written decisions that carry the information needed for G2 review and Stage 05 generation. Add visual detail only to cuts that need clarification. An AI draft package includes per-cut images and a composed full-episode preview; neither is a publishable export.

## Completion contract

Every stage change should identify:

- the input and output artifacts;
- the changed files;
- the validation performed;
- unresolved questions or risks;
- the next stage that can consume the result.
