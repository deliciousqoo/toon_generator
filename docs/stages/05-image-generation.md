# Stage 05 — AI image-generation workflow

> **Current candidate direction:** The app, source files, and canonical project records stay local; local inference is preferred under D-0031, with a conditional external path. The target execution PC is `unknown`; the current PC's GPU is not a requirement or a selection basis. After the target PC is selected and scoped execution is separately authorized, compare Gemini/OpenAI external candidates with ComfyUI/Krita-based local candidates using the same synthetic input snapshot and review criteria. These names are candidates only; exact models, prices, hardware requirements, and provider selection remain unresolved. See the [synthetic evaluation plan](../synthetic-model-evaluation-plan.md) and [pre-implementation decision pack](../preimplementation-decision-pack.md). No API call, installation, image generation, or implementation is authorized here. Source and specifications are portable through Git; secrets, model weights/caches, project records, references, and generated media stay outside Git by default.

## 1. Purpose

This stage translates one human-approved Stage 04 storyboard package into a traceable set of AI-generated visual drafts. The review package contains per-unit image drafts and a composed preview of the whole episode in its selected layout. It defines how a generation candidate is selected, how prompts and references are assembled, how runs are recorded, and how the human G3 decision is captured. Stage 06 is a later extension, not a prerequisite for completing the first storyboard/draft cycle.

This document is a specification only. It does not select a real model, workflow, plugin, tool, prompt, seed, canvas, character, story, storyboard, image, or production project. In the current `specification_only` mode, every execution value remains `unknown` or an example ID.

The approved storyboard remains the source of truth for narrative intent, character identity, layout intent, text responsibility, and rights restrictions. Stage 05 may translate those decisions into generation instructions, but it may not silently rewrite them. A generated image is a draft until a human approves the exact draft package at the visual-draft gate.

## 2. Scope and non-goals

### In scope

- One `content_id` inside one isolated `project_id`.
- Consumption of the exact Stage 04 `storyboard_package` approved at `G2`.
- A repeatable procedure for evaluating model/workflow candidates without fixing a technology in this specification.
- Versioned prompt bundles, reference selections, generation attempts, intermediate review artifacts, and output provenance.
- Candidate generation, consistency review, draft selection, human visual-draft approval, failure recovery, and Stage 06 handoff.
- Per-unit draft images and a composed full-episode preview sufficient to review the selected format, reading order, and text responsibility.
- Human selection among per-unit image candidates and requests to regenerate selected cuts, with previous candidates retained.
- Rights, identity, brand, privacy, and project-isolation checks before and after generation.

### Non-goals

- Choosing or mandating a particular model, provider, UI, plugin, workflow engine, adapter, LoRA, checkpoint, or hosting arrangement.
- Training a model or creating an operational LoRA during the first vertical slice.
- Creating a real project brief, character, story, storyboard, prompt, generation run, image, or publication record in specification mode.
- Replacing Stage 04 story, text, layout, character, or rights decisions with prompt wording.
- Treating a model's confidence, aesthetic score, similarity score, or automated checklist as human approval.
- Providing a general-purpose in-app raster editor for drawing, pixel retouch, manual crop manipulation, or balloon/text placement.
- Adding generated binaries or copied reference assets to Git before a storage/versioning policy is approved.

The implementation may later choose a technology after the selection procedure in this document is run against concrete constraints. That choice is an execution record and does not become a universal project rule merely because it was useful for one content item.

### First local-platform validation sequence

This sequence describes future milestones and the existing mock baseline, not permission to resume implementation under D-0029. A mock validates mechanics only; it provides no evidence of identity preservation or story-bound image quality. The revised first technical slice remains Stage 04 under D-0031.

The first local-platform workflow milestone uses a mock generation adapter that returns clearly labeled synthetic outputs. It validates the shared request/result contract, per-cut selection and regeneration, versioning, and G3 review without contacting an image provider.

A later milestone adds one provider adapter. Before its first call, document the selected provider and model, credential handling, cost limits, permitted synthetic-data transfer, reference-upload conditions, and timeout/retry behavior. Validate the connection with synthetic prompts and synthetic assets (or no reference assets), and retain request, response, output, and provenance records. The mock and provider adapters use the same request/result contract. Provider validation requires a separate explicit authorization in `platform_build`; it does not authorize real project data or `content_execution`, which remains a separate transition.

## 3. Inputs

Stage 05 accepts exact, versioned inputs bound to one project and episode. File presence is not approval. Every input must be traceable in the run manifest.

| Input | Required information | Minimum status |
|---|---|---|
| `project_id` and `content_id` | Stable project/content boundary and state transition context | Present and consistent |
| Stage 04 storyboard package | Exact `artifact_id`/version, selected story, ordered units, character IDs, text plan, layout constraints, generation boundaries, rights restrictions, validation, and `G2` decision | Human-approved `G2` version |
| Stage 02 character package | Exact character package and sheet/reference IDs, invariants, allowed variation, forbidden traits, provenance restrictions | Human-approved `CG2` version, or the exact version embedded in the approved Stage 04 package |
| Stage 01 research package | Relevant observation IDs, `not_to_copy`, use classifications, source restrictions, and open risks | Approved package or explicitly inherited restrictions |
| Stage 03 strategy package | Selected series/pillar, format, audience/tone constraints, editorial filters, and brand restrictions | Human-approved `SG2` version, carried through Stage 04 |
| Episode format decision | The exact single-frame or multi-panel layout selected for this episode, rationale, and any human decision resolving ambiguity or conflict | Recorded in the approved Stage 04 storyboard package |
| Generation brief | Unit scope, purpose of this run, output responsibility, and unresolved questions | Bounded and recorded; unknowns remain visible |
| Candidate evaluation record | Constraints and test protocol used to compare model/workflow candidates | Draft before evaluation; human selection required |

If any input is missing, unapproved, inaccessible, contradictory, or owned by another project, Stage 05 may create a blocked preflight record. It may not guess, generate, pass `G3`, or hand off to Stage 06.

### 3.1 Minimum input envelope

The execution envelope below is illustrative only. It uses example IDs and `unknown` values; it is not a request to populate a production project.

```json
{
  "project_id": "production-project-example-001",
  "content_id": "content-example-001",
  "storyboard_package": {
    "artifact_id": "storyboard-package-project-example-001-v001",
    "version": "1.0.0",
    "project_id": "production-project-example-001",
    "content_id": "content-example-001",
    "approval_status": "approved",
    "approval_gate": "G2",
    "next_consumer": "05-image-generation"
  },
  "character_package": {
    "artifact_id": "character-package-project-example-001-v001",
    "version": "1.0.0",
    "project_id": "production-project-example-001",
    "character_id": "character-example-001",
    "sheet_artifact_id": "unknown",
    "approval_status": "approved"
  },
  "strategy_package": {
    "artifact_id": "account-strategy-project-example-001-v001",
    "version": "1.0.0",
    "project_id": "production-project-example-001",
    "series_id": "series-example-001",
    "series_version": "1.0.0",
    "approval_status": "approved"
  },
  "reference_research": {
    "artifact_id": "reference-research-project-example-001-v001",
    "version": "1.0.0",
    "project_id": "production-project-example-001",
    "approval_status": "approved",
    "restriction_status": "unknown"
  },
  "generation_scope": {
    "unit_ids": ["unit-example-001"],
    "purpose": "unknown",
    "output_responsibility": "image_and_layout",
    "text_handling": "overlay_later",
    "unknowns": []
  }
}
```

The preflight check must compare every nested `project_id` and `content_id` with the envelope. It must resolve the exact storyboard version rather than a mutable `latest` pointer. A Stage 04 approval does not approve a model, prompt, image, or Stage 05 output.

## 4. Project and content-state boundaries

### 4.1 `project_id` is the isolation boundary

Every prompt bundle, model/workflow candidate record, reference selection, run, output, review artifact, validation record, approval, and provenance entry belongs to the same `project_id` unless an explicit shared-source decision says otherwise. Project-local IDs are not global settings.

Stage 05 must block:

- a storyboard, character, reference, output path, or metadata record with a different `project_id`;
- a cross-project reference or template with no source project, exact version, permission/rights basis, transformation decision, and human review note;
- a lookup that resolves a newer character, storyboard, or strategy version without recording the version actually consumed;
- reuse of a prompt, seed, reference set, or workflow state that cannot be proven to belong to this run;
- any generated output whose project ownership is ambiguous.

Generated output, temporary files, and review boards must be stored or referenced in a way that preserves the project boundary. The local MVP stores durable candidates and previews in the app-managed local asset store; only transient cache and interrupted-write files may be removed during recovery. The manifest records logical asset IDs and exact versions; checksums and local storage keys are recorded in asset records. The mock adapter creates synthetic image outputs only.

### 4.2 Mapping to the content state machine

Stage 05 covers the visual-draft transition:

```text
storyboard --G3 Visual draft--> ai_draft --Stage 06 handoff--> human_retouch
```

`G2` is a mandatory precondition. A generated candidate can exist as a failed or unapproved work-in-progress, but it is not an `ai_draft` state until the exact package passes the human visual-draft gate. Rejection preserves the candidate and names one of these paths:

- return to Stage 04 `storyboard` rework when the approved plan is incomplete, contradictory, or unsuitable for generation;
- remain in Stage 05 and create a new generation run when the plan is valid but the candidate fails;
- stop for a rights, identity, brand, privacy, or project-isolation decision when the risk cannot be resolved by regeneration.

## 5. Model and workflow selection contract

### 5.1 Selection principle

The project does not fix a generation technology in advance. A candidate is selected only after it is evaluated against the exact approved storyboard and the first-slice constraints. The record must distinguish:

- `required`: directly imposed by the approved input or a human decision;
- `preferred`: a useful property that may be traded off;
- `unknown`: not yet established;
- `rejected`: tested or ruled out with a recorded reason.

The candidate record must never imply that a familiar tool or model is approved by default. `model_id`, `model_version`, `workflow_id`, `workflow_version`, provider, adapters, and tool versions may all remain `unknown` until a real evaluation occurs.

### 5.2 Evaluation dimensions

Each candidate is evaluated with a bounded protocol. The dimensions below are criteria, not technical prescriptions:

| Dimension | Evaluation question |
|---|---|
| Storyboard fit | Can the candidate express the required scene, action, emotion, camera, background, and layout boundary without inventing material facts? |
| Character identity | Does it preserve Stage 02 invariants and allowed variation across the required units? |
| Controllability | Can required/may-vary/must-avoid constraints be represented and inspected? |
| Cross-unit consistency | Can the character, props, direction, and continuity remain recognizable across the run? |
| Korean text separation | Can the image remain free of baked-in dialogue while a separate editable Korean text/layout layer preserves exact dialogue, speaker, reading order, and text-safe areas? |
| Editability | Can a selected unit be corrected or regenerated without changing untouched units, identity cues, or source text, with a before/after record and preserved previous outputs? |
| Reproducibility | Can the run record model/workflow versions, parameters, seed policy, and inputs sufficiently to repeat or explain it? |
| Provenance and inspection | Can intermediate settings, references, outputs, and transformations be reviewed? |
| Rights and privacy | Can restricted references, likenesses, brands, and personal data be excluded or controlled? |
| Output compatibility | Can the result be exported, stored, and handed to Stage 06 under the known or explicitly unknown format constraints? |
| Human workload | Does the candidate reduce useful work without moving identity, rights, or quality judgment out of the human gate? |

The evaluation also records failure modes, resource/cost observations, latency, and operational dependencies when known. These are evidence for a scoped choice, not promises about future content.

### 5.3 Selection procedure

1. Freeze the exact Stage 04 package and list the constraints that the candidate must satisfy.
2. Before provider selection, use the synthetic-only protocol in `docs/synthetic-model-evaluation-plan.md`; no real project inputs enter that comparison. For a separately authorized content run, use only approved project references and the units needed to answer the selection questions.
3. Register candidate IDs with model/workflow/tool fields as `unknown` until the execution environment exposes exact values.
4. Run equivalent tests with the same review criteria and record failed attempts; do not compare an undocumented best result to a documented full run.
5. Review identity, composition, rights, reproducibility, output handling, and human-edit burden together.
6. A human selects, rejects, or defers the candidate and records the reason, evidence, trade-offs, and validity scope.
7. Freeze the selected candidate record into the run manifest. A later change creates a new candidate or run version.

If no candidate satisfies a required dimension, stop and route the package to Stage 04 or an implementation decision. Do not weaken a storyboard constraint inside a prompt merely to make a candidate appear successful.

### 5.4 Comparable trials and execution preflight

Freeze one synthetic character/reference, story, storyboard, and separate Korean text/layout snapshot for all candidates. Record exact versions/checksums, equivalent output/crop requirements, the rubric version, and all candidate-specific prompt or preprocessing transformations. Reference restrictions or unsupported controls must be disclosed as non-comparable dimensions; do not quietly remove them. Evaluate the first result and every failure, rather than choosing an undocumented best output. Extra samples, a repeatability attempt, and a selected-cut edit require a finite, human-confirmed trial budget. Equal seeds across unrelated models do not establish equivalent conditions.

Keep `target_machine_id` and its OS, GPU/VRAM, RAM, driver/runtime, storage, and dependency profile `unknown` until the intended PC is selected. Confirm the chosen local model, workflow nodes, plugins, licenses, and current official requirements against that profile before any authorized installation/trial. If it is missing, local measurements and a completed local-versus-external comparison remain `not_run`; external observations alone do not establish a local winner/loser.

Before any external request, identify the provider/model/endpoint/tier, selected payload and reference IDs, training-use terms, retention/deletion/region conditions, and estimated and maximum spend including retries and edits. Unknown or unacceptable transfer/retention conditions or unbounded spend block the request. D-0032's USD 5 synthetic comparison ceiling and sample/retry defaults are recommendations pending human confirmation, not accepted execution settings. Recheck changing facts in official documentation at selection, immediately before trial, and after a relevant version/terms change; record access date and evidence. The comparison itself still requires separate execution authorization.

## 6. Prompt composition contract

### 6.1 Prompt is a derived, versioned artifact

The prompt bundle is a translation of the approved storyboard, not a second source of creative truth. It must identify the source field or decision for each material instruction and mark any interpretation as `unknown`, `interpretation`, or `human_decision`.

At minimum, a prompt bundle contains:

- prompt bundle ID/version and the exact storyboard, character, strategy, and reference versions;
- unit scope and the `beat_id`/`unit_id` each prompt serves;
- locked project and output context;
- character identity constraints and permitted variation;
- scene, action, emotion, camera, background, props, continuity, and focal-point instructions;
- `must_include`, `may_vary`, and `must_avoid` blocks;
- text and layout responsibility, including whether text is deliberately left for human overlay;
- reference IDs, allowed roles, restriction status, and transformation/abstraction note;
- negative or exclusion constraints derived from approved restrictions, not generic assumptions;
- model/workflow-specific rendering fields kept separate from story decisions;
- unresolved questions, interpretation notes, and human review points.

Prompt text must not copy reference wording, reproduce a protected character, request a recognizable artist imitation, or smuggle in an unapproved brand, logo, prop, trait, or plot detail. The implementation may have system, project, character, unit, exclusion, and output sections, but the section names are not a required technology.

### 6.2 Prompt integrity checks

Before a run begins, compare the rendered prompt package with the storyboard:

- every generation unit maps to an existing approved `unit_id`;
- every required character and prop is sourced from the storyboard or approved character package;
- no `must_avoid` restriction is contradicted by a positive instruction;
- text marked for human overlay is not represented as an instruction to render exact text;
- unknown dimensions, crop limits, or export requirements are not replaced by platform defaults;
- material prompt changes after review create a new prompt bundle version and invalidate the affected candidate review.

The prompt renderer may normalize syntax for a selected workflow, but the normalized result and its source bundle must both be retained when provenance is available.

## 7. Generation procedure and reviewable intermediate outputs

The procedure is deliberately staged so that a human can inspect where a failure entered the process. Each output is a versioned, episode-scoped artifact within its owning project, or an explicitly referenced external artifact.

| Checkpoint | Required intermediate output | Review purpose |
|---|---|---|
| `P0` Preflight | Input envelope, approval evidence, scope check, restriction carry-forward, and blocker list | Confirms that the run may start and that Stage 04 is not being silently changed |
| `P1` Candidate evaluation | Candidate matrix, test protocol, failed/accepted observations, human selection decision | Explains why the selected model/workflow is fit for this scoped run |
| `P2` Prompt package | Versioned structured prompt bundle and rendered per-unit instructions | Makes translation from storyboard to generation inspectable |
| `P3` Workflow preparation | Resolved workflow/tool settings, input reference manifest, parameter profile, and validation result | Shows what will actually execute without hiding defaults |
| `P4` Pilot outputs | Small scoped output set, per-output metadata, contact sheet/review board, and failure notes | Finds identity, layout, rights, and consistency failures before a larger run |
| `P5` Unit batch outputs | All attempted outputs, including failed/quarantined outputs, with unit mapping and checksums when available | Establishes coverage and complete provenance |
| `P6` Draft review package | Selected draft IDs, alternatives, comparison board, review observations, unresolved risks, and proposed decision | Gives the human a reviewable visual-draft package |
| `P7` G3 decision record | Human approval or rework decision for exact draft/package versions | Authorizes or rejects the `ai_draft` transition |

The G3 review package includes each selected per-unit image and a composed preview showing the full episode in its selected layout. A contact sheet or board may provide both views; the chosen representation and version are recorded. A missing per-unit image or full-episode preview is a review blocker, not a pass.

### 7.1 Execution boundaries

The run must define whether it produces:

- a single visual unit or a bounded set of units;
- per-unit image outputs and a composed full-episode layout preview;
- an output intended for later human text overlay;
- a pilot, retry, comparison, or final draft candidate.

The run must not silently expand from a unit subset to the whole content item. If a unit fails or needs a different generation strategy, record the affected IDs and create a scoped retry or return to Stage 04.

### 7.2 Selected-cut revision and Korean lettering

Recommendation pending review (D-0032): initially one rough per unit, then one extra candidate only for a human-selected unit. The human names the unit IDs and intended change; the run preserves untouched candidate IDs and records the affected beat, source version, edit mask/scope when applicable, and `retry_of` or `supersedes`. A new episode preview composes the selected new candidates with the unchanged units. Cross-unit continuity is reviewed again; no automatic whole-episode regeneration is allowed. If a source/storyboard change affects other units, explain those dependencies and obtain the expanded scope before generating them. Limit exhaustion or conflicting evaluator feedback stops for human review, not automatic approval.

Keep Korean dialogue/captions, speaker mapping, balloon/layout anchors, and text-safe areas in a separately versioned editable record/layer. Generate artwork without dialogue lettering; compose a review overlay without overwriting the artwork. Check exact text, Hangul glyph coverage, clipping, reading order, and legibility in the whole-episode preview. A text-only correction updates the text/preview version without invoking image generation. In-image stray lettering is a recorded defect. Krita or another editor is an optional candidate for later manual polish, not a mandatory Stage 05 integration or a replacement for this separate text contract.

## 8. Run manifest contract

The run manifest (`artifact_type: image_generation_run_manifest`) is the canonical provenance record for one generation attempt or a clearly bounded comparison run. Its minimum record shape is defined in `docs/contracts/mvp-records-v1.schema.json`. The JSON example below explains domain-specific fields and is not a schema-complete persisted record; the synthetic fixture set shows the full common envelope. It is immutable after approval; corrections create a new manifest with `supersedes` or `retry_of`.

The canonical Stage 05 review package consists of the preflight/evaluation records, versioned prompt bundle, workflow-preparation record, run manifest, reviewable intermediate artifacts, selected AI-draft output references, a composed full-episode preview, and the `G3` decision. For the local MVP, the run manifest is the aggregate handoff record: `outputs` identifies each per-unit candidate and the episode preview, while `review_package` groups candidates by unit and records selections. The package owner is human or `unknown`; AI may populate evidence but cannot own the approval decision.

```json
{
  "artifact_id": "run-manifest-project-example-001-content-example-001-v001",
  "artifact_type": "image_generation_run_manifest",
  "project_id": "production-project-example-001",
  "content_id": "content-example-001",
  "version": "1.0.0",
  "state": "draft",
  "created_at": "YYYY-MM-DDThh:mm:ssZ",
  "created_by": "human",
  "owner": "human",
  "run": {
    "run_id": "generation-run-example-001",
    "purpose": "candidate_evaluation",
    "unit_ids": ["unit-example-001"],
    "started_at": "unknown",
    "completed_at": "unknown",
    "status": "not_started",
    "retry_of": "unknown",
    "supersedes": "unknown",
    "parent_run_id": "unknown",
    "execution_environment": "unknown",
    "reproducibility_status": "unknown"
  },
  "inputs": {
    "storyboard_package": {
      "artifact_id": "storyboard-package-project-example-001-v001",
      "version": "1.0.0",
      "project_id": "production-project-example-001",
      "content_id": "content-example-001",
      "approval_gate": "G2",
      "approval_status": "approved"
    },
    "character_package": {
      "artifact_id": "character-package-project-example-001-v001",
      "version": "1.0.0",
      "project_id": "production-project-example-001",
      "character_id": "character-example-001",
      "sheet_artifact_id": "unknown"
    },
    "strategy_package": {
      "artifact_id": "account-strategy-project-example-001-v001",
      "version": "1.0.0",
      "project_id": "production-project-example-001",
      "series_id": "series-example-001",
      "series_version": "1.0.0"
    },
    "reference_research": {
      "artifact_id": "reference-research-project-example-001-v001",
      "version": "1.0.0",
      "project_id": "production-project-example-001",
      "observation_ids": ["observation-example-001"],
      "not_to_copy": ["unknown"],
      "rights_restrictions": ["unknown"]
    },
    "prompt_bundle": {
      "artifact_id": "prompt-bundle-project-example-001-content-example-001-v001",
      "version": "1.0.0",
      "project_id": "production-project-example-001",
      "source_storyboard_version": "1.0.0",
      "rendered_prompt_artifact_id": "unknown"
    },
    "workflow_preparation": {
      "artifact_id": "workflow-preparation-project-example-001-content-example-001-v001",
      "version": "1.0.0",
      "project_id": "production-project-example-001",
      "validation_status": "unknown"
    }
  },
  "selection": {
    "evaluation_protocol_id": "candidate-evaluation-example-001",
    "selected_candidate_id": "model-workflow-candidate-example-001",
    "decision": "selected",
    "decision_scope": "content-example-001",
    "decision_by": "unknown",
    "decision_at": "unknown",
    "reason": "unknown",
    "tradeoffs": [],
    "candidate": {
      "model": {
        "provider": "unknown",
        "family": "unknown",
        "name": "unknown",
        "version": "unknown",
        "revision_or_checksum": "unknown",
        "license_or_usage_basis": "unknown"
      },
      "workflow": {
        "workflow_id": "workflow-example-001",
        "version": "unknown",
        "revision_or_checksum": "unknown",
        "input_contract_version": "unknown",
        "state_or_graph_artifact_id": "unknown"
      },
      "adapters_or_components": [],
      "toolchain": []
    }
  },
  "prompt": {
    "prompt_bundle_id": "prompt-bundle-project-example-001-content-example-001-v001",
    "version": "1.0.0",
    "per_unit_prompt_ids": ["prompt-example-001"],
    "negative_or_exclusion_block_ids": ["exclusion-block-example-001"],
    "prompt_hashes": [],
    "source_field_map_artifact_id": "unknown",
    "interpretation_notes": [],
    "unknowns": []
  },
  "references": [
    {
      "reference_id": "reference-example-001",
      "artifact_id": "character-sheet-example-001",
      "version": "unknown",
      "project_id": "production-project-example-001",
      "role": "character_identity",
      "source_project_id": "production-project-example-001",
      "rights_status": "approved_for_this_use",
      "upload_or_tool_use": "allowed",
      "transformation_or_abstraction": "unknown"
    }
  ],
  "parameters": {
    "canvas_or_output_spec": "unknown",
    "aspect_ratio": "unknown",
    "sampler_or_generation_method": "unknown",
    "steps_or_iterations": "unknown",
    "guidance_or_strength": "unknown",
    "batch_size": "unknown",
    "seed_policy": "fixed",
    "seeds": [
      {
        "unit_id": "unit-example-001",
        "seed": "unknown",
        "random_state_or_subseed": "unknown"
      }
    ],
    "additional_parameters": {},
    "defaults_used": [],
    "unknowns": []
  },
  "tools": [
    {
      "tool_id": "tool-example-001",
      "name": "unknown",
      "version": "unknown",
      "provider": "unknown",
      "purpose": "generation",
      "configuration_artifact_id": "unknown"
    }
  ],
  "outputs": [
    {
      "output_id": "generated-output-example-001",
      "artifact_id": "ai-draft-output-project-example-001-content-example-001-v001",
      "version": "1.0.0",
      "project_id": "production-project-example-001",
      "content_id": "content-example-001",
      "unit_id": "unit-example-001",
      "status": "candidate",
      "file_or_uri": "unknown",
      "media_type": "unknown",
      "checksum": "unknown",
      "dimensions": "unknown",
      "prompt_id": "prompt-example-001",
      "seed": "unknown",
      "source_reference_ids": ["reference-example-001"],
      "derived_from_output_ids": [],
      "created_at": "unknown",
      "storage_policy_status": "unknown",
      "failure_or_quarantine_reason": "unknown"
    }
  ],
  "provenance": {
    "input_artifact_ids": [],
    "input_versions": {},
    "model_versions": [],
    "workflow_versions": [],
    "prompt_versions": [],
    "reference_versions": [],
    "tool_versions": [],
    "parameter_records": [],
    "seed_records": [],
    "output_artifact_ids": [],
    "transforms": [],
    "human_decisions": [],
    "ai_assistance": [],
    "unknowns": []
  },
  "validation": {
    "schema_check": "unrun",
    "project_boundary_check": "unrun",
    "input_approval_check": "unrun",
    "unit_coverage_check": "unrun",
    "prompt_storyboard_alignment": "unrun",
    "character_identity_check": "unrun",
    "continuity_check": "unrun",
    "rights_and_brand_check": "unrun",
    "text_and_layout_check": "unrun",
    "output_integrity_check": "unrun",
    "provenance_completeness": "unrun",
    "review_artifact_check": "unrun",
    "performed_by": "unknown",
    "performed_at": "unknown",
    "unresolved_risks": []
  },
  "approval": {
    "gate": "G3",
    "status": "pending",
    "approved_artifact_ids": [],
    "approver": "unknown",
    "decision": "approved",
    "decision_at": "unknown",
    "reason_or_notes": "unknown",
    "return_state": "storyboard"
  },
  "handoff": {
    "next_consumer": "06-polish-and-qa",
    "required_input_status": "blocked_until_G3_approval",
    "selected_output_ids": [],
    "selected_output_version": "unknown",
    "human_retouch_scope": [],
    "open_risks": [],
    "affected_consumers_on_revision": []
  }
}
```

### 8.1 Manifest rules

- The manifest identifies the exact model, model version/revision, workflow version, tool versions, prompt version, reference versions, parameters, seed policy/values, output artifacts, and transformations when available. Missing values remain `unknown`.
- `seed` is not proof of reproducibility by itself. The manifest also records model revision, workflow revision, toolchain, defaults, parameters, reference preparation, and environment when available.
- Every output maps to a `unit_id`, prompt ID, input references, and the run that produced it. An output with missing provenance remains failed, quarantined, or blocked until a human explicitly decides how it may be used.
- A retry is a new `run_id` and manifest version. It records `retry_of`, the reason, whether inputs changed, and all new outputs. It does not overwrite the earlier attempt.
- A manifest cannot set `approval.status = approved` from validation fields alone. A human must approve the exact output and review package named by the manifest.
- The manifest is not a license record. It carries rights evidence and restrictions so Stage 06 can recheck them; legal uncertainty remains a human blocker.
- The MVP manifest includes a `review_package` with `per_unit_candidate_sets`, `composed_preview_asset_id`, and `selected_output_ids`. Every candidate maps to a `unit_id`; the preview covers the whole episode. A separate `image_draft_package` artifact type is not used in this MVP.

## 9. Rights, identity, brand, and privacy restrictions

### 9.1 References and source material

- Carry forward every relevant Stage 01 `not_to_copy`, use classification, restriction, and unresolved-rights note.
- Public accessibility does not imply permission to upload a reference to a generation tool, use it as a training input, reproduce it, or publish a derivative.
- A reference may guide an approved abstract structural observation only when the Stage 01 record permits that use. Direct copied wording, characters, logos, panels, distinctive artwork, or recognizable artist imitation is prohibited.
- A reference used as a technical input must have an explicit artifact ID/version, source project or source information, rights/use basis, intended role, and transformation/abstraction note.
- When upload permission, license, consent, or source identity is unknown, do not send the reference to the tool. Record the blocker and use a permitted project-owned substitute or return for a human decision.

### 9.2 Character identity

- Stage 02 invariants are required constraints, not suggestions. The workflow must not introduce a redesign, unsupported trait, new recurring prop, or unapproved identity exception.
- Allowed pose, expression, outfit, camera, and scene variation must remain within the character package and Stage 04 unit boundary.
- A similarity check may flag drift but cannot decide identity or approve an exception. A human reviews the actual output at `G3`.
- Secondary characters, likenesses, or personal data require an explicit project-scoped basis. Do not infer consent or add a real person's likeness from a reference.

### 9.3 Brands and publication safety

- Do not introduce unapproved brand names, logos, trade dress, protected characters, or implied endorsement.
- Do not let a model's invented text or symbol become accepted brand content. Unreadable or invented text is a generation failure unless the storyboard explicitly assigns later human overlay and the generated image is otherwise acceptable.
- Brand, rights, identity, privacy, and safety uncertainty blocks `G3` until a human resolves it or the output is rejected.

## 10. AI and human roles

### AI may assist with

- candidate matrix preparation and bounded comparison summaries;
- translating approved storyboard fields into prompt bundle drafts;
- workflow preparation, parameter capture, batching, file naming, and manifest population;
- generating candidate images, previews, contact sheets, and deterministic validation reports;
- flagging identity, continuity, text, crop, provenance, or rights-risk signals for human review;
- preserving failed attempts and assembling the review package.

AI assistance must cite the exact input versions, preserve uncertainty, and never fabricate model, seed, tool, rights, or output metadata. A generated image, score, or automated pass is not an approval.

### Human must perform or approve

- model/workflow selection for the scoped run and the trade-offs it accepts;
- whether the prompt translation preserves story, character, layout, and rights intent;
- reference upload/use permission and any exception to project-local inputs;
- identity, originality, brand, privacy, and visual-quality judgment;
- selection of the exact draft outputs and the Stage 05 `G3` visual-draft decision;
- whether a failure is retried, routed back to Stage 04, quarantined, or abandoned;
- the handoff scope and any change that affects Stage 06 or publication risk.

Automation may stop a run or request review. It may not waive a restriction, select a final draft without human review, mark `G3` approved, or publish.

## 11. Human approval gates

`P0`–`P6` are preparation and evidence checkpoints. `P7` records the human `G3` decision for the exact draft package; it is not an additional automated checkpoint or a substitute for the G3 gate.

| Gate | Decision | Minimum evidence | Rework path |
|---|---|---|---|
| `G3` Visual draft | The exact generated draft package follows the approved storyboard, preserves the character and restrictions, and lets a human review every unit and the whole episode in its chosen layout | Approved Stage 04 package, candidate decision, prompt/workflow versions, complete run manifest, every selected per-unit image, composed full-episode preview, identity/layout/rights review, unresolved-risk decision | Regenerate in Stage 05, return to Stage 04 `storyboard`, or block for a rights/identity decision |

The approval record must name the human approver, exact manifest/output/review-package versions, decision, timestamp, reason, and next consumer. `G3` completes the initial storyboard/draft validation target. It may authorize a later Stage 06 handoff, but it does not approve polish, refinement, QA, or publication.

## 12. Validation checklist

Before requesting `G3`, validate the exact manifest and review package:

- [ ] `project_id` and `content_id` are present and consistent in every envelope, input, prompt, reference, output, and approval record.
- [ ] The exact Stage 04 `storyboard_package` version is recorded and has human `G2` approval.
- [ ] Stage 01 restrictions, Stage 02 identity invariants, Stage 03 format/brand constraints, and Stage 04 generation boundaries are carried forward.
- [ ] The selected model/workflow candidate is identified or explicitly `unknown`, and the human selection decision and scope are recorded.
- [ ] The synthetic comparison uses the same frozen input/rubric and discloses candidate-specific transformations, unsupported controls, failed attempts, and any `not_run` local measurements.
- [ ] Target-machine requirements are verified against the selected PC rather than the current host; costs, transfer payload, retention terms, and separate execution authorization are recorded before a request.
- [ ] Prompt bundle versions map to exact storyboard units, beats, character IDs, text responsibility, and `must_include`/`may_vary`/`must_avoid` rules.
- [ ] No prompt or reference copies protected wording, characters, panels, logos, distinctive artwork, or a recognizable artist's expression.
- [ ] Every reference has an exact artifact/version, role, project boundary, rights/use status, and upload/use decision; unknown permission blocks use.
- [ ] Model revision, workflow revision, adapters/components, tool versions, parameters, defaults, seed policy, and environment are recorded or marked `unknown`.
- [ ] Every attempted output has a stable output ID, unit mapping, prompt mapping, source references, status, and file/URI or an explicit failure/quarantine reason.
- [ ] Output integrity, coverage, crop/layout, text responsibility, continuity, and identity checks were run or visibly marked `unrun`/`unknown`.
- [ ] A human-inspectable pilot/batch review artifact exists; a missing preview is not treated as pass.
- [ ] Failed and rejected candidates remain traceable and are not silently reused as selected outputs.
- [ ] Selected-cut revisions preserve untouched output IDs and prior candidates; the composed preview and continuity review are refreshed without an automatic whole-episode rerun.
- [ ] Korean dialogue/layout remains separately editable; text-only changes do not trigger image generation, and glyph coverage, clipping, safe areas, and reading order are reviewed.
- [ ] Any retry is a new run/manifest version with `retry_of`, reason, input-change status, and new provenance.
- [ ] No automated score or checklist has been used as the approval record.
- [ ] A human approved the exact output package at `G3`, or the package remains blocked/rework.
- [ ] The handoff identifies the selected output, source manifest, human retouch scope, open risks, and the Stage 06 consumer.

Automated validation may report malformed JSON, duplicate IDs, missing references, inconsistent project IDs, missing unit coverage, unrecorded defaults, broken output paths, or incomplete provenance. It may not decide originality, rights, character identity, creative quality, or approval.

## 13. Failure, retry, quarantine, and rollback

| Failure | Required response | Recovery output |
|---|---|---|
| Stage 04 package is missing, unapproved, or from another project | Stop before prompt rendering or generation | Blocked preflight record naming the exact missing/conflicting input |
| Format, text responsibility, or generation boundary is unknown | Preserve `unknown`; do not adopt a platform default | Bounded question, clarified Stage 04 version, or blocked run |
| No candidate meets a required selection dimension | Do not weaken the storyboard silently | Candidate evaluation with rejection evidence and an implementation/Stage 04 decision request |
| Prompt conflicts with storyboard or restrictions | Discard the affected prompt version and regenerate the prompt bundle from the approved source | New prompt bundle version and invalidated candidate review |
| Model/workflow execution fails or output is corrupt | Preserve logs/metadata, mark outputs failed, and retry only with a new manifest | New retry run with `retry_of` and reason |
| Character identity drifts or continuity breaks | Quarantine affected outputs; inspect whether the cause is prompt, reference, workflow, or storyboard | Corrected prompt/workflow run or Stage 04 rework package |
| Output contains copied, restricted, brand, private, or unsafe material | Quarantine; do not upload, select, publish, or pass downstream | Rights/identity review record and rejected or corrected version |
| Provenance is incomplete | Mark output blocked even if visually acceptable | Recovered metadata or a human decision that rejects the output for downstream use |
| Prompt/model/workflow change affects an accepted candidate | Preserve the prior package and create a new version | New manifest with changed fields, affected outputs, and new review |
| Approved storyboard changes after generation | Do not edit the manifest or output in place | Return to Stage 04, create a new storyboard version, and invalidate affected draft consumers |
| `G3` rejects the selected draft | Preserve the rejected draft and exact decision | New Stage 05 run, Stage 04 rework, or blocked decision as named by the human |

### 13.1 Retry policy

A retry is allowed only when the input scope and failure reason are recorded. The retry must state whether it reuses the same model/workflow/reference/prompt/seed policy or changes any of them. A changed material input is a new candidate comparison, not an undocumented retry. Repeated failure with the same cause routes to a human decision; it does not authorize indefinite regeneration.

### 13.2 Rollback policy

Rollback means moving the active working pointer back to the last valid, human-approved artifact or reopening the named earlier state. It does not mean deleting manifests, outputs, logs, or rejected candidates. Approved artifacts remain immutable. If a selected draft is later found unsafe, mark it revoked or superseded, notify the affected downstream consumer, and create a new version after the relevant gate is reopened.

## 14. Versioning and metadata

- Version the prompt bundle, candidate evaluation, workflow preparation, run manifest, review package, output package, and approval record independently when useful, while retaining their exact relationships.
- Create a new run and manifest version for every retry, changed model/workflow, changed prompt, changed reference set, changed seed policy, changed parameter profile, or changed output responsibility.
- Preserve `retry_of`, `supersedes`, `derived_from`, changed IDs, reason, affected consumers, and approval status.
- Do not mutate an approved storyboard, character package, prompt bundle, run manifest, selected output, or `G3` decision in place.
- Keep rejected, failed, and quarantined outputs traceable without making them available to Stage 06 as selected inputs.
- Record model, model version/revision, workflow version/revision, tool versions, references, parameters, seed policy/values, environment, transformations, and human decisions whenever available. Use `unknown` when not available.
- Record access dates and decision dates separately from artifact creation and run timestamps.
- Use repository-relative logical artifact IDs and a storage reference; do not add large binaries or copied reference files to Git until the storage/versioning policy permits it.
- A project duplication creates a new `project_id` and records clone provenance. Mutable prompts, references, runs, and outputs are not shared automatically.

## 15. Handoff to Stage 06

Stage 06 may consume a Stage 05 package only after `G3` approves the exact draft package. The handoff must include:

- the exact `project_id`, `content_id`, Stage 04 storyboard package ID/version, and `G2` approval evidence;
- the selected output artifact IDs/versions and the complete run manifest ID/version;
- the exact model/workflow/tool/prompt/reference/parameter/seed provenance, with explicit `unknown` fields where unavailable;
- per-unit mapping, selected alternatives, failed/quarantined output notes, and review-board artifact;
- the character package/sheet version, identity observations, continuity notes, and any permitted variation;
- text responsibility: what must remain for human overlay, what was generated, and what remains unresolved;
- canvas, crop, safe-area, accessibility, export, and layout requirements or explicit unknowns;
- carried-forward rights, brand, privacy, `not_to_copy`, and source restrictions;
- the human `G3` decision, approver, timestamp, exact approved versions, and rework history;
- a bounded human retouch brief naming intended changes and what must not change;
- open risks and affected consumers if any later revision occurs;
- `next_consumer = 06-polish-and-qa` and the required input status.

Stage 06 must not infer missing provenance, replace the selected output with a different candidate, or treat `G3` as approval of polish or publication. A material change to the story, identity, rights classification, or generation scope returns to the named earlier stage and creates a new version.

## 16. Open questions

- Which target PC profile and local model/workflow will be evaluated, and which external endpoint/tier will be compared after authorization?
- Which trial sample count, selected-cut edit/repeatability allowance, timeout, and numeric total/per-run/monthly cost caps will the human accept? D-0032 values remain recommendations.
- Which transfer/retention/deletion conditions and local backup/retention policy will be accepted for each candidate?
- Which storage/versioning policy will hold generated binaries, previews, logs, and manifests while preserving project isolation?
- Which candidate-evaluation protocol is small enough for the first slice but sensitive enough to reveal cross-unit identity and layout failures?
- Which format-specific output, crop, accessibility, and thumbnail checks should Stage 07 automate once the Project Brief supplies concrete limits?
- Which provenance fields can the selected execution environment capture automatically, and which require a human declaration?
- How should a reference be transformed or abstracted when it is useful structurally but cannot be uploaded to a generation tool?
- What minimum human review board is sufficient for `G3`: per-unit previews, a contact sheet, an interactive board, or all applicable views?
- Under what conditions may a content-local secondary character or recurring prop enter the generation package without first becoming a Stage 02 canonical asset?
- Which visual consistency checks are deterministic enough to block a run without turning them into an automated identity or quality approval?
