# Stage 04 — Story and storyboard production

> **Current direction:** D-0035 resumes the Stage 04 synthetic technical slice under the [P0 implementation baseline](../p0-implementation-baseline.md). Use the [product direction](../product-direction-revision.md) and [decision pack](../preimplementation-decision-pack.md) when older input tables require a complete episode brief up front. A synthetic character fixture is allowed for this technical slice; real episodes require the independent Stage 02 character package. Developer fixtures do not satisfy visual creative acceptance.

## 1. Purpose

This stage turns one Episode Brief into a reviewable story and storyboard that Stage 05 can consume without guessing. An episode may start from a short topic or request, in which case AI may propose a story direction for human selection, or from a developed story/script, in which case its intent and dialogue are preserved unless a change is requested. The storyboard defines narrative intent, beat structure, variable panel/layout choice, character actions, expressions, dialogue, camera, background, text placement, and continuity for one episode.

The current work is `platform_build` under D-0035. Implement these contracts with synthetic project/character/series inputs through the additive studio v2 API. The formal stage handoff remains the target for model-backed creative work; implementing and testing a deterministic fixture does not establish narrative or visual quality. Real inputs require the later explicit `content_execution` transition.

The storyboard is a planning and review artifact, not an image-generation prompt and not a final visual asset. It includes written cut-by-cut decisions and low-fidelity visual roughs detailed enough to review the whole episode. Each rough must make the character's readable action, pose/expression, staging, focal event, and meaningful change from adjacent beats visible. A geometric placeholder or camera-label-only card may be used as a development fixture, but it cannot count as a usable storyboard or acceptance evidence. The rendering technique remains open; using a generative image model or external renderer requires the decision pack's separate **P1 execution gate**, covering the exact task, tool, inputs, limits, and rights/data conditions. Stage 05's `IG-C1` candidate-evaluation checkpoint does not grant that permission. Neither a prompt nor a generated image replaces the human-readable story and panel/shot decisions.

Pre-G2 review roughs may be created to prepare G2 from the selected story/G1 reference, exact character/reference versions, and pending cut decisions (or an explicitly labeled synthetic harness fixture). Their outputs remain versioned Stage 04 roughs and a storyboard overview; the rough being prepared does not require its own G2 approval first. This does not authorize execution during specification work. Post-G2 Stage 05 episode image drafts instead require the exact human-approved G2 package and execution permission covering that separate task. A rough or synthetic test asset cannot substitute for G2, become a selected Stage 05 draft automatically, or bypass G3. Record output role, exact source versions, execution-permission reference/scope, provenance, and next consumer separately; later reuse as a technical reference requires explicit role/use permission and lineage. The persisted rough/evaluation record remains pending schema reconciliation.


## 2. Scope and non-goals

### In scope

- One content item in one production project.
- An episode-scoped story record with a selected premise, narrative intent, beats, dialogue intent, and constraints.
- An episode-scoped storyboard record with ordered visual units and a reviewable rough board for the complete episode.
- Explicit separation of scene, action, emotion, dialogue, camera, background, props, text, and layout.
- Text/readability, safe-area, crop, reading-order, and continuity constraints that can be checked before image generation.
- Character identity and voice checks against an approved Stage 02 package.
- Human revision of storyboard dialogue and cut descriptions, recorded as a new version before approval.
- Versioned script/storyboard artifacts, human approval gates, failure recovery, and Stage 05 handoff.

### Non-goals

- Creating a concrete story, script, storyboard, image, prompt, or generation run during the specification phase.
- Selecting ComfyUI, ControlNet, IP-Adapter, a model, a LoRA, or another post-G2 episode image-draft workflow; those decisions belong to Stage 05 after this package is approved. Evaluation or use of pre-G2 rough tools for G2 preparation remains within the Stage 04 boundary and follows the decision pack's separate P1 execution gate.
- Replacing the account/series strategy or character bible with a per-content exception.
- Defining a posting calendar, caption strategy, audience-growth claim, or publication decision.
- Treating a reference panel, wording, character, logo, or distinctive composition as a source to copy.
- Providing an in-app drawing or raster-image editing tool for storyboard thumbnails.
- Automatically approving a story, storyboard, character identity, rights decision, or publication.
- Expanding the first slice into a cast, world, animation project, or multi-account system without a separate decision.

The contract permits a storyboard to contain more than one character or scene when the approved project and content brief require it. A secondary character, recurring prop, or new identity trait must be explicit, project-scoped, and reviewed; it must not be smuggled in through a panel description.

### Conversational working rules

- Start with any convenient rough input: a short topic, anecdote, observation, reference material, or existing story/script. Do not require a title, tone matrix, format, panel count, or complete brief.
- First show a concise understanding of the input and what remains unclear. Ask at most one consequential question at a time; if the agent can safely draft alternatives, do that instead of asking the user to fill a form.
- Settle the actual story before choosing one-frame/multi-panel format or cut count. Story alternatives contain a concrete premise, ordered beats, character actions, emotional turn, and payoff—not abstract labels alone.
- Preserve user-provided story and dialogue outside the requested edit scope. Every correction creates a visible new version, explains what changed, and refreshes only affected descendants.
- Stage 07 owns the generator/evaluator/validator loop and its bounded revision policy. D-0032 recommends at most two targeted creative revisions after the initial draft; this number is a proposal awaiting review, not an accepted default. A missing accepted limit blocks unattended iteration, while a user-requested scoped revision can still be prepared without inferring permission for further rounds.

This is a user-flow rule, not permission to populate a production `content_id` during specification work.

## 3. Inputs

Stage 04 accepts exact, versioned inputs. A file being present is not enough: the referenced artifact must be approved for the role stated below, must belong to the same `project_id`, and must remain traceable in the output.

| Input | Required information | Minimum status before the gate |
|---|---|---|
| `project_id` | Stable production-project identifier and content boundary | Present and consistent across every input |
| Episode Brief | `content_id`, request/intent, supplied short topic, anecdote, observation, reference, or concrete original story/script; source/reference IDs and versions when applicable, optional format request, known constraints, and open questions | Built progressively from conversation; a complete form is not an entry requirement; the item is in `idea` or an explicitly bounded draft |
| Project Brief | Minimal project identity, audience/target hypothesis, tentative series direction, and known exclusions; character, tone, and episode format are carried by their exact later-stage packages | Human-approved version |
| Stage 03 strategy package | Account direction, selected `series_id`/version, content pillars, editorial filters, text/readability rules, rights restrictions, and open risks | Human-approved `SG2` version |
| Stage 02 character package | `character_id`, identity invariants, behavior/voice rules, forbidden traits, sheet artifact/status, and provenance restrictions | Human-approved `CG2` version; a missing sheet is a visible blocker, not an implicit approval |
| Stage 01 research package | Relevant structural observations, evidence links, `not_to_copy`, and use classifications | Approved package or explicitly linked inherited restriction |
| Existing story/storyboard | Previous artifact ID/version and scoped change request, if revising | Optional; if present, the change scope and supersession relationship are explicit |

The strategy package is the primary source for series, audience, tone, and supported-format boundaries. The character package is the primary source for identity, behavior, and voice. The Episode Brief and permitted structural observations in its references guide the format choice for this episode. Record the requested format, selected format, rationale, and whether a material ambiguity or conflict needs a human decision. If it does, stop for that decision before treating the layout as approved. References supply observations and restrictions only; they do not supply copied art or text.

If an input is missing, unapproved, inaccessible, contradictory, or owned by another project, Stage 04 may record a draft blocker or prepare a non-approved analysis. It may not pass the relevant human gate or hand the package to Stage 05 as generation-ready.

### 3.1 Input envelope

The following is the minimum structured envelope for a Stage 04 run. Values are placeholders for the contract and must be replaced by exact artifact IDs and versions during execution. `unknown` is a valid recorded value for an unresolved fact; it is not permission to guess.

```json
{
  "project_id": "production-project-example-001",
  "content_id": "content-example-001",
  "content_item": {
    "artifact_id": "content-brief-project-example-001-v001",
    "version": "1.0.0",
    "state": "idea",
    "title_or_label": "unknown",
    "change_scope": "new_content_item"
  },
  "project_brief": {
    "artifact_id": "project-brief-project-example-001-v001",
    "version": "1.0.0",
    "approval_status": "approved",
    "project_id": "production-project-example-001"
  },
  "reference_research": {
    "artifact_id": "reference-research-project-example-001-v001",
    "version": "1.0.0",
    "approval_status": "approved",
    "project_id": "production-project-example-001"
  },
  "character_package": {
    "artifact_id": "character-package-project-example-001-v001",
    "version": "1.0.0",
    "approval_status": "approved",
    "project_id": "production-project-example-001",
    "character_id": "character-example-001",
    "sheet_artifact_id": "unknown"
  },
  "strategy_package": {
    "artifact_id": "account-strategy-project-example-001-v001",
    "version": "1.0.0",
    "approval_status": "approved",
    "project_id": "production-project-example-001",
    "series_id": "series-example-001",
    "series_version": "1.0.0"
  },
  "constraints": {
    "requested_format": "unknown",
    "language": "unknown",
    "known_limits": [],
    "unknowns": []
  }
}
```

Input validation must compare every nested `project_id` with the envelope value. A content item may consume an older approved strategy or character version only when that exact version is recorded and remains valid for the content; the package must not silently resolve to the latest version.

## 4. Project and content-state boundaries

### 4.1 `project_id` is the isolation boundary

Every story, beat, panel/shot, text object, referenced artifact, validation record, approval, and provenance entry belongs to the same production project unless a separate shared-source decision is recorded. Project-local IDs are stable within that boundary and are not global mutable settings.

Stage 04 must reject or block:

- a strategy, character, reference, or content item whose `project_id` differs from the input envelope;
- a source artifact whose project ownership or permission basis is unknown when the storyboard relies on it;
- implicit cross-project copying of a premise, dialogue, character trait, panel layout, or asset;
- a “latest” lookup that loses the exact version consumed by the content item.

If a shared template or observation is later allowed, the record must include the source project, source artifact/version, permission or rights basis, transformation/abstraction decision, and a human review note. The default remains project-local.

### 4.2 Mapping to the content state machine

Stage 04 covers the `idea`, `script`, and `storyboard` portion of the content lifecycle:

```text
idea --G1 Story--> script --G2 Storyboard--> storyboard --G3 Visual draft--> ai_draft
```

`G0 Scope/bible` is a precondition for this stage. It confirms that the idea fits the accepted project, account, series, character, and format. A candidate script is not a new content state until a human selects it; a storyboard is not generation-ready until the exact package passes `G2`.

The `script` state contains the selected narrative record. The `storyboard` state contains the selected script plus its visual execution plan. A rejection names a return state, preserves the rejected artifact, and creates a new version. No approved story or storyboard is edited in place.

## 5. Story model

The script is a structured story record, optionally accompanied by human-readable prose. Prose alone is insufficient because later stages need to distinguish narrative intent from visual instructions and exact text.

### 5.1 Required story decisions

The story record defines, at minimum:

- the content item's relation to the selected series and pillar;
- a short premise/logline and the audience-facing promise;
- the emotional or communicative intent;
- the narrative structure and ordered beats;
- each beat's purpose, action, character state, and information change;
- dialogue/caption/sound-effect intent, speaker, and text status;
- target reading context, pacing, and format limits;
- exclusions, rights restrictions, and unresolved risks;
- acceptance questions that the storyboard must answer.

The record distinguishes `fact`, `project_decision`, `interpretation`, and `hypothesis` where a claim is not directly established by an approved input. A hypothesis may guide an experiment, but it is not presented as a performance guarantee.

### 5.2 Beat structure

A beat is the smallest narrative unit that changes the viewer's understanding, emotion, or expectation. A beat may map to one or more panels/shots, and one panel/shot must not silently represent multiple unrelated beats when that would make review or generation ambiguous.

The contract does not force one universal beat pattern. A story may use setup/trigger/escalation/turn/payoff, a reaction sequence, or another named pattern when the choice is recorded. Every structure must make the following reviewable:

| Beat field | Required meaning |
|---|---|
| `beat_id` | Stable ID referenced by panels/shots and text objects |
| `order` | Intended narrative order, independent of file order |
| `beat_type` | Project-defined role such as setup, turn, reaction, payoff, or `unknown` |
| `purpose` | What the beat communicates or changes |
| `action` | Observable event, not only an adjective or mood |
| `character_state_before/after` | Relevant goal, emotion, knowledge, or relationship change |
| `dialogue_intent` | Why text is needed and what it must communicate |
| `information_dependency` | What the viewer must know before or after the beat |
| `panel_or_shot_ids` | Planned visual units; empty only while the script is a draft |
| `open_questions` | Unresolved decisions that block or limit storyboard approval |

The writer must not introduce a new identity trait merely to make a beat work. If the story requires a new recurring behavior, prop, relationship, or voice rule, Stage 02 is revised first or the exception is explicitly approved as content-local and non-canonical.

### 5.3 Dialogue and text as reviewable content

Text is recorded separately from image instructions. Each text object has a stable ID, type, speaker/source, exact copy or explicit placeholder, status, reading order, placement intent, and readability constraints. A storyboard may contain `draft` wording during development, but `G2` requires human approval of the text that Stage 05 is expected to preserve unless the package explicitly marks text as a later human-overlay task.

Do not hide dialogue inside a prompt, panel description, or image reference. Do not copy wording from a reference. A sound effect is text content with its own placement and legibility decision, not an untracked decoration.

## 6. Storyboard model

The storyboard is an ordered list of visual units. A unit is a `panel` for a static multi-panel toon, a `shot` for a time-based or camera-oriented format, or an explicitly declared project-specific unit. The chosen unit type and reading order are part of the contract.

### 6.1 Panel/shot responsibilities

Each unit must keep the following concerns distinct:

| Concern | What the unit records |
|---|---|
| Scene | Setting, time/context, continuity with adjacent units |
| Visual purpose | Linked beat and the information/emotion the reader must understand from this cut; the observable evidence that carries it |
| Action | Observable character/object action and the intended focal event |
| Emotion | Before/after state, expression, gesture, and intensity if known |
| Dialogue/text | Text object IDs, speaker, exact copy/status, reading order, and purpose |
| Camera | Framing, distance, angle, focal point, crop, and movement if relevant |
| Background | Required setting cues, depth, negative space, and complexity budget |
| Character | Character ID, invariant checks, pose, facing/gaze, and allowed variation |
| Props | Required/optional objects, ownership, continuity, and rights restrictions |
| Layout | Safe area, text region, bubble/caption placement, overlap/occlusion, and crop risks |
| Transition | Relation to previous/next unit and information or motion continuity |
| Pacing | Reading pause, reaction hold, reveal timing, or compression; relation to adjacent units and why the beat is split or combined |

An image-generation operator must be able to identify what must be present, what may vary, and what must not be introduced without translating a paragraph of ambiguous prose.

### 6.2 Composition and continuity

The plan records only the composition decisions needed for the target format. It should identify the focal point, silhouette/readability requirements, subject position, gaze direction, negative space for text, and crop-sensitive regions. It must not claim a universal composition rule from a single reference.

For adjacent units, record continuity that matters to comprehension: screen/reading direction, character location, prop state, gaze/action direction, time progression, and what changed. If continuity is intentionally broken, record the transition reason.

### 6.3 Text and layout constraints

The storyboard carries format-specific constraints from Stage 03 and the Project Brief. It does not invent platform defaults. If a canvas size, safe-area margin, text limit, font size, contrast threshold, or export rule is unknown, record `unknown` and identify the decision or test that blocks approval.

At minimum, define or explicitly mark unknown:

- canvas and aspect ratio;
- panel/shot count or allowed range;
- reading order and unit numbering;
- safe area and crop behavior;
- text object types and exact copy status;
- maximum text density or character count, if applicable;
- text region, bubble/caption anchor, and occlusion rules;
- language, line-break, alignment, contrast, and accessibility constraints;
- whether text is generated in-image, added by a later overlay, or undecided;
- thumbnail/readability check size and the result status.

The storyboard may use layout zones such as `top_left`, `bottom_right`, or a project-owned coordinate system, but a zone is not a measurement unless the format contract defines its coordinates. A text object must not cover the focal action or an identity-bearing cue without an explicit human decision.

The text-mode choice remains unresolved until a human selects it. Before Stage 05 handoff, verify that Stage 05 explicitly supports the selected mode and its validation path. In-image, mixed, or `unknown` mode is a handoff blocker until that support is confirmed; do not silently convert the storyboard to overlay. The currently described Stage 05 artwork-plus-separate-text path does not settle the broader product choice. Any mode or approved wording/layout change creates a new version and reopens the affected G1/G2 review.

## 7. Procedure

### 7.1 Confirm scope and inputs (G0)

1. Resolve one `project_id` and `content_id`.
2. Confirm the exact Project Brief, Stage 01, Stage 02, and Stage 03 versions.
3. Confirm the selected series and content pillar, or record why the item is an approved exception.
4. Carry forward exclusions, `not_to_copy`, forbidden traits, rights restrictions, accessibility constraints, and open risks.
5. Check that the project has an approved primary-character package and that the episode's format choice can vary within the project strategy.
6. Record missing or contradictory inputs before drafting. A human accepts the scope before story selection.

### 7.2 Draft and select the story (G1)

1. Accept a short topic, anecdote, observation, permitted reference, or concrete original story/script. Restate the core event, intended emotion/point, and preserved wording; distinguish supplied facts from proposed interpretation. Ask one consequential question at a time when the core is unclear. Build the Episode Brief from this conversation rather than requiring it up front.
2. For rough inputs, prepare story-direction candidates with observable events and a payoff without changing the account promise or character identity. For developed stories/dialogue, preserve everything outside the requested transformation. References guide permitted structural observations and never supply copied story text or panels.
3. For each candidate, record the series/pillar fit, audience promise, beat pattern, production trade-offs, rights risks, and unanswered questions.
4. Separate premise, beats, dialogue intent, and visual assumptions. Leave cut count and layout undecided; a user-supplied format is recorded as a constraint rather than treated as a reason to approve an unfinished story.
5. Check character action/voice against the approved character package and source-derived ideas against permitted abstract observations.
6. A human confirms the exact story version at G1. Preserve all previous candidates and decisions. Do not propose the episode's cut format/count or dispatch storyboard planning until this story decision is recorded.

### 7.3 Convert the selected story into a storyboard (G2 preparation)

1. Resolve the exact G1-confirmed story first. Then propose a single-frame, multi-panel, or other supported layout and cut count, explaining how the beats, reveal, reading rhythm, request, and permitted references support it. Record alternatives and human selection before fixing the board; an unresolved choice remains proposed. If a format constraint requires narrative changes, return a new story version to G1.
2. Map every beat to one or more ordered panels/shots.
3. For each unit, fill visual purpose, scene, observable action, expression/gesture, dialogue/text IDs, composition/camera, subject placement, gaze direction and target, background, character constraints, props, pacing, dialogue space, and continuity. A mood label or generic pose is insufficient to communicate a visual beat.
4. Assign text objects to a reading order and a placement zone; mark exact copy as draft or approved.
5. Use Level 1 beat thumbnails as the default rough for each unit and create a composed overview that makes the complete reading flow reviewable. The thumbnails may stay visually sparse because the written unit record carries the scene, action/state, emotion, character/prop continuity, composition, and text responsibility needed for G2 and Stage 05. Add drawing detail only to a specific unit if its written notes and thumbnail together leave a material ambiguity.
6. Check unit count, pacing, crop safety, thumbnail legibility, and known format limits.
7. Identify which parts are generation instructions, which are later human overlay/retouch work, and which remain unknown.
8. Run deterministic completeness and consistency checks, then list unresolved risks rather than filling gaps with plausible defaults.
9. A human approves the exact story-plus-storyboard package before Stage 05 consumes it. A Level 1 thumbnail does not reduce the written handoff, validation, rights, or approval requirements.

### 7.4 Revision and supersession

When a premise, beat, text object, character behavior, panel/shot, or layout constraint changes after selection or approval, create a new artifact version. Record the changed IDs, reason, affected downstream consumers, and whether the item returns to `script` or remains in `storyboard` rework. Keep the previous version and its approval/rejection record.

The first-slice review interface lets the human edit dialogue and cut descriptions as structured fields. It does not require freehand drawing or direct editing of the rough-board image. Any edit to an approved story or storyboard creates a new version and reopens the applicable gate.

On user feedback, immediately create and present a new draft version for the affected scope, with the feedback reference, `supersedes`, changed beat/unit/text IDs, preserved references, before/after summary, and pending review status. Do not wait for an unrelated episode-wide batch. Unchanged content remains linked to its exact prior version; preserve prior drafts, roughs, reports, and decisions. If the scope is ambiguous, preserve the feedback and ask the one scope question needed before rewriting content.

Dialogue-only feedback updates that text and its affected placement/readability checks. Action, expression, composition, or gaze feedback updates the named cuts and any dependent adjacent continuity; pacing/order feedback also updates beat mapping and the episode overview. Premise, intent, payoff, or meaning changes create a new story version and reopen G1 before revising dependent format/board decisions. Refresh the composed overview from changed units and preserved units; never automatically regenerate all cuts or Stage 05 images. Stage 07 records the dependency impact, supersedes stale queued work, reruns affected checks, and reopens G2 for a changed board. Historical approvals remain attached to their old exact versions.

## 8. Tools and AI techniques

### AI may assist with

- generating premise and beat alternatives from the approved strategy and character package;
- converting a selected narrative into structured beats and panel/shot candidates;
- proposing camera, composition, pacing, and text-placement alternatives;
- detecting missing beat mappings, duplicate IDs, continuity conflicts, text overflow risks, and unsupported character traits;
- checking that reference-derived observations remain abstract and that source restrictions are carried forward;
- producing a human-readable review board from the structured record;
- preparing a list of questions for the G1/G2 review.

AI assistance must cite the input artifact versions and must mark uncertain interpretation, missing format data, and missing provenance as `unknown`. An AI-generated candidate is not a selected story, a rights decision, or an approval.

### Human must perform or approve

- scope, premise, series/pillar fit, and audience-facing intent;
- whether the story is original enough and within the reference restrictions;
- character actions, behavior, voice, and any exception to the character bible;
- exact dialogue/caption/sound-effect wording and text strategy;
- panel/shot order, readability, pacing, composition, and layout trade-offs;
- the G0, G1, and G2 decisions for the exact artifact version;
- rework routing and any change that affects downstream generation or publication risk.

Automated checks may block or request review. They may not select among story candidates, waive an unresolved rights or identity issue, approve a package, or advance the content item.

## 9. Outputs and artifact contract

The canonical execution package is episode-scoped within its owning project and may be represented by:

- `story-record.json` — selected story, beats, text intent, constraints, and story approval;
- `storyboard-record.json` — ordered visual units, layout, continuity, validation, and handoff;
- a human-readable `storyboard.md` plus a low-fidelity rough board with one view per unit and a composed full-episode overview, generated from the same structured records;
- the fictional [storyboard detail calibration example](../examples/storyboard-detail-calibration.md), used to tune review detail and not as a fixed format or real project story;
- `04-storyboard.md` — this stage specification.

The first specification pass does not create production content. The minimum persisted shape is formalized by `episode_brief` and `storyboard_package` in `docs/contracts/mvp-records-v1.schema.json`; the synthetic fixtures in `docs/contracts/fixtures/` are the intended schema-conformant examples. The stage examples below explain the richer creative fields and may omit the common machine-readable envelope.

Record the visual rough level used by the episode and any per-unit increase with its `unit_id` and reason. The default is Level 1 beat thumbnails. This records drawing density only; it does not remove any written cut fields or G2 evidence.

### 9.1 Output envelope

```json
{
  "artifact_id": "storyboard-package-production-project-example-001-content-example-001-v001",
  "artifact_type": "storyboard_package",
  "project_id": "production-project-example-001",
  "content_id": "content-example-001",
  "version": "1.0.0",
  "state": "draft",
  "created_at": "YYYY-MM-DDThh:mm:ssZ",
  "created_by": "human",
  "source_artifact_ids": [
    "content-brief-project-example-001-v001",
    "project-brief-project-example-001-v001",
    "reference-research-project-example-001-v001",
    "character-package-project-example-001-v001",
    "account-strategy-project-example-001-v001"
  ],
  "source_versions": {
    "project_brief": "1.0.0",
    "reference_research": "1.0.0",
    "character_package": "1.0.0",
    "strategy_package": "1.0.0",
    "series_id": "series-example-001",
    "series_version": "1.0.0"
  },
  "visual_detail": {
    "default_level": "level_1_beat_thumbnails",
    "unit_overrides": []
  },
  "content_scope": {
    "content_id": "content-example-001",
    "content_item_version": "1.0.0",
    "account_or_content_topic": "unknown",
    "content_pillar_id": "unknown",
    "primary_character_id": "character-example-001",
    "secondary_character_ids": [],
    "format_decision": {
      "requested_format": "unknown",
      "selected_format": "unknown",
      "rationale": "unknown",
      "human_resolution": "pending"
    },
    "language": "unknown",
    "exclusions": [],
    "unknowns": []
  },
  "story": {
    "story_id": "story-content-example-001-v001",
    "version": "1.0.0",
    "status": "candidate",
    "logline": "unknown",
    "premise": "unknown",
    "audience_promise": "unknown",
    "intent": {
      "emotion_or_effect": "unknown",
      "takeaway": "unknown",
      "success_question": "unknown"
    },
    "structure": {
      "pattern": "unknown",
      "beats": [
        {
          "beat_id": "beat-001",
          "order": 1,
          "beat_type": "unknown",
          "purpose": "unknown",
          "action": "unknown",
          "character_state_before": "unknown",
          "character_state_after": "unknown",
          "dialogue_intent": "unknown",
          "information_dependency": "unknown",
          "panel_or_shot_ids": ["unit-001"],
          "open_questions": []
        }
      ]
    },
    "text_objects": [
      {
        "text_id": "text-001",
        "kind": "dialogue",
        "speaker_or_source": "unknown",
        "copy": "unknown",
        "status": "draft",
        "purpose": "unknown",
        "reading_order": 1,
        "unknowns": []
      }
    ],
    "constraints": {
      "tone": [],
      "pacing": "unknown",
      "panel_or_shot_count": "unknown",
      "required_elements": [],
      "forbidden_elements": [],
      "rights_restrictions": [],
      "unknowns": []
    }
  },
  "storyboard": {
    "storyboard_id": "storyboard-content-example-001-v001",
    "version": "1.0.0",
    "unit_type": "panel",
    "reading_order": "unknown",
    "canvas_and_export": {
      "canvas": "unknown",
      "aspect_ratio": "unknown",
      "safe_area": "unknown",
      "crop_behavior": "unknown",
      "thumbnail_test_size": "unknown"
    },
    "units": [
      {
        "unit_id": "unit-001",
        "order": 1,
        "beat_id": "beat-001",
        "scene_id": "scene-001",
        "visual_purpose": "unknown",
        "scene": {
          "setting": "unknown",
          "time_or_context": "unknown",
          "continuity_from_previous": "unknown"
        },
        "action": "unknown",
        "emotion": {
          "state_before": "unknown",
          "state_after": "unknown",
          "expression": "unknown",
          "gesture": "unknown",
          "intensity": "unknown"
        },
        "characters": [
          {
            "character_id": "character-example-001",
            "role": "primary",
            "pose": "unknown",
            "facing_or_gaze": "unknown",
            "gaze_target": "unknown",
            "invariant_checks": [],
            "allowed_variations": [],
            "must_not_introduce": []
          }
        ],
        "camera": {
          "framing": "unknown",
          "distance": "unknown",
          "angle": "unknown",
          "focal_point": "unknown",
          "movement": "none",
          "crop_risks": []
        },
        "background": {
          "setting_cues": [],
          "depth_or_negative_space": "unknown",
          "complexity_budget": "unknown",
          "must_not_include": []
        },
        "props": [],
        "text_refs": ["text-001"],
        "pacing": {
          "reading_rhythm": "unknown",
          "hold_or_reveal": "unknown",
          "relation_to_adjacent_units": "unknown"
        },
        "layout": {
          "subject_regions": [],
          "text_regions": [],
          "dialogue_space_intent": "unknown",
          "bubble_or_caption_anchors": [],
          "occlusion_rules": [],
          "safe_area_check": "unrun",
          "readability_notes": []
        },
        "transition": {
          "from_previous": "unknown",
          "to_next": "unknown",
          "continuity_requirements": []
        },
        "generation_boundary": {
          "must_include": [],
          "may_vary": [],
          "must_avoid": [],
          "human_overlay_or_retouch": [],
          "unknowns": []
        }
      }
    ]
  },
  "text_and_layout_constraints": {
    "language": "unknown",
    "max_text_density": "unknown",
    "line_break_rules": [],
    "contrast_or_accessibility": [],
    "in_image_or_overlay": "unknown",
    "reading_order_checks": [],
    "unknowns": []
  },
  "validation": {
    "input_scope_check": "unrun",
    "id_and_reference_check": "unrun",
    "beat_mapping_check": "unrun",
    "character_identity_check": "unrun",
    "text_and_layout_check": "unrun",
    "continuity_check": "unrun",
    "rights_and_source_check": "unrun",
    "thumbnail_or_crop_check": "unrun",
    "unresolved_risks": [],
    "performed_at": "unknown",
    "performed_by": "unknown"
  },
  "approval": {
    "status": "pending",
    "gate": "G0",
    "approver": "unknown",
    "approved_version": "unknown",
    "decision_at": "unknown",
    "decision": "approved",
    "return_state": "idea",
    "reason_or_notes": ""
  },
  "provenance": {
    "source_artifact_ids": [],
    "reference_observation_ids": [],
    "ai_assistance": [],
    "models": [],
    "workflows": [],
    "prompts": [],
    "seeds": [],
    "tools": [],
    "human_decisions": [],
    "human_edits": [],
    "unknowns": []
  },
  "handoff": {
    "next_consumer": "05-image-generation",
    "required_input_status": "blocked_until_G2_approval",
    "open_risks": [],
    "affected_consumers_on_revision": []
  }
}
```

The example is a human-readable field reference, not an executable story or schema-complete persisted record. The previous local MVP persists one `storyboard_package` containing both parts. The revised contract requires separate exact G1 story and G2 package decision references even when stored together; one package-level approval cannot stand for both. The new visual-purpose, gaze-target, pacing, dialogue-space, and feedback-impact fields require later reconciliation with the persisted schema; this specification does not change that schema or claim runtime compatibility.

### 9.2 Contract rules

- `artifact_id`, `story_id`, `storyboard_id`, `beat_id`, `unit_id`, and `text_id` are stable within the project/content version and are unique within their respective collections.
- Every `beat_id` referenced by a unit exists in `story.structure.beats`.
- Every `text_id` referenced by a unit exists in `story.text_objects`; unused text objects are removed or explicitly marked as unresolved.
- Every ordered beat maps to at least one unit before `G2`; every unit maps to one beat unless the package records a deliberate transition/establishing unit.
- `copy = unknown` or `status = draft` may remain before G2, but must be resolved or explicitly assigned to later human overlay work before the package is called generation-ready.
- `approval.status = approved` is valid only for the exact package version named in `approved_version` and after a human decision. Passing validation fields alone cannot set it.
- Unknown provenance, format limits, or rights information stays in `unknowns` and may block a gate; it is never inferred from filenames, common platform defaults, or visual plausibility.
- An approved storyboard does not approve any later image, prompt, model, or publication. Stage 05 still records its own run manifest and gate.

## 10. Human approval gates

| Gate | Decision | Minimum evidence | Rework path |
|---|---|---|---|
| `G0` Scope/bible | The content item fits the project, selected strategy/series, character, target format, and source restrictions | Same-`project_id` input envelope, approved source versions, content brief, exclusions, open-risk list | Return to the content brief, Stage 01, Stage 02, or Stage 03 as appropriate |
| `G1` Story | The exact premise and script communicate a worthwhile, project-safe idea | Selected story version, series/pillar fit, beat map, character/voice checks, text intent, rights/source review | Create a new script version or return to `idea` for a new premise |
| `G2` Storyboard | The exact story can be reviewed and generated without guessing about units, actions, emotions, text, camera, background, or layout | Storyboard package, complete beat/unit/text references, readability/crop/continuity results, provenance, unresolved-risk decision | Create a new storyboard version; return to `script` when narrative changes, otherwise remain in `storyboard` rework |

The approval record names the human approver, exact artifact version, decision, timestamp, reason, and next permitted consumer. A discussion thread, populated JSON file, AI score, or automated pass is supporting evidence only.

## 11. Failure and recovery

| Failure | Required response | Recovery output |
|---|---|---|
| Project or content scope is missing or crosses `project_id` boundaries | Stop the gate; identify the conflicting record and do not merge it silently | Corrected input envelope or explicitly blocked draft |
| Strategy or character package is missing/unapproved | Do not select a story or pass G0; record the exact missing approval | Correct input version or a draft marked unapproved |
| Target format, canvas, or text limits are unknown | Preserve `unknown`, define a bounded question/test, and block affected layout decisions | Clarified constraint or explicitly limited storyboard version |
| Premise does not fit the selected series or pillar | Record the mismatch and revise the premise or request a strategy revision | New candidate/story version with decision note |
| Story requires unsupported character behavior, trait, prop, or voice | Treat the character bible as authoritative; revise the story or make a separately reviewed character change | New story version or approved scoped exception |
| Story is too broad, dense, or difficult to read at the target format | Reduce beats/text, change pacing, or revise the target constraint; do not hide overflow in a prompt | New script/storyboard version and readability result |
| Reference-derived expression, wording, panel, logo, or artwork is too close to a source | Remove or abstract the dependency, downgrade the source use, and record the reason | New project-owned story/storyboard version with updated restrictions |
| AI invents details or conflicts with the structured record | Human record takes precedence; mark the generated candidate as failed and preserve provenance | Corrected candidate with a failure note |
| Unit order, beat mapping, dialogue mapping, or continuity is incomplete | Block G2 and identify the exact missing IDs or transition | Corrected structured record and validation result |
| Text overlaps a focal action, identity cue, or unsafe crop area | Re-layout, shorten text, assign a later overlay, or accept an explicit human exception | New unit/layout version with review note |
| Downstream Stage 05 cannot use a unit or constraint | Preserve the approved package; route to storyboard rework rather than letting generation guess | New storyboard version with affected unit and consumer note |
| An approved package needs any material change | Preserve the approved version, create a new version, and reopen the affected gate | Superseding package with impacted consumers and new approval status |

Rejected, blocked, and superseded versions remain traceable. Recovery never edits an approved story or storyboard in place and never silently changes the content state.

## 12. Validation checklist

Before requesting `G2`, verify the exact package version against this checklist:

- [ ] `project_id` and `content_id` are present and consistent in every record.
- [ ] Project Brief, Stage 01, Stage 02, and Stage 03 artifact IDs and versions are recorded.
- [ ] The selected series and content pillar are identified, or the exception is explicitly recorded.
- [ ] The story has a premise, audience-facing intent, named structure, ordered beats, and acceptance question.
- [ ] Rough topic/anecdote/reference and detailed-original input paths both build a brief through conversation; supplied wording outside the change scope is preserved.
- [ ] The exact G1 story decision predates format/count proposals; the selected format explains beat coverage and pacing and is human-confirmed before board layout is fixed.
- [ ] Each beat has an observable action, character-state change or rationale, dialogue intent, and unit mapping.
- [ ] The story does not copy reference characters, wording, panels, logos, distinctive artwork, or a recognizable artist's expression.
- [ ] Character actions, expressions, voice, props, and recurring traits are compatible with the approved character package.
- [ ] The storyboard declares panel/shot unit type, reading order, and target format assumptions.
- [ ] Every unit separates scene, action, emotion, dialogue/text, camera, background, character, props, layout, and transition.
- [ ] Each cut has visual purpose, observable action, expression/gesture, composition/focal point, gaze direction/target, pacing, dialogue space, and adjacent continuity. Notes plus Level 1 roughs make the intended visual beat reviewable without invention.
- [ ] Every beat and text object is referenced correctly; IDs are unique and there are no orphaned required records.
- [ ] Text copy/status, reading order, placement zone, safe area, occlusion, and overlay responsibility are explicit.
- [ ] The chosen text mode and Stage 05 support evidence are identified; in-image/mixed/unknown handoffs remain blocked until explicitly supported, without automatic overlay conversion.
- [ ] Panel/shot count, canvas, crop behavior, and accessibility limits are known or visibly marked `unknown` with a blocker/question.
- [ ] Continuity and intentional transitions are described for adjacent units.
- [ ] Rights restrictions, `not_to_copy`, source observation IDs, and unresolved risks are carried forward.
- [ ] Schema/shape checks, reference checks, and deterministic completeness checks have been run and recorded.
- [ ] Thumbnail/crop/readability checks are actually inspected or marked `unrun`/`unknown`; neither status is treated as pass.
- [ ] AI assistance and human decisions are recorded; missing provenance is `unknown`.
- [ ] Scoped feedback immediately produces a visible new version/change summary; unchanged cut versions remain linked, prior results remain inspectable, affected checks/overview are refreshed, and stale downstream work cannot consume the new package under an old approval.
- [ ] A human approved the exact story/storyboard version for `G2`.
- [ ] Stage 05 can identify the exact package, character sheet/reference IDs, unit boundaries, text plan, constraints, and open risks without guessing.

Automated validation may report malformed JSON, duplicate IDs, missing references, inconsistent project IDs, unmapped beats, orphan text objects, or incomplete fields. It may not decide originality, rights, character identity, creative quality, or approval.

## 13. Versioning and metadata

- Use stable IDs for the content item, story, storyboard, beats, units, text objects, and source artifact references.
- Version the story and storyboard independently when possible, but retain a package version that identifies the exact pair consumed by Stage 05.
- Increment the relevant version when the premise, beat structure, dialogue/text, character behavior, unit order, camera, layout, constraints, rights restrictions, or provenance changes.
- Preserve approved and rejected versions. A correction creates a new version with `supersedes`, reason, changed IDs, affected consumers, and a new approval status.
- Record the decision date separately from source access dates and artifact creation dates.
- Record AI model, workflow, prompt, seed, tool, and human-edit metadata when they materially contribute. If a field is unavailable, record `unknown`.
- A content item records the exact strategy version, character package version, reference package version, story version, and storyboard version it consumed.
- Do not add generated binaries or copied references to Git without an approved storage/versioning policy. The storyboard may reference an external/local artifact ID and must record an inaccessible or missing artifact as unresolved.
- If a project is duplicated, assign a new `project_id` and record source/clone provenance; do not share mutable story or storyboard records.

## 14. Handoff to later stages

Stage 05 consumes the approved storyboard package for the same `project_id`. The handoff must provide:

- the exact `storyboard_package` artifact ID/version and `content_id`;
- the exact selected story version and separate G1 decision reference, plus the G2 decision bound to this package; any generative execution also requires the decision pack's P1 execution permission covering the downstream task;
- the selected strategy/series/pillar version and the exact character package/sheet version;
- the relevant Stage 01 observation IDs, `not_to_copy` rules, and rights restrictions;
- the ordered unit list with beat mapping, character IDs, action, emotion, camera, background, props, and continuity, including exact `visual_purpose`, character `facing_or_gaze`/`gaze_target`, and `pacing` fields with their source artifact/version/field references; Stage 05 carries these into the corresponding prompt and output/review mapping without inventing missing decisions;
- text objects with exact copy/status, reading order, placement responsibility, selected mode, Stage 05 mode-support evidence or blocker, and readability constraints;
- canvas, safe-area, crop, thumbnail, accessibility, and export requirements or explicit unknowns;
- generation boundaries: `must_include`, `may_vary`, `must_avoid`, and human overlay/retouch work;
- validation results, unresolved risks, approval record, provenance, and the next consumer.

Stage 05 may translate these decisions into prompts and workflows, but it may not change the story, character identity, rights classification, or layout intent without returning to Stage 04. It must create its own run manifest and visual-draft approval record. A storyboard approval is not an `ai_draft` approval.

## 15. Open questions

- Are D-0032's proposed role split and numeric creative-revision/technical-retry limits accepted, or should the review choose other bounds?
- How will separate G1/G2 decision references and the richer cut/feedback fields be reconciled with the existing persisted contract before implementation resumes?

- Which format families belong in the Project Brief envelope, and which dimensions, panel count, and export limits must be chosen per episode?
- Will the first format place text in-image, as a later overlay, or support both with separate validation paths?
- What minimum thumbnail size and accessibility thresholds should Stage 07 automate after supported formats and episode-level limits are decided?
- Which storyboard review representation is most useful for humans: a static contact sheet, an interactive board, or both?
- How should a content-local secondary character or recurring prop be promoted into the Stage 02 package when it becomes reusable?
- Which continuity checks can be deterministic without turning visual judgment into an automated approval?
- What storage/versioning policy will permit storyboard previews and generated binaries to be referenced safely?
