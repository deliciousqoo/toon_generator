# Stage 03 — Account concept and content strategy

## 1. Purpose

This stage develops the tentative series direction from minimal project creation into a reusable project-scoped strategy through conversation with the user. Creation asks only for project name, intended readers, and tentative series direction. Stage 02 independently develops the character. Stage 03 connects that confirmed identity and purposeful reference observations to a repeatable audience promise, behavior/voice application, and editorial choices; it does not require a complete strategy form to begin.

The output is a decision framework for Stage 04. It is not a posting calendar, a promise of audience growth, or a replacement for the project brief. It connects the project's identity to repeatable content decisions while keeping facts, hypotheses, and experiments separate.

During the specification phase, this document defines the fields, contracts, and approval rules only. It does not require an actual account, audience, series, or content idea to be selected.

## 2. Scope and non-goals

### In scope

- One project-scoped account/content direction for the first vertical slice.
- Account purpose, audience hypothesis, tone, positioning, and boundaries.
- One or more repeatable series definitions under that project account.
- Progressively developed content pillars, editorial filters, known format constraints, and optional experiment hypotheses.
- A versioned strategy package that Stage 04 can use without guessing.

### Non-goals

- Creating or registering an external platform account.
- Automatically posting, scheduling, scraping, or optimizing for engagement.
- Treating unverified competitor metrics or platform trends as facts.
- Defining the final script, panel plan, image prompt, or generation model.
- Moving project settings between production projects without explicit versioning and permission.

The first slice may contain one account direction and one initial series. The contract permits later series under the same project, but adding a new series must not silently change the approved identity or audience assumptions.

## 3. Inputs

The strategy package consumes exact, project-scoped versions:

| Input | Required information |
|---|---|
| `project_id` | Stable production-project identifier |
| Project Brief | Exact minimal artifact ID/version: project name, intended readers, and tentative series direction; no protagonist, fixed topic, tone, title, panel count, or exclusions form is required at creation |
| Stage 01 package | Exact reviewed reference scope/package, purpose and influence links, observations, restrictions, open questions, or explicit no-reference outcome |
| Stage 02 package | For final handoff, approved character package with exact bible/sheet versions, identity invariants, behavior/voice rules, and forbidden traits; initial strategy discussion may use a clearly labeled draft |
| Existing strategy | Optional previous strategy version and explicit revision scope |
| Platform/format constraints | Known channel rules, canvas limits, accessibility, language, publication limitations, and unknowns |

If Stage 01 or Stage 02 is missing, unapproved, belongs to another `project_id`, or has unresolved restrictions that affect strategy, the package may remain a draft but cannot pass the strategy gate. The concrete handoff records the Project Brief, Stage 01, and Stage 02 artifact IDs/versions in named fields; a free-form source list must not be the only way to identify the inputs.

Tentative direction, tone, recurring subject matter, and format may stay open while the conversation develops. Only unresolved information necessary for the current decision blocks that decision. Platform rules for real people/personal information, impersonation, real brands, and protected characters remain enforced; users need not fill in an optional safety-exclusions form. Known project-specific restrictions are carried forward when supplied.

## 4. Strategy model

### 4.1 Account direction

The account direction explains the project's durable promise without reducing it to a slogan. It records:

- the problem, feeling, or interest the content serves;
- the role of the primary character in delivering that promise;
- the intended audience and the evidence or assumptions behind it;
- the desired tone and unacceptable tonal boundaries;
- the account's distinctiveness hypothesis;
- what the account will not attempt.

An audience is a hypothesis until supported by project evidence. Demographics, platform behavior, market claims, and performance expectations must be labeled as assumptions unless directly verified.

### 4.2 Series definition

A series is a repeatable content pattern under one project account. Each series defines:

- `series_id` and version;
- its purpose and audience relationship;
- recurring premise or situation;
- character role and behavior constraints;
- narrative unit or beat pattern;
- supported format families, length range, and project-level editorial constraints;
- text and visual conventions;
- acceptable variation and anti-patterns;
- production effort and human review points;
- success signals to observe, without promising a metric.

The series is not an individual content item. A content item may instantiate a series version and may record a scoped exception, but it cannot silently rewrite the series contract.

The strategy records known format/readability boundaries without requiring a fixed layout or length to confirm the series direction. Stage 04 first settles a story from the episode conversation, then proposes one frame or multiple panels and a reasoned cut count/layout using permitted structural references. Unknown format remains `unknown` until that decision. If an episode proposal conflicts with a known series rule, explain the conflict and wait for a scoped human choice.

### 4.3 Content pillars

Content pillars are durable topic or emotional lanes that help select ideas. A pillar must state:

- the audience need or project promise it serves;
- typical premises and exclusions;
- its relationship to the character identity;
- appropriate format or pacing;
- evidence or hypothesis status;
- a testable example or acceptance question.

Pillars should be few enough to guide decisions. They may start as one working audience promise and grow when conversation or repeated production shows a need. Do not require a fixed topic inventory, test episode, or content calendar before the user can review an initial direction. Label proposed pillars and use acceptance questions instead of inventing concrete episodes during specification work.

### 4.4 Format and editorial constraints

The strategy records constraints that Stage 04 must honor:

- supported canvas/layout families, reading-order principles, and crop-safety rules;
- project-level format limits and what an episode may vary without revising the strategy;
- text amount, language, readability, and accessibility;
- recurring visual grammar and allowed variation;
- emotional intensity and subject exclusions;
- publication metadata or caption boundaries;
- rights, brand, privacy, and platform restrictions.

Unknown constraints remain `unknown`. They are not filled with common platform defaults or treated as mandatory upfront questions. A missing episode cut count, title, or canvas does not block project-level direction approval; unresolved rights or a known contradictory constraint blocks the affected use.

## 5. Procedure

### 5.1 Confirm project scope (SG0)

1. Confirm `project_id` and the exact Project Brief, Stage 01, and Stage 02 versions.
2. Summarize the intended readers and tentative series direction in the user's words; identify only the next consequential series decision.
3. Separate project-level defaults from future per-content overrides.
4. List unresolved audience, tone, format, rights, or production questions.
5. Ask one useful next question and show a current direction draft. A human reviews the scope before alternatives are selected; SG codes and internal IDs remain under details, not normal creative controls.

### 5.2 Synthesize evidence into hypotheses

Use Stage 01 patterns and Stage 02 identity constraints as inputs, not as automatic conclusions. For each strategic claim, record:

- the claim;
- supporting reference or project artifact IDs;
- whether it is a fact, interpretation, or hypothesis;
- the trade-off it creates;
- the experiment or decision it enables;
- confidence and unresolved risks.

Do not convert a visible pattern into a claim about popularity, conversion, or platform ranking without direct evidence. Do not define the project by copying a reference account's name, character, text, series premise, or distinctive presentation.

### 5.3 Define account direction

Write the account direction in a form that can reject or accept ideas. A useful direction specifies what belongs, why it belongs, and what is outside the boundary. The human selects the final direction from AI-assisted alternatives or writes it directly.

Develop tone and recurring subjects here from the character's confirmed behavior/voice and the user's feedback; do not promote an initial hypothesis into a fact. For each reference-derived suggestion, show its source purpose and the decision it informs. Character cues constrain identity, visual/storytelling references inform abstract narrative structure, and anecdotes/source text remain story material for Stage 04 rather than image-style inputs.

### 5.4 Define series candidates

Propose only as many series candidates as are needed to test the account direction. Compare them using:

- fit with the Project Brief and character package;
- ability to produce multiple distinct content items;
- clarity at the target format and reading time;
- human editing and QA burden;
- rights and originality risk;
- learnings the first slice can produce.

Select one initial series for the first vertical slice unless a documented decision explicitly requires more. Preserve rejected candidates and reasons when they contain useful evidence.

Allow natural-language feedback and direct text edits. Each scoped change creates a new draft version immediately and a concise before/after summary; preserve the previous version and exact user feedback. Mark only affected series rules and downstream stories/boards/drafts as needing review or refresh. A direction change cannot silently redesign the approved character: request a separate Stage 02 revision when identity must change. Save feedback as a recurring preference only after the user confirms its reuse scope.

### 5.5 Define pillars and editorial filters

Turn the selected direction into a small set of content pillars and a decision filter. The filter should help later work answer:

- Does this idea serve the project promise?
- Is the character behaving within the approved identity?
- Does the premise fit a selected series?
- Can the idea communicate within the target format?
- Does it avoid the project's excluded topics and rights risks?
- Is the production effort appropriate for the first slice?

### 5.6 Define experiments and measurement boundaries

The first slice is a learning exercise, not a growth guarantee. Record observable signals such as completion of the intended read, human review findings, production time, rework reasons, or qualitative feedback when available. Do not invent baseline numbers or claim causation from one result.

An experiment record names the hypothesis, input version, change, observation method, decision threshold if one exists, and next action. A result may update the strategy only through a new version and human review.

### 5.7 Package and approve (SG1/SG2)

Assemble the account direction, selected series, working pillars, known constraints, optional experiment list, and open risks. Validate exact input versions, project boundaries, and consequential restrictions. Later episode fields may be explicit unknowns with a named decision point. A human approves the exact package version before Stage 04 consumes it.

## 6. Tools and AI techniques

### AI may assist with

- turning approved observations into strategy alternatives;
- comparing series candidates against explicit criteria;
- generating premise and pillar examples;
- finding contradictions, missing constraints, or duplicate content lanes;
- checking that claims link to evidence and that the package is internally consistent;
- drafting experiment plans and acceptance questions.

### Human must perform or approve

- account purpose, audience boundaries, and tone;
- the distinction between evidence, interpretation, and hypothesis;
- series selection and project exclusions;
- rights, brand, privacy, and publication constraints;
- final strategy approval and any version that changes the project promise.

AI suggestions are drafts. They cannot authorize an external account, promise performance, approve publication, or change the project or character identity.

## 7. Outputs and artifact contract

The canonical strategy package is project-scoped and normally contains:

- `account-strategy.md` — account direction, audience/tone, boundaries, and decisions;
- `series-definition.md` — selected series contract and allowed variation;
- `strategy-record.json` — structured versions, evidence, constraints, pillars, experiments, and approval.

The package must identify the exact `project_id`, Project Brief version, Stage 01 version, and Stage 02 version it consumed. Large media uses the app-managed local project asset store and remains outside Git; external analytics exports are not part of the local MVP.

The structured record must carry at least:

The example below illustrates the revised stage-specific strategy fields, not a schema-valid production record. The existing synthetic MVP schema supplies the common envelope and exact `source_artifact_refs`; its old Project Brief requirements, deferred series fields, reference-purpose links, and user revision trace need a scoped contract review before implementation. This document does not migrate that schema.

```json
{
  "artifact_id": "account-strategy-project-example-v001",
  "artifact_type": "account_strategy",
  "project_id": "production-project-example-001",
  "account_id": "account-example-001",
  "version": "1.0.0",
  "state": "draft",
  "created_at": "YYYY-MM-DDThh:mm:ssZ",
  "created_by": "human",
  "owner": "human",
  "input_versions": {
    "project_brief": "project-brief-v001",
    "stage_01_reference_research": "reference-research-project-example-v001",
    "stage_02_character_package": "character-package-project-example-v001"
  },
  "source_artifact_ids": [
    "project-brief-v001",
    "reference-research-project-example-v001",
    "character-package-project-example-v001"
  ],
  "account_direction": {
    "purpose": "unknown",
    "primary_character_role": "unknown",
    "audience_hypothesis": "unknown",
    "tone": [],
    "boundaries": [],
    "distinctiveness_hypothesis": "unknown",
    "not_for": [],
    "evidence_links": [],
    "unknowns": []
  },
  "content_pillars": [
    {
      "pillar_id": "pillar-001",
      "name": "unknown",
      "audience_need": "unknown",
      "premise_types": [],
      "exclusions": [],
      "character_application": [],
      "format_notes": [],
      "claim_type": "hypothesis",
      "testable_example": "unknown",
      "acceptance_question": "unknown",
      "status": "hypothesis",
      "evidence_artifact_ids": []
    }
  ],
  "selected_series": {
    "series_id": "unknown",
    "version": "unknown",
    "selection_rationale": "unknown"
  },
  "series": [
    {
      "series_id": "series-001",
      "version": "1.0.0",
      "name": "unknown",
      "purpose": "unknown",
      "audience_relationship": "unknown",
      "recurring_premise": "unknown",
      "beat_pattern": [],
      "character_constraints": [],
      "supported_formats": ["unknown"],
      "target_length": "unknown",
      "format_constraints": [],
      "text_and_visual_conventions": [],
      "allowed_variation": [],
      "anti_patterns": [],
      "production_effort": "unknown",
      "review_points": [],
      "success_signals": [],
      "status": "candidate"
    }
  ],
  "editorial_constraints": {
    "supported_formats": ["unknown"],
    "text_and_readability": [],
    "subject_exclusions": [],
    "rights_and_brand_rules": [],
    "accessibility": [],
    "unknowns": []
  },
  "experiments": [],
  "open_risks": [],
  "approval": {
    "gate": "SG2",
    "status": "pending",
    "approver": "unknown",
    "approved_version": "unknown",
    "decision_at": "unknown",
    "notes": "",
    "next_consumer": "stage-04-storyboard"
  },
  "validation": {
    "status": "not_run",
    "checked_at": "unknown",
    "checks": [],
    "notes": []
  },
  "next_consumer": "stage-04-storyboard",
  "provenance": {
    "evidence_artifact_ids": [],
    "ai_assistance": [],
    "human_decisions": [],
    "cross_project_sources": [],
    "unknowns": []
  }
}
```

`audience_hypothesis` and `distinctiveness_hypothesis` are not confirmed market facts. A selected series is not automatically approved for every future content item; the item records the exact series version it consumes.
`account_id` and all nested pillars, series, experiments, and constraints inherit the containing `project_id`; cross-project evidence additionally records its source project, permission basis, and provenance. The `state` field describes package lifecycle (`draft|approved|rework|superseded`), while `approval.status` records the human gate decision.

## 8. Human approval gates

| Gate | Decision | Minimum evidence | Rework path |
|---|---|---|---|
| `SG0` Strategy scope | The project, inputs, decisions, and first-slice boundaries are clear | `project_id`, input versions, scope, unresolved questions | Return to Project Brief, Stage 01, or Stage 02 |
| `SG1` Account and series direction | The account promise, audience hypothesis, tone, and initial series fit the project and character | Direction draft, candidate comparison, evidence/hypothesis labels, exclusions | Revise direction or reject the series candidate |
| `SG2` Handoff package | Reviewed series direction and character application can guide Stage 04, with deferred episode choices explicit | Exact brief/reference scope/character versions, strategy and selected series, known restrictions, labeled hypotheses/unknowns, validation and provenance | Revise affected direction; unresolved identity returns to Stage 02 |

Approval is version-specific and human-owned. A completed template, AI recommendation, or unverified analytics claim is not an approval record.

Normal review actions are “확인”, “수정 요청”, or “이 방향은 사용하지 않음”, with a plain explanation of what advances and what needs refresh. These actions retain exact-version records internally; the user does not operate gate codes or queue fields.

## 9. Failure and recovery

| Failure | Required response | Recovery output |
|---|---|---|
| Project or input package is missing/unapproved | Stop the strategy gate and record the blocker | Correct input version or an explicitly unapproved draft |
| Direction is too broad to reject ideas | Convert it into boundaries, filters, and acceptance questions | Revised account direction |
| Audience claim is unsupported | Mark it as a hypothesis or remove it | Evidence-linked hypothesis with experiment plan |
| Series depends on copied source expression | Remove the dependency and rework the premise | Project-owned series definition |
| Series cannot produce distinct items | Retire it or narrow the premise and record why | New candidate or revised selected series |
| Strategy conflicts with character invariants | Return to account/series direction or create a character revision only when identity must change | New strategy version or separately approved character version |
| Episode format/length is unknown | Defer the choice until Stage 04 has a coherent story; keep project direction review available | Explicit unknown and named later decision |
| Known constraints contradict the proposed use | Explain the conflict and block that use; ask only the necessary question | Scoped human choice or revised strategy |
| Later evidence invalidates a strategy claim | Preserve the old version, mark the claim superseded, and re-evaluate dependent pillars/series | New strategy version with impact notes |

Never overwrite an approved strategy to hide a failed experiment. The content item or experiment records the strategy version it used.

## 10. Validation checklist

Before requesting `SG2`, verify:

- [ ] The exact `project_id`, Project Brief, Stage 01, and Stage 02 versions are recorded.
- [ ] Minimal creation needs only name, intended readers, and tentative series direction; no full strategy form has been added as an entry condition.
- [ ] Reference purposes and influence links are carried forward, including explicit no-reference decisions where applicable.
- [ ] User edits preserve previous versions, explain changed choices, and identify affected downstream work.
- [ ] The named exact input references (`source_artifact_refs`) and every input's `project_id` agree.
- [ ] The account direction is project-scoped and does not imply platform-global settings.
- [ ] The primary character's role in the account direction is explicit.
- [ ] Audience, market, and performance claims are labeled as facts, interpretations, or hypotheses.
- [ ] Tone and known boundaries/restrictions are recorded; deferred choices and accessibility unknowns have a named later consumer.
- [ ] Content pillars are few enough to guide decisions and each has an audience need, claim status, evidence, and a testable example or acceptance question.
- [ ] The intended initial series is identified by `selected_series.series_id` and version, with a repeatable direction and character application; beat/format/length/convention/effort choices are reviewed values, proposed hypotheses, or explicit unknowns with later decision points.
- [ ] Character behavior and identity constraints are compatible with the strategy.
- [ ] Rights, brand, privacy, and source restrictions are carried forward.
- [ ] No copied character, wording, series premise, distinctive artwork, or unverified competitor metric is presented as a project decision.
- [ ] Future per-content overrides are distinguished from project-level defaults.
- [ ] Experiments identify what will be observed and do not promise a result.
- [ ] The package has a human approval record for the exact version.
- [ ] Owner, validation result, and next consumer are recorded for the handoff.
- [ ] Stage 04 can select a strategy and series version without guessing.

Automated checks may find missing fields, duplicate IDs, invalid JSON, unlinked evidence, contradictory constraints, or incomplete series records. They may not approve strategy, rights, or publication.

## 11. Versioning and metadata

- Use stable IDs for `project_id`, strategy package, pillars, series, constraints, and experiments.
- Increment the strategy version when account purpose, audience boundaries, tone, pillars, series rules, or format constraints change.
- Preserve approved versions; create a new version for corrections, experiments, or changed evidence.
- A content item records the exact strategy and series versions it consumed.
- Record source artifact versions and decision dates separately.
- Record AI assistance, evidence links, human decisions, and unknowns; do not infer missing analytics or platform behavior.
- If a project is duplicated, the new project receives a new `project_id` and explicit source/clone provenance rather than sharing mutable records.

## 12. Handoff to later stages

Stage 04 consumes the approved strategy package for the same `project_id`. It needs:

- account ID and project boundary;
- account direction and boundaries;
- selected series ID/version;
- content pillars and editorial filters;
- character package ID/version;
- known format and text/readability constraints, plus deferred choices; Stage 04 settles the story before proposing exact episode format and cut count;
- exclusions, rights restrictions, and unresolved risks;
- experiment or validation questions relevant to the next content item.

Stage 05 may later use the strategy's format and editorial constraints, but it cannot use the strategy package to bypass storyboard or character approval. Stage 06/07 may use experiment and QA fields as evidence, but they cannot silently rewrite account direction.

Every handoff identifies `project_id`, the exact strategy package version, source package versions, owner, approval record/condition, validation result, unresolved risks, and next consumer. Child records do not become portable across projects merely because their IDs are unique.

## 13. Open questions

- Which series preferences may be saved for future reuse after explicit user confirmation?
- Should a project support multiple accounts, or should each account receive its own production project?
- Which format constraints are global platform rules and which belong only to a project or series?
- What qualitative feedback format should the first vertical slice use?
- Which strategy checks should Stage 07 automate without turning hypotheses into false facts?
