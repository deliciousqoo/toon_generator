# Project thread index

Threads are discussion surfaces. This repository is the source of truth for approved specifications and decisions.

The local Stage 01–05 mock application started under D-0027 and paused for revision under D-0029. On 2026-10-14 the user explicitly resumed implementation and delegated P0 recommendations (D-0035). The current work is the Stage 04 synthetic LangGraph slice and simpler conversational workspace under [P0 implementation baseline](p0-implementation-baseline.md). Stage 01–03 specification alignment and Stage 04/05 cross-review are complete; actual character creation remains a prerequisite before real episodes. D-0033 keeps hardware independent of the current PC. D-0034 requires coherent commits and normal pushes with `[추가]` / `[수정]` / `[삭제]`. Product/creative acceptance, concrete provider execution and real-content execution remain distinct. Main-thread development coordination and the in-product orchestrator are separate responsibilities.

| ID | Thread | Specification deliverable now | Future production output (not created) | Status |
|---|---|---|---|---|
| 00 | Project governance and specification rules | `README.md`, `AGENTS.md`, `DECISIONS.md`, `docs/01-operating-rules.md` | N/A | specification complete |
| 01 | Reference research and benchmarking | `docs/stages/01-reference-research.md`, revised by `docs/product-direction-revision.md` | Clearly labeled character, visual/storytelling, and story-material references | revised specification complete; implementation later |
| 02 | Character bible and character sheet | `docs/stages/02-character.md`, revised by `docs/product-direction-revision.md` | Dedicated character conversation, project-owned bible and reusable sheet | revised specification complete; actual workflow pending |
| 03 | Account concept and content strategy | `docs/stages/03-account-strategy.md`, revised by `docs/product-direction-revision.md` | Minimal project inputs and evolving series direction; defer episode format choices | revised specification complete; implementation later |
| 04 | Story and storyboard production | `docs/stages/04-storyboard.md`, `docs/p0-implementation-baseline.md` | Conversational story development, useful visual thumbnails, bounded generator/evaluator loop | specification cross-review complete; technical implementation active |
| 05 | AI image-generation workflow | `docs/stages/05-image-generation.md`, revised by `docs/product-direction-revision.md` | Story-bound image workflow selected after candidate evaluation; human review | candidate evaluation pending |
| 06 | Human polish and QA | `docs/stages/06-polish-and-qa.md` | Follow-up retouch, optional refinement, QA/export and publication package | specification complete |
| 07 | Harness and automation | `docs/stages/07-harness-automation.md`, `docs/p0-implementation-baseline.md` | Stage 04 LangGraph slice; role workers, validation, bounded revision and trace | Stage 04 technical implementation active |
| 08 | Git and personal local platform | `docs/stages/08-git-platform.md`, `docs/platform-mvp-scope.md`, `docs/platform-technical-baseline.md` | Simple local workspace around the agent orchestrator | revised workspace active; studio v2 backup integration pending |
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

The affected specification revisions were integrated before D-0035 resumed implementation. D-0024–D-0026 still document the legacy local technical baseline, file import and history retention. Source is in `backend/` and `frontend/`, launchers in `scripts/`; implementation results and remaining gates must be reported with inspected evidence. This index records status; D-0035 and the user's direct instructions provide current implementation authority.
