# Predictive Advisory Implementation Backlog (Phase 1.1 -> 2)

Date: 2026-02-06  
Status: Execution backlog aligned to AGI-like structuring plan

## 1) Objective

Implement a foundational advisory layer that is:

1. fast in direct path,
2. strategic in background path,
3. memory and outcome grounded,
4. deterministic where safety/authority matters,
5. adaptable via local/OAuth LLM routing.

## 2) Execution Rules

1. No feature merges without replay-based validation.
2. Direct path latency budget is protected first.
3. Deterministic contracts ship before adaptive/LLM refinement.
4. Every advisory output must be trace-linkable to source and outcome.
5. Phase gates are hard; do not skip.

## 3) Workstream Map

WS-A: Foundation Kernel and Dual Path  
WS-B: Intent, Goals, Rails, Gotchas  
WS-C: Memory Fusion and Conflict Resolution  
WS-D: Team/Orchestration/Program Intelligence  
WS-E: Outcomes, Feedback, and Evaluation  
WS-F: Provider Routing, Audit, and Benchmarks

## 4) Dependency Order

1. WS-A baseline routing and packet store.
2. WS-C memory fusion adapter.
3. WS-B intent-goal-rails-gotchas.
4. WS-E scoped outcomes and feedback.
5. WS-D team/orchestration/program contracts.
6. WS-F provider routing + audit + plane benchmarks.

## 5) Backlog Tickets

## Phase 1.1: Foundational Layer Wiring (Mandatory)

### Ticket A1

Title: Advisory packet store and index  
Type: core infra  
Files:

- add `lib/advisory_packet_store.py`
- update `lib/advisory_engine.py`
- add tests `tests/test_advisory_packet_store.py`

Depends on: none  
Acceptance:

1. Create/read/update/invalidate packet operations pass unit tests.
2. Cache lookup path adds <= 20ms p50 overhead in synthetic benchmark.
3. Packet lineage fields required and validated.

### Ticket A2

Title: Dual-path router in advisory engine  
Type: core routing  
Files:

- update `lib/advisory_engine.py`
- update `hooks/observe.py` (ensure call contracts remain stable)
- add tests `tests/test_advisory_dual_path_router.py`

Depends on: A1  
Acceptance:

1. Direct path executes without background worker availability.
2. Background path schedules prefetch/refine jobs non-blocking.
3. Fallback to deterministic synthesis always works.

### Ticket A3

Title: Background prefetch planner and worker skeleton  
Type: background infra  
Files:

- add `lib/advisory_prefetch_planner.py`
- add `lib/advisory_prefetch_worker.py`
- add tests `tests/test_advisory_prefetch_worker.py`

Depends on: A1, A2  
Acceptance:

1. Planner emits constrained plans (`max_jobs`, min tool probability).
2. Worker supports pause/resume and bounded concurrency.
3. No direct path latency regression under worker load test.

### Ticket A4

Title: Foundational config surface and defaults  
Type: configuration  
Files:

- update `lib/advisory_engine.py`
- update `lib/advisory_synthesizer.py`
- update docs `TUNEABLES.md`

Depends on: A2  
Acceptance:

1. New env toggles recognized with safe defaults.
2. Config dump/status endpoint includes advisory foundation fields.
3. Missing config never breaks advisory path.

## Phase 1.2: Intent-Goal-Rails (Mandatory)

### Ticket B1

Title: Deterministic intent taxonomy mapper  
Type: deterministic parser  
Files:

- add `lib/advisory_intent_taxonomy.py`
- update `lib/advisory_engine.py`
- add tests `tests/test_advisory_intent_taxonomy.py`

Depends on: A2  
Acceptance:

1. Prompt-to-intent-family mapping deterministic for same input.
2. Task-plane mapping returned with confidence and fallback behavior.
3. Intent-family precision gate dataset support added.

### Ticket B2

Title: Goal lifecycle store and scoring  
Type: goal management  
Files:

- add `lib/advisory_goals.py`
- update `lib/advisory_engine.py`
- add tests `tests/test_advisory_goals.py`

Depends on: B1  
Acceptance:

1. Active/completed/stale transitions enforced.
2. Max active goals constraint enforced.
3. Goal-progress updates persisted and trace-linked.

### Ticket B3

Title: Rail registry and deterministic steering evaluator  
Type: policy engine  
Files:

- add `lib/advisory_rails.py`
- update `lib/advisory_gate.py`
- update `lib/advisory_engine.py`
- add tests `tests/test_advisory_rails.py`

Depends on: B2  
Acceptance:

1. Hard/soft/directional rails evaluated deterministically.
2. Steering states (`steer_ok`, `steer_adjust`, `steer_warn`) emitted reliably.
3. No authority decisions delegated to LLM.

## Phase 1.3: Gotcha Layer (Mandatory)

### Ticket B4

Title: Gotcha registry and detector engine  
Type: risk interception  
Files:

- add `lib/advisory_gotchas.py`
- update `lib/advisory_engine.py`
- add tests `tests/test_advisory_gotchas.py`

Depends on: B3  
Acceptance:

1. Sequence/safety/context/process/schema gotchas supported.
2. Severity promotion logic works (`nudge` -> `warning` -> `critical`).
3. Detector precision/false-positive metrics emitted.

### Ticket B5

Title: Recovery playbook execution helper  
Type: recovery policy  
Files:

- add `lib/advisory_recovery_playbooks.py`
- update `lib/advisory_engine.py`
- add tests `tests/test_advisory_recovery_playbooks.py`

Depends on: B4  
Acceptance:

1. Each gotcha can map to deterministic playbook steps.
2. Recovery completion recorded against trace and goal.
3. Playbooks produce concise direct-path guidance format.

## Phase 1.1+1.2+1.3 Cross-Cut: Memory Fusion + Conflict Resolver

### Ticket C1

Title: Memory Fusion Bundle adapter  
Type: memory unification  
Files:

- add `lib/advisory_memory_fusion.py`
- update `lib/advisor.py`
- update `lib/advisory_engine.py`
- add tests `tests/test_advisory_memory_fusion.py`

Depends on: A2  
Acceptance:

1. Bundle includes cognitive, EIDOS, chips, outcomes, orchestration, optional Mind.
2. Missing source fallback works and is observable.
3. Advisory emits `memory_absent_declared` when no evidence available.

### Ticket C2

Title: Deterministic conflict resolver  
Type: consistency policy  
Files:

- add `lib/advisory_conflict_resolver.py`
- update `lib/advisory_engine.py`
- add tests `tests/test_advisory_conflict_resolver.py`

Depends on: C1, B3  
Acceptance:

1. Source precedence rules enforced deterministically.
2. Repeated identical inputs resolve identically.
3. Conflict metadata logged for diagnostics.

## Phase 2: Async AI Refinement + Cross-Plane Intelligence

### Ticket D1

Title: Team context contract implementation  
Type: team intelligence  
Files:

- add `lib/advisory_team_context.py`
- update `lib/orchestration.py`
- update `lib/advisory_memory_fusion.py`
- add tests `tests/test_advisory_team_context.py`

Depends on: C1  
Acceptance:

1. Team ownership/deadline/dependency fields available in team sessions.
2. Team context missing data handled gracefully.
3. Team-plane advisory uses context in packet generation.

### Ticket D2

Title: Orchestration milestone graph  
Type: dependency intelligence  
Files:

- add `lib/advisory_orchestration_graph.py`
- update `lib/orchestration.py`
- update `lib/advisory_engine.py`
- add tests `tests/test_advisory_orchestration_graph.py`

Depends on: D1  
Acceptance:

1. Graph contract persisted and queryable.
2. Advisory can select next-step based on dependency status.
3. Blocker signals surfaced with recovery recommendations.

### Ticket D3

Title: Program-level objective tracking  
Type: long-horizon steering  
Files:

- add `lib/advisory_program_goals.py`
- update `lib/advisory_goals.py`
- update `lib/advisory_engine.py`
- add tests `tests/test_advisory_program_goals.py`

Depends on: D2, B2  
Acceptance:

1. Multi-session objective model persisted per project.
2. Drift alerts trigger when session actions diverge from program goals.
3. Progress signals update from scoped outcomes.

### Ticket E1

Title: Scoped outcome ontology and tracker updates  
Type: evaluation quality  
Files:

- update `lib/outcome_log.py`
- update `lib/outcomes/signals.py`
- update `lib/outcomes/tracker.py`
- add tests `tests/test_outcome_scope_dimension.py`

Depends on: C1  
Acceptance:

1. Outcome scope/dimension fields supported.
2. Non-tool advisories receive labels through pipeline.
3. Aggregates available by plane and source mode.

### Ticket E2

Title: Advisory feedback capture path  
Type: human-in-loop  
Files:

- add `lib/advisory_feedback.py`
- update `sparkd.py` (feedback endpoint/event)
- update Pulse integration API surface (if in-repo adapter exists)
- add tests `tests/test_advisory_feedback.py`

Depends on: E1  
Acceptance:

1. Feedback model (`accepted`, `partially_helpful`, `not_helpful`, `incorrect`, `too_noisy`) stored.
2. Debounce and anti-spam controls enforced.
3. Feedback updates packet/goal ranking signals.

### Ticket F1

Title: Provider routing policy engine  
Type: model governance  
Files:

- update `lib/advisory_synthesizer.py`
- update `lib/advisory_prefetch_worker.py`
- add `lib/advisory_provider_policy.py`
- add tests `tests/test_advisory_provider_policy.py`

Depends on: A3, E1  
Acceptance:

1. `local|oauth|hybrid` modes enforce route decisions.
2. Routing considers task plane, risk, confidence, latency budget.
3. Deterministic fallback path preserved when provider unavailable.

### Ticket F2

Title: Provider audit trail and Pulse aggregates  
Type: observability  
Files:

- update `lib/advisory_synthesizer.py`
- add `lib/advisory_provider_audit.py`
- update dashboard/pulse status integration surfaces
- add tests `tests/test_advisory_provider_audit.py`

Depends on: F1  
Acceptance:

1. 100% provider-routed advisories emit audit records.
2. Audit includes selected provider/model and rationale.
3. Aggregates queryable by day, plane, and provider.

### Ticket F3

Title: Plane-specific benchmark harness extensions  
Type: validation tooling  
Files:

- update `scripts/local_ai_stress_suite.py`
- add `benchmarks/scenarios/team_management.json`
- add `benchmarks/scenarios/orchestration_execution.json`
- add `benchmarks/scenarios/research_decision.json`

Depends on: D2, E1, F1  
Acceptance:

1. Harness reports per-plane latency/intelligence/usefulness.
2. Regression thresholds enforce no plane degradation.
3. Benchmark output includes provider/source attribution breakdown.

## 6) Phase Gates

## Gate G1 (after A1-A4)

1. Direct path p95 not worse than baseline.
2. Packet cache path stable in soak test.
3. Foundational config and status reporting complete.

## Gate G2 (after B1-B5 + C1-C2)

1. Intent-goal-rails-gotchas deterministic and validated.
2. Conflict resolution stable on replay suite.
3. Goal progression and gotcha metrics visible.

## Gate G3 (after D1-D3 + E1-E2 + F1-F2)

1. Team/orchestration/program contracts active.
2. Scoped outcomes and human feedback shaping ranking.
3. Provider governance auditable and policy-compliant.

## Gate G4 (after F3)

1. Plane benchmark coverage complete.
2. No significant regression on any task plane.
3. Ready for controlled production default rollout.

## 7) Suggested Sprint Cut (Practical)

Sprint 1:

- A1, A2, A4

Sprint 2:

- A3, C1, B1

Sprint 3:

- B2, B3, C2

Sprint 4:

- B4, B5, E1

Sprint 5:

- D1, D2, E2

Sprint 6:

- D3, F1, F2, F3

## 8) Monday Start List

Start in this exact order:

1. A1 packet store
2. A2 dual-path router
3. C1 memory fusion adapter
4. B1 intent mapper

This gives a working backbone quickly and unlocks every downstream task.
