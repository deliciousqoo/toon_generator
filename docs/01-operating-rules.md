# Operating rules

> **Current direction (2026-10-14):** D-0035 resumes `platform_build` with the delegated [P0 implementation baseline](p0-implementation-baseline.md). Implement the Stage 04 synthetic technical slice with the conversation-led workflow, simplified setup, independent character prerequisite, story-first layout, immediate revision, and agent harness in [Product direction revision](product-direction-revision.md). These supersede conflicting legacy Stage 01–05 interaction details below. The v1 backup remains a legacy capability; studio v2 backup/restore must be integrated and checked before claiming complete project portability. Provider execution and real-content use remain P1/P2.

## 1. Goal and scope

The project defines a personal, local-first platform for a repeatable AI-assisted Instagram toon pipeline. The first validation target is the platform itself: its Stage 01–05 workflow, exercised with synthetic fixtures and a mock image adapter. Producing a real episode is a later, separately authorized activity.

### Included in the local platform MVP

- project setup and reusable project-owned reference, character, and series records for Stage 01–03;
- episode intake and Stage 04 storyboard workflow, including short-topic proposals and preservation of supplied detailed stories/dialogue;
- an episode format selected from its request and permitted structural reference observations, rather than one fixed panel count;
- Level 1 beat thumbnails as the default storyboard visual rough, with complete written cut decisions and added visual detail only where needed;
- human edits to dialogue/cut descriptions and a human-recorded storyboard approval (`G2`);
- Stage 05 mock image drafts with clearly labeled synthetic outputs, per-cut candidate selection, selected-cut regeneration, and a composed episode preview;
- a human-recorded visual draft review (`G3`);
- versioned project/episode inputs, approvals, and generation metadata using synthetic fixtures during MVP validation.

### Deferred beyond the local platform MVP

- real project/content production, until the local MVP is accepted and the user separately authorizes an execution transition;
- human retouch, optional AI refinement, QA, rights/export preparation, and publication (Stage 06);
- advanced harness automation (Stage 07), hosted/multi-user platform operation, multi-account permissions and scheduling;
- autonomous publishing, production LoRA training, and automatic competitor scraping.

The first mock adapter makes no external calls. Adding one provider adapter is a later synthetic-data milestone after provider/model, credentials, data transfer, cost limits, and failure/retry conditions are specified and separately authorized. D-0024 and `docs/platform-technical-baseline.md` set the local MVP's Python/FastAPI + React/TypeScript/Vite stack, SQLite metadata store, local asset store, backup choices, and minimum Stage 01–05 contract approach. Provider and hosted-operation choices remain deferred.

### Operating modes and transitions

The repository has three distinct operating modes:

| Mode | Meaning |
|---|---|
| `specification_only` | Define the pipeline, platform, contracts, roles, gates, validation, recovery, storage, and provenance with abstract examples. Do not populate or request a real production project. |
| `platform_build` | After an explicit implementation-start instruction and completion of the MVP entry decisions, build/test the local application using synthetic fixtures only. Start with the mock adapter; provider calls require a separate reviewed condition and authorization. |
| `content_execution` | After platform acceptance and a separate explicit user instruction, use approved project inputs to run an actual episode through the state machine. |

`platform_build` was explicitly authorized on 2026-10-12 by D-0027 and produced the current local prototype. D-0029 pauses additional implementation pending user review of the revised scope. If implementation resumes, use synthetic fixtures unless the user separately authorizes a provider validation or real-content execution. D-0013 alone did not authorize the prior build. Use `unknown`, placeholders, example IDs, and synthetic fixtures for any future platform validation.

Stage documents describe contracts for future platform or content use. Their input/output sections do not mean that real inputs should be collected during specification work. Likewise, `next`, `queued`, and `completed` in `docs/THREAD_INDEX.md` describe workstream status and do not authorize a code or content transition.

Platform implementation begins only after the user explicitly requests it (for example, “로컬 플랫폼 구현 시작”) and the MVP entry decisions are recorded. Real content execution begins only after platform acceptance and a separate explicit instruction (for example, “실제 에피소드 실행 시작”). The exact Project Brief, project-owned versions, rights/use restrictions, and human approval records are then required inputs.

## 2. Terminology

| Term | Meaning in this project |
|---|---|
| Production project | An isolated production space for reusable account/series direction, protagonist, references, character assets, episodes, and provenance. It is distinct from a repository workstream or discussion thread. |
| Project brief | The project-scoped configuration containing account/series direction, a required primary character, audience, tone, supported formats, exclusions, reference questions, constraints, owner, version, and approval. It is reused across episodes until a new approved version replaces it. |
| Account | The external content identity for which a series is produced. |
| Character | A named visual and behavioral identity with a character bible and sheet. Every project has a recurring protagonist; supporting characters may be added as needed. |
| Series | A repeatable content pattern under an account, including its audience and tone. |
| Content item / episode | One Instagram toon episode independently tracked through the content state machine and identified by `content_id`. |
| Asset | A file or structured record consumed or produced by a stage. |
| Work-in-progress | A non-approved version that may be edited or replaced. |
| Approved artifact | A human-approved version that may be consumed by the next stage; it is not overwritten. |
| Publishable export | A later-stage file and metadata package that passed QA and rights review; it is outside the first validation target. |
| Reference | External or internal material used to analyze patterns or guide a decision. |
| Run manifest | The record of a generation or refinement run, including inputs, tools, parameters, and outputs. |
| Approval gate | A human decision that permits a defined state transition. |
| Workstream | A project-level body of work such as research, automation, or Git policy. It is not a content state. |

### Production-project boundary

The platform may contain multiple production projects. A project owns and versions its project brief, references, character bible, series strategy, content items, generation runs, approvals, and publication records. These records carry a stable `project_id` and must not be automatically reused across projects. A future shared asset or template mechanism requires an explicit source project, permission/rights basis, version, and provenance record.

The specification phase defines these fields and boundaries without requiring actual project values. Platform-build validation uses synthetic project fixtures; concrete project briefs are content-execution inputs and remain out of the platform-build phase.

### Canonical project and episode briefs

The Project Brief is project-scoped and reusable. It records `project_id`, project/account or series direction, the primary character (or a Stage 02 setup requirement before approval), audience and tone hypotheses, supported format envelope, exclusions, reference questions, constraints, owner, version, and human approval. Its minimum persisted shape is defined by `project_brief` in `docs/contracts/mvp-records-v1.schema.json`. A project-level reference, character, or strategy package carries `project_id` and omits `content_id` unless it is intentionally episode-specific.

An Episode Brief carries `project_id` and `content_id`, the request/intent, the supplied input detail (short topic or developed story/script), exact source/reference IDs and versions, any requested format, episode-specific constraints, and unresolved questions. A short topic can receive a proposed story direction; an existing detailed story or dialogue is preserved unless the user asks to change it. Its minimum persisted shape is defined by `episode_brief` in the bundled MVP JSON Schema.

## 3. Project workstreams and outputs

The thread index organizes project work. Its outputs are inputs to later workstreams, but only the content states below describe the lifecycle of a content item.

| ID | Workstream | Required input | Primary output |
|---|---|---|---|
| 00 | Governance and specification | Existing repository files and open project questions | Goal, glossary, state machine, contracts, approval and repository rules |
| 01 | Reference research and benchmarking | Project Brief supported formats, research questions, external references | Reference matrix, pattern analysis, rights/use notes |
| 02 | Character bible and sheet | Accepted references and character constraints | Character bible, character sheet, identity checklist |
| 03 | Account concept and content strategy | Reference matrix and character bible | Account/series direction, audience, content pillars, format constraints |
| 04 | Story and storyboard | Accepted strategy and character bible | Script, shot/panel plan, structured storyboard |
| 05 | AI image-generation workflow | Accepted storyboard, character references, generation constraints | Prompt/workflow definition, run manifest, AI draft asset package |
| 06 | Human polish and QA | Selected draft, run manifest, approval notes | Retouched asset, local refinement result, QA and publication package |
| 07 | Harness and automation | Repeated handoffs and accepted contracts | Checks, helpers, and automation that stop at human gates |
| 08 | Git and personal local platform | Versioning, isolation, and storage requirements | Local-first MVP design and acceptance plan; implementation remains separately authorized |
| 09 | AI technical blog and portfolio | Verified project records and artifacts | Evidence-based technical notes and portfolio material |

Workstreams `07–09` support production and do not advance a content item by themselves.

Stages 01–03 establish project-level references, protagonist identity, and series direction for reuse. Stages 04–05 repeat per episode. The first validation cycle ends with a G2-approved storyboard and a G3-reviewed visual draft package. Stages 06–09 remain documented follow-up work; they are not prerequisites for calling the storyboard/draft cycle complete.

## 4. Content state machine

```text
idea -> script -> storyboard -> ai_draft -> human_retouch
      -> ai_refine -> qa -> approved -> published
```

The forward transition is allowed only when the exit condition and human gate for that state are satisfied. Rework is explicit: a rejection names the return state, preserves the rejected version, and creates a new version. A content item is never silently moved backward or overwritten.

The state machine describes the broader future lifecycle. The first validation target stops at `ai_draft` after the human G3 decision. It does not imply retouch, QA, approval for publication, or actual posting. The optional `ai_refine` path remains a Stage 06 follow-up clarification and must be resolved before automating or executing that extension.

| State | Entry condition | Required output before exit | Human gate / permitted rework |
|---|---|---|---|
| `idea` | An Episode Brief exists; it may contain a short topic or a developed story/script | Brief with project/episode IDs, intent, source references, format request if any, and constraints | Scope/bible gate; ask when request/reference leave a material conflict unresolved |
| `script` | Idea is in scope | Selected script or structured story record | Story gate; return to `idea` for a new premise |
| `storyboard` | Story is selected or user-provided story is accepted | Cut-by-cut written plan, low-fidelity visual roughs, and a full-episode review view | G2 human gate; return to `script` or `idea` |
| `ai_draft` | G2-approved storyboard and approved project character package are available | Per-cut draft images, composed full-episode preview, prompt/workflow and run manifest | G3 human gate; return to `storyboard` or regenerate as a new draft |
| `human_retouch` | A draft is selected | Human edit record and retouched working asset | Polish gate; return to `ai_draft` if the source is unsuitable |
| `ai_refine` | Retouched asset and refinement scope are defined | Local refinement result with changed-region record | Refinement gate; return to `human_retouch` or create another refinement version |
| `qa` | A candidate and provenance package exist | QA checklist, rights review, export checks, caption/metadata draft | QA/rights gate; return to the failing earlier state |
| `approved` | QA/rights gate passes | Immutable publishable export and recorded approval | Human publication decision; any change creates a new version and reopens QA |
| `published` | Approved package is actually published | Publication record with destination, timestamp, and final artifact reference | No silent edits; corrections are a new content version |

Minimum transition record:

```text
project_id, content_id, from_state, to_state, input_artifact_ids, output_artifact_ids,
actor, decision, timestamp, notes, next_consumer
```

An approval record additionally contains the approver, approved artifact version, decision (`approved` or `rework`), reason/notes, and the next permitted state. AI-generated confidence or checklist output is supporting evidence, not an approval record.

## 5. Stage input/output contracts

The following is the baseline contract. Each later `docs/stages/*.md` file may add required fields, but may not remove the handoff and approval requirements without a new decision.

| Stage | Input | Output |
|---|---|---|
| Governance | Existing rules, decisions, thread plan, unresolved questions | Approved operating rules, glossary, state/approval model, stage contract, decision entries |
| Reference research | Project brief and candidate references | Reference matrix, structural observations, source records, rights and reuse notes |
| Character | Accepted reference analysis and character constraints | Character bible, visual sheet, identity invariants, versioned reference set |
| Account strategy | Reference analysis and character bible | Account bible, series definition, audience/tone, content pillars, format constraints |
| Storyboard | Accepted strategy and character bible | Script, structured story record, panel/shot plan, text/layout constraints |
| Image generation | Accepted storyboard, character references, generation constraints | AI draft files, prompt/workflow version, run manifest, source and output references |
| Polish and refinement | Selected AI draft, run manifest, human edit brief | Retouched working file, refinement output, changed-region notes, updated provenance |
| QA and publication preparation | Candidate export, source references, provenance, captions/metadata | QA and rights checklist, final export, publication metadata, approval record |
| Harness and automation | Repeated handoffs and accepted validation rules | Deterministic checks and helpers with explicit stop points at human gates |
| Git and platform | Artifact/version needs, account isolation needs, storage constraints | Repository conventions, storage/versioning proposal, implementation plan |
| Blog and portfolio | Verified decisions, diffs, previews, and validation records | Claims-safe technical note or portfolio entry with evidence links |

Every handoff must make the next consumer able to identify the exact project and input version. The minimum Stage 01–05 persisted record carries `artifact_type`, `project_id`, `content_id` when it belongs to an episode, `artifact_id`, artifact `version`, `schema_id`/`schema_version`, `state`, `created_at`, `created_by`, `owner`, exact `source_artifact_refs`, `approval`, `validation`, `provenance`, `unresolved_risks`, and `next_consumer`. Image-generation provenance should include model, workflow, prompt, seed, reference versions, and tool versions when available. Stage-specific packages may add fields but must preserve these handoff facts; see `docs/contracts/mvp-records-v1.schema.json`.

For human-readable JSON examples, each enum-like field shows one illustrative value; alternatives, when defined, are explained in prose or tables rather than encoded as a pipe-delimited string. Stage-document examples may omit the formal common envelope and do not prove schema validity. The local MVP contracts are the bundled JSON Schema Draft 2020-12 file and synthetic fixture set in `docs/contracts/`; full Stage 00–09 schemas and production compatibility remain deferred until later evidence and review. Schema validation does not replace human approval.

## 6. Human and AI responsibilities

### AI may assist with

- reference categorization and structural comparison;
- story alternatives and structured drafts;
- prompt and workflow preparation;
- image draft generation;
- localized inpainting, cleanup, and refinement;
- schema, completeness, and checklist checks;
- caption and publication metadata drafts;
- repository checks that do not alter approval state.

### Human owns and approves

- project scope, project brief, and account/character direction;
- reference-use and rights decisions;
- story selection and storyboard acceptance;
- selection of a visual draft;
- retouching quality and refinement acceptance;
- final QA, publishable export, and publication.

An automated check may fail a package or request review, but it may not convert a failed or unreviewed package into `approved` or `published`.

## 7. Approval gates

| Gate | Decision | Evidence required |
|---|---|---|
| G0 Scope/bible | This item fits the accepted account, character, and format | Brief, applicable bible versions, constraints |
| G1 Story | The premise and script are worth producing | Selected script and decision note |
| G2 Storyboard | The visual plan can be generated and reviewed | Storyboard version, text/layout checks |
| G3 Visual draft | The draft preserves character and communicates the plan | Draft preview, run manifest, comparison notes |
| G4 Polish/refinement | The edited result is visually acceptable and traceable | Before/after references, edit/refinement record |
| G5 QA/rights/publication | The final package is safe and ready to publish | QA checklist, rights decision, export and metadata checks |

Approval is explicit and version-specific. A populated file, a passing automated check, or a thread message without an approval record does not satisfy a gate.

## 8. Git and document operations

### Git

1. Check status and diff before editing; preserve unrelated changes.
2. For each substantial, coherent work unit, commit and push after its scope is complete, reviewed, and validated. Do not create a commit for every message or small edit. This is the project-wide rule recorded in D-0034.
3. Commit titles use exactly one prefix: `[추가]`, `[수정]`, or `[삭제]`, followed by a concise description. The prefix describes the main purpose; unrelated work is split into separate commits.
4. Stage only paths belonging to the current work unit. Inspect the complete staged diff before committing; never sweep unrelated untracked or modified files into a commit.
5. Push to the existing configured upstream after the commit. Do not force-push or rewrite published history. If the upstream is missing, diverged, or rejects the push, preserve the commit and report the issue.
6. Do not commit secrets, credentials, private project data, local databases, source references, model weights/caches, or generated media by default. Large assets require an explicit storage/versioning decision.
7. A stage is not complete because a file exists in Git. The artifact, relevant validation evidence, and approval state must also be recorded.

### Documents

1. `AGENTS.md` contains durable execution rules; `README.md` gives the project overview; `DECISIONS.md` records accepted cross-cutting choices; `docs/` contains specifications and indexes.
2. Stage specifications use the following template: purpose, scope/non-goals, inputs, procedure, tools/AI techniques, outputs, human gate, failure/recovery, validation, versioning/metadata, and open questions.
3. When an established rule changes, add a dated decision with reason and impact. Do not silently rewrite the rationale for an earlier decision.
4. A document may call a result accepted, complete, or verified only when the relevant artifact and validation were actually inspected.
5. Thread closeout records accepted decisions, changed files, validation performed, unresolved questions, and the next thread's required inputs.

## 9. Definition of done

A stage or workstream is complete only when:

- its output exists in the repository or in explicitly referenced storage;
- input/output versions and provenance are identifiable;
- the relevant validation and human approval result are recorded;
- unresolved risks and open questions are visible; and
- the next stage has enough information to consume the result without guessing.

## 10. Open questions for later stages

- Which exact output dimensions and file formats are required for each target channel?
- Which image-generation stack satisfies the first slice after a real storyboard exists?
- Where should large binary assets and previews be stored and versioned?
- Which schema validation and preview checks should be automated first?
- What account isolation and permission model is needed after the single-account slice succeeds?
