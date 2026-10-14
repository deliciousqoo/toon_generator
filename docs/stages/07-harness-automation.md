# Stage 07 — Harness and automation

## 1. Purpose

Specify a future harness that validates the versioned handoffs from Stages 01–06, coordinates bounded work, and stops at human decisions. The harness makes contract failures visible and repeatable; it does not decide whether a creative or rights judgment is correct.

This document defines interfaces, state boundaries, recovery, audit and acceptance criteria. D-0035 authorizes implementing its bounded Stage 04 synthetic slice under the [P0 implementation baseline](../p0-implementation-baseline.md), including executable orchestration, checkpointing and meaningful tests. The full Stage 07 production harness remains future scope; provider calls and real content still use P1/P2.

## 2. Scope and non-goals

### In scope

- Contract and schema validation for stage inputs and outputs.
- Version and compatibility rules for artifact contracts.
- Project/content isolation and exact-version input resolution.
- Classification of deterministic checks and human-only decisions.
- An implementation-neutral orchestration and work-queue model.
- Human-gate hold, decision verification, and explicit resume behavior.
- Explicit work-item transitions, bounded retries, idempotency, concurrency, and recovery.
- Audit events, provenance, secret handling, dry-run/simulation, failure reports, and observability.
- Future implementation acceptance criteria and the Stage 08 handoff.

### Non-goals and hard limits

- Populating a real project or content item while the repository remains in `specification_only` mode.
- Choosing a queue, database, workflow engine, schema library, CI provider, model, image tool, or storage vendor.
- Generating or editing media, collecting references, selecting creative work, or making rights determinations.
- Creating or changing a human approval record, choosing a rework destination, or authorizing publication.

Automation may validate evidence, prepare a review packet, block a package, and schedule work after an authoritative human decision is recorded. It must never synthesize a G0–G5 approval, make a rights or creative decision, mark content `approved`, or publish. `published` requires a separate actual human publication event and evidence.

## 2.1 Agent orchestration and creative feedback loop

The harness is also the bounded orchestrator for stage agents. A platform can host this workflow: its interface presents the user's current step and artifact, while the orchestrator resolves exact-version inputs, dispatches a role-specific agent or tool, validates the result, requests a bounded evaluation/revision, and records the trace. The user-facing flow should not expose queue mechanics or gate codes as creative tasks. The product interaction and first-slice requirements are defined in [Product direction revision](../product-direction-revision.md).

For the first technical slice, apply four logical specialist roles: story generator, storyboard planner, deterministic contract validator, and evaluator, supervised by the orchestrator. D-0035 applies D-0032's P0 role/retry recommendations as delegated engineering defaults: two automatic creative rewrites and one transient technical retry per bounded segment. Roles may share a model/runtime, but each receives a distinct instruction, required scoped inputs, an output contract and a versioned rubric. Later Stage 05 work can add a versioned image-workflow adapter. Agent roles do not approve one another or the user.

The current first-slice engineering choice is LangGraph for local checkpointed orchestration and human pause/resume, with an explicit Python state machine as the simpler fallback if checkpoint persistence or recovery proves too costly. This does not select a permanent workflow engine for the full Stage 07 harness; that specification remains implementation-neutral outside the bounded slice.

The orchestrator must:

1. Freeze the exact project, character, story/reference, artifact, schema, prompt, and rubric versions for an attempt.
2. Send only the role's required project-scoped inputs and requested output structure.
3. Run deterministic validation separately from subjective evaluation. Contract, version, rights/use, or project-boundary failures stop dispatch and produce a clear blocker.
4. Ask the evaluator for evidence-linked issues and targeted revisions, not an approval token or an opaque quality score.
5. Create immutable output/evaluation versions for every pass and preserve `retry_of`, `supersedes`, consumed input versions, and change scope.
6. Enforce attempt, time, and cost limits; stop on human review, a plateau, conflicting evaluations, a blocker, or an exhausted limit.
7. Return a user-readable summary: what was used, what changed, what remains unclear, and the next choice. A user's change creates a new version, invalidates only affected descendants, and resumes the named stage.

Prior feedback can become reusable project guidance only through an inspectable, versioned human-confirmed preference. Rejected outputs and evaluator notes must not silently rewrite prompts, identity rules, or global policy. A structural evaluator pass is not human creative approval, rights approval, final-quality approval, or publication.

### Role contracts and story-first dispatch

| Logical role | Required output | Boundary |
|---|---|---|
| Story generator | Understanding of a rough topic, anecdote, observation, reference, or detailed original; source/preserved wording; premise, intent, ordered observable beats, payoff, and unresolved questions | Builds the brief through conversation. Preserves supplied text outside the requested edit. Does not fix cut format/count or approve G1. |
| Storyboard planner | Format/count proposals justified by the exact G1 story, then ordered cuts with visual purpose, action, expression, composition, gaze, pacing, dialogue space, continuity, rough views and episode overview | Dispatch only after exact G1 confirmation; human format selection precedes fixed layout. Does not invent a new story or character trait to satisfy a format. |
| Evaluator | Issues containing `blocker`, `revise`, or `optional improvement`, exact artifact/version, beat/unit/text ID or explicit episode scope, requirement/rubric reference, evidence, proposed affected scope, and unresolved judgment | Advisory semantic/visual review. No scalar score is approval; subjective findings stay distinct from deterministic failures and human decisions. |
| Deterministic validator | Separate per-check results for syntax/schema, IDs, exact versions, project/content boundary, beat/text/unit coverage, required cut fields, approval references, and known layout constraints | Checks presence/relationships and known limits; cannot establish expressive quality, originality, continuity quality, rights adequacy, or approval. |

The harness owns dispatch, checkpointing, evaluation, validation, dependency impact, and limited repetition. Stage 04 owns the story/cut contract and the human owns creative selection. The future flow is: conversational input understanding → story draft → separate validation/evaluation → bounded scoped revision if authorized → G1 hold → verified human story decision → format/count proposal and human selection → board planning → separate validation/evaluation → bounded scoped revision → G2 hold → exact-version Stage 05 handoff. Ask one consequential question at a time at an unclear core or choice. Do not expose an administrative form or job queue as the user's creative task. A format-driven story change returns a new story to G1.

### Bounded loops and immediate feedback

D-0032 proposes an initial draft plus at most two targeted creative revisions and one transient technical retry. These are proposed counts, not active policy. Record the human-accepted creative-round, technical-retry, elapsed-time, cost, and scope limits with policy/version references before unattended iteration. Missing accepted bounds permit no automatic repeat. A user-requested scoped correction creates a new draft immediately but does not imply permission for further autonomous rounds. Creative revisions and technical retries use separate counters; neither resets the other or expands the changed scope.

After each candidate, validate deterministic preconditions and obtain a separately versioned evaluator report. Dispatch only the named affected revision permitted by the request/policy. Stop at a gate, contract/rights blocker, unresolved scope, conflicting evaluation, no useful improvement, unknown side-effect outcome, cancellation, or exhausted bound. Return the latest candidate, prior-version references, issues, count/cost status, and next human choice; never continue merely to obtain a passing score.

Each feedback event records feedback ID, actor/time, base artifact/version, requested change, affected beat/unit/text IDs, preserved input references, dependency rationale, reopened gates, stale jobs, and named next consumer. Immediately expose the new draft version and change summary when scope is clear; an ambiguous request remains pending clarification without overwriting content. Create a new package/changed-unit version with `supersedes`, reuse exact references for unchanged units, preserve every prior result, and rerun only affected checks and dependent adjacent continuity/overview assembly. A dialogue edit affects its text/layout; a gaze/action edit affects the cut and declared neighboring continuity; a premise/payoff change reopens G1 and blocks dependent board planning. Supersede stale queued work and retain late results as historical attempts; they cannot replace the current draft. G2 changes require new version-bound human review, and Stage 05 generation is never restarted for the whole episode automatically.

These are future behavior contracts. They do not authorize executing agents, implementing a harness, using real inputs, or calling providers during the current specification work.

## 3. Authority and stage boundaries

Approved stage specifications, decisions, and exact human approval records remain authoritative. A discussion, queue status, validator result, populated field, or passing score is not an approval. Workstream progress is separate from the content-item state machine.

The harness must preserve the stage-specific gates and their relationship to the content lifecycle:

| Producer | Gate contract consumed by the harness | Automation boundary |
|---|---|---|
| Stage 01 | `RG0` research scope, `RG1` reference set, `RG2` handoff | Validate structure and evidence links; a human decides reference use, restrictions, and approval. |
| Stage 02 | `CG0` character scope, `CG1` identity direction, `CG2` bible and sheet | Validate required records and provenance; a human decides identity and approves the exact package. |
| Stage 03 | `SG0` strategy scope, `SG1` account/series direction, `SG2` handoff | Validate fields and references; a human decides strategy, evidence interpretation, and approval. |
| Stage 04 | `G0` scope/bible, `G1` story, `G2` storyboard | Validate exact approved inputs and deterministic record relationships; a human owns scope, story, storyboard, and each gate. |
| Stage 05 | `G3` visual draft | Validate manifest, input/output IDs, completeness, and integrity; a human selects and approves the exact draft. |
| Stage 06 | `G4` polish/refinement, `G5` QA/rights/publication preparation | Validate edit, export, and review evidence; a human owns visual acceptance, rights disposition, G4/G5, and the separate publication action. |

`RG*`, `CG*`, and `SG*` are stage package gates; they do not themselves advance a content item. Stage 04 `G0`–`G2`, Stage 05 `G3`, and Stage 06 `G4`–`G5` are the content-workflow gates defined by the operating rules. An automated pass cannot substitute one gate for another.

Every future handoff must retain the producing stage's contract, exact artifact ID/version, `project_id`, `content_id` when content-scoped, owner, approval evidence or explicit pending/blocker status, validation result, unresolved risks, provenance, and next consumer. Approved artifacts are immutable; changes create a new version and invalidate affected downstream checks and approvals.

## 4. Inputs and contract validation

### 4.1 Exact input resolution

Each future harness request identifies a stage operation and an explicit set of immutable input references. Each reference resolves by artifact ID and artifact version plus schema/contract ID and schema version. A mutable `latest` alias is not a valid execution input. Missing, ambiguous, inaccessible, superseded, revoked, or checksum-mismatched inputs fail closed and produce a blocker tied to the exact reference.

The artifact's own version and the schema version are separate values. An artifact version identifies the content/record revision; a schema version identifies the shape and semantics used to validate that record. Validators record both. They do not guess schema versions from filenames, artifact versions, or producer defaults.

### 4.2 Validation layers

Run these checks in order and retain a distinct result for each layer:

1. **Envelope and syntax:** valid serialization, supported envelope/contract version, required top-level fields, legal field types, and recognized enum values.
2. **Schema shape:** required fields, field types, constraints, stable IDs, uniqueness within the defined scope, and permitted additional fields.
3. **References and versions:** every required source resolves to the exact artifact and schema version; required sources are not silently replaced by newer versions.
4. **Boundary isolation:** all nested records, inputs, outputs, retries, approvals, and provenance match the envelope's `project_id` and, where content-scoped, `content_id`.
5. **Approval preconditions:** required upstream human records exist, identify an authorized human actor, and bind to the exact artifact ID/version and gate. The validator may verify an approval record; it may not create or upgrade one.
6. **Stage-specific contract:** producer and consumer requirements from Stages 01–06 are met, including required evidence, restrictions, provenance, and next-consumer fields.
7. **Known integrity constraints:** available checksums, file/path or storage references, output coverage, export metadata, and other deterministic requirements whose values are established by an approved contract.

A check result is one of `pass`, `fail`, `blocked`, `human_review_required`, or `unrun`. An unknown or unsupported requirement remains `unknown` and blocks any dependent check; it is never filled from a guessed default. A warning does not become a pass for a required check.

### 4.3 Schema and compatibility policy

- Every schema has a stable `schema_id`, explicit `schema_version`, owning stage, and documented required/optional fields and semantics.
- Producers declare the schema version they emitted. Consumers declare which exact versions or compatibility ranges they accept. An undeclared version or range is unsupported and blocks processing.
- A compatible additive change may be accepted only when the consumer explicitly declares it compatible. Semver labels alone do not prove compatibility.
- A breaking shape or meaning change requires a new incompatible schema version and a separately versioned, deterministic migration definition before a consumer may accept it.
- A migration preserves the source artifact, identifies source and target schema versions, records its own version and result, and reruns affected validations. It does not rewrite approval history or infer missing values.
- A migration that changes creative meaning, rights scope, identity, or any human-approved content cannot be automatic. It requires a new artifact version and the affected human gate(s) to be reopened.
- Unknown required fields, enum values, gate names, producer versions, or compatibility claims fail closed. No field is silently dropped, defaulted, or renamed.

### 4.4 Project and content isolation

`project_id` is mandatory for every project-owned package and harness operation. `content_id` is mandatory wherever the artifact or operation belongs to a content item; it may be absent only for explicitly project-level records such as reference, character, or strategy packages. A missing identifier is not a wildcard.

For this project, `project_id` identifies the reusable Instagram toon project setup and `content_id` identifies one episode. Stage 01–03 setup artifacts normally omit `content_id`; Stage 04–06 episode artifacts carry it. Machine validation remains a later workstream after the human-readable field contract has been exercised on an episode.

The validator recursively checks identifiers in nested objects and linked records, including source lists, approvals, outputs, retry lineage, and audit context. Any mismatch blocks the operation; the harness must not merge records or choose one side. Cross-project reuse is allowed only when the source project, source artifact/version, explicit permission or rights basis, transformation/reuse decision, and provenance are recorded under the consuming project's envelope and human review requirements.

## 5. Deterministic checks and human review

| Deterministic harness checks (when the governing contract is known) | Human review only; automation may surface evidence or request review |
|---|---|
| JSON/record syntax, schema/version support, required-field presence, type/enum checks, duplicate IDs, and reference resolution | Originality, creative quality, story value, tone, and audience fit |
| Exact artifact/version matching and required upstream approval-record presence/shape | Character identity, expression, continuity, and whether a visual result preserves intent |
| Nested `project_id`/`content_id` consistency and explicit shared-source record presence | Rights, license, consent, brand, privacy, and whether a use basis is adequate |
| Recorded unit/beat/output coverage, known ordering rules, and declared export dimensions or format constraints | Whether a reference is safe to use, a restriction is satisfied, or an unresolved risk is acceptable |
| File existence, checksum equality, manifest completeness, and known metadata constraints | Readability in context, crop quality, accessibility judgment, visual polish, and final QA |
| Retry lineage, idempotency-key/request-digest matching, job lease ownership, and legal work-item transitions | Any G0–G5, RG*, CG*, or SG* approval; any choice of rework state or publication |

Automated analysis that is probabilistic, heuristic, or dependent on visual/semantic judgment is advisory. It may return `human_review_required`, evidence, and a confidence value when its method is recorded. It cannot satisfy a deterministic requirement by itself and cannot create, approve, reject, or override a human gate.

## 6. Orchestration and work-queue abstraction

The future implementation may use any suitable work-queue or workflow engine, but must expose the following logical records and behavior:

- A **work item** identifies operation, stage, project/content scope, exact inputs, contract versions, requester/owner, priority or scheduling policy if applicable, and current operational status.
- An **attempt** is an immutable execution record with a unique `attempt_id`, input digest, start/end events, validator/tool versions, outputs or failure evidence, and optional `retry_of`.
- A **gate review request** packages the exact artifact/version, gate, evidence references, blockers/risks, and human decision instructions. It is not an approval record.
- A **resume event** references a newly recorded human decision or corrected input and explicitly names the downstream operation or human-selected rework target.

Operational work-item status is separate from content state. The permitted work-item statuses are `queued`, `claimed`, `running`, `awaiting_human`, `blocked`, `retry_wait`, `succeeded`, `failed`, `cancelled`, and `superseded`. A status describes harness work only; it never means `approved`, `published`, or any other content state.

Every status change is an explicit event with a valid source state, destination state, actor/service identity, timestamp, reason, and related attempt or decision. At minimum:

| Transition | Required guard |
|---|---|
| `queued` → `claimed` → `running` | A worker holds the current scoped lease and has resolved the immutable request. |
| `running` → `succeeded` | The declared operation completed and recorded its outputs/report; this does not imply content approval. |
| `running` → `awaiting_human` | The operation reached a named human gate and created a review request tied to exact versions. No downstream gated work is dispatched. |
| `running` → `blocked` | A required input, contract, permission, decision, or integrity condition is missing, conflicting, or unknown. |
| `running` → `retry_wait` | The failure is classified retryable, retry policy permits another attempt, and the failure/reason are recorded. |
| `retry_wait` → `queued` | The bounded delay elapsed and the same immutable request is still current and eligible. |
| `awaiting_human` → `queued` | An authoritative human decision for the exact gate/artifact version is newly recorded and verified, and a separate resume event specifies next work. |
| `blocked` → `queued` | The blocking input/condition has been corrected or resolved and an explicit resume event requests revalidation. |
| Any active state → terminal state | An authorized cancellation, supersession, or non-retryable failure event identifies the reason and preserves attempt evidence. |

Invalid or stale transitions are rejected and audited. An approval or rework decision must be a version-bound human record; a queue item, job completion, or thread message is insufficient. A rework decision must name its return state/consumer. The harness may schedule only that named path after verifying the new input/version; it may not choose a creative route.

## 7. Idempotency, concurrency, retries, and recovery

### 7.1 Idempotency and duplicate requests

Each requested operation supplies an idempotency key scoped to the project, content when applicable, stage operation, and caller. The system stores a canonical request digest covering the operation, contract versions, and exact input IDs/versions. Repeating the same key with the same digest returns or resumes the existing logical operation without duplicating side effects. Reusing a key with a different digest is an `idempotency_conflict` and is blocked for review.

Each physical attempt still receives a new `attempt_id`. Side-effecting adapters must support an idempotency token or a queryable operation ledger before automatic retry is allowed. If the outcome of an external side effect is unknown, reconcile it before replay; never assume that a timeout means nothing happened.

### 7.2 Concurrency and stale work

Read-only validation may run concurrently. Mutable work is serialized or protected by an implementation-equivalent lease/compare-and-swap mechanism scoped at least to the project, content (when applicable), operation, and exact input set. A worker must recheck lease ownership and input currentness before recording a result. A stale worker cannot replace a newer result or advance a content state.

Outputs are immutable and versioned. Concurrent changes produce an explicit conflict, preserve both attempt records, and require re-resolution or human direction; the harness never merges two creative artifacts. A new input version invalidates or supersedes queued work whose contract declares that input as a dependency.

### 7.3 Retry and recovery policy

Failures are classified as retryable transient, deterministic contract failure, permission/rights blocker, concurrency conflict, or unknown-side-effect failure. Only retryable transient failures may be retried automatically. Retries are bounded by an implementation policy and record delay, attempt count, failure code, input-change status, and whether model/tool/workflow/parameters changed. The same failure repeated without a relevant change eventually requires a human decision; it never authorizes unbounded work.

Every retry creates a new attempt and preserves the failed attempt, logs, outputs, and partial artifacts. If inputs or execution parameters change, the retry is a new request/run version with `retry_of` and a changed-input summary, not a replay hidden under the old identity. Deterministic schema errors, ID mismatches, unsupported versions, disallowed use, and missing human decisions do not retry automatically.

On worker crash or lease expiry, recovery inspects the attempt ledger and recorded artifact IDs/checksums before resuming. It either resumes an idempotent step, reconciles a completed external operation, or marks the outcome blocked/unknown for human resolution. It must not overwrite an approved artifact, discard a quarantined output, or infer that an interrupted approval/publication succeeded.

## 8. Audit log and provenance

The implementation must retain an append-only, queryable event trail for request creation, contract resolution, each check, work-item transition, lease/attempt, retry, review request, human decision reference, resume, output, failure, quarantine, and supersession. Corrections append a new event; they do not rewrite the earlier record.

Each event records, where applicable: `event_id`, timestamp, actor/service identity, event type, project and content scope, work-item/attempt/correlation IDs, stage and contract/schema versions, exact input/output artifact IDs and versions, checksums or storage references, validator/tool version, check result and stable failure code, retry lineage, human-decision reference, reason, and next consumer. Unknown metadata is `unknown`, not guessed. The log distinguishes who performed a deterministic check from who made a human decision.

Generated or transformed outputs retain source artifact IDs/versions and available model, workflow, prompt, seed, tool, parameter, and transformation provenance as required by their producing stage. Missing provenance can block downstream use; the harness does not reconstruct it from a filename or visual result.

## 9. Secrets and data protection

- Credentials are supplied to future workers only through scoped secret references backed by an approved secret-management boundary. Plaintext secrets never enter schemas, artifacts, prompts, command output, logs, metrics, exception text, or audit records.
- Use least privilege and project-scoped access for input resolution, storage reads/writes, and any future external adapter. A work item must not grant access to another project's data by sharing a queue or worker identity.
- Redact sensitive values before recording diagnostics. If redaction cannot be confirmed, stop the operation and emit a sanitized error code rather than raw payloads.
- Apply the upstream rights/use restrictions before any future upload or external processing. Unknown or disallowed input-use basis blocks the operation; no tool call can be authorized by a passing schema check.
- Keep large generated binaries out of Git until an approved storage/versioning policy exists. Retention, residency, deletion, and backup policy remain Stage 08/platform decisions.

## 10. Dry-run and simulation

`dry_run` validates the same declared contracts and predicts the work plan, blockers, gate holds, and intended status events without writing project artifacts or invoking external providers. `simulation` may model queue transitions, retries, failures, worker loss, or a human decision event in an isolated, non-authoritative simulation context.

Both modes must be labeled in every result, must use `unknown` or example IDs only during specification work, and must guarantee that no real approval, rights decision, content-state transition, upload, generation, or publication is created. A simulated approval can exercise the state-machine model only; it is not persisted as an approval and cannot resume real work. Under D-0013, a separately authorized `platform_build` may persist isolated synthetic fixtures and test-only gate records, but may use only the mock image adapter unless provider validation is separately authorized. Real project data remains prohibited until a distinct `content_execution` transition after platform acceptance.

Illustrative request envelope (contract example only):

```json
{
  "contract_id": "harness_job_request",
  "contract_version": "1.0.0",
  "request_id": "request-example-001",
  "operation_id": "operation-example-001",
  "mode": "dry_run",
  "stage_id": "unknown",
  "project_id": "production-project-example-001",
  "content_id": "content-example-001",
  "inputs": [
    {
      "artifact_id": "artifact-example-001",
      "artifact_version": "1.0.0",
      "schema_id": "stage-contract-example",
      "schema_version": "1.0.0",
      "project_id": "production-project-example-001",
      "content_id": "content-example-001"
    }
  ],
  "idempotency_key": "idempotency-example-001",
  "requested_by": "unknown",
  "requested_at": "unknown",
  "side_effects_enabled": false
}
```

The example illustrates field separation only; it is not a complete production schema and supplies no real project, account, character, content, tool, or publication values.

## 11. Failure reporting and observability

Every operation produces a structured report even when it stops before execution. The report identifies mode, request/work-item/attempt IDs, stage and schema versions, exact inputs, overall status, per-check status, stable failure code, severity, retryability, evidence references, sanitized explanation, and explicit next action or human owner. It must distinguish `fail` (a known violated rule), `blocked` (missing/unknown prerequisite), `human_review_required` (deterministic work is complete but a human decision remains), and `unrun`.

Useful stable failure-code families include unsupported contract/schema version, malformed record, missing input, project/content boundary mismatch, approval missing or version mismatch, provenance incomplete, checksum mismatch, forbidden transition, idempotency conflict, concurrency conflict, retry exhausted, and side-effect outcome unknown. Reports point to the relevant artifact/field/check without copying secrets or unnecessary source content.

Metrics and traces should cover queue depth and age, operation and attempt duration, check pass/fail/block counts, retry counts, gate wait time, stale lease recovery, idempotency/concurrency conflicts, and terminal outcomes. Metric dimensions remain bounded (for example stage, contract version, status, and failure family); raw project IDs, content IDs, prompts, asset paths, and secret values are excluded from metric labels. Correlation IDs link sanitized logs and audit events.

## 12. Validation and future acceptance criteria

This stage defines acceptance requirements; it does not create or run tests, test fixtures, executable validators, or CI. A later implementation is acceptable only when review evidence demonstrates all of the following:

- Both a rough topic/anecdote/reference and a detailed-original path enter through conversation; preserved original wording and unresolved interpretations are visible without requiring a complete brief up front.
- Storyboard dispatch is blocked while G1 is pending or bound to another story version. Format/count proposals follow the exact story decision and fixed layout follows human selection; a narrative change reopens G1.
- Generator/planner outputs, evaluator evidence/issues, and deterministic check reports remain separate records. Every cut covers purpose, action, expression, composition, gaze, pacing, dialogue space, and continuity; semantic adequacy remains human-reviewed.
- A scoped text/cut feedback event immediately exposes a superseding draft and summary, retains old results and unchanged exact unit references, refreshes affected dependencies only, reopens the applicable gate, and prevents stale jobs or approvals from dispatching Stage 05.
- Proposed D-0032 numbers are not applied as accepted policy. Missing accepted limits prevent automatic repeats; exhaustion, plateau, conflicting evaluation, and blockers stop with an inspectable result. Technical retry cannot silently become creative regeneration or restart a full episode.

- A valid known contract is checked at the declared schema version; malformed, unsupported, or incompatible inputs fail closed with field-level evidence.
- Stage-specific handoffs preserve required exact input versions, provenance, next-consumer data, and the correct RG/CG/SG/G0–G5 human approval boundaries.
- A nested project or content ID mismatch, missing exact-version input, missing/revoked approval, or stale approval blocks all downstream work.
- Schema compatibility is explicit; any migration preserves the source, records its versions, reruns affected checks, and never fabricates approval or human-owned values.
- Deterministic checks produce reproducible findings while creative, visual, rights, and publication judgments remain assigned to a human.
- A pending gate creates an `awaiting_human` work item and prevents gated downstream dispatch. Resume requires a newly verified, version-bound human decision and an explicit resume event.
- Invalid work-item transitions are rejected and audited. No harness transition writes `approved` or `published` to the content state.
- Duplicate requests with the same key and digest are idempotent; key reuse with a changed digest is rejected. Concurrent writers cannot overwrite or merge immutable outputs.
- Retries are bounded and traceable; deterministic failures do not retry; crash recovery reconciles partial/external work before replay.
- Audit events retain inputs, outputs, versions, checks, actors, and retry/gate lineage without logging secrets. Dry-run and simulation have no real side effects.
- Failure reports distinguish fail, blocked, human review, and unrun; metrics and traces avoid sensitive/high-cardinality labels.

## 13. Versioning and change impact

Version the harness request/result contract, each stage validator contract, compatibility declaration, migration definition, and policy set independently. Every attempt captures the exact versions it used. Updating a validator or policy does not rewrite old results; revalidation creates a new report linked to the prior one and explains the changed rule/version.

Changes to an upstream artifact, schema meaning, rights restriction, approved creative constraint, file content, checksum, or required export metadata invalidate the dependent checks declared by the contract. Re-run only affected deterministic checks automatically. If a human-approved artifact or the basis of a human decision changed, reopen the affected gate and obtain a new version-bound human decision.

## 14. Handoff to Stage 08

Stage 08 consumes this specification as the harness boundary contract. Its design must decide, without assuming a vendor here:

- Where schemas, immutable artifacts, validation reports, audit events, leases, and work items are stored and versioned.
- How project-scoped authorization, secret references, retention, backup, and any future shared-source grants are enforced.
- How transactions, leases, compare-and-swap, idempotency ledgers, and crash recovery are provided by the chosen platform.
- How an authoritative human approval record is written and how its version-bound event reaches the harness without giving the harness approval authority.
- Which validations belong in repository checks versus a future service, and how generated binaries stay out of Git under the current storage decision.
- How to retain a clear boundary between workstream/task status, harness status, content state, human approval, and actual publication.

Stage 08 must not treat this specification as authorization to implement or execute a production pipeline. Its handoff should identify the accepted Stage 07 contract version, unresolved platform choices, required threat/data review, and any separate authorization needed before implementation or real project execution.

## 15. Open questions

- Which D-0032 role split and numeric revision/retry/time/cost limits will the user accept for the first slice? These remain proposals until recorded review.
- How will feedback-impact records, separate G1/G2 decision references, and richer cut fields be reconciled with the existing Stage 04 persisted schema before implementation resumes?

- Which schema compatibility range and migration review policy will Stage 08 adopt?
- Which human identity/role source and approval-record integrity mechanism will bind approvals to exact artifacts?
- Which operations, if any, can safely support automatic retries after external side effects, and how will outcomes be reconciled?
- What are the retention and access rules for audit events, failure evidence, generated assets, and simulation records?
- Which deterministic checks become enforceable only after the first approved execution defines concrete format/export constraints?
- Which metric retention and alert thresholds are appropriate once a real workload and service boundary exist?
