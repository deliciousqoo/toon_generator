# Product direction revision — 2026-10-13 feedback

## Status and authority

This document translates the user's 2026-10-13 product feedback and referenced harness discussion into the revised product direction. The stage-by-stage choices are expanded in [구현 재개 전 결정 팩](preimplementation-decision-pack.md). On 2026-10-14, the user explicitly directed the assistant to document P0 recommendations and resume implementation (D-0035). The [P0 implementation baseline](p0-implementation-baseline.md) now governs the Stage 04 synthetic technical slice. The legacy interface and deterministic output are not creative-quality acceptance evidence.

D-0035 supersedes D-0029's implementation pause. The user's 2026-10-13 local-first constraints remain: keep the app, project records, and sources local; prefer local inference; use GPU/VRAM when useful; and allow selected external generation costs and selected input transfer when needed. Each concrete provider execution still identifies its model, inputs, retention terms and limits under P1. Actual projects/content require P2. Do not constrain image hardware to the current PC or request these broad preferences again.

Where this document conflicts with the product interaction or output expectations in `docs/platform-mvp-scope.md` and Stages 01–05, this revision takes precedence until the user accepts a reconciled baseline. Backup, project isolation, version history, and human-owned creative/rights/publication decisions remain in effect unless separately changed.

Decision status is split in the [DQ classification and priority gates](preimplementation-decision-pack.md). D-0031 selects LangGraph with an explicit Python-state-machine fallback. D-0035 delegates P0 engineering defaults: four specialist roles plus the supervising orchestrator, two automatic creative rewrites and one transient technical retry. D-0032's character-sheet quantities, image candidate counts, USD 5 budget and model labels remain recommendations pending the relevant P1/P2 choices and evaluation. Human acceptance of creative results remains separate.

## 1. What was and was not carried forward

The initial pipeline discussion recommended a family of tools and techniques. They were recommendations, not installation or adoption decisions. Later decisions narrowed the first build to a local browser platform, synthetic records, and deterministic mock imagery. The project then moved into platform implementation without an explicit candidate-by-candidate evaluation connecting the original recommendations to the accepted scope.

The resulting gap is substantive: the prototype can exercise records, screens, review states, and file handling, but it does not use an image model, story model, agent loop, or storyboard-aware visual workflow to demonstrate creative quality. Its fixed story-direction labels and geometric thumbnails are mock behavior, not evidence that the story-to-board-to-image pipeline works. The user's quality and usability feedback is therefore a product-direction correction, not a request to polish the same mock flow.

| Initial proposal | Actual status in the current prototype | Revised disposition |
|---|---|---|
| Krita + Krita AI Diffusion | Not integrated | Evaluate as a human drawing, local generation, inpainting, and refinement surface after the storyboard and character-sheet needs are specified. |
| ComfyUI | Not integrated | Keep as a candidate image-workflow runtime; assess saved workflow/API execution and whether the local machine can run the selected models. |
| ControlNet / auxiliary preprocessors | Not integrated | Evaluate for translating approved pose, composition, line, or depth guidance into controllable image generation. |
| IP-Adapter / reference-image conditioning | Not integrated | Evaluate for project-owned character references and identity consistency; do not assume it guarantees identity. |
| Regional prompting, inpainting, upscaling | Not integrated | Consider for later image refinement and localized correction, once a usable base image workflow exists. |
| LoRA | Not used; production training was excluded | Defer until the character identity is stable and there is enough authorized, project-owned training material. Do not make it a prerequisite for character definition. |
| Structured story output; Markdown/JSON character and account bibles; RAG | Structured records exist, but no story LLM or retrieval pipeline is connected | Use exact-version project artifacts as the first retrieval source. Add vector search only if measured retrieval failures justify its complexity. |
| n8n / Node-RED | Not integrated | Not required for the first personal workflow. Compare only if external service and file automation needs outgrow the platform's own orchestrator. Recheck license and operating burden at selection time. |
| PostgreSQL / pgvector / MinIO / DVC / Directus | Not integrated | Multi-user or scale-out candidates only. Keep the current local storage boundary for now; do not add infrastructure to make a single-user UI look more complete. |
| Instagram publishing API | Not integrated | Out of scope. Keep the final publish action human-operated unless a later, separate decision changes it. |

The current prototype's confirmed runtime stack is FastAPI/Python, React/TypeScript/Vite, SQLite, local assets, Pillow-based deterministic mock images, JSON Schema validation, and `pyrage` for optional encrypted backups. Its proposal labels are fixed mock strings. These components implement platform mechanics; they are not the creative AI techniques listed above. This description comes from the current manifests and implementation files, not from the initial recommendations.

## 2. Product principle and platform/orchestrator relationship

The product is a personal, conversation-led toon-making workspace. The platform is still useful: it owns project materials, versions, review history, and the visible work queue. It should act as the simple control surface around an orchestrator. The orchestrator dispatches bounded specialist tasks to agents and tools, checks outputs, runs targeted feedback iterations, and returns a clear result to the user.

```text
One simple project workspace
  -> conversation and visible episode progress
  -> orchestrator / harness
       -> stage agent(s) and local tools
       -> deterministic contract checks
       -> evaluator feedback and bounded revision
  -> versioned artifacts and trace
  -> human review, change request, or acceptance
```

This is compatible with a platform. The platform provides the user-facing workspace and durable records; the orchestrator provides the agent work loop. The platform must not expose an operations console full of internal gate codes, queue fields, or implementation details as the normal creative workflow. Agent roles are logical responsibilities and do not require different vendors or models. Agent-to-agent work is mediated by the orchestrator; no open-ended, unbounded chat swarm is required.

## 3. Simpler user journey

### 3.1 Project creation

Ask only for:

1. Project name.
2. Intended readers/audience, in the user's own words.
3. Series direction, which may remain a short, revisable hypothesis.

Do not ask for the recurring protagonist, a fixed topic/concept, tone, episode title, cut format, or cut count here. Develop character identity in its own stage. Let tone and recurring subject matter emerge and be revised during work. Safety exclusions (using real people or their personal information, impersonation, real brands, and protected characters) are platform rules, not a confusing optional “do not use” form field.

### 3.2 Character creation as a first-class stage

After creating a project, guide the user through a dedicated character conversation. Ask for references and desired traits in context, one meaningful question at a time. Label each reference by purpose: appearance/identity, pose or expression, visual structure/composition, or story/source material. Explain what the selected reference can inform and show the user which decisions were derived from it.

The character workflow produces editable concept candidates, a selected project-owned identity, a written character bible, and a visual character sheet. Proposed downstream coverage includes clear views, proportions and silhouette, palette, face cues, and expression/pose examples appropriate to the project. The exact minimum contract is DQ-07; D-0032's four views, six expressions, and three poses remain recommended quantities until reviewed. The human edits/selects the identity and confirms the exact version. An image candidate is not a character approval. Character identity, visual sheet, behavior/voice, variation, and prohibited changes are all part of this stage—not a protagonist-description field in project creation.

### 3.3 References have a visible purpose

Replace an unexplained “reference drawer” with an add-reference action that asks what the material is for, with plain descriptions and examples:

- **Character reference:** an appearance or pose cue used during character design, subject to its recorded use basis.
- **Visual/storytelling reference:** an example used to discuss abstract framing, pacing, reading order, or visual hierarchy; it is not copied into the output.
- **Story material:** the user's anecdote, observation, notes, or source text that provides subject matter for an episode.

These roles are not interchangeable. An anecdote may inform story facts or emotional intent; it should not be treated as an image-style reference. Each episode output shows which reference influenced which decision. Existing source and rights restrictions remain enforced.

### 3.4 Episode work is conversational and progressive

Start an episode with a rough idea, a user-provided anecdote/source, or an existing story. Do not require a title, complete script, tone matrix, panel count, format, or a large brief up front. Continue the conversation by summarizing what is understood, asking only a necessary next question, and showing the current draft and unresolved choice.

First settle the story. Offer useful story alternatives with an actual premise, ordered beats, character action, intended emotional turn/payoff, and a short explanation of why each fits the project. Do not present generic labels such as “small setback” as if they were story options. A direction can be edited in conversation; supplied story or dialogue is preserved outside the scope the user asked to change.

Only after the story is coherent should the workflow propose whether it works as one frame or multiple panels, and suggest a cut count/layout with a reason. The user may accept, alter, or defer that format. The title is optional and can be named later.

### 3.5 Storyboard communicates the story visually

A storyboard is not a grid of shapes or a page of camera labels. Each thumbnail must show the character's readable action, pose/expression, staging, focal event, and the change from the previous beat; written notes clarify camera/framing, setting, text placement, and continuity. A sequence should communicate setup, action/reaction, turn, and payoff at a glance, with every panel serving a reason in the story. Text and lettering remain separately reviewable and may be overlaid after image generation.

Use rough thumbnails to explore and discuss the story first. Refine only the panels that are unclear or important. Review the whole sequence in order for readability, pacing, emotional progression, and whether the promised payoff lands. Do not claim that a storyboard is adequate because every schema field is present.

This direction is informed by Blender Studio's production guide, which describes storyboards as a visual exploration of angles, beats, and acting, and its Project Gold account of starting from story beats, using quick thumbnails with concise notes, iterating through feedback, then refining selected boards. These are transferable workflow principles, not a mandate to use Blender or to imitate a feature-animation pipeline. See [Blender Studio's storyboard guide](https://studio.blender.org/tools/artist-guide/pre-production/storyboard) and [Project Gold: Storyboarding in Blender](https://studio.blender.org/blog/project-gold-storyboarding-in-blender/).

### 3.6 Image draft must be story-bound

An image run must consume the selected, versioned story, character sheet, and storyboard. For each panel, carry forward the action, expression, staging, composition, character constraints, setting, and text-safe area. Record exact versions and workflow/model provenance. Review the full sequence for character identity and narrative continuity, not just whether image files exist.

The current geometric mock may remain a technical harness fixture for IDs, storage, selection, and version handling. It must be labeled as a fixture and must not be presented as a meaningful AI image or as proof that story intent reached the image. A real image workflow is a separate evaluation and authorization step.

## 4. Conversation, progress, and immediate revision behavior

Keep one active workspace per project, with a single step-by-step episode screen and one current task in focus. Use a quiet white/light background, clear typography, and only the controls needed for the current step. Avoid nested menus, decorative dashboards, dense forms, and prominent technical status panels. The main screen always answers: “Where am I?”, “What has been made?”, “What did the agent do with my input?”, “What needs my choice?”, and “What happens next?” Show the story/board/image result directly. Keep technical IDs, prompt payloads, validation details, model settings, and provenance under a secondary details view.

The user should be able to respond in natural language or make a direct edit. A change request immediately creates a new draft version, marks affected downstream outputs as needing refresh, and sends the scoped feedback to the responsible agent. Re-run only affected work. Preserve the previous version and show a concise before/after summary. A rejection returns the workflow to the relevant prior conversation with the reason attached; it does not erase work or leave a silent rejected status. An approval advances the exact version the user reviewed.

Replace RG/CG/SG jargon in the normal interface with one clear review action such as “확인”, “수정 요청”, or “이 방향은 사용하지 않음”. Internally, retain typed, exact-version review records when needed for traceability. Always state the consequence in plain language: what advances, what will be regenerated, what is preserved, and which previous choices are affected. Ask the user for decisions only when there is a consequential ambiguity or creative choice, not to make them operate the workflow engine.

## 5. Agent-orchestration contract

The orchestrator is the workflow owner; agents are bounded workers. The first technical vertical slice is Stage 04 story-to-storyboard, using a clearly labeled synthetic character package to validate the agent loop and human pause/resume before image-model work. Character creation remains a first-class stage and must be available before the first real project episode is produced. The initial orchestrator choice for the slice is LangGraph, with a simpler explicit Python state machine as the fallback if local persistence and recovery become more complex than the graph is worth. This is a bounded implementation choice, not a claim that LangGraph improves creative quality.

### 5.1 Roles

- **Conversation/brief agent:** summarizes user intent and identifies only consequential missing information.
- **Story generator:** prepares or revises structured story alternatives and can explain how each beat serves the premise.
- **Storyboard planner:** maps selected story beats to panels and produces visual thumbnails plus actionable shot/composition notes.
- **Evaluator:** critiques a specific immutable result against the supplied story, character, reference restrictions, and stage rubric; returns cited issues and suggested targeted changes. It cannot approve or reject on the user's behalf.
- **Deterministic validator:** checks schema, exact input versions, required beat/panel coverage, IDs, output files, and known project boundaries. It does not score creative quality.
- **Image workflow adapter:** later, executes a selected, versioned image workflow and returns outputs plus provenance.

These roles can share infrastructure. They must have separate instructions, permissions, and output contracts. The orchestrator passes only approved, project-scoped, exact-version inputs to each role.

### 5.2 Bounded generate–evaluate–revise loop

1. Freeze the exact input snapshot: project direction, character version, story/reference inputs, user request, stage contract, and evaluation rubric.
2. Ask the responsible generator for one versioned draft in the required structure and visual deliverables.
3. Run deterministic checks. If an input, schema, rights basis, or project boundary fails, stop and explain the blocker; do not ask the creative agent to guess around it.
4. Ask the evaluator to compare the draft with the exact source story and rubric. Each issue cites a field/panel/beat, explains its effect, and classifies severity. “Pass” can mean only that no further agent issue was found; it is not human approval.
5. If useful, send a targeted revision request to the generator. Create a new artifact version and preserve the prior draft, evaluation, prompt/workflow versions, and relationship between them.
6. Stop for human review when the user has a coherent draft, when the improvement plateaus, when evaluators conflict, or when the attempt/cost/time limit is reached. The user can accept, edit, request another bounded revision, or return to an earlier decision.

Every loop has a configurable finite attempt cap, timeout, and cost ceiling. Do not allow recursive agents to create agents or continue without a user-visible stopping point. An iteration limit is not a quality pass. If limits are reached, report what remains unresolved and let the user decide the next step.

### 5.3 Evaluation rubric for story and board

The first rubric should check: fidelity to the user's supplied idea and requested edit scope; clarity of premise and audience promise; cause-and-effect between beats; visible character action and emotional change; believable character behavior/voice against the exact character version; setup and payoff; readable panel order and pacing; whether each cut adds information; visual staging, focal event, and continuity; space for later text overlay; reference restrictions; and whether the proposed visuals can be generated or need a human drawing step.

Do not reduce this to one opaque quality score. Return concrete examples and revision instructions. A structural score or checklist can prioritize issues; only the user decides what is good enough creatively.

### 5.4 Trace and learning

Persist each user turn that changes creative direction, exact agent inputs/outputs, role/model/prompt/workflow versions where applicable, evaluator rubric/version, deterministic check results, retry relation, human feedback, and downstream invalidation. Show a human-sized summary in the UI and make technical trace available on demand.

Use prior feedback as project-scoped evidence for future proposals only when the user confirms it as a reusable preference. Do not automatically rewrite prompts, character rules, or global policies from one rejected result. Any learned preference becomes an explicit, versioned project setting that the user can inspect and undo through a new version.

## 6. Candidate tool and technique evaluation before implementation

Tool names in the initial pipeline discussion remain candidates. Before selecting an image stack, compare a small end-to-end synthetic task: one approved-style character sheet and a short storyboard with distinct actions, expressions, composition, and text-safe areas. Judge actual outputs for identity continuity, fidelity to panel intent, editability, local operation/data transfer, Korean text handling, repeatability, workflow/API integration, provenance, setup burden, GPU needs, failure recovery, and license/terms. Do not decide from feature lists alone.

The current PC's GPU was observed during earlier research, but the user explicitly said not to use it as the product baseline. Image-generation requirements must be evaluated on the intended target PC or PCs, which may be a higher-spec machine reached through Git. Keep source code and specifications portable; provide reproducible dependencies and configurable paths; keep secrets, model weights/caches, project records, references, and generated media out of Git by default. The earlier labels Gemini Nano Banana 2.1 and GPT Image 2 remain synthetic API comparison candidates alongside local workflows. This consolidation does not verify their current availability, capabilities, price, or data terms. Before any evaluation/integration, verify exact model IDs, selected-machine requirements, license, endpoint-specific training use and retention/deletion conditions, transferred inputs, and numeric spend limits. See [Krita hardware guidance](https://github.com/Acly/krita-ai-diffusion/blob/main/docs/src/content/docs/installation.mdx), [Gemini API terms](https://ai.google.dev/gemini-api/terms), and [OpenAI API data controls](https://developers.openai.com/api/docs/guides/your-data). No provider is selected or called by this specification work.

Initial candidate map:

| Stage | Technique/tool candidate | Question to answer |
|---|---|---|
| Story/continuity context | Exact-version Markdown/JSON retrieval; RAG only if needed | Can the agent reliably retrieve the current character, series, and restrictions without confusing old versions? |
| Character and panel drafts | Gemini Nano Banana 2.1 and GPT Image 2 for synthetic API comparison; ComfyUI/Krita local trial on a selected target PC | Which path preserves identity and panel intent while fitting the selected target machine, transfer boundary, editability, and cost? |
| Pose/composition control | ControlNet and suitable preprocessors | Does it improve action, framing, and silhouette from an approved sketch/pose input? |
| Character visual reference | IP-Adapter or comparable reference conditioning | Does it reduce identity drift without merely copying unwanted source features? |
| Local correction | Inpainting, regional prompting, upscaling | Are edits local, reversible, and consistent with the approved panel? |
| Manual finish and Korean text | Krita or a similarly suitable editor; deterministic text overlay | Can the user correct anatomy/details and place Korean dialogue reliably? |
| Orchestration | D-0031: Python LangGraph for the Stage 04 slice; explicit Python state machine if persistence/recovery burden outweighs benefit; Node-RED/n8n only for a later demonstrated need | Can exact-version feedback loops, local checkpoints, pause/resume, retries, gates, and provenance stay understandable and testable? |
| Scale-out storage | PostgreSQL/pgvector/object storage/DVC/Directus candidates | Is any multi-user or corpus scale problem real enough to justify this extra infrastructure? |

LoRA, hosted image providers, external reference uploads, automatic publishing, and cloud/multi-user services are not initial defaults. Evaluate separately against data rights, cost, license, privacy, and actual workload. Tool/model selection must be recorded before integration, with reasons for rejected alternatives.

## 7. Revised stage sequence

1. **P0, scope and restart:** accept the Stage 04 synthetic slice, its rubric, bounded role/revision/stop policy and technical completion criteria, then separately instruct implementation to resume. Do not reopen the already confirmed local-first, GPU, Stage 04-first, character-before-real-episode, current-PC-exclusion or Git portability choices.
2. **First technical vertical slice:** Stage 04 story → human story selection → format/cut proposal → storyboard → exact G2 review with synthetic character/series fixtures. Validate LangGraph checkpoints, version-bound feedback, downstream invalidation, bounded loops, human pause/resume, recovery and useful progress summaries. Fixture/MOCK checks prove harness behavior; readable AI thumbnails and creative quality require separately authorized model evaluation.
3. **P1, model evaluation when needed:** settle target machine for local runs, exact tools/models and licenses, permitted inputs, retention and numeric limits, then separately authorize the scoped [synthetic evaluation](synthetic-model-evaluation-plan.md). This may support character, Stage 04 thumbnails or Stage 05 drafts; it does not wait for a real episode and does not permit one.
4. **Character and project setup before real use:** accept the DQ-07 character contract, then implement the Stage 01 reference-purpose/rights conversation, Stage 02 character conversation and human edits/identity selection, and Stage 03 human series-direction selection. Each uses exact project-owned versions. The first technical slice's fixture is not a route for bypassing this journey in real use.
5. **P2, real episode entry:** platform acceptance and a separate `content_execution` instruction are required. Approved character/series/reference versions and rights/storage choices feed the same conversational Stage 04 flow. Do not request real identity, style or episode inputs during specification work.
6. **Draft and later extension:** separately authorized Stage 05 runs produce cut candidates and a composed sequence; human selection/targeted regeneration and G3 review end the first story/draft cycle. Stage 06 human polish, optional local refinement, QA/rights and human-directed export/publication preparation are later scope (P3). Stage 07 harness, Stage 08 local/Git operations and Stage 09 verified technical notes support the journey rather than advancing an episode themselves.

The active implementation pause remains until the user reviews the revised direction. This order is a specification roadmap, not a request to start the next stage automatically.

## 8. Prioritized remaining review choices

Use the [decision pack's DQ table and P0–P3 gates](preimplementation-decision-pack.md) as the consolidated review index; this section does not introduce a second approval list.

- **P0 before restarting Stage 04 implementation:** DQ-09's scope/completion criteria and DQ-06/08's role, bounded-loop and story/board rubric proposals; then explicit scope acceptance and a separate resume instruction. Model IDs, image target PC and character-sheet quantities are not blockers for a provider-free fixture/MOCK contract slice.
- **P1 before model/tool execution:** DQ-02/03/04/06/10/11's evaluation task, target local machine, exact candidate IDs/licenses, input/retention boundary, credentials and numeric time/spend limits, plus scoped execution authorization. D-0032's USD 5 is a proposal to review, not available spending permission.
- **Before character implementation / P2 before real use:** DQ-07's minimum sheet/bible contract and visible reference-purpose journey; then accepted platform, separately authorized real execution, exact human-approved project versions, rights and DQ-11 preservation/backup choices. Specific character style is a future project decision.
- **P3 later extension:** Stage 06 polish/QA/export scope and any DQ-12 expansion beyond human publishing. Reusable story/character preferences require explicit project-scoped confirmation and versioning.

The main-thread integration review compared the current Stage 01–09 work, synthetic evaluation plan, and prior MVP/technical documents against this journey. Remaining P0 acceptance decisions, schema reconciliation, and the separate P1/P2 execution gates are tracked in the [pre-implementation decision pack](preimplementation-decision-pack.md).
