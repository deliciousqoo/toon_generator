# Stage 01 — Reference research and benchmarking

## 1. Purpose

This stage turns a minimal project brief and a guided reference conversation into a traceable reference set for character creation and series development. Project creation asks only for project name, intended readers, and a tentative series direction. Character, tone, recurring subject matter, and episode format develop later; they are not prerequisites for reference work. Research may be supplemented during character creation or for a particular episode. It answers questions such as:

- What visual, narrative, and publishing patterns are relevant to the target account and format?
- Which patterns are useful to test in the first vertical slice?
- Which observations are supported by an identifiable source, and which are only hypotheses?
- What may be observed, reused, quoted, uploaded to a tool, or not used at all?

The output is a decision aid for the character, account-strategy, and storyboard stages. It is not a collection of assets to copy and it is not a claim that a reference is legally safe to reuse.

## 2. Scope and non-goals

### In scope

- Research questions developed from the intended readers, tentative series direction, and the next character or storytelling decision.
- External and internal references that can be inspected and recorded with provenance.
- Structural benchmarking of composition, alternative formats, character expression, text treatment, pacing, production effort, and series consistency.
- Rights/use classification and a human decision about how each reference may inform the project.
- A versioned reference matrix, pattern analysis, and handoff package for Stage 02 and Stage 03.

### Non-goals

- Selecting an image model, plugin, LoRA, or generation workflow. Those choices belong to Stage 05 after a storyboard and concrete generation constraints exist.
- Automatically scraping competitor accounts or collecting a large dataset.
- Reproducing protected characters, text, panels, distinctive artwork, logos, or a recognizable artist's style.
- Treating public visibility as permission to reuse, train on, upload, or publish a reference.
- Making a legal conclusion. Rights labels in this stage are operational routing decisions and must be escalated when uncertain.

Use the smallest set that answers the current question. Approximately 5–8 selected references is a research recommendation when comparison is useful, not a minimum upload count or a project-creation requirement. An explicit no-reference outcome is valid when the user chooses to develop an original direction through conversation; record that scope and do not invent evidence.

## 3. Inputs

The stage starts from a versioned minimal Project Brief. The user-facing creation inputs and the system-managed metadata are distinct:

| Field | Required content |
|---|---|
| `project_name` | User's project name |
| `audience` | Intended readers in the user's own words; a revisable hypothesis |
| `series_direction` | Short, tentative direction; may remain explicitly undecided |
| `project_id`, `brief_version`, owner/review metadata | System-managed identifiers and exact version/review record; not extra creation questions |

Do not require an account identity, primary character, fixed topic, tone, title, format, panel count, or exclusions form at project creation. The primary character is developed independently in Stage 02. Known restrictions are retained when supplied; platform safety rules for real people/personal information, impersonation, real brands, and protected characters apply without an optional avoidance field. Tone, reference questions, and readability/format constraints are progressively recorded only when relevant to the next decision. Unknown format information does not block reference or character exploration.

An unreviewed brief permits only a draft; package approval requires review of the exact brief version and the scoped research question. An undecided series direction or later-stage field is not an incomplete creation form. During specification work, all inputs are contracts and abstract examples only.

The approved reference package is project-scoped and carries `project_id` without `content_id`. A supplemental research record focused on one episode may also carry that episode's `content_id`. A reference from another project may be used only through an explicit shared-source decision that records the source project, permission basis, and provenance.

## 4. Research questions and selection criteria

### Visible reference purposes

The add-reference conversation explains the purpose before asking for material. One source may have several purposes, but each has its own permitted use and decision links:

| Purpose | Plain explanation | Consumer and boundary |
|---|---|---|
| `character_reference` | Appearance/identity, pose, or expression cues for discussing a new character | Stage 02; observation-only sources yield abstract notes, not uploadable character targets |
| `visual_storytelling_reference` | Framing, reading order, pacing, composition, or visual hierarchy to discuss | Stages 02–04 as relevant; learn structure without copying panels or distinctive expression |
| `story_material` | A user's anecdote, observation, notes, or source text supplying story subject matter | Stage 04; preserve attributed facts and emotional intent within the requested edit scope; never infer an image style from an anecdote |

Record the user's intended purpose, what may inform the result, what must not be copied, and which candidate, bible rule, series choice, or later beat/panel it influenced. Rights classification is separate from purpose: selecting a character reference never grants upload or reuse rights. Story material need not be forced into a visual benchmark matrix; keep its source/use record and pass its exact version to the episode consumer. If purpose is unclear, ask one contextual question and leave it unresolved rather than guessing.

Every selected reference must answer at least one benchmark question. Questions should be decision-shaped, for example:

- How much visual information fits the target canvas before readability drops?
- Which recurring expression, pose, or framing patterns make a character immediately legible?
- How are text, speech bubbles, captions, and sound effects placed without obscuring the action?
- What makes a single post look like part of a repeatable series?
- Which production choices are achievable in the first vertical slice with the available human time and tools?

Candidate references are selected using the following criteria, in this order:

1. **Relevance:** directly informs the target account, format, audience, or production constraint.
2. **Traceability:** has an identifiable creator/publisher, URL or repository path, reviewed item, and access date.
3. **Evidence value:** clearly demonstrates a pattern or useful contrast rather than merely being attractive.
4. **Diversity:** adds a different format, tone, composition, pacing, or production approach; redundant examples are removed.
5. **Comparability:** can be analyzed against the same questions and dimensions as the other references.
6. **Operational risk:** its use classification and source terms are understood well enough to prevent accidental reuse.
7. **Stability:** the source can reasonably be revisited; a volatile or unavailable source is marked accordingly rather than silently treated as absent.

The final set should contain both successful patterns and, where useful, a contrast or anti-pattern. A high engagement number is not evidence by itself; metrics may be recorded only when the source and measurement context are directly verified.

## 5. Analysis dimensions

The matrix uses these dimensions. A reference may leave a dimension `unknown` when the source does not support an observation.

| Dimension | What to record | What not to infer |
|---|---|---|
| Account/series system | Recurring premise, series grammar, posting unit, recognizable conventions | Audience size, conversion, or business success without verified evidence |
| Format and layout | Canvas, aspect ratio, panel count, reading order, safe area, thumbnail legibility | Hidden production specifications |
| Composition and camera | Framing, silhouette, focal point, negative space, depth, visual hierarchy | A universal rule from one example |
| Character communication | Pose, facial expression, gesture, contrast, readable identity cues | Copying a character's design or signature traits |
| Text and sound | Text amount, hierarchy, bubble/caption placement, sound-effect role, language density | Reusing wording, lettering, or distinctive dialogue |
| Color and rendering | Palette role, contrast, value grouping, line/rendering complexity | Imitating a living artist's distinctive style |
| Narrative and pacing | Setup, beat, turn, payoff, panel-to-panel information flow | Claiming the source caused a result without evidence |
| Production feasibility | Apparent number of decisions, repeatable elements, likely human touch points | Exact effort, pipeline, or model used unless documented |
| Rights and use | Source identity, visible rights signals, terms, restrictions, allowed operational use | Permission based only on public availability |

Observations are written as testable statements: `observation`, `evidence_reference_ids`, `confidence`, and `proposed implication`. Separate an observation from a recommendation and from an unverified hypothesis.

## 6. Procedure

### 6.1 Develop the research question (RG0)

1. Read the minimal Project Brief, summarize the intended readers and tentative direction, and identify the next decision the reference can inform.
2. Define inclusion, exclusion, and rights-routing rules before collecting examples.
3. Explain the reference purposes and ask only the necessary next question. The user may supply a reference, request scoped research, or proceed without one; record that choice.
4. Record a bounded research scope and any useful selected-set target. A human reviews the questions and boundaries in plain language; AI cannot approve them. Do not require a complete strategy or format form.

### 6.2 Build the candidate register

For each candidate, record the source before detailed analysis. Prefer primary or creator-controlled pages when the purpose is to understand the work itself. Use secondary commentary only when it answers a distinct research question and is labeled as such.

Do not bulk-download or mirror reference assets from the web. Record a source link and the minimum text notes needed to identify what was reviewed. If the user explicitly selects a local file and its source/use basis permits local retention, copy it into the app-managed project asset store, record its origin and checksum, and leave the original unchanged. Do not import a file whose known retention restriction forbids keeping the project copy.

### 6.3 Inspect and record evidence

Inspect the actual page or item, not only a search-result snippet. Record:

- the exact item or post reviewed;
- source identity, creator/publisher, URL or repository path, and access timestamp;
- the visible context needed to interpret the item;
- direct evidence locations such as panel number, caption, page section, or timestamp;
- observations by analysis dimension;
- unknowns, conflicting signals, and confidence.

If a link expires, requires login, redirects, or cannot be rendered, record that access issue. Do not report the content as nonexistent and do not substitute an unverified summary.

### 6.4 Compare and synthesize

1. Group observations by benchmark question and analysis dimension.
2. Identify repeated patterns only when they are supported by more than one relevant reference, unless explicitly labeled as a single-example hypothesis.
3. Mark contradictions and trade-offs, such as readability versus density or expressiveness versus production cost.
4. Convert patterns into project-safe implications: what to test, what to avoid, and what must be decided in Stage 02 or 03.
5. Keep source facts, project judgments, and open hypotheses in separate fields.

### 6.5 Make the rights/use decision (RG1)

Each reference receives an operational use classification. The classification is a routing decision, not legal advice:

| Classification | Permitted project action |
|---|---|
| `owned_or_authorized` | Reuse only within the recorded permission scope; retain the permission evidence |
| `licensed_reusable` | Reuse only under the verified license and attribution/derivative conditions |
| `public_domain_or_open` | Use only after the relevant source and license/public-domain basis is verified |
| `observe_structure_only` | Analyze abstract structure and patterns; do not copy, publish, upload, or adapt the source asset |
| `restricted_or_unknown` | Do not reuse or upload; at most record a rights-risk note and seek human/legal review |
| `do_not_use` | Exclude from the approved reference set and record the reason |

Unless `owned_or_authorized`, `licensed_reusable`, or `public_domain_or_open` is verified for the intended action, the default is `observe_structure_only` or `restricted_or_unknown`. A third-party image must not be uploaded to a generation or editing tool merely because it is publicly viewable. Any training, fine-tuning, image-to-image, or style-transfer use requires a separate, explicit rights and tool-terms decision.

### 6.6 Assemble the handoff package (RG2)

The package contains:

- a reference matrix;
- per-reference source and rights records;
- pattern analysis linked to evidence;
- decisions and proposed experiments for Stage 02/03;
- purpose and influence links for each source, plus exact-version story-material records for Stage 04 when relevant;
- unresolved questions and blocked items;
- a human approval record for the exact package version.

The package must distinguish `selected_for_analysis` from `approved_for_reuse`. Most external references will be selected for analysis only.

## 7. Tools and AI techniques

### AI may assist with

- generating candidate search terms from the approved questions;
- de-duplicating and grouping the candidate register;
- extracting visible layout or pacing observations from supplied material;
- proposing comparison dimensions and experiment ideas;
- checking that each claim links to a source and that required fields are present.

### Human must perform or approve

- the research questions, scope, and candidate inclusion;
- source interpretation when context is ambiguous;
- rights/use classification and escalation;
- the selected reference set and pattern conclusions;
- any direct reuse, upload, adaptation, or publication decision.

AI output is an analysis draft. It is not evidence until a human inspects the cited source and confirms the observation. AI must mark missing provenance or uncertain interpretation as `unknown` rather than fill gaps from plausibility.

No image model or plugin is selected by this stage. A later tool choice must cite the approved storyboard and the generation constraints it satisfies.

## 8. Outputs and artifact contract

The canonical output is a versioned research package, normally represented by:

- `reference-matrix.md` — human-readable comparison and decisions;
- `reference-records.json` — structured source, observation, rights, and provenance records;
- `01-reference-research.md` — this stage specification and its required fields.

For the local MVP, permitted source files and previews use the app-managed local asset store keyed by project and asset IDs, as specified in `docs/platform-technical-baseline.md`. Binary payloads are not committed to Git. The platform preserves imported versions and does not automatically delete them.

The structured record must carry at least:

The example below illustrates the revised stage-specific research fields, not a schema-valid production record. The existing synthetic MVP schema supplies the common envelope and exact `source_artifact_refs`, but its older Project Brief requirements have not been reconciled with minimal creation. Reference-purpose/influence fields and the no-reference path require a scoped contract review before implementation; do not interpret this document as completing that migration.

```json
{
  "artifact_id": "reference-research-project-example-v001",
  "artifact_type": "reference_research",
  "project_id": "production-project-example-001",
  "version": "1.0.0",
  "state": "draft",
  "created_at": "YYYY-MM-DDThh:mm:ssZ",
  "created_by": "human",
  "source_artifact_ids": ["project-brief-v001"],
  "scope": {
    "project_name": "Example production project",
    "project_brief_version": "project-brief-v001",
    "audience": "unknown",
    "series_direction": "unknown",
    "benchmark_questions": ["question-001"]
  },
  "references": [
    {
      "reference_id": "ref-001",
      "source": {
        "url_or_path": "https://example.invalid/item",
        "creator_or_publisher": "unknown",
        "source_type": "article",
        "reviewed_item": "exact post, page, frame, or file",
        "accessed_at": "YYYY-MM-DDThh:mm:ssZ"
      },
      "selection_reason": "question-001",
      "purposes": ["visual_storytelling_reference"],
      "intended_use": "Discuss abstract composition",
      "influence_links": [],
      "use_classification": "observe_structure_only",
      "observations": [
        {
          "dimension": "composition_and_camera",
          "observation": "Abstract structural observation",
          "evidence_locations": ["panel 1"],
          "confidence": "high",
          "proposed_implication": "Testable project implication"
        }
      ],
      "not_to_copy": ["character design", "wording", "distinctive artwork"],
      "unknowns": []
    }
  ],
  "patterns": [
    {
      "pattern_id": "pattern-001",
      "claim": "Pattern stated without copying source expression",
      "evidence_reference_ids": ["ref-001"],
      "confidence": "hypothesis",
      "tradeoffs": [],
      "next_stage_action": "Validate against character or account constraints"
    }
  ],
  "decisions": [],
  "approval": {
    "status": "pending",
    "approver": "unknown",
    "approved_version": "unknown",
    "decision_at": "unknown",
    "notes": ""
  },
  "provenance": {
    "research_tools": [],
    "ai_assistance": [],
    "human_reviewed_sources": [],
    "unknowns": []
  }
}
```

`approved_for_reuse` is never implied by `approval.status = approved`; each reference's `use_classification` controls the permitted action. Unknown values remain explicit.

## 9. Human approval gates

| Gate | Decision | Minimum evidence | Rework path |
|---|---|---|---|
| `RG0` Research scope | The next question, reference purposes, and rights-routing boundaries are understood | Reviewed minimal Project Brief, scoped question, inclusion/exclusion rules or explicit no-reference choice | Clarify only the consequential question |
| `RG1` Reference set | Each selected reference is relevant, traceable, non-redundant, and assigned a rights/use classification | Candidate register, source records, access notes, rights evidence or explicit unknown | Replace, downgrade to observation-only, or exclude the reference |
| `RG2` Handoff | Patterns are evidence-linked and actionable for Stage 02/03 | Matrix, structured records, pattern analysis, unresolved-risk list | Return to collection/analysis and create a new package version |

The approval record names the approver, exact package version, decision, reason, timestamp, and next permitted consumer. A thread message, populated matrix, or passing automated check alone is not an approval.

## 10. Failure and recovery

| Failure | Required response | Recovery output |
|---|---|---|
| Reference purpose or next decision is unclear | Ask a contextual question; do not require a full creation brief | Scoped question or recorded no-reference choice |
| Format, tone, or character is not defined yet | Keep unknowns; continue work that does not depend on them | Progressive notes for the relevant later stage |
| Source cannot be accessed or rendered | Record the access failure; do not infer absence | Replacement source or unresolved access note |
| Source identity or rights are unclear | Downgrade to `restricted_or_unknown`; do not upload/reuse | Human rights decision or excluded reference |
| Observation is supported by one weak example | Label as hypothesis and seek contrast | New evidence-linked pattern or removed claim |
| References are redundant or too broad | Reduce to the smallest set that answers the questions | New matrix version with deduplication note |
| AI analysis conflicts with visible source | Human inspection wins; preserve the conflict | Corrected observation with provenance note |
| A selected reference is later found unsafe | Preserve the old package, mark the reference revoked, and create a new version | New approved package with affected patterns rechecked |
| A downstream stage rejects the implication | Do not edit the approved package in place | New research version or a documented downstream constraint |

Rejected or superseded packages remain traceable. Corrections create a new version and identify affected reference IDs, pattern IDs, and downstream consumers.

## 11. Validation checklist

Before requesting `RG2`, verify all of the following:

- [ ] The exact input brief version is recorded.
- [ ] Creation inputs are limited to name, intended readers, and tentative series direction; later unknowns do not become entry requirements.
- [ ] Each reference has an explained purpose and intended-use boundary; story material is not treated as an image-style reference.
- [ ] Influence links identify the decisions informed, or explicitly state that the source has not yet been used; a no-reference package has a scoped human decision.
- [ ] Every selected reference has a stable ID, source, reviewed item, and access timestamp.
- [ ] Every important observation points to an evidence location and has a confidence level.
- [ ] Facts, project judgments, and hypotheses are separate.
- [ ] No unverified metrics, creator claims, or production details are presented as facts.
- [ ] Every reference has a use classification; unknown rights block reuse and upload.
- [ ] The matrix identifies what may be abstractly learned and what must not be copied.
- [ ] Repeated patterns cite more than one relevant reference or are labeled as single-example hypotheses.
- [ ] The selected set is small enough to review and diverse enough to answer the questions.
- [ ] No copied or generated binary has been added to Git without an approved storage/versioning policy.
- [ ] The package has a human approval record for the exact version.
- [ ] Stage 02 and Stage 03 can identify their required inputs without guessing.

Automated checks may report missing fields, duplicate IDs, broken local paths, malformed JSON, or unlinked claims. They may not approve rights, select references, or advance the content item.

## 12. Versioning and metadata

- Use stable IDs for the package, each reference, each observation, and each pattern.
- Increment the package version when sources, rights classification, observations, decisions, or handoff implications change.
- Preserve approved versions; do not overwrite them.
- Record tool/model names and versions when they materially contribute to a result. If unavailable, write `unknown`.
- Record the date/time of source access and the project decision date separately.
- If a source changes, disappears, or changes terms, create a new package version and re-run the affected validation.

## 13. Handoff to later stages

Stage 02 consumes the reviewed reference scope for the same `project_id`, including an explicit no-reference outcome when applicable. It can request supplementary research while exploring identity; it does not need a completed benchmark corpus before the character conversation. Final use of reference-derived constraints needs the approved exact source versions. It needs:

- the approved package ID, version, and `project_id`;
- the selected structural patterns and their evidence references;
- explicit `not_to_copy` and rights restrictions;
- character-relevant identity questions and open constraints;
- unresolved risks that can change character design.

Stage 03 consumes the same package plus the character-bible version when available. It needs the account/series patterns, format observations, audience/tone hypotheses, and proposed experiments. Neither stage may treat `observe_structure_only` references as approved source assets.

## 14. Open questions

- Which reference-purpose controls should be visible first, and which can remain contextual?
- Which format/readability constraints become necessary only after a story is settled in Stage 04?
- Which source-retention policy is approved for permitted previews, if any?
- Which schema validator and link/access check should Stage 07 automate first?
- Which rights questions require external legal review for the chosen jurisdiction and platform terms?
- How will the project record a later change to a source's availability or license terms?
