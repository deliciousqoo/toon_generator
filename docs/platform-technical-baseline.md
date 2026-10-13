# Local platform technical baseline

## Status and authority

This is the accepted implementation baseline for the personal local MVP. It settles the local stack, storage boundary, selected-file import and history-retention rules, minimum Stage 01–05 record contracts, backup choices, and synthetic acceptance evidence (D-0024–D-0026). The user explicitly started `platform_build` on 2026-10-12 (D-0027). The machine-readable contracts are in [the MVP JSON Schema](contracts/mvp-records-v1.schema.json); the accompanying [synthetic fixture set](contracts/fixtures/mvp-minimum-records.json) contains one representative record for every contract family. Provider calls and real-content execution still require separate authorization. See [the local application guide](local-platform-guide.md) for the implemented flow and runtime.

The formal contracts here are intentionally the minimum needed to implement and validate Stages 01–05 with synthetic fixtures. They do not claim that Stages 00–09, hosted operation, or the full Stage 07 automation harness have been formalized. D-0029 pauses further implementation for product-direction review; this portability revision is `specification_only`. D-0033 preserves portability while leaving the intended target-machine profiles unknown.

## 1. Runtime and local browser application

- Use Python with FastAPI for the local service and a React + TypeScript interface built with Vite.
- Serve the built frontend and API from the same local origin. The end user launches the app through a desktop shortcut; no terminal command or separate Node.js development environment is part of normal use.
- Bind the service to `127.0.0.1` only. Do not bind to `0.0.0.0`, advertise a LAN address, or call external services during the mock-only milestone.
- The app does not require a separate app password. Active local data is protected by access to the user's PC account, as set by D-0022. This is not a guarantee that full-disk encryption is enabled.
- Because no app password is required, the local service must still reject non-local host/origin requests and protect state-changing browser requests against cross-site requests. This is a local request boundary, not an account or remote-access feature.
- Keep implementation/runtime versions pinned when platform build begins. The frontend build output is included with the app; runtime packaging details can be selected during implementation without changing this interface contract.

The stack follows the accepted loopback browser workflow. FastAPI's database tutorial uses SQLite for a local single-file database and notes Python's integrated support; Vite provides React and TypeScript templates. See [FastAPI SQL database tutorial](https://fastapi.tiangolo.com/tutorial/sql-databases/) and [Vite guide](https://vite.dev/guide/).

### 1.1 Installation reproducibility and machine-specific paths

These are portability requirements derived from D-0033, not a claim that another PC has been installed or tested.

- Use the nested `toon_generator` repository root and an exact reviewed commit/release as the setup input. Transfer code, specifications, schemas, synthetic fixtures, install/build scripts, dependency manifests/lockfiles, and non-secret configuration templates through Git. Resolve repository paths from the checkout/script location; never require the current user's absolute desktop path or account name.
- Recreate `.venv`, frontend dependencies, build output, and shortcuts on each PC from that revision's pins. The current prototype has `requirements.txt`, `requirements-dev.txt`, `frontend/package.json`, and `frontend/pnpm-lock.yaml`; preserve their versions rather than upgrading on the destination by default. Record OS/architecture, Python, Node, pnpm, app/repository revision, schema/database/package versions, and installation outcome in future synthetic acceptance evidence. Exact compatible runtime versions and target hardware remain to be reviewed; minimum-version checks alone do not prove reproducibility.
- The current installer accepts Python 3.12+ and checks Node 22.12+ when a frontend build is needed, uses the frontend frozen lockfile, and can find a Codex-bundled runtime as a fallback. That fallback path is optional host-specific discovery, not a destination-PC prerequisite. The guide's Python 3.12/Node 24/pnpm 11 record describes the tested prototype environment; it is not the target-machine matrix. No package installation or build is run in this specification work.
- Distinguish checkout root, per-user active-data root, user-selected backup destination, future model/weight root, and temporary/cache root. Current Windows data default: `%LOCALAPPDATA%\ToonStudio`. Backup manifests and asset keys use validated relative paths and stable IDs, not source-PC absolute paths. A future configurable data/model root must be specified and validated before use; this revision does not claim that such settings exist. Shortcuts point at the local checkout/runtime and must be checked after relocation; the current installer preserves existing shortcuts rather than retargeting them automatically.
- Non-secret templates contain placeholders and document defaults/precedence; PC-specific resolved values remain local. Do not add a template, environment variable, or settings feature merely by describing it here. Secret provisioning remains separate per PC: no keys/tokens/passphrases in Git, templates, backups, command arguments, or logs. Provider secret storage is still an unresolved provider-entry detail and does not authorize a provider call.
- Do not transfer local databases, project records/references/generated media, model weights/caches, runtime folders, or private configuration automatically with Git. Model installation/transfer requires separately recorded model identity/version, license/use basis, checksum, destination path and target-runtime compatibility; no model is selected here. Project data uses section 4's supported export/restore route.
- The intended PCs' OS, CPU, RAM, GPU/VRAM and disk needs remain `unknown`. Establish a target profile before local-generation trials; neither observed current-host hardware nor prior mock acceptance determines image-generation requirements. Missing compatible runtimes, unavailable pinned packages, unsupported backup/schema versions, or unresolved paths block the relevant setup/restore step with existing data preserved.

## 2. Local metadata, assets, and versions

- Store metadata, project configuration, artifact/version indexes, approvals, audit events, and migration state in SQLite under the user's private application-data directory.
- Store image and other binary assets as files under that same local data root, grouped by `project_id` and stable asset/artifact identifiers. Do not put binary payloads in Git or in a cloud-synced live database.
- When the user explicitly imports a local reference or media file, copy it into the app-managed project store and leave the original unchanged. Do not bulk-download or mirror web references. Record the source/use basis and checksum; a known restriction that forbids retention blocks import.
- Each asset record includes its `asset_id`, owning `project_id`, optional `content_id`, media type, byte size, storage key, SHA-256 checksum, and exact artifact/version references.
- Use `project_id` as the isolation boundary and `content_id` for episode-scoped records. Every lookup and mutation must enforce the project scope; ambiguous or cross-project references fail closed.
- Treat approved artifacts and their binary versions as immutable. Edits, regeneration, or corrected provenance create a new version and retain the prior record. Approval records point to the exact artifact ID and version reviewed.
- Stage binary writes in a temporary location, verify size/checksum, then register the asset metadata transactionally. Failed or interrupted writes must not produce a visible complete artifact; startup recovery may remove unreferenced temporary files but must not delete registered versions.
- Track the SQLite database schema version separately from artifact schema versions and backup package format. A database migration is explicit and must not overwrite or discard artifact history.
- Keep all project records, binary versions, generated drafts, review decisions, and audit events in the MVP; do not automatically prune them. The MVP has no whole-project deletion feature. A superseded record remains available as history (D-0026).

SQLite transactions provide atomic commits for database records; the file-plus-database write sequence above supplies the corresponding application-level recovery rule. See [SQLite atomic commit](https://www.sqlite.org/atomiccommit.html).

## 3. Minimum Stage 01–05 data contracts

Use JSON Schema Draft 2020-12 for persisted artifacts that cross a stage handoff. Bundle schemas with the app; validation must not fetch a schema from the network. The first contract bundle declares `$schema` and versioned `$id` `urn:toon-generator:contracts:mvp-records:1.0.0`. Each stored artifact records `schema_id: "urn:toon-generator:contracts:mvp-records"`, `schema_version: "1.0.0"`, and its separate artifact `version`. JSON Schema defines `$schema` for the dialect and `$id` for schema identity; see [JSON Schema reference](https://json-schema.org/understanding-json-schema/reference/schema).

### Common artifact envelope

The minimum common envelope is:

- `artifact_type`, `artifact_id`, `version`, `schema_id`, and `schema_version`;
- `project_id`, plus `content_id` when the artifact belongs to an episode;
- `state`, `created_at`, `created_by`, and `owner`;
- exact `source_artifact_refs` containing source `artifact_id`, `version`, and `project_id`, plus `content_id` where applicable;
- `approval`, `validation`, `provenance`, `unresolved_risks`, and `next_consumer`.

Project setup packages for Stages 01–03 carry `project_id` and omit `content_id` unless a reference package is intentionally episode-specific. Episode briefs, storyboard packages, generation runs, and episode reviews carry both IDs. A source reference is never resolved by a `latest` alias, display name, or file path alone.

Human approval is also stored as an immutable `review_decision` record containing the gate, exact artifact/version, human actor, decision, timestamp, notes, and permitted next state. Automated validation may report evidence but cannot create an approval. Audit events record user edits, version creation, selection, regeneration, review decisions, export, restore, and failure/retry actions without overwriting earlier events.

### Required artifact families

| Scope | Artifact families | Minimum stage-specific content |
|---|---|---|
| Project | `project_brief`, `reference_research`, `character_package`, `account_strategy` | Project direction and supported constraints; source/use restrictions and `not_to_copy`; character identity invariants and allowed/forbidden variation; audience/tone, series direction, content pillars, and supported-format envelope. |
| Episode | `episode_brief`, `storyboard_package` | Input mode (`short_topic` or `developed_story`), supplied material and requested edit scope, exact source versions, unresolved questions; selected story and preservation scope; format decision and rationale; ordered cut/unit records with dialogue and visual/action/composition notes; Level 1 rough detail and exact G2 decision. `storyboard_package` contains the structured story and storyboard together for the MVP. |
| Episode image draft | `image_generation_run_manifest` | Exact approved G2 input, `mock` adapter and synthetic flag, selected unit IDs, per-cut candidate asset references, regeneration/supersession links, composed episode preview, review selection, validation/provenance, and exact G3 decision. The manifest and its output asset records form the review package; there is no separate `image_draft_package` record in this slice. |
| Shared records | `asset_record`, `review_decision`, `audit_event` | Asset storage/checksum and exact-version metadata; human decision against an exact artifact; append-only actor/action/scope/time and before/after references. |

The detailed business fields and human gate criteria remain defined in the corresponding `docs/stages/01`–`05` specifications. The schema enforces the minimum common envelope and the core data shape needed for the accepted MVP flow; stage documents retain the richer creative, rights, and review rules. Historical stage JSON examples are explanatory and may omit the formal envelope. During platform build, `backend/contracts.py` validates the bundled schema and all 10 synthetic fixtures offline with `jsonschema` Draft 2020-12 and a format checker. This verifies shape/dialect/format, not creative or rights approval.

### Contract/version compatibility

- Start each MVP artifact schema at contract version `1.0.0`; schema versioning is independent of a project's artifact versions and the app/database release.
- A correction to an artifact creates a new artifact version. A breaking change to a schema creates a new schema major version; optional compatible additions may use a minor version.
- Every handoff validates against the exact schema version recorded on the artifact. The app may accept older versions only when an explicit migration is defined and preserves the source record and approval evidence.
- Unknown future schema or package versions fail closed with no partial write. Do not silently coerce values, invent missing provenance, or migrate an approved artifact in place.
- The initial implementation needs only the schemas and migrations required for Stage 01–05 synthetic fixtures. Full cross-version compatibility and automated migration governance remain later Stage 07 work.

## 4. Project backup and restore

- Export one project at a time through a save-location picker. Each export explicitly asks whether to encrypt it; do not silently reuse the previous export's choice.
- The plain format is `.toonbackup`; the encrypted form is `.toonbackup.age`. Clearly label an unencrypted export because anyone with file access can read its project contents.
- The inner package is a ZIP archive containing a manifest, project records, retained versions, review/audit history, and all included binary assets. Use non-compressing storage for already-compressed media where appropriate.
- The manifest records `backup_id`, `package_format_version`, creation time, app version, source `project_id`, supported schema IDs/versions, and each relative file's path, size, media type, checksum, and owning artifact/version. Include no credentials, API keys, passphrases, runtime cache, or temporary files.
- For encrypted export, encrypt the complete archive using the established `age` passphrase-encryption format, not a project-defined cipher. Offer a long generated passphrase and a strength guide for a user-chosen passphrase. Keep the passphrase only in transient operation memory; never write it to the app database, backup, logs, command-line arguments, or environment variables. If a passphrase is lost, that encrypted backup cannot be restored. The age project documents passphrase-encrypted files and generated passphrases: [age documentation](https://github.com/FiloSottile/age).
- On restore, detect plain versus encrypted format, request a passphrase only for encrypted files, and validate package version, manifest, project scope, paths, and all checksums in a staging location before registering anything. Wrong passphrase, tampering, path traversal, missing files, or unsupported versions fail without changing existing projects.
- Restore always creates an independent copy with a new `project_id`; preserve the source ID in `lineage.source_project_id` and the source backup ID in `lineage.source_backup_id`. Update the copied records' project scope consistently while preserving their artifact history and internal exact-version links. Never overwrite the source or an existing project.
- Preserve copied review decisions as historical evidence marked `restored_history`; reopen current human gates in the new project instead of inheriting approval authority (D-0028).
- Register the restored copy only after validation and migration succeeds. If restore fails, remove only its temporary staging data and leave the original backup and every existing project unchanged.

The prototype uses `pyrage` 1.4.0 for this format (D-0028). Future packaging must preserve the age format and keep the passphrase out of persistent or process-argument storage.

### 4.1 Transfer between independent local PCs

Git clone/update supplies the application; a project backup supplies one project's data. Install a compatible exact revision on the destination independently, then explicitly export on the source, move the selected `.toonbackup` or `.toonbackup.age` file, and restore through the destination app. The file-transfer medium/location is the user's choice and is not an app synchronization service. Credentials, model weights/caches, and external original reference files are not transferred; the backup includes project-owned imported copies and their source records.

Before continuing, inspect restored settings, included assets/checksums, retained artifact/version relationships, source lineage, and historical reviews. A successful restore creates a new copy; it never updates an existing project. Backups from unsupported future app/schema/package formats are rejected unless an explicit compatible migration exists. Keep the source copy and backup until destination verification is complete. Repeating export/restore or switching back creates further independent copies, not a synchronized project identity.

Recommendation awaiting human choice: use one working PC/copy per project work period and retain a transfer record of repository/app version, `backup_id`, source/new `project_id`, validation outcome, and next working copy. If edits diverge across PCs, preserve both and stop automatic reconciliation; the human selects a continuation. This recommendation does not add a scheduler, transfer log feature, automatic conflict resolution, or remote access. See [Stage 08 portability contract](stages/08-git-platform.md#1311-personal-multi-pc-portability-two-separate-transfers).

## 5. Synthetic acceptance evidence

Before a separate real-content decision, retain reviewable evidence that:

1. The desktop shortcut opens the browser app and the service accepts only loopback requests.
2. Two synthetic projects remain isolated across project setup, Stage 04, Stage 05, search, asset access, and restore.
3. Project setup, episode brief/storyboard, image run, asset, human review, and audit synthetic records validate against their pinned schema IDs/versions; missing or mismatched scope and unsupported versions fail closed.
4. Short-topic and developed-story inputs preserve supplied material within the requested edit scope; G2/G3 remain human decisions.
5. The mock adapter creates labeled per-cut candidates and a composed preview without external calls; selection and selected-cut regeneration preserve prior versions.
6. Both backup choices work. Plain backup restores as a copy. Encrypted backup rejects a wrong passphrase or changed file. Both restore all included project data with a new project ID and source lineage while leaving the source untouched.
7. Credentials/passphrases are absent from backup contents and logs, and no real production records or provider calls exist in the validation registry.

For later multi-PC acceptance, additionally verify installation at a different checkout/user path on a selected destination profile, exact dependency/runtime records, independent local stores, complete synthetic backup/restore with reopened gates, and failure without partial writes for incompatible formats or damaged files. Review Git/package contents and backup manifests for excluded local data and secrets. This work supplies only document checks; no second-PC installation, transfer, provider call, or acceptance result is claimed.

These are future implementation acceptance checks, not tests run or results claimed by this specification work.

## 6. Explicitly deferred

- App-level encryption/password lock for active local data; the app relies on the PC user account for MVP access.
- Cloud synchronization, remote access from another computer, hosted/multi-user operation, and conflict recovery.
- Whole-project deletion and automated retention cleanup; these are outside the MVP. A known rights or retention restriction that conflicts with keeping a local project copy blocks import/use. Any future item-level removal flow needs its own authority, history/backup behavior, and permitted audit evidence (D-0025–D-0026).
- External provider/model choice, API credentials, data-transfer approval, cost limits, and provider retry behavior; these require a later synthetic-only provider milestone and separate authorization.
- Stage 06, full Stage 07 harness/schema governance, Stage 08 hosted expansion, and Stage 09 publication.

The approved local choices are also recorded in `DECISIONS.md`; `docs/platform-mvp-scope.md` remains the product boundary and acceptance authority.
