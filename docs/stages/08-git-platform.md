# Stage 08 — Git and personal local platform

## 1. Purpose

Define the repository and platform contracts for a personal local-first MVP that supports Stages 01–05 with synthetic data before any real content is produced. This stage specifies logical entities, ownership, access boundaries, local storage, concurrency, recovery, and staged adoption. The accepted local MVP stack and minimum artifact contract baseline are recorded in [the technical baseline](../platform-technical-baseline.md). This stage does not implement the application.

This document remains a specification, with example IDs and unknown values. D-0027 authorized the earlier local prototype; D-0029 now pauses additional implementation pending acceptance of the revised scope. This work is `specification_only`. See `docs/local-platform-guide.md` and `docs/implementation-validation.md` for the earlier implemented behavior and recorded verification. D-0033 requires Git-portable source and specifications without inferring target hardware from the current PC. Hosted/multi-user requirements here remain future design contracts; this revision neither implements them nor starts real content.

## 2. Scope and non-goals

### In scope

- A logical tenancy, production-project, account, content, asset, artifact, version, and audit model.
- Stable identifiers, ownership, project isolation, and explicit cross-project sharing.
- A single-user local MVP that preserves project isolation and supports the Stage 01–05 workflow.
- Immutable versions, supersession, schema evolution, and migration requirements.
- The division between Git and external binary/object storage, including logical path and object-key contracts.
- Abstract authentication, authorization, human approval ownership, secret handling, privacy, retention, backup, export, and audit requirements.
- Concurrency, idempotency, failure reporting, recovery, conceptual service boundaries, staged adoption, future acceptance criteria, and Stage 09 handoff.

### Non-goals

- Creating or populating a real production project, account, character, content item, asset, credential, or production database.
- Implementing a multi-user service, Git convention enforcement, CI, application migrations/APIs, storage buckets, or deployment infrastructure.
- Choosing a cloud provider, object store, identity provider, Git hosting model, secret manager, or retention duration. The local MVP database and stack are set by D-0024.
- Enabling automatic publishing or allowing an automated service to approve creative, rights, quality, or publication decisions.
- Implementing the application in this specification workstream. Implementation requires a separate start instruction after MVP entry decisions are recorded.

## 3. Inherited constraints and design status

The following are inherited requirements from the decision log:

- **D-0013 sets the first product goal:** build and validate the local Stage 01–05 platform flow with synthetic fixtures and a mock adapter before using real content. D-0002 is superseded only on the sequencing question; evidence-first restraint still applies before expanding to hosted or multi-account operation.
- **D-0007 remains accepted:** each production project is an independent container, and project-owned creative records carry a stable `project_id`. Cross-project reuse needs an explicit, traceable decision.
- Platform validation uses synthetic project and episode fixtures. Real content production is a separate transition after local MVP acceptance.
- Stage 01–05 user actions include editing dialogue/cut descriptions, selecting per-cut candidates, requesting selected-cut regeneration, and making human G2/G3 decisions. A mock adapter is used first; provider calls are not part of the initial build milestone.
- Stage 07's exact-version resolution, fail-closed validation, append-only audit events, scoped work, and human-gate stops remain authoritative.
- The content state machine (`idea` through `published`), harness work-item status, approval state, and workstream status are separate concepts. A platform operation must not conflate them.
- D-0014–D-0026 require a loopback-only browser UI, defer access from other PCs, keep active materials on the PC, copy explicitly selected local references into project storage, preserve registered history without automatic pruning, and provide no whole-project deletion feature. A complete project backup can be plain or age-encrypted per export. The restored copy never overwrites existing data, receives a new `project_id`, and retains the source ID as lineage. The backup includes settings, materials, episode images, retained versions, provenance, and human review/approval records. The user relies on the PC account for active data and chooses a destination for each export. The accepted runtime/framework, local backend, metadata and asset storage, manifest/checksum model, passphrase UX, lineage representation, and minimum Stage 01–05 contracts are specified in `docs/platform-technical-baseline.md`. This document does not select a provider or authorize implementation.

## 4. Inputs

Stage 08 is based on approved repository-level contracts, not on live project data. Its inputs are:

| Input | Required interpretation |
|---|---|
| `README.md`, `AGENTS.md`, `DECISIONS.md`, `docs/01-operating-rules.md`, `docs/platform-mvp-scope.md`, and `docs/platform-technical-baseline.md` | Current mode, D-0013 MVP boundary, D-0007 project ownership, accepted local technical baseline, mode transitions, and change-control requirements. |
| Stage 01–06 specifications | Project-scoped artifacts, account/content fields, versioning, approval gates, and binary storage needs. |
| Stage 07 specification | Exact-version resolution, work-item and content-state separation, append-only audit, idempotency, concurrency, retries, and automation stop conditions. |
| Open platform questions | The accepted local MVP baseline and later hosted/provider decisions that remain open. The local stack, storage boundary, minimum contract IDs, backup format, encryption choice, restore lineage, selected-file import, and no-pruning boundary are fixed in D-0022–D-0026 and `docs/platform-technical-baseline.md`. |

No real `project_id`, `account_id`, `content_id`, account name, character, content, credential, or storage URI is required to produce this specification. If a later execution uses real inputs, it must identify the explicit execution transition and the exact human-approved versions; the current thread cannot infer or populate them.

## 5. Procedure and tools/AI techniques

1. Extract the accepted invariants from D-0013, D-0007, D-0011, D-0012, and the operating rules.
2. Trace each Stage 01–07 handoff requirement into the logical domain model, version contract, authorization boundary, and recovery path.
3. Separate the accepted personal local MVP baseline from later hosted/multi-user questions and keep only genuinely deferred choices open.
4. Trace the accepted minimum Stage 01–05 contracts to the stage documents. Do not silently add a required schema field to historical records; record its version and migration impact first.
5. Review the acceptance criteria and Stage 09 handoff for claims that can be supported by this design document versus claims that require later evidence.

Repository text search and human review are appropriate tools for this stage. AI may summarize existing contracts, identify inconsistent identifiers or omitted failure paths, and draft alternatives using example IDs. AI may not decide rights, security acceptance, retention policy, an unapproved platform vendor, or a human approval. This specification workstream creates versioned JSON Schema and synthetic contract fixtures, but no executable workflow, service, database migration, or deployment.

## 6. Outputs and artifact contract

The primary output is this version-controlled specification: `docs/stages/08-git-platform.md`. Its companion implementation-entry artifacts are `docs/platform-technical-baseline.md`, `docs/contracts/mvp-records-v1.schema.json`, and the synthetic contract fixtures. These are design/specification artifacts, not a production platform, real project record, database migration, or authorization grant.

The document contract includes the inherited decision boundaries, domain and ownership model, isolation/sharing rules, version and migration behavior, Git/storage and path/key guidance, authorization and human authority, data protection and audit, concurrency/recovery, adoption plan, future acceptance criteria, open questions, and Stage 09 handoff. Future consumers must cite the exact repository revision of this document and distinguish required invariants from unresolved implementation choices.

The minimum machine-readable Stage 01–05 contracts are defined by the bundled schema; they carry schema IDs/versions, common ownership/scope fields, exact source versions, and compatibility rules. Creating runnable APIs, migrations, and application code remains a separate `platform_build` activity.

## 7. Human gate and authority

This workstream has no content-state transition and does not issue G0–G5, RG*, CG*, or SG* approvals. A human must review and accept platform-level choices before they become implementation rules; a populated specification, AI review, or future validator result is not that decision.

Human authority remains explicit for account and project ownership, identity and access policy, cross-project sharing and rights basis, privacy/retention exceptions, schema migrations that change meaning, creative decisions, final quality, and actual publication. Service operators may enforce and audit a recorded decision but may not substitute for its accountable human. Local platform implementation requires the separate start instruction defined by D-0013; actual content execution remains separately gated under D-0008 and the operating rules.

## 8. Logical domain model and ownership hierarchy

The platform model separates the organization/access boundary from the production boundary. A tenant (the logical label is still subject to the open questions) groups principals and projects for access administration. It is not a creative configuration container. Every production project remains independently isolated, including from other projects in the same tenant.

```text
Platform
└── Tenant / organization boundary (logical; provider and exact lifecycle unknown)
    ├── Human and service principals, memberships, and scoped grants
    └── Production project (project_id; required creative/data isolation boundary)
        ├── Project Brief and project-level reference, character, and strategy packages
        ├── Account record(s) associated with the project
        ├── Episode(s), each a content item with content_id and a target account reference when applicable
        │   └── Stage handoffs, runs, reviews, approvals, and publication records
        ├── Project-level and content-level assets / artifact records
        └── Audit events and export manifests
```

| Entity | Logical purpose and ownership | Scope rule |
|---|---|---|
| Tenant | Groups principals, projects, and administration for an owning organization or individual. It is an access boundary, not a default sharing grant. | A tenant owns or administers projects. Whether every future deployment needs this level is open; a single-user deployment may map one owner to one tenant without changing `project_id` semantics. |
| Production project | Owns the Project Brief, account/content direction, characters, strategies, references, content, provenance, and project-local decisions. | `project_id` is mandatory and is the creative-data isolation boundary. A project belongs to one tenant at a time in the proposed model. |
| Account | Identifies an external publishing identity or a project-scoped content destination; it is not a login credential. | Account records are owned by a project and have a stable `account_id`. For the first slice, there is one account. Whether one project can later contain multiple account records is unresolved; multiple accounts can be represented as separate projects without resolving that question. |
| Content item / episode | One Instagram toon episode tracked through its own state machine. | `content_id` is required on all episode-scoped records. An episode references the exact project-owned account and strategy versions it uses; it does not inherit an implicit “current account.” |
| Asset | A file or structured record consumed or produced by a stage, including a binary, preview, prompt, manifest, or review evidence. | An asset has an owning project; it is either project-level or tied to a `content_id`. Its stable logical identity is separate from its physical storage location. |
| Artifact | A versioned deliverable or handoff record that binds inputs, outputs, approvals, provenance, validation, and next consumer. | Every project-owned artifact identifies `project_id`; content-scoped artifacts also identify `content_id`. An artifact may reference one or more assets by logical ID and exact version. |
| Approval / publication event | A version-bound human decision or evidence of an actual publication. | Append-only, actor-attributed, and tied to the exact project, artifact/version, and gate or publication event. A service can record a human decision reference but cannot make the decision. |

A future first real content validation can use one project, one project-owned account, one recurring protagonist, and one episode. The project-level character and series setup is reused by later episodes. That real-content target ends at the human-reviewed storyboard and AI draft, before Stage 06 polish/QA; it follows, and is separate from, local synthetic platform acceptance. The platform must not require project-specific values to be global settings. An account record does not become a tenant or project, and an account handle is not an authorization token.

## 9. Stable identifiers and ownership rules

1. Use stable opaque IDs for tenant, principal, project, account, character, series, content, asset, artifact, run, approval, export, and audit-event records. Human-readable names, account handles, filenames, and storage paths are labels or attributes, never primary references.
2. `project_id` is present on every project-owned record and nested handoff. `content_id` is present when the record is content-scoped. `account_id` is present on account-scoped records and content records that target an account. Absence means “not applicable” only where the contract says so; it is never a wildcard.
3. Treat `(artifact_id, version)` as the immutable artifact revision reference. A consumer must resolve both values, plus its declared schema/contract ID and version. A mutable `latest` alias, filename, branch name, or bare account label is not an execution input.
4. IDs survive rename, archival, storage migration, and export/import of the same project. A cloned or split project receives a new `project_id`; copied child records receive new project-scoped IDs or an explicit immutable source link, with clone provenance.
5. Ownership metadata names the owning tenant/project and, where appropriate, the accountable human or service principal. Creator, current editor, approver, and owner are separate roles and must not be collapsed into one generic `created_by` field.
6. Validate the full ownership chain at every read, write, reference resolution, job dispatch, and export. A matching ID in a payload does not grant access. Authorization is checked against the caller and the referenced object's owner.
7. Existing stage contracts may add `account_id` where account scope is meaningful, but Stage 08 does not silently make it a mandatory field on every historical schema. A contract change is versioned and adopted through an explicit compatibility declaration or migration.

## 10. Project isolation and explicit sharing

Project isolation is enforced in the authorization and storage layers, not by naming conventions or obscure IDs. A principal's access to one project does not imply access to another project in the same tenant. Service identities, queues, caches, temporary files, search indexes, previews, and exports must preserve the same boundary.

Cross-project reuse is denied by default. A future shared-source or copy operation must create a record under the consuming project that names:

- the source `project_id`, exact source `artifact_id`/version, and source asset IDs/checksums when applicable;
- the consuming project, intended purpose, allowed operations, and whether the operation is a reference, copy, or transformation;
- the permission or rights basis, its evidence and scope, any expiration/revocation condition, and the responsible human decision;
- the transformation or abstraction performed, the resulting target-owned IDs/versions, and provenance back to the source;
- the downstream restrictions and approval gates that still apply.

A shared link does not transfer ownership, make the source mutable, or automatically transfer its approval to a changed context. A copied or transformed record belongs to the consuming project and must be reviewed under that project's rules. If a grant is revoked or its basis becomes uncertain, affected access and downstream processing stop; retain the audit record and route any already-produced output for human disposition. Shared assets never become global defaults merely because several projects use them.

## 11. Current-slice compatibility and future account relationships

The first slice remains the canonical compatibility profile:

- one `project_id`, one project-owned `account_id`, one primary character, one content item, and exact versioned handoffs;
- the `content_id` identifies that episode; project-level reference, character, and strategy records omit it unless explicitly scoped to the episode;
- project-level reference, character, and strategy artifacts may omit `content_id` only where their stage contract defines them as project-level;
- content-level runs, edits, exports, approvals, and publication evidence carry both project and content scope and identify their account target when applicable;
- all approval and publication authority remains human-owned; no multi-account scheduling or autonomous publishing is introduced.

Future platform support can host many independent production projects, each with its own account context. This is sufficient to support separate accounts without crossing D-0007 boundaries. A project with multiple external accounts, shared characters across accounts, account-specific roles, and cross-account content reuse require explicit relationship and permission decisions before a consumer relies on them. The platform must not infer those relationships from matching handles or duplicated briefs.

For compatibility, keep the established `project_id`, `content_id`, `artifact_id`, and `version` fields. If an account-scoped operation needs an explicit account identifier, add a versioned field or wrapper to that operation's contract. Legacy records are not relabeled with guessed account IDs; they remain valid under their declared schema or are blocked pending a reviewed migration.

## 12. Versioning, immutability, supersession, and migrations

### 12.1 Immutable revision contract

- Drafts may be edited while they are clearly marked work-in-progress and are not treated as an approved input. Once a revision is approved, published, exported as an immutable deliverable, or consumed by a downstream operation, its bytes and meaning are frozen.
- A frozen revision is identified by `artifact_id` plus `version`, schema/contract version, and a content checksum where bytes exist. The registry also records creation time, creator, owner, source IDs/versions, approval reference/status, validation result, storage reference, and next consumer.
- A correction creates a new version with `supersedes` (or the stage-specific `retry_of`/`derived_from` relationship), reason, changed fields/asset IDs, affected downstream consumers, and revalidation requirements. Preserve the old revision and its decision history.
- Approval is bound to the exact artifact/version and gate. Changing content, rights basis, provenance, export, or schema meaning cannot keep the prior approval active by pointer alone; affected gates are reopened.
- The platform may mark a revision revoked, quarantined, expired, or superseded, but these are appended status events. They do not rewrite the original event or erase its historical identity.

### 12.2 Contract and schema evolution

Artifact version and schema version are separate. A producer declares the schema version emitted; a consumer declares supported exact versions or an explicit compatibility range. A semantic-version label alone does not prove compatibility. Unknown fields, unsupported versions, and unknown required values fail closed.

A migration is a separately versioned, deterministic transformation record with source/target schema IDs and versions, migration version, code/tool identity, input/output IDs and checksums, validation results, and human owner. It preserves the original source and never fabricates missing values, provenance, rights, or approvals. A field rename/default or lossy transform needs a documented mapping and review. Any migration that changes creative meaning, identity, rights scope, or a human-approved artifact creates a new artifact version and reopens the relevant human gate. If the source is inaccessible or the transformation cannot be verified, block and retain the failure report.

### 12.3 Deletion and revocation

Normal correction is supersession, not deletion. For the local MVP, records and registered asset versions are not automatically pruned, and the app has no whole-project deletion feature (D-0026). A known source restriction that forbids local retention blocks import; do not keep or use such material contrary to its conditions. A separately authorized item-level removal flow may be specified later and must preserve only a permitted, non-sensitive tombstone/audit record. Hosted retention, deletion timelines, audit minimization, and legal-hold behavior remain open policy choices. A tombstone never represents approval or successful publication.

## 13. Git boundary and binary asset storage

### 13.1 Git is for reviewable source and policy

Git is the source of truth for approved human-readable specifications, decisions, schemas, migration definitions, and (after separate implementation authorization) maintainable source code and non-secret configuration. Text artifacts are versioned through reviewed commits and retain their platform `project_id`/artifact metadata when they are project-owned. Git history is not the approval database, audit ledger, credential store, or large-media archive.

Do not commit API keys, OAuth tokens, personal credentials, unnecessary personal data, private source material without an approved basis, or generated binary assets under the current repository rules. In the local MVP, project binaries live in the app-managed per-user asset store described in `docs/platform-technical-baseline.md`; they remain outside Git (D-0024–D-0026). Git LFS or another extension is not implicitly approved by this specification.

Additional implementation is paused under D-0029; this revision only clarifies the D-0033 portability contract. Shared rules and stage specifications remain under `docs/stages/` relative to the nested `toon_generator` Git root; local synthetic registry data and binary assets stay outside Git. If a future approved workflow stores project-specific text records in Git, use a project-ID namespace such as `projects/{project_id}/records/`; the local MVP does not add its database or project assets there.

### 13.1.1 Personal multi-PC portability: two separate transfers

| Transfer | Included | Not implied |
|---|---|---|
| Git repository | Reviewed code, specifications, schemas, synthetic fixtures, install scripts, pinned dependencies/lockfiles, and non-secret configuration templates. Use an exact repository revision as the installation input. | No automatic transfer of a PC's live database, project records, imported references, generated images, credentials, model weights, or caches. |
| Project backup file | One project's settings, retained versions, references/materials, episode images, provenance, reviews, and audit records through the existing backup/restore contract. | No repository installation, runtime environment, credential transfer, live synchronization, update-in-place, or merging of projects from two PCs. |

Each PC runs its own loopback-only installation and owns its own local database and asset root. Moving the Git checkout installs the same application/specification revision; it does not make the PCs clients of a shared app. Recreate virtual environments, installed dependencies, build output, and shortcuts on the destination instead of copying machine-bound installation folders. See [installation and path requirements](../platform-technical-baseline.md#11-installation-reproducibility-and-machine-specific-paths).

Move project data only by an explicit per-project export, file transfer chosen by the user, and verified restore on the destination. Restore allocates a new `project_id`, preserves source project/backup lineage and exact-version history, and marks copied reviews `restored_history`; current gates require a new human decision (D-0018–D-0019, D-0028). A plain or age-encrypted backup remains a snapshot, even if stored on removable media or a user-chosen transfer location. It does not synchronize future edits.

**Recommended operating convention, not a new user-approved decision:** designate one PC/copy as the working copy for each work period; record source backup, source project ID, destination project ID, and app/repository revision when moving it. Keep the source until the destination's restored contents are checked. If both copies were edited, preserve both and ask the human which copy to continue; no last-write-wins, automatic merge, or reverse restore into the original is defined. Switching back uses another export/restore and creates another independent copy.

Target OS/runtime and CPU/RAM/GPU/VRAM/storage profiles are `unknown` until the intended PCs are selected and evaluated. The current host is not the requirements baseline. Model/runtime selection, weight licenses and checksums, and any transfer of model files need explicit later specifications; they are not part of a project backup or Git clone. Remote app access, cloud/live database synchronization, and multi-PC conflict reconciliation remain deferred under D-0015–D-0016.

### 13.2 Binary storage by deployment profile

For the local MVP, binary payloads (imported references, generated drafts, previews, and review evidence) use the app-managed local file store scoped by project and asset/version IDs. A user-selected local reference is copied into that store while its original remains unchanged; web references are not bulk-downloaded. The asset record keeps the source/use basis, checksum, exact version, ownership, and provenance. These choices are specified in `docs/platform-technical-baseline.md` and D-0025–D-0026. A future hosted profile may use a versioned object/file store; its vendor, bucket topology, cache policy, and external storage controls remain undecided.

For a future hosted object store, writes must be immutable or conditional-create. Reusing an existing key with different bytes is an integrity conflict. Enable backend versioning or an equivalent immutable revision mechanism where the chosen service supports it; a mutable URL alone is not a version. Compute and verify checksums on transfer, export, and restore where supported. Temporary, failed, and quarantined objects retain scoped IDs and lifecycle state; cleanup follows an approved retention policy, not ad hoc deletion. The local MVP instead uses the local file/database recovery contract in `docs/platform-technical-baseline.md` and does not automatically delete registered versions.

### 13.3 Logical URI and path/key layout contract

Names and external account handles are excluded from repository paths and object keys. Use stable IDs and a safe, canonical encoding; reject traversal, ambiguous normalization, and caller-controlled path fragments. Authorization is independent of path secrecy.

Logical asset reference:

```text
asset://{project_id}/{asset_id}@{version}/{role}
```

Illustrative external object-key template (provider-neutral; it does not specify a bucket):

```text
v1/projects/{project_id}/assets/{asset_id}/versions/{version}/{sha256}.{extension}
```

Illustrative record namespace if a future approved Git workflow stores project-owned text:

```text
toon_generator/projects/{project_id}/records/{artifact_type}/{artifact_id}/{version}.json
```

Example references use only example IDs, such as `asset://project-example-001/asset-example-001@1.0.0/preview`. They are not actual storage locations. The authoritative registry binds a logical URI to its physical provider reference and object-version token; consumers resolve it through an authorized storage interface rather than constructing provider URLs. If a physical key must change, create a new location mapping event while preserving the logical asset ID, version, checksum, and old-to-new audit trail. A different project copy receives a new target asset ID and explicit provenance.

## 14. Authentication, authorization, and human approval ownership

Authentication establishes a human or service principal; authorization checks the principal's action against the tenant/project/resource and exact version. The identity provider is not selected. Use least privilege, deny by default, and scoped service identities. Tenant membership is not permission to read every project, and a project-scoped grant is not permission to access a different project's object by guessing its ID.

Conceptual roles (assignments and granularity remain implementation choices):

| Role | Permitted responsibility | Explicit limit |
|---|---|---|
| Platform operator | Operate platform control plane, monitor service health, perform audited break-glass recovery where authorized | No routine creative-data access or approval authority follows from infrastructure access. |
| Tenant owner/admin | Manage tenant membership and project-level grants | Cannot bypass project isolation or replace a version-bound creative/rights approval. |
| Project owner/editor | Maintain project configuration and create or revise draft records/assets | Cannot silently change an approved version or self-promote an automated check into approval. |
| Contributor | Work on explicitly granted project/content scopes and submit review packages | No access outside the granted scope; no approval unless separately granted. |
| Human reviewer/approver | Record a decision for an exact permitted gate, artifact/version, and project scope | Must be an authenticated human principal; approval is not implied by review access or a passed check. |
| Read-only auditor | Inspect authorized artifacts and audit evidence | Cannot mutate records, grants, approvals, or publication state. |
| Service principal | Perform a named, bounded operation such as validation, object transfer, or export under scoped grants | Cannot act as a human approver, decide rights/creative quality, or publish autonomously. |

Roles are conceptual and do not require separate humans for every gate; the repository does not yet decide a two-person rule. The responsible human owns creative direction, rights dispositions, final quality, approval, and publication. An approval record identifies the human actor, exact artifact/version, gate, decision, timestamp, reason, and evidence. A system may verify that the actor held an applicable grant at decision time, but it may not create or upgrade the approval. Account credentials are separate secret references and never define a user's role.

## 15. Secrets, privacy, retention, backup, export, and audit

### 15.1 Secrets and privacy

- Store provider credentials and external-account tokens only behind an approved secret-management boundary. Records contain a scoped opaque `secret_ref`, never the secret value. Do not place credentials in Git, prompt text, manifests, logs, metrics, errors, screenshots, or audit events.
- Separate secret scopes by tenant/project/account integration where the provider permits. Rotate and revoke through the selected provider boundary; a token cannot grant access to another project merely because a worker can resolve it.
- Minimize personal and account data. Record purpose, source, rights/use basis, classification, and permitted processing for data sent to a third-party tool. Unknown or disallowed use basis blocks the transfer. Avoid storing personal data in IDs, paths, metrics, or free-form diagnostics.
- Encrypt transport and stored sensitive data under the selected platform's controls, and restrict support/break-glass access with an audit event. Exact key management and residency requirements remain open.

### 15.2 Retention and deletion

For the local MVP, keep registered records, asset versions, generated drafts, review decisions, and audit history without automatic pruning, and provide no whole-project deletion action (D-0026). Check source/use and retention restrictions before import or use; a known restriction incompatible with keeping a project copy blocks import. A later item-level removal capability must define its authority, effect on backups/history, and permitted audit evidence. A future hosted profile must define separate retention classes, owners, triggers, access rules, deletion/legal-hold behavior, and completion evidence for drafts, references, approvals, logs, and backups. Those hosted durations and procedures remain open.

### 15.3 Backup and recovery

For the local MVP, a project backup is complete enough to restore the whole project. It includes project settings, project materials and their source/use records, episode records and binaries, retained artifact versions, provenance, and human review/approval records linked to the exact versions. Exclude credentials and secrets. At each export, offer plain `.toonbackup` or age-encrypted `.toonbackup.age`; clearly warn that a plain file is readable by anyone with file access. Encrypted export offers a long generated passphrase and strength guidance for a user-chosen passphrase. The user must enter that passphrase for restore; a lost passphrase makes only that encrypted backup unrecoverable, with no bypass. Never store or log the passphrase. Restore validates the complete package in staging, then creates a separately addressable project copy and never overwrites the source or any existing project. The copy receives a new `project_id` and stores the source project and backup IDs in lineage. Format, manifest, checksums, encryption choice, passphrase handling, integrity verification, and destination behavior are specified in `docs/platform-technical-baseline.md` and D-0022–D-0024.

The local MVP provides a user-triggered, whole-project backup export; it does not define scheduled backups or automatic retention cleanup. The export includes structured metadata, binary assets, immutable artifact/version manifests, approval references, and audit history, preserving project ownership and checksums. Each export offers plain or age-encrypted output, uses a user-selected destination, and restore creates a separate project copy as specified in `docs/platform-technical-baseline.md`. A future hosted service must define backup topology, encryption/key access, retention, recovery objectives, and verification cadence. Restore into an isolated target first; verify manifests/checksums and project boundaries before serving restored data. Restoring an object does not recreate or rebind an approval that was revoked, superseded, or tied to a different version. Hosted recovery time and recovery point objectives remain open.

### 15.4 Export and audit

A project export is a scoped, human- or explicitly authorized service-requested package containing selected records, exact versions, provenance, approval/audit references, checksums, and any permitted binaries. It must be complete enough to interpret offline, label missing/unavailable payloads, and exclude other projects, unrelated credentials, and unapproved source material. Record requester, scope, purpose, time, manifest version, included/excluded item counts, and result. A multi-project tenant export needs a separate explicit scope and authorization.

Keep append-only audit events for access grants/revocations, exact-version resolution, artifact creation/supersession, sharing, storage movement/deletion, migrations, approval references, exports, backup/restore, and security-relevant failures. Each event identifies actor/service, project and content scope where applicable, object/version, action, time, result, reason, correlation/attempt IDs, and sanitized evidence reference. Keep approval decision content in the versioned decision record; audit events refer to it without copying unnecessary personal or sensitive content. Access logs and audit history are themselves access-controlled and retained under an explicit policy.

## 16. Concurrency and conflict handling

- Treat immutable artifact creation as append-only. Concurrent creators may produce sibling draft/revision IDs; the platform must not merge creative content or choose a winner implicitly.
- For mutable draft metadata, use a compare-and-swap revision, ETag, or equivalent optimistic concurrency token. A stale write returns a conflict with the observed and current versions so a human can reconcile it.
- Serialize or lease operations that mutate shared project configuration or a single content item's active work pointer. Independent content items and read-only validations may proceed concurrently when their contracts permit.
- Approval decisions and audit events are append-only. If two incompatible decisions are recorded for the same gate/version, flag a decision conflict and block dependent work; do not apply last-write-wins. The human owner resolves the conflict with a new, explicit decision event.
- Use idempotency keys scoped to project, content (when applicable), operation, caller, and exact input digest. A repeat with the same digest returns the same logical operation; a repeated key with a different digest is a conflict.
- For external side effects, record the operation ID and reconcile the provider outcome before retrying after a timeout or worker loss. An unknown outcome is blocked for review; a timeout is not evidence that nothing happened.
- A newly superseding input invalidates queued work that depends on the old version when its contract says so. Workers recheck lease and exact input currentness before publishing any result. Stale workers cannot replace a newer pointer, approval, or immutable artifact.

These requirements complement Stage 07's queue/attempt model. Work-item status remains distinct from content state and approval status.

## 17. Conceptual service and operations boundaries

These are logical responsibilities, not prescribed microservices or endpoint names. They may be co-located in a future implementation, but authority and records remain distinct.

| Boundary | Conceptual operations | Required guard |
|---|---|---|
| Identity and access | Authenticate principal; resolve membership/grant; grant/revoke scoped access | Deny by default; record grant scope and actor; no implicit cross-project access. |
| Project/account registry | Create, read, archive, or transfer project/account metadata after authorized execution begins | Stable IDs; explicit ownership; account credential material stays outside registry records. |
| Artifact/version registry | Create draft, freeze a version, resolve an exact artifact/schema version, supersede, revoke, or tombstone | Validate ownership and schema; immutable frozen revisions; no implicit `latest`. |
| Asset storage adapter | Write/read/verify/quarantine/delete a binary by logical ID and version | Project-scoped authorization; conditional immutable writes; checksum and audit evidence. |
| Harness/work coordinator | Validate, queue, claim, retry, stop at gate, and resume named work | Honor Stage 07 statuses, idempotency, concurrency, and explicit resume event. Cannot approve or publish. |
| Human review/approval | Present exact review package and record a human's version-bound decision | Authenticated human and grant check; append-only decision; explicit gate and next permitted action. |
| Audit/export/backup | Query permitted events, produce a scoped export, and verify a restore | Independent scope authorization; sanitized evidence; checksums and manifests; no cross-project leakage. |

At a conceptual level, future operations include `resolve_exact(artifact_id, version, schema_version)`, `create_draft(project_id, ...)`, `freeze_revision(...)`, `request_review(...)`, `record_human_decision(...)`, `request_share(...)`, `revoke_grant(...)`, `export_project(...)`, and `verify_restore(...)`. These names only explain boundaries. Request and result contracts must carry caller identity, `project_id`, `content_id` when applicable, exact input/output IDs and versions, contract versions, idempotency/correlation identifiers, validation status, and an explicit blocker or next consumer. No endpoint shape, implementation, or external API is selected here.

## 18. Failure and recovery contract

| Failure | Required behavior | Recovery path |
|---|---|---|
| Missing, ambiguous, or unsupported artifact/schema version | Fail closed; return a field-level blocker; do not resolve to a newer version | Correct the exact input reference or review/version a migration, then revalidate. |
| Project, tenant, content, or account ownership mismatch | Deny access and downstream work; emit sanitized security/audit evidence | Resolve ownership through an authorized human/admin action; never merge records automatically. |
| Cross-project source lacks an active, scoped sharing decision | Block read, transfer, and processing | Record and review a permitted source grant or use a project-owned source; re-run affected checks. |
| Checksum mismatch, missing object, or partial upload | Quarantine the affected version; preserve metadata and attempt evidence | Reconcile/re-upload as a new immutable attempt and verify checksum before use. |
| Schema migration fails or loses required data | Preserve source and failure report; do not emit an approved target | Repair and version the migration, or leave the consumer blocked; human gates reopen if semantics change. |
| Concurrent/stale write or conflicting approval | Reject stale write; preserve both records; mark dependent work blocked | Re-read exact versions and obtain explicit human resolution/new revision. |
| Secret reference invalid, revoked, or broader than scope | Stop before external access; never log the secret | Revoke/replace through the secret boundary and retry only after a scoped authorization check. |
| External operation outcome unknown after timeout | Do not replay blindly; mark outcome unknown and reconcile the provider ledger | Human/service owner confirms outcome, then records a new resume/retry event with idempotency evidence. |
| Retention/deletion request conflicts with hold or audit needs | Restrict access while the authorized policy owner resolves the conflict | Record a scoped hold/disposition; carry out deletion or approved exception and audit its result. |
| Backup restore has missing objects or boundary mismatch | Keep restore isolated; do not serve partially verified data | Reconcile manifest and object set, rerun integrity checks, and record unresolved losses. |
| Export includes unauthorized or unavailable records | Fail or produce an explicitly partial export with exclusions and reason; never silently broaden scope | Correct scope/grants and create a new export manifest; audit both attempts. |

All recovery preserves original attempts and outputs where retention permits. Unknown conditions remain `unknown` or `blocked`; they are never filled with defaults. Restoring infrastructure does not change content state, human approval, or publication history.

## 19. Staged adoption plan

1. **Specification (recorded):** the local MVP scope, accepted decisions, minimum contract schema, and synthetic fixtures were recorded before implementation. D-0027 explicitly moved the repository to `platform_build`; human platform acceptance and actual content remain subsequent decisions.
2. **Revised implementation entry review (current, specification only):** D-0029 pauses further build work. Reconcile the product direction before resumption; preserve D-0024–D-0028 storage, contract, import, retention, backup, and historical-review boundaries unless separately changed. Dependency pins and the offline validator already exist for the earlier prototype. Review D-0033 target-PC profiles, reproducible installation, variable paths, and the separate Git/project-data transfer contract without running installation or generation.
3. **Local platform build (after revised scope acceptance and explicit resume):** follow the reconciled scope and D-0031's synthetic Stage 04 story-to-storyboard first slice. Do not infer resumption from D-0027's earlier authorization. Provider calls and real project data remain separately gated.
4. **Synthetic acceptance:** demonstrate the Stage 01–05 criteria in `docs/platform-mvp-scope.md`, including G2/G3 holds, version history, project isolation, recovery, and absence of real records.
5. **Optional provider validation:** add one provider adapter only after its provider/model, credential, data-transfer, cost, and retry conditions are documented and the user explicitly authorizes synthetic-data calls.
6. **Real content execution:** only after synthetic platform acceptance and a separate explicit user request, use an approved real project and episode. This is not implied by platform implementation or provider validation.
7. **Later expansion:** consider Stage 06, advanced Stage 07, hosted/multi-user, or multi-account features only through separate evidence-backed decisions and implementation authorization.

## 20. Validation and future implementation acceptance

### Stage 08 document review checklist

- [ ] D-0013, D-0014, and D-0007 are reflected; D-0002 is marked superseded only for platform/content sequencing.
- [ ] The browser UI is loopback-only; first platform acceptance uses synthetic fixtures, and real content remains separately gated.
- [ ] Every ownership, sharing, access, and storage rule uses project isolation as the default and requires exact versions.
- [ ] Git and project backup transfers are distinct; installation uses exact revisions and machine-resolved paths, local DB/media/secrets are excluded from automatic Git transfer, and target hardware remains unknown under D-0033.
- [ ] Independent PC copies do not imply remote access or synchronization; restored reviews remain historical and current gates reopen under D-0028.
- [ ] Human approval, harness state, content state, and publication are separate in the domain model and operations.
- [ ] Concurrency, failure, retention, backup, export, and migration behavior have explicit fail/blocked/recovery outcomes.
- [ ] Remaining cardinality and implementation choices are visible as open questions rather than implied decisions.
- [ ] Stage 09 can consume the platform specification without treating it as evidence of an implementation or production run.

### Future implementation acceptance criteria

A future implementation is acceptable only when review evidence demonstrates that:

- The app is single-user and local-only for this MVP; the browser UI binds only to loopback and cannot be reached from other devices or the public internet.
- Stage 01–05 synthetic flows, mock image generation, G2/G3 human review, cut selection, and selected-cut regeneration meet `docs/platform-mvp-scope.md` acceptance criteria.
- The synthetic validation has no external provider calls, real project data, or production registry entries.
- A principal with access to one project cannot read, write, resolve, search, cache, export, or restore another project's data without a separately recorded grant.
- All project-owned records and nested references preserve `project_id`, applicable `content_id`/`account_id`, stable IDs, and exact artifact/schema versions; missing or mismatched scope fails closed.
- The single-account slice can use the same records and exact-version handoffs without requiring a real multi-account configuration.
- Frozen artifacts and binary object versions cannot be overwritten; checksum mismatch, stale write, or idempotency-key digest mismatch is rejected and audited.
- Sharing records identify source and target projects, exact source version, purpose, permission basis, provenance, and revocation behavior; downstream approvals are not silently inherited.
- Schema compatibility is declared, migrations preserve source evidence, and semantic changes reopen the relevant human gates.
- A service principal can validate, store, or prepare a review packet but cannot create a human approval, rights disposition, `approved`/`published` content state, or publication event.
- Concurrency conflicts and unknown external outcomes block automatic progress until reconciled; retry behavior is bounded and traceable.
- Secrets are not present in artifacts, repository history, logs, metrics, error messages, or exports; sensitive access is scoped and auditable.
- The local MVP keeps registered history without automatic pruning and exposes no whole-project deletion action; any separately specified item-level removal respects known restrictions and records only permitted audit evidence. Backup, restore, and export preserve manifests, checksums, project boundaries, and approval references without fabricating history. Hosted retention/deletion follows a separately approved policy.
- Both plain and encrypted project backups can be exported. Plain output is labeled; encrypted output uses the age format and a generated or user-chosen passphrase. A wrong passphrase or damaged package is rejected without changing existing data, and no credentials, secrets, or passphrases are included in package contents or logs. A lost passphrase cannot unlock an encrypted backup.
- Restoring a project backup creates a separate project copy with a new `project_id`, retains the source project ID as lineage, and never overwrites the source or any existing project.
- Audit events are append-only, queryable by authorized principals, sanitized, and sufficient to trace ownership, version, access, sharing, approval reference, export, and recovery actions.
- A project-scoped export contains only its authorized records and records exclusions or missing payloads explicitly.

This document does not run or prescribe tests during specification work. Future implementation evidence must be reviewed against the criteria before the platform is accepted for a separate real-content decision.

## 21. Versioning and metadata

- Version this specification as a repository document; any approved change to tenancy, ownership, sharing, Git/storage boundaries, authorization, retention, or recovery records its rationale and impact in `DECISIONS.md` when it changes an established rule.
- Keep platform-contract/schema versions separate from artifact versions and from implementation release versions.
- Version project briefs, account records, creative packages, content artifacts, asset metadata, migration definitions, access grants, and export manifests independently where useful; use exact references at every handoff.
- Record the actor, timestamp, source/target project, reason, and affected consumers for ownership transfer, clone, share/revoke, storage relocation, migration, deletion, export, backup, and restore.
- Unknown ownership, permission, rights basis, storage status, or retention state stays explicit and blocks dependent use.
- No generated binary, real credential, or production record is created by this stage.

## 22. Handoff to Stage 09

Stage 09 may consume this document as a reviewed platform/repository design artifact. Its input package should identify this specification's exact repository revision, inherited D-0013/D-0014/D-0007 boundaries, the distinction between accepted requirements and open implementation questions, and any later decision or implementation evidence that is actually verified.

Stage 09 may explain why `project_id` isolation, exact-version provenance, external binary storage, human-owned approval, or a staged adoption path matters. Claims about a deployed service, multi-account behavior, security guarantees, performance, cost, or production outcomes require separately inspected implementation and validation evidence; this specification alone does not support those claims. Stage 09 remains a documentation workstream and does not itself start production or authorize a platform build.

Required handoff fields:

- Stage 08 document revision and the exact source revision used;
- accepted inherited constraints versus unresolved platform choices;
- changed files, document consistency checks performed, and any known limitations;
- links/IDs for separately verified implementation or execution evidence, if such evidence exists;
- claims that must remain framed as design intent, plus the next human review or decision owner.

## 23. Open questions

### Local MVP implementation-time details

D-0022–D-0028, `docs/platform-technical-baseline.md`, and `docs/contracts/` settle the earlier prototype's local launch, active-data access, stack, database/asset storage, explicit local-file import behavior, history retention, minimum Stage 01–05 contracts, backup/restore behavior, encryption choice, and historical-review handling. Dependency pins and the offline validator exist for that prototype; they do not establish compatibility on an untested target PC. D-0029 still pauses implementation, and the revised product scope needs human acceptance. Under D-0033 the intended PC profiles, supported runtime matrix, future packaging/distribution mechanism, configurable data/model paths, and model transfer/license handling remain open. The one-working-copy convention above is a recommendation awaiting human choice. Provider credentials and their secret-management boundary remain deferred until a later provider milestone.

### Hosted, multi-user, and provider extension questions

- Is a tenant/organization object required for the first hosted deployment, or can a single owner map to the same logical boundary without an extra service entity?
- Will a future production project have exactly one external account, or may it own multiple account records? What are the ownership, character/series, and content-target semantics in that case?
- What identity provider, service-principal model, project-level role grants, and break-glass process fit the expected users?
- What object store and artifact registry can enforce immutable versions, scoped access, checksums, lifecycle rules, and project-safe export/restore?
- Which artifact/version numbering and compatibility policy will producers and consumers declare, and who reviews migrations that affect approvals?
- What sharing permission model covers reference-only use, copying, transformation, expiration, and revocation without allowing implicit global assets?
- Which data classes, retention durations, residency rules, deletion guarantees, and legal-hold process apply to binaries, third-party references, personal/account data, approval records, logs, and backups?
- What backup topology, recovery-point objective, recovery-time objective, and restore verification cadence are appropriate?
- Which project export scope, file packaging format, and audit evidence are required for portability and account closure?
- Which checks belong in repository review versus a future registry, storage adapter, or harness service?
- After the local MVP, which evidence justifies hosted or multi-user operation, and what threat/data review is required before external storage or remote access?
