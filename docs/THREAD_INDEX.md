# Project thread index

Threads are discussion surfaces. This repository is the source of truth for approved specifications and decisions.

The local Stage 01–05 mock application was started under D-0027. D-0029 pauses further implementation while the user reviews a simpler, conversation-led product direction and agent orchestration model. D-0031 records the local-first/conditional-external boundary, permission to use GPU/VRAM, and Stage 04 as the first technical vertical slice; character creation is still required before any real episode. D-0032 records proposed character/evaluation/retry defaults. D-0033 makes hardware portability a user-confirmed constraint: the current PC is not the image-generation baseline, and work may move to another PC through Git. D-0034 sets the project-wide commit/push rule for substantial work units and the `[추가]` / `[수정]` / `[삭제]` title prefixes. The current app is a prototype, not an accepted product. Read [Product direction revision](product-direction-revision.md) and the [pre-implementation decision pack](preimplementation-decision-pack.md) before treating the older interaction requirements or implementation plan as current. This does not resume implementation or select an external provider. Existing local storage, project isolation, backup, and version-history decisions remain unless separately changed.

| ID | Thread | Specification deliverable now | Future production output (not created) | Status |
|---|---|---|---|---|
| 00 | Project governance and specification rules | `README.md`, `AGENTS.md`, `DECISIONS.md`, `docs/01-operating-rules.md` | N/A | specification complete |
| 01 | Reference research and benchmarking | `docs/stages/01-reference-research.md`, revised by `docs/product-direction-revision.md` | Clearly labeled character, visual/storytelling, and story-material references | direction revision drafted |
| 02 | Character bible and character sheet | `docs/stages/02-character.md`, revised by `docs/product-direction-revision.md` | Dedicated character conversation, project-owned bible and reusable sheet | direction revision drafted |
| 03 | Account concept and content strategy | `docs/stages/03-account-strategy.md`, revised by `docs/product-direction-revision.md` | Minimal project inputs and evolving series direction; defer episode format choices | direction revision drafted |
| 04 | Story and storyboard production | `docs/stages/04-storyboard.md`, revised by `docs/product-direction-revision.md` | Conversational story development, useful visual thumbnails, bounded generator/evaluator loop | direction revision drafted |
| 05 | AI image-generation workflow | `docs/stages/05-image-generation.md`, revised by `docs/product-direction-revision.md` | Story-bound image workflow selected after candidate evaluation; human review | candidate evaluation pending |
| 06 | Human polish and QA | `docs/stages/06-polish-and-qa.md` | Follow-up retouch, optional refinement, QA/export and publication package | specification complete |
| 07 | Harness and automation | `docs/stages/07-harness-automation.md`, `docs/product-direction-revision.md`, `docs/preimplementation-decision-pack.md` | Stage 04 LangGraph-first technical slice; role-based agents, deterministic checks, bounded evaluation/revision, trace | revised draft; implementation paused |
| 08 | Git and personal local platform | `docs/stages/08-git-platform.md`, `docs/platform-mvp-scope.md`, `docs/platform-technical-baseline.md` | Simple local workspace around the agent orchestrator | prototype implemented; acceptance pending; further implementation paused |
| 09 | AI technical blog and portfolio | `docs/stages/09-technical-blog.md` | Published technical article or portfolio material | specification complete |

## Review guide

- [Specification review and follow-up guide](specification-review-guide.md): cross-stage findings, acceptance checklists, unresolved decisions, and recommended next steps. This is a review aid; it does not authorize platform code or real-content execution.
- [Pre-implementation decision pack](preimplementation-decision-pack.md): stage-by-stage tools and AI techniques, candidate status, flowchart, outstanding decisions, and implementation restart gate.
- [Synthetic model evaluation plan](synthetic-model-evaluation-plan.md): hardware-aware local/cloud candidates, synthetic-only comparison criteria, cost cap, and data-transfer boundaries; no provider calls are authorized by the plan.

## Thread closeout

Before closing a thread, record:

- accepted decisions;
- changed files;
- validation performed;
- unresolved questions;
- the next thread's required inputs.

Each Stage 05–09 specification is handled in its own chat. During `specification_only`, a chat may update specifications only; it must not create real project content, provider-generated media, executable workflow, or platform implementation. `platform_build` requires a separate explicit start instruction and synthetic fixtures. Real content requires platform acceptance and a separate explicit execution transition. Update this index when a specification has actually been reviewed and completed.

The original Stage 00–09 specification pass is complete, but D-0029 reopens the affected Stage 01–05 interactions and Stage 07 orchestration contract. D-0024–D-0026 still document the current local technical baseline, local file import, and history-retention boundaries. Runnable prototype source is in `backend/` and `frontend/`, with launcher helpers in `scripts/`; human product acceptance is pending. This index records status only and does not authorize work beyond the user's current specification-review request.
