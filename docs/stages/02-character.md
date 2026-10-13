# Stage 02 — Character bible and character sheet

## 1. Purpose

This independent creative stage develops a project-scoped character through conversation, purposeful references, candidate comparison, and user edits. Project creation supplies only a name, intended readers, and tentative series direction; it does not define the protagonist. Stage 02 develops appearance, behavior, and voice together and then confirms the exact written and visual package for later reuse:

- a written character bible;
- a visual character sheet confirmed with the bible; a missing sheet remains a draft blocker;
- identity invariants that must survive variation;
- permitted variation and forbidden changes;
- a validation checklist and versioned handoff for account strategy, storyboarding, and image generation.

The character is owned by one `project_id`. The stage may learn abstract structural lessons from approved references, but it does not copy a protected character or import a reference asset into the project without a recorded rights basis.

During the specification phase, this document defines the fields and decisions. It does not require a real character, image, model, or final art style to exist.

## 2. Scope and non-goals

### In scope

- One project-scoped recurring primary character that remains visually and behaviorally consistent across episodes.
- Optional supporting characters added when an episode needs them; any recurring supporting character receives a project-owned, versioned identity record.
- Character identity, behavior, communication style, visual invariants, and controlled variation.
- Editable written/visual candidates, user correction and selection, and a character bible and sheet that later stages can consume after confirmation.
- Identity checks for readability, consistency, project fit, and rights/provenance.
- Versioned changes, human approval, and explicit rework paths.

### Non-goals

- Producing episode-final art or selecting an image model, LoRA, plugin, or generation workflow. Character-sheet visuals are this stage's own deliverable in authorized execution, not episode art.
- Defining the complete account strategy or content calendar; those belong to Stage 03.
- Solving every secondary character, world-building, costume library, or animation state in the first slice.
- Treating a style reference as permission to imitate a living artist or reproduce distinctive artwork.
- Allowing AI to approve character identity, rights, or the final character sheet.

Every project requires a primary character before an episode can pass the scope gate. A supporting character may be introduced for a particular episode; if the character recurs, add and approve a project-scoped bible/sheet before relying on that identity in later episodes. New character values are not populated during specification-only work.

## 3. Inputs

The stage begins only with project-scoped, versioned inputs:

| Input | Required information |
|---|---|
| `project_id` | Stable production-project identifier; all outputs remain within this boundary |
| Project Brief | Approved minimal version containing project name, audience/target hypothesis, and tentative series direction; it need not contain a protagonist description |
| Reference scope/package | Exact Stage 01 scope/package version, source purposes, observations, restrictions, or an explicit no-reference choice; new references may be added during the conversation |
| Character direction | Optional initial wishes or existing concept; role, appearance, behavior, and voice are developed here and are not entry form requirements |
| Existing character asset | Optional. If present, exact artifact ID/version, ownership or permission basis, and change scope |
| Target readability constraints | Known canvas, panel size, thumbnail context, language, accessibility, or export limitations; unknowns remain explicit |

Character exploration can start after minimal project creation; it does not wait for a complete benchmark corpus. An unreviewed reference may be discussed as a draft with its uncertainty shown, but cannot be used as an approved visual input or identity constraint. Before final handoff, each consumed reference scope/package needs its exact Stage 01 review record and the same `project_id`, or an explicit shared-source decision. A no-reference scope contains no invented source observations.

## 4. Character identity model

The bible separates what must remain stable from what may change for storytelling. This prevents a generated variation from becoming an accidental redesign.

### 4.1 Identity invariants

The following categories are candidates for invariants. The project fills their concrete values during execution:

| Category | Examples of what to define | Validation question |
|---|---|---|
| Silhouette and proportions | Overall shape, body/ head proportion, dominant contour, scale cues | Is the character recognizable as a small silhouette or crop? |
| Face and identity cues | Eye/face structure, distinctive but project-owned features, expression limits | Can the character be distinguished without relying on copied traits? |
| Palette and value | Base colors, contrast roles, prohibited color changes, accessibility needs | Does the identity survive different backgrounds and compression? |
| Mark-making and rendering constraints | Line weight range, fill/shadow rules, complexity budget | Can the rendering be repeated without hidden style assumptions? |
| Behavior and personality | Goals, temperament, reactions, social boundaries, recurring choices | Would two writers make compatible decisions about the character? |
| Voice and text behavior | Speech length, vocabulary, humor boundary, silence/reaction patterns | Does dialogue reinforce the character without copying source wording? |
| Props and symbols | Essential props, optional props, forbidden symbols or logos | Are props identity-bearing, story-dependent, or merely decorative? |

An invariant must be observable or testable. Abstract labels such as “cute” or “energetic” require concrete indicators, examples, or acceptance tests before they can be used as a gate.

### 4.2 Controlled variation

The bible explicitly lists what may vary:

- pose, expression, gesture, and camera angle;
- scene-appropriate props and backgrounds;
- approved outfit or seasonal variants;
- text, speech bubble, and reaction timing;
- controlled exaggeration required by the target format.

Each variation records whether it is `allowed`, `allowed_with_review`, or `forbidden`. New recurring variants create a new character-bible version rather than silently changing the base identity.

### 4.3 Identity checklist

The checklist contains three classes:

1. **Must preserve:** failure means the asset cannot pass the character gate.
2. **May vary:** variation is allowed when the scene or format requires it.
3. **Must not introduce:** copied, rights-risky, confusing, or project-incompatible traits.

The checklist is a project asset, not a model prompt. Prompts may reference the checklist, but a prompt is not a substitute for the approved identity record.

## 5. Procedure

### 5.1 Confirm project scope (CG0)

1. Confirm `project_id` and the minimal Project Brief version; summarize the intended readers and tentative series direction.
2. Open a dedicated character conversation and explain the goal: a reusable identity plus bible and visual sheet. The first slice develops one primary character here.
3. Reflect any existing wishes, ask one meaningful next question, and explain appearance/identity versus pose/expression reference purposes before requesting material. References are optional; preserve the Stage 01 scope/version or record a no-reference choice.
4. Show what is understood, what remains undecided, and what the next candidate will test. Do not demand all identity fields or a complete strategy upfront.
5. A human reviews the bounded scope; technical CG codes and artifact IDs remain in a secondary details view.

### 5.2 Translate references into project-safe constraints

Separate:

- source facts;
- abstract structural observations;
- project decisions;
- hypotheses to validate.

Link each derived constraint to its reference ID/version and stated purpose. Show the user what the source informed and what came from their own direction. Story material may explain a character's behavior or emotional intent when relevant, but must not automatically become a visual-style target.

Do not copy names, costumes, facial designs, logos, distinctive props, text, panels, or a recognizable artist's expression. If a source is `observe_structure_only`, it may inform a general constraint such as “readable silhouette at thumbnail size,” but it may not become a visual target asset.

### 5.3 Develop identity candidates

AI may propose multiple written directions, rough thumbnails, or variation matrices. Each candidate records:

- candidate ID and version;
- the project question it addresses;
- source observation IDs, if any;
- what is original project direction versus reference-derived abstraction;
- rights/use assumptions and unknowns;
- expected production trade-offs.

Develop candidates through a short conversation: reflect the user's intent and selected references, ask only a consequential next question, then show a small number of concrete identity directions. A direction explains personality and behavior as well as appearance. The human may select, edit text directly, request targeted visual correction, or reject a direction. Do not treat image selection alone as approval of the bible/sheet.

Each user edit creates a new draft version immediately, preserves the previous candidate and exact feedback, and shows a concise before/after summary. Apply only the requested scope. Mark affected bible rules, sheet views, and any downstream strategy/story/board/draft as needing review or refresh; do not silently rewrite approved identity or regenerate unrelated assets. Return rejected work to the relevant conversation with its reason attached. Unselected candidates remain traceable when they contain useful decisions or failure evidence.

### 5.4 Write the character bible

The bible must define the character's role, identity invariants, behavior, voice, controlled variation, exclusions, and validation examples. It should be usable by a writer, storyboard artist, retoucher, and image-generation operator without requiring them to infer the character from a moodboard.

Write it from the selected and user-revised direction, linking rules to candidate versions, source observations, and confirmed user choices. An AI suggestion remains proposed until reviewed; a one-off correction becomes a reusable preference only when the user confirms that scope.

### 5.5 Define and produce the character sheet

D-0032 is an assistant recommendation awaiting product-direction review. Its proposed first useful package is a group of reviewable assets, not one crowded generated canvas:

- a visual identity summary: silhouette, proportions, palette, distinctive project-owned cues, and traits that must not change;
- full-body front, three-quarter, profile, and back views;
- six core expressions, including a neutral baseline;
- three characteristic acting poses that express how this character reacts or moves;
- a small-size silhouette/readability check.

The four listed views, six expressions, and three poses are proposed counts, not accepted minima or validation thresholds. The user decides the useful coverage during review; record the selected requirements and exact versions separately from this recommendation. Do not invent an accepted count. Keep the visuals consistent with the behavior/voice bible. A missing sheet or a missing component in the human-selected scope is `missing` and blocks final CG2 handoff; a placeholder can support specification or draft exploration only. Human correction or direct drawing remains a supported path when generated views drift. No sheet is produced in the current specification-only work.

### 5.6 Validate and request approval (CG1/CG2)

Run the checklist against the exact bible and sheet versions and the human-selected coverage. Review at normal size and the smallest known expected display size; unknown future episode dimensions remain explicit. Show behavior/voice and visuals together so the user can correct disagreement. Record failures by invariant and create a new version after correction. The human confirms both exact bible and sheet versions; a selected image, placeholder, or passing checklist is insufficient. The interface uses plain actions such as “확인”, “수정 요청”, and “이 방향은 사용하지 않음”, explaining what proceeds or needs refresh.

## 6. Tools and AI techniques

### AI may assist with

- extracting candidate identity constraints from approved structural observations;
- generating written character alternatives and controlled-variation tables;
- producing non-final thumbnails or consistency test variations;
- checking completeness, terminology consistency, and checklist coverage;
- comparing a candidate against the written invariants.

### Human must perform or approve

- the character's role, identity, and project fit;
- the distinction between an abstract observation and copied expression;
- rights/use decisions for supplied or generated references;
- the final invariants, forbidden traits, bible, and character sheet;
- approval or rework of the exact version.

Any generated visual records its model, workflow, prompt, seed, input references, tool versions, and unknowns when available. Missing provenance is not filled by inference.

## 7. Outputs and artifact contract

The canonical Stage 02 package is project-scoped and normally contains:

- `character-bible.md` — human-readable identity and behavior contract;
- `character-sheet.md` — human-selected coverage, exact visual asset versions, approved references, and test notes;
- versioned candidate comparisons and user feedback/edit records, with links from bible rules and sheet changes to their sources;
- `character-record.json` — structured identity, version, approval, and provenance record.

For the local MVP, character sheets and visual binaries use the app-managed project asset store and exact asset/version IDs; binary payloads remain outside Git. A missing or checksum-mismatched asset is recorded as unresolved and blocks dependent review.

The structured record must carry at least:

The example below illustrates the revised stage-specific character fields, not a schema-valid production record. The existing synthetic MVP schema supplies the common envelope and exact `source_artifact_refs`; minimal creation, conversation/edit trace, and bible/sheet coverage confirmation need a scoped contract review before implementation. This document does not migrate that schema or establish accepted sheet counts.

```json
{
  "artifact_id": "character-package-project-example-v001",
  "artifact_type": "character_package",
  "project_id": "production-project-example-001",
  "character_id": "character-example-001",
  "version": "1.0.0",
  "state": "draft",
  "created_at": "YYYY-MM-DDThh:mm:ssZ",
  "created_by": "human",
  "source_artifact_ids": [
    "project-brief-v001",
    "reference-research-project-example-v001"
  ],
  "identity": {
    "role": "unknown",
    "invariants": [
      {
        "invariant_id": "inv-001",
        "category": "silhouette_and_proportions",
        "requirement": "Concrete, testable requirement",
        "evidence_or_test": "Thumbnail silhouette check",
        "severity": "must_preserve"
      }
    ],
    "controlled_variations": [],
    "forbidden_traits": []
  },
  "behavior_and_voice": {
    "goals": [],
    "temperament": [],
    "voice_rules": [],
    "unknowns": []
  },
  "bible": {
    "artifact_id": "unknown",
    "version": "unknown",
    "status": "draft"
  },
  "candidate_refs": [],
  "user_feedback_refs": [],
  "sheet": {
    "artifact_id": "unknown",
    "version": "unknown",
    "coverage_decision": "pending",
    "required_views": [],
    "status": "missing",
    "validation_notes": []
  },
  "rights_and_sources": {
    "source_reference_ids": [],
    "not_to_copy": [],
    "use_restrictions": [],
    "unknowns": []
  },
  "approval": {
    "status": "pending",
    "approver": "unknown",
    "approved_version": "unknown",
    "decision_at": "unknown",
    "notes": ""
  },
  "provenance": {
    "models": [],
    "workflows": [],
    "prompts": [],
    "seeds": [],
    "tools": [],
    "human_edits": [],
    "unknowns": []
  }
}
```

The record must not contain a reference from another project without its source project and permission/provenance record. `approval.status = approved` means the package version passed the human character gate; it does not grant reuse rights to any third-party source listed inside it.

## 8. Human approval gates

| Gate | Decision | Minimum evidence | Rework path |
|---|---|---|---|
| `CG0` Character scope | The dedicated conversation has a bounded next identity question | `project_id`, minimal Project Brief version, reference scope or no-reference choice, known restrictions | Clarify the question or request scoped Stage 01 support |
| `CG1` Identity direction | The selected character direction is original enough, project-appropriate, and testable | Candidate comparison, source restrictions, invariant draft, human decision note | Revise candidate direction or return to Stage 01 |
| `CG2` Bible and sheet | Both exact bible and visual sheet are confirmed and usable by later stages | Bible and present sheet versions, human-selected coverage, user edit record, identity checklist, validation, provenance | Missing sheet blocks handoff; revise only affected components as a new version |

The approval record names the approver, exact package version, decision, reason, timestamp, and next permitted consumer. AI confidence, visual similarity, or a passing automated checklist is supporting evidence only.

## 9. Failure and recovery

| Failure | Required response | Recovery output |
|---|---|---|
| Minimal brief is missing or input belongs to another project | Stop dependent work; preserve the project boundary | Correct input version or explicitly unapproved draft |
| Reference scope is undecided or a source is unapproved | Continue source-independent conversation; block use of that source and final dependent approval | Reviewed source or explicit no-reference scope |
| Sheet is missing or bible and visuals disagree | Keep draft status and block CG2; return to the relevant conversation | Corrected exact bible/sheet pair with user review |
| Character direction is too generic to test | Convert adjectives into observable invariants and acceptance tests | Revised identity checklist |
| Candidate is too close to a protected reference | Exclude copied traits, downgrade source use, and record the reason | New candidate based on project-owned decisions |
| Character is inconsistent across views or expressions | Identify the failed invariant and revise the bible/sheet | New package version with before/after evidence |
| Character is readable at full size but not at target size | Add a scale/crop test and simplify the identity cues | Revised sheet or documented format constraint |
| AI output invents unsupported traits | Human source and bible take precedence; mark the output as failed | Corrected variation with provenance |
| Rights or source provenance becomes uncertain | Revoke the affected source/asset from use and re-check dependent invariants | New package version with restrictions |
| Downstream storyboard or generation cannot use the sheet | Preserve the approved package and create a scoped revision | New version with changed-region and consumer notes |

Rejected and superseded packages remain traceable. A correction never silently edits the approved character identity.

## 10. Validation checklist

Before requesting `CG2`, verify:

- [ ] The exact `project_id`, Project Brief version, and Stage 01 package version are recorded.
- [ ] Entry needs only the minimal project; protagonist, tone, format, and full identity fields are developed in this independent conversation.
- [ ] Reference purposes and influence links are visible, or the reviewed scope explicitly records no references.
- [ ] Candidate selection, direct user edits, revision scope, and resulting versions are traceable; image selection alone has not approved the identity.
- [ ] The primary character scope is explicit; secondary characters are not silently included.
- [ ] Every invariant is observable, testable, and assigned a severity.
- [ ] Must-preserve, may-vary, and must-not-introduce traits are separated.
- [ ] Character behavior and voice are concrete enough to guide story and dialogue decisions.
- [ ] The sheet requirements match the target format and known readability constraints.
- [ ] D-0032 counts remain proposed until an explicit human coverage decision; checks use the selected scope.
- [ ] The sheet's visual artifact is present for CG2; missing assets remain a draft blocker.
- [ ] Each supplied or generated reference has source and provenance information.
- [ ] No protected character, text, panel, logo, or distinctive artwork has been copied.
- [ ] Rights restrictions and `not_to_copy` notes are carried into the package.
- [ ] Thumbnail, crop, expression, and required-view checks were actually inspected or marked unrun.
- [ ] The exact package version has a human approval record.
- [ ] The next consumer can identify the package without guessing or crossing project boundaries.

Automated checks may find missing fields, duplicate IDs, invalid JSON, unresolved local paths, or checklist gaps. They may not approve identity, rights, or publication.

## 11. Versioning and metadata

- Use stable IDs for `project_id`, `character_id`, package artifacts, invariants, and sheet views.
- Increment the character package version when identity invariants, behavior, voice, controlled variation, rights restrictions, or sheet requirements change.
- Preserve approved packages. Corrections create a new version and record affected consumers.
- Keep source reference versions separate from the character package version.
- Record model, workflow, prompt, seed, tool, and human-edit metadata whenever they contribute to a visual result.
- Mark unknown provenance as `unknown`; do not infer it from filenames, visual appearance, or model defaults.
- A project may have multiple character versions over time, but a content item records the exact character package version it consumed.

## 12. Handoff to later stages

Stage 03 consumes the approved character package for the same `project_id` and uses it to define account/series direction, audience/tone application, content pillars, and format constraints.

Stage 04 consumes the character package to make character actions, expressions, dialogue, and panel decisions. It must not invent a new identity trait without a documented character-package revision.

Stage 05 consumes the approved identity invariants, sheet artifact IDs, forbidden traits, and provenance restrictions as generation constraints. It may prepare prompts and workflows, but it cannot change the character bible or approve a new identity.

Every handoff includes:

- `project_id`;
- character package ID and version;
- source Project Brief and reference package versions;
- exact approved bible and sheet artifact IDs/versions; missing/blocker status identifies a draft only and does not permit final handoff;
- identity checklist and restrictions;
- unresolved risks and next consumer.

## 13. Open questions

- What minimum character-sheet views are required for each target format?
- Which identity fields should be machine-validated first, and which require human review only?
- How should project-specific character assets be stored when visual binaries become large?
- What is the approved process for adding a secondary character without expanding the first slice?
- Which visual similarity or provenance checks are useful as warnings without becoming an automated approval decision?
