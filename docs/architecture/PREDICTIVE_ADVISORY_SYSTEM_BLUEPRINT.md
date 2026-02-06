# Predictive Advisory System Blueprint (V2)

Date: 2026-02-06  
Status: Comprehensive design for implementation

## 1) Executive Summary

This system is worth building. The architecture direction is correct, but the original version under-specified the two capabilities that determine whether it feels truly "anticipatory":

- next-tool prediction quality,
- intent clustering quality.

The system should be implemented with deterministic authority, strict hot-path budgets, background AI refinement, and hard phase gates. Local LLMs should carry most refinement load; OAuth/cloud LLM should be optional for escalation and overflow.

## 2) Honest Assessment

## What is strong

1. Two-lane architecture is correct.
   - Lane A: deterministic and bounded.
   - Lane B: richer, asynchronous quality work.
2. Safety posture is correct.
   - EIDOS/control-plane remains deterministic authority.
3. Outcome-bound feedback is correct.
   - Advice quality is measured by acted-on/effectiveness, not style.

## Where it can fail

1. Race-to-first-tool:
   - first `PreToolUse` can happen before prefetch completes.
2. Prediction fan-out:
   - naive prefetch across too many `(tool, category)` pairs wastes compute.
3. Stale packet toxicity:
   - TTL-only freshness is insufficient after `Edit`/`Write`.
4. Key churn:
   - overly volatile fingerprint keys can thrash packet cache.
5. Shared compute contention:
   - background synthesis can degrade interactive path if not lane-prioritized.

## 3) Goals and Non-Goals

## Goals

1. Keep advisory hot path predictable and fast.
2. Pre-stage high-value advice before tool calls.
3. Improve intelligence/usefulness with AI where budget allows.
4. Support both local LLM and OAuth/cloud LLM routes.
5. Preserve deterministic, auditable control.

## Non-Goals

1. Do not let LLMs make safety/control-plane decisions.
2. Do not replace existing deterministic retrieval/gate stack.
3. Do not auto-execute actions from advisory text.

## 4) Runtime Fit: Exact Integration Points

Current modules to extend:

- `hooks/observe.py`
  - already calls `on_user_prompt`, `on_pre_tool`, `on_post_tool`.
- `lib/advisory_engine.py`
  - primary orchestrator for new routing and packet lookup.
- `lib/advisory_gate.py`
  - remains deterministic authority filter.
- `lib/advisory_synthesizer.py`
  - remains synthesis backend; gains provider policy routing rules.
- `lib/advisor.py`
  - remains multi-source retrieval core.
- `lib/chip_merger.py`
  - remains chip-to-cognitive bridge.

New modules to add:

- `lib/advisory_packet_store.py`
- `lib/advisory_prefetch_planner.py`
- `lib/advisory_prefetch_worker.py`
- `lib/advisory_predictor.py`
- `lib/advisory_intent_taxonomy.py`
- `scripts/advisory_packet_report.py`

## 5) Architecture

This system is a foundational advisory layer for the full Spark session lifecycle, not only coding tool prompts.

It should guide:

- project building sessions,
- team management decisions,
- orchestration and execution control,
- research and decision support tasks.

Advisory must run in two visibility levels:

- direct surface path (fast, immediate, operator-visible),
- background direction path (strategic, precomputed, continuously learning).

## 5.1 Foundational Advisory Layer Components

1. Advisory Kernel (deterministic core)
   - lives in `lib/advisory_engine.py` + `lib/advisory_gate.py`.
   - authoritative for hot path routing, rails, gotchas, and final emit.
2. Direction Loop (background strategist)
   - prefetch planner/worker + packet refinement.
   - anticipates likely next steps and prepares guidance ahead of use.
3. Surface Router (direct path)
   - chooses what to show now for current action with strict budget.
4. Learning Integrator (feedback spine)
   - binds advice -> action -> outcome -> memory updates across Spark stores.

## 5.2 Task Plane Coverage

Every advisory decision should declare a task plane:

- `build_delivery`: implementation, validation, release readiness.
- `team_management`: delegation, coordination, accountability, status risk.
- `orchestration_execution`: sequencing, dependencies, blocker routing, recovery.
- `research_decision`: compare options, uncertainty reduction, evidence weighting.

Hot-path advisory remains concise, but background packets can include task-plane context so Spark steers toward the correct end result for that plane.

## Lane A: Realtime Hot Path (authoritative)

Budget target:

- p50 <= 300ms
- p90 <= 900ms
- p95 <= 1200ms

Order:

1. Try packet cache exact lookup.
2. If miss, try relaxed lookup.
3. If miss/stale, run deterministic retrieval + gate + programmatic synthesis.
4. AI sync synthesis only if remaining budget condition passes.
5. If budget condition fails, skip AI and emit deterministic output.

Hard rule:

- Lane A must work with AI disabled.

## Lane B: Background Quality Lane

Purpose:

- prefetch and refine advisory packets without blocking tools.

Behavior:

1. Trigger from `on_user_prompt`.
2. Build constrained prefetch plan.
3. Generate deterministic packet first.
4. Optionally refine via LLM.
5. Persist packet with lineage and freshness metadata.

Hard rule:

- Lane B must yield to Lane A under load.

## 6) Data Contracts

## 6.1 Stable vs Volatile Keys

Stable project key (`project_key`):

- repo root canonical hash,
- dominant language set,
- framework markers.

Volatile session key (`session_context_key`):

- current phase,
- recent tool sequence signature,
- latest prompt digest.

Policy:

- stable-key changes can trigger broad cache migration/invalidation.
- volatile-key changes invalidate only matching packet subsets.

## 6.2 Intent Taxonomy (no free-form drift)

Use fixed top-level intent families:

- `auth_security`
- `deployment_ops`
- `testing_validation`
- `schema_contracts`
- `performance_latency`
- `tool_reliability`
- `knowledge_alignment`
- `team_coordination`
- `orchestration_execution`
- `stakeholder_alignment`
- `research_decision_support`

Allow one controlled fallback:

- `emergent_other`

No arbitrary string cluster IDs in Phase 1.

Task plane mapping is deterministic:

- each intent family maps to one primary task plane.
- mixed prompts can map to at most two planes with ranked confidence.

## 6.3 Goal Contract (intent -> outcome target)

Each session maintains an explicit active goal set, not just raw prompt text.

Goal object:

```json
{
  "goal_id": "g_01J...",
  "session_id": "abc123",
  "intent_family": "auth_security",
  "goal_type": "reduce_risk",
  "target_outcome": "harden auth middleware and prevent token leakage",
  "success_signals": ["tests_pass", "redaction_present", "no_secret_logging"],
  "priority": "high",
  "status": "active",
  "created_ts": 1765398112.0,
  "updated_ts": 1765398112.0
}
```

Rules:

- max 3 active goals per session.
- each advisory packet must map to 1 primary goal.
- goals are deterministic records; LLM may propose but validators must confirm schema and taxonomy.

## 6.4 Rail Contract (steering boundaries)

Rails define how advisory should steer behavior toward goals.

Rail object:

```json
{
  "rail_id": "r_01J...",
  "scope": "project",
  "intent_family": "auth_security",
  "rail_type": "hard",
  "condition": "never_log_secrets_or_tokens",
  "enforcement": "warning",
  "reason": "security_leak_risk",
  "source": "policy",
  "active": true
}
```

Rail types:

- `hard`: must not be violated; emits warning/escalation signals.
- `soft`: preferred behavior; advisory guidance only.
- `directional`: tie-breaker toward desired outcome path.

Hard rule:

- rail enforcement decision remains deterministic.
- LLM can explain/rephrase, not decide allow/block authority.

## 6.5 Advisory Packet Schema

```json
{
  "packet_id": "pkt_01J...",
  "project_key": "pk_9f2...",
  "session_context_key": "sk_8ac...",
  "session_id": "abc123",
  "phase": "implementation",
  "intent_family": "auth_security",
  "goal_id": "g_01J...",
  "rail_hits": ["r_01J_hard_secret_redaction", "r_01J_soft_test_first"],
  "chip_categories": ["security", "testing"],
  "likely_tool": "Edit",
  "advice_ids": ["security:jwt_redaction", "tool:Edit_read_before_edit"],
  "advisory_text": "Validate auth server-side and redact token logs before editing middleware.",
  "source_mode": "programmatic_prefetch",
  "provider": "none",
  "confidence": 0.86,
  "effectiveness_score": 0.50,
  "fresh_until_ts": 1765398712.0,
  "trace_refs": ["tr_aa12", "tr_b942"],
  "created_ts": 1765398112.0,
  "updated_ts": 1765398112.0
}
```

## 6.6 Gotcha Profile Contract (preventable failure traps)

Each high-risk workflow can attach gotcha profiles that represent known trap patterns.

```json
{
  "gotcha_id": "gt_edit_without_read",
  "intent_family": "tool_reliability",
  "phase_scope": ["implementation"],
  "trigger_pattern": {
    "sequence": ["Edit"],
    "requires_prior": ["Read"],
    "window_s": 180
  },
  "severity": "warning",
  "message": "Read target content before Edit to avoid mismatch and stale assumptions.",
  "recovery_playbook_id": "pb_read_verify_edit",
  "enabled": true
}
```

Gotcha severities:

- `nudge`: low-risk reminder.
- `warning`: high-probability failure risk.
- `critical`: likely harmful path; escalate with hard warning and alternative next step.

Hard rule:

- gotcha detection is deterministic in hot path.
- LLM can refine phrasing or suggest recovery variants in background.

## 6.7 Memory Fusion Contract (Spark-wide context bundle)

Advisory consumes a normalized memory bundle so it can use existing Spark intelligence instead of isolated prompt text.

Bundle sources:

1. cognitive insights (`lib/cognitive_learner.py`)
2. memory banks/store (`lib/memory_banks.py`, `lib/memory_store.py`)
3. EIDOS distillations/evidence (`lib/eidos/retriever.py`, `lib/eidos/store.py`)
4. chip insights (`~/.spark/chip_insights/*.jsonl`, `lib/chip_merger.py`)
5. outcomes and linkers (`lib/outcome_log.py`, `lib/outcomes/*`)
6. orchestration state (`lib/orchestration.py`, `~/.spark/orchestration/*` if present)
7. optional Mind retrieval (`lib/mind_bridge.py`)

Bundle contract:

```json
{
  "memory_bundle_id": "mb_01J...",
  "project_key": "pk_9f2...",
  "task_plane": "orchestration_execution",
  "goal_ids": ["g_01J..."],
  "top_evidence": [
    {"source": "eidos", "id": "d_abc", "confidence": 0.82},
    {"source": "chip", "id": "ci_123", "confidence": 0.76}
  ],
  "recent_outcome_signals": ["failed_retry_loop", "recovered_after_read"],
  "created_ts": 1765398112.0
}
```

Hard rule:

- no advisory emit without at least one evidence-bearing source or explicit `memory_absent_declared=true`.

## 7) Core Flow

## 7.1 On `UserPromptSubmit`

1. Persist intent (`on_user_prompt` existing behavior).
2. Update stable and volatile keys.
3. Determine intent family deterministically.
4. Derive/update active goals from intent + session state.
5. Attach applicable rails for those goals.
6. Predict top tools (with confidence scores).
7. Build constrained prefetch plan.
8. Queue background jobs.

## 7.2 Prefetch Constraints (cost cap)

Per prompt:

- max 2 AI refinement jobs.
- only tools with probability >= 0.70.
- always create 1 deterministic baseline packet.

Session-start safeguard:

- create project baseline packet immediately to reduce first-tool race miss.

## 7.3 On `PreToolUse`

Lookup order:

1. exact `(project_key, phase, intent_family, tool)`.
2. relaxed `(project_key, tool)` with confidence/freshness gate.
3. run steering check against active goals and rails.
4. run gotcha detectors for current tool/action context.
5. deterministic fallback (current retrieval+gate+programmatic synthesis).
6. optional AI sync only if budget permits.

Steering check outputs:

- `steer_ok`: advisory aligns with active goal and rails.
- `steer_adjust`: advisory is rewritten/reranked toward goal-aligned action.
- `steer_warn`: candidate path risks rail violation; emit warning-grade guidance.

## 7.4 On `PostToolUse` / Failure

1. bind outcome to packet/advice trace.
2. update packet `effectiveness_score`.
3. update goal progress signals.
4. apply event-driven invalidation rules.

## 7.5 Dual-Path Session Flow (direct + background)

1. Direct surface path
   - for immediate next action and tool choice.
   - emits short advisory with current goal/rail/gotcha context.
2. Background direction path
   - prepares milestone-oriented packets for next likely decisions.
   - updates team/orchestration/research task-plane packets between tool calls.
3. Sync point on each major action
   - merge fresh outcomes into memory bundle,
   - refresh direction packets if confidence drops or dependencies change.

Expected result:

- immediate guidance stays fast and practical,
- session-level direction improves continuously without blocking actions.

## 8) Event-Driven Invalidation (Critical)

TTL remains, but event invalidation is primary.

Rules:

1. After `Edit` or `Write` success:
   - invalidate `implementation` and `testing_validation` packets touching same files/domain.
2. After build/test command failure (`Bash` patterns):
   - downrank packets used immediately before failure.
3. After major branch/context shift:
   - invalidate volatile-key packets only.
4. After repeated non-use:
   - age down confidence aggressively.

## 8.5) Gotcha System Layer (prevent + recover)

Goal:

- catch predictable mistakes before they consume budget or create regressions.

## 8.5.1 Gotcha detector classes

1. Sequence gotchas
   - `Edit` without recent `Read`.
   - deploy-like commands without recent test signal.
2. Safety gotchas
   - logging tokens/secrets.
   - using unsafe shell patterns in risky contexts.
3. Context gotchas
   - stale branch assumptions.
   - editing file paths that no longer match repository state.
4. Process gotchas
   - repeated retries with same failed command and no parameter change.
5. Schema gotchas
   - structured output requested but invalid schema evidence in recent attempts.

## 8.5.2 Gotcha handling policy

On detector hit:

1. attach gotcha to advisory context.
2. promote advisory authority (nudge -> warning -> critical).
3. emit short "why + safe next step" guidance.
4. bind hit to trace for outcome analysis.

No auto-block in advisory layer unless an existing deterministic safety policy already mandates block.

## 8.5.3 Recovery playbooks

Each gotcha maps to a deterministic recovery playbook:

- playbook includes 1-3 concrete recovery actions,
- includes minimal verification command/check,
- records whether recovery cleared the gotcha state.

Example:

- gotcha: `gt_edit_without_read`
- playbook:
  1. Read target file slice.
  2. Confirm intended edit anchor exists.
  3. Re-run edit with validated anchor.

## 8.5.4 LLM optimization for gotchas

Use local/OAuth LLM in background for:

1. gotcha candidate discovery from recent failures,
2. wording refinement for recovery steps,
3. consolidation of duplicate gotcha signatures.

Acceptance rule:

- no new gotcha enters hot path until deterministic validator approves pattern and false-positive check passes.

## 9) Ranking Strategy (Phased, not overfit)

Phase 1:

- deterministic exact/heuristic ranking only:
  - intent family match,
  - tool match,
  - freshness,
  - historical effectiveness.

Phase 2+:

- weighted learned ranking once enough outcomes exist.

Do not ship static hand-tuned weighted formula as final policy before data calibration.

Goal-aware tie-break policy in Phase 1:

- prefer packets that advance active high-priority goals,
- downrank packets with recent rail conflicts,
- prefer packets with proven goal-progress outcomes.

## 10) Provider Strategy: Local vs OAuth/Cloud

Current synthesizer already supports:

- Local: Ollama (`SPARK_OLLAMA_MODEL`, `SPARK_OLLAMA_API`)
- OAuth/cloud via keys:
  - OpenAI (`OPENAI_API_KEY`/`CODEX_API_KEY`)
  - Anthropic (`ANTHROPIC_API_KEY`/`CLAUDE_API_KEY`)
  - Gemini (`GEMINI_API_KEY`/`GOOGLE_API_KEY`)

## 10.1 Routing Modes

Add policy env:

- `SPARK_ADVISORY_PROVIDER_MODE=local|oauth|hybrid`

Semantics:

1. `local`:
   - only local providers used for advisory synthesis.
2. `oauth`:
   - only key-backed cloud providers used.
3. `hybrid`:
   - local-first for background refinement.
   - OAuth/cloud escalation for high-priority misses when permitted.
   - intent/goal parsing can escalate if local parser confidence is low.

## 10.2 Recommended Operating Policy

Realtime lane:

- default deterministic.
- optional low-latency local model only when budget allows.

Background lane:

- local quality model as default.
- OAuth/cloud only for escalated packets:
  - high business criticality,
  - repeated low effectiveness from local refinement,
  - explicit user opt-in.

## 10.3 Provider Selection by Work Type

1. Short actionable rewrite:
   - local small model first.
2. Conflict-heavy synthesis:
   - local quality model; cloud fallback if repeated failures.
3. Long-context consolidation:
   - background only; prefer stronger model path.
4. Intent-goal extraction:
   - local parser first; OAuth/cloud only for low-confidence ambiguous prompts.

## 10.4 LLM Pickup Contract (provider-agnostic)

To ensure any model (local or OAuth) can pick up Spark context reliably, synthesis calls should use a strict structured payload.

Required fields:

```json
{
  "task_plane": "build_delivery",
  "intent_family": "testing_validation",
  "active_goals": ["g_01J..."],
  "active_rails": ["r_01J..."],
  "active_gotchas": ["gt_edit_without_read"],
  "memory_bundle": {"id": "mb_01J..."},
  "candidate_actions": ["Read target file", "Run focused tests"],
  "desired_outcome": "pass auth tests with no secret leakage",
  "response_contract": {
    "max_sentences": 3,
    "must_include_next_step": true,
    "must_include_risk_if_any": true
  }
}
```

If provider output fails contract validation, advisory kernel falls back to deterministic synthesis.

## 10.5 Configuration Profiles (best-effect deployment)

Recommended new policy envs:

- `SPARK_ADVISORY_FOUNDATION=1`
- `SPARK_ADVISORY_DIRECT_PATH=1`
- `SPARK_ADVISORY_BACKGROUND_PATH=1`
- `SPARK_ADVISORY_TASK_PLANES=build_delivery,team_management,orchestration_execution,research_decision`
- `SPARK_ADVISORY_GOAL_MAX_ACTIVE=3`
- `SPARK_ADVISORY_GOTCHA_ENABLE=1`
- `SPARK_ADVISORY_PREFETCH_MAX_JOBS=2`
- `SPARK_ADVISORY_PREFETCH_TOOL_MIN_PROB=0.70`
- `SPARK_ADVISORY_PROVIDER_MODE=hybrid`
- `SPARK_ADVISORY_MEMORY_REQUIRED=1`

Suggested profiles:

1. `foundation_safe`:
   - deterministic-heavy, local-only, minimal AI sync.
2. `balanced_hybrid`:
   - local background refinement + selective OAuth escalation.
3. `quality_max`:
   - stronger background synthesis, strict direct-path fallback.

## 11) Model Role Mapping (Current Evidence-Aligned)

1. `phi4-mini`
   - default for async refinement quality.
2. `llama3.2:3b`
   - low-latency fallback when AI sync is allowed.
3. `qwen2.5-coder:3b`
   - secondary coding-oriented diversity fallback.

Large models currently timed out in active harness profile; treat as offline experiments until separate worker profile proves stable.

## 12) Phase Plan with Hard Gates and Abort Criteria

## Phase 0: Baseline Instrumentation

Deliver:

- packet metrics plumbed (hit rate, p95, lead time, source outcomes).

Gate:

- metrics correctness validated on replay traces.

Abort if:

- source attribution cannot be bound reliably to outcomes.

## Phase 1: Deterministic Prefetch Core

Deliver:

- packet store,
- baseline packet on session start,
- deterministic planner/predictor,
- direct-path lookup + deterministic fallback,
- background direction loop wired for all task planes.

Gates:

- hot-path p95 improves vs baseline,
- no correctness regression in emitted advice,
- first-tool packet coverage >= 50%.

Abort if:

- p95 worsens materially,
- packet hit rate < 20% after warmup period.

## Phase 1.1: Foundational Layer Wiring (Mandatory)

Deliver:

- advisory kernel owns both direct and background paths,
- memory fusion bundle adapter across cognitive/EIDOS/chips/outcomes/orchestration,
- task-plane classifier with deterministic mapping.

Gates:

- direct-path emits valid advisory for >= 95% applicable events,
- background packets available for >= 70% active sessions,
- advisory source attribution visible end-to-end in logs.

Abort if:

- direct and background paths diverge in contradictory guidance frequently,
- memory bundle assembly adds unstable latency or missing-source failures.

## Phase 1.2: Intent-Goal-Rails Foundation (Mandatory)

Deliver:

- deterministic intent-family mapper,
- goal object lifecycle (`active`, `completed`, `stale`),
- rail registry and deterministic steering evaluator.

Gates:

- goal extraction coverage >= 90% on sampled sessions,
- rail-evaluation determinism verified (same input -> same decision),
- no increase in false warning rate beyond agreed threshold.

Abort if:

- steering adds noise (low acceptance / high ignore rate),
- rail warnings are frequently irrelevant.

## Phase 1.3: Gotcha Layer Foundation (Mandatory)

Deliver:

- deterministic gotcha registry + detector engine,
- recovery playbook registry,
- gotcha trace logging and authority promotion logic.

Gates:

- gotcha precision >= 85% on labeled replay set,
- false-positive rate <= 10% on top 10 gotchas,
- recovery success rate >= 60% for warning/critical gotchas.

Abort if:

- warning fatigue emerges (warning acceptance drops below threshold),
- gotcha detector causes measurable hot-path latency regression.

## Phase 1.5: Prediction and Intent Quality Gate (Mandatory)

Gates:

- top1 next-tool accuracy >= 60%,
- top3 next-tool accuracy >= 85%,
- intent-family precision >= 80% on labeled sample.
- goal-to-outcome linkage precision >= 75% on labeled sample.

Do not start AI refinement phase until these pass.

## Phase 2: Async AI Refinement

Deliver:

- constrained AI refinement jobs,
- local/oAuth route policy,
- capped fan-out and concurrency control.

Gates:

- usefulness and strict effectiveness improve,
- goal progress rate improves vs deterministic baseline,
- no p95 hot-path regression,
- queue pressure stays within limits.

Abort if:

- background load increases user-visible latency,
- effectiveness does not improve after tuning window.

## Phase 3: Learned Ranking and Advanced Routing

Deliver:

- calibrated ranking weights from outcome data,
- escalation rules for provider route selection.

Gates:

- improved acted-on and strict effectiveness by statistically meaningful margin.

## Phase 4: Operational Hardening

Deliver:

- Pulse panel for predictive advisory,
- repair tooling,
- schema migration/versioning.

## 13) Resource Scheduling and Backpressure

Rules:

1. Lane A always priority 1.
2. Lane B has strict concurrency cap.
3. Lane B pauses automatically when:
   - Lane A p95 breaches threshold,
   - queue depth exceeds cap,
   - system under heavy tool burst.

## 14) Security and Trust Boundaries

1. No LLM authority over control-plane block/allow.
2. Advisory text must pass output validators.
3. Sensitive context redaction before cloud/OAuth route.
4. Full trace logging for:
   - packet source,
   - provider used,
   - outcome linkage.

## 15) Testing Plan

1. Unit
   - key derivation, intent->goal mapping, rail evaluator, gotcha detectors/playbooks, packet scoring, invalidation rules.
2. Integration
   - prompt -> goals/rails/gotchas -> prefetch -> first-tool lookup path.
   - memory bundle assembly from cognitive/EIDOS/chips/outcomes/orchestration sources.
3. Performance
   - burst scenarios with mixed tools and queue load.
   - direct vs background lane contention tests.
4. Reliability
   - corrupted packet store, stale packet cleanup, worker crash recovery.
   - missing memory source fallback behavior.
5. Policy
   - provider routing behavior under `local`, `oauth`, `hybrid`.
6. Task-plane quality
   - build, team, orchestration, and research scenario suites.

## 16) Key KPIs

Predictability:

- hot-path p95, p99,
- percent advisory under 3s,
- first-tool packet availability.

Intelligence/Utility:

- acted-on rate by source mode,
- strict effectiveness by source mode,
- packet reuse success rate.
- goal progress delta per session,
- rail conflict rate and rail warning acceptance rate.
- gotcha catch rate on known trap scenarios,
- gotcha false-positive rate,
- gotcha recovery completion rate.
- task-plane success delta (build/team/orchestration/research),
- background-to-direct advisory consistency score.

Efficiency:

- background job success rate,
- dropped/paused jobs due to backpressure,
- token/compute budget per session.

## 16.1 Remaining Missing Pieces to Close

1. Team context contract
   - role owners, deadlines, and dependency map ingestion is not yet formalized.
2. Orchestration milestone graph
   - no canonical step-dependency graph format in advisory layer yet.
3. Outcome label quality
   - need cleaner outcome schemas for team and orchestration tasks (not just tool outcomes).
4. Advisory conflict resolver
   - needs deterministic policy when memory sources disagree.
5. Human feedback capture UX
   - acceptance/rejection feedback for advisories should be easier to record in-flow.
6. Plane-specific benchmark suites
   - build scenarios exist; team/orchestration/research stress suites are still limited.
7. Provider policy audit trail
   - ensure all local vs OAuth escalations are logged with rationale.
8. Long-horizon objective tracking
   - session goals exist, but multi-session program goals need a durable strategy.

## 16.2 Gap Closure Specification (Detailed)

This section turns each missing piece into an implementation contract with concrete flow wiring and acceptance gates.

## 16.2.1 Team Context Contract

Purpose:

- let advisory reason about ownership, deadlines, and dependencies during team-management sessions.

Data contract:

```json
{
  "team_context_id": "tc_01J...",
  "project_key": "pk_9f2...",
  "members": [
    {"member_id": "m_alex", "role": "backend", "capacity": 0.7},
    {"member_id": "m_sam", "role": "qa", "capacity": 0.5}
  ],
  "work_items": [
    {"item_id": "wi_123", "owner": "m_alex", "status": "in_progress", "due_ts": 1765490000}
  ],
  "blocked_items": ["wi_456"],
  "updated_ts": 1765398112.0
}
```

Flow integration:

1. build in `lib/advisory_team_context.py`.
2. ingest from orchestration events and optional manual updates.
3. merge into memory bundle before advisory routing.

Acceptance gates:

- team context present in >= 80% sessions marked `task_plane=team_management`.
- owner and due-date fields populated for >= 90% team work items.

## 16.2.2 Orchestration Milestone Graph

Purpose:

- provide deterministic dependency-aware guidance, not isolated next-step advice.

Data contract:

```json
{
  "graph_id": "og_01J...",
  "project_key": "pk_9f2...",
  "milestones": [
    {"id": "ms_design", "status": "done"},
    {"id": "ms_impl", "status": "in_progress"},
    {"id": "ms_validate", "status": "todo"}
  ],
  "edges": [
    {"from": "ms_design", "to": "ms_impl"},
    {"from": "ms_impl", "to": "ms_validate"}
  ],
  "critical_path": ["ms_impl", "ms_validate"]
}
```

Flow integration:

1. new module `lib/advisory_orchestration_graph.py`.
2. consume `lib/orchestration.py` handoffs and status outcomes.
3. advisory engine checks graph before emitting next-step guidance.

Acceptance gates:

- dependency violations reduced vs baseline.
- blocker-resolution time improves for orchestration sessions.

## 16.2.3 Outcome Label Quality (beyond tool outcomes)

Purpose:

- track outcomes for team/orchestration/research, not only command/tool success.

Schema additions:

- `outcome_scope`: `tool|team|orchestration|research`
- `outcome_dimension`: `speed|quality|risk|alignment|delivery`
- `evidence_refs`: array of trace-linked evidence ids

Flow integration:

1. extend outcome writes in `lib/outcome_log.py`.
2. extend label detection in `lib/outcomes/signals.py`.
3. include scope/dimension in tracker aggregation.

Acceptance gates:

- >= 70% non-tool advisories receive scoped outcome labels.
- inter-rater consistency acceptable on sampled labeling set.

## 16.2.4 Deterministic Advisory Conflict Resolver

Purpose:

- resolve contradictory memory/advice sources without LLM arbitration.

Resolution precedence (deterministic):

1. hard rails and explicit safety policy.
2. recent validated outcomes.
3. EIDOS high-confidence distillations.
4. chip insights with strong outcome linkage.
5. semantic/cognitive retrieval remainder.

Flow integration:

- add `lib/advisory_conflict_resolver.py`.
- run before final emit and before AI refinement.

Acceptance gates:

- conflict cases resolved with stable outputs (same input -> same resolution).
- contradiction-induced flip-flops reduced across repeated sessions.

## 16.2.5 Human Feedback Capture UX

Purpose:

- reduce friction for marking advice as useful/noisy/wrong in-flow.

Feedback model:

- `accepted`
- `partially_helpful`
- `not_helpful`
- `incorrect`
- `too_noisy`

Flow integration:

1. add lightweight feedback endpoint/event in sparkd/pulse path.
2. connect to advisory packet lineage and goal progress score updates.
3. include cooldown/debounce so repeated clicks do not over-weight.

Acceptance gates:

- feedback capture rate increases materially vs current baseline.
- feedback-linked ranking adjustments correlate with improved strict effectiveness.

## 16.2.6 Plane-Specific Benchmark Suites

Purpose:

- avoid overfitting advisory to coding-only tasks.

Suites required:

1. build/delivery suite.
2. team management suite.
3. orchestration/dependency suite.
4. research decision suite.

Flow integration:

- extend `scripts/local_ai_stress_suite.py` with plane tags and scenario families.
- report plane-specific latency/intelligence/usefulness/effectiveness.

Acceptance gates:

- each plane has minimum scenario coverage and repeat count.
- no plane regresses significantly after model/policy changes.

## 16.2.7 Provider Policy Audit Trail

Purpose:

- guarantee explainability for local vs OAuth routing decisions.

Audit record schema:

```json
{
  "audit_id": "pa_01J...",
  "trace_id": "tr_abc",
  "provider_mode": "hybrid",
  "selected_provider": "ollama",
  "selected_model": "phi4-mini",
  "reason": "local_first_background_refine",
  "fallback_used": false,
  "latency_ms": 812.4,
  "created_ts": 1765398112.0
}
```

Flow integration:

- write to `~/.spark/advisory_provider_audit.jsonl`.
- expose aggregates in Pulse panel.

Acceptance gates:

- 100% provider-routed advisories have audit records.
- escalation rationale is present and parseable for compliance review.

## 16.2.8 Long-Horizon Objective Tracking

Purpose:

- steer advisory across multi-session programs, not only current session.

Program objective contract:

```json
{
  "program_id": "pg_01J...",
  "project_key": "pk_9f2...",
  "objective": "ship secure v1 with stable onboarding funnel",
  "horizon_days": 30,
  "milestones": ["security_hardening", "qa_stability", "launch_readiness"],
  "status": "active",
  "progress": 0.42,
  "updated_ts": 1765398112.0
}
```

Flow integration:

1. new module `lib/advisory_program_goals.py`.
2. join program objectives into session goal initialization.
3. compute drift alerts when short-term actions diverge from program objective.

Acceptance gates:

- measurable improvement in milestone completion predictability.
- reduced goal drift events over rolling windows.

## 16.3 Configuration for Best Effect

Recommended additional env keys:

- `SPARK_ADVISORY_TEAM_CONTEXT_ENABLE=1`
- `SPARK_ADVISORY_ORCH_GRAPH_ENABLE=1`
- `SPARK_ADVISORY_OUTCOME_SCOPE_ENABLE=1`
- `SPARK_ADVISORY_CONFLICT_RESOLVER_ENABLE=1`
- `SPARK_ADVISORY_FEEDBACK_ENABLE=1`
- `SPARK_ADVISORY_BENCH_PLANES=build_delivery,team_management,orchestration_execution,research_decision`
- `SPARK_ADVISORY_PROVIDER_AUDIT_ENABLE=1`
- `SPARK_ADVISORY_PROGRAM_GOALS_ENABLE=1`

Rollout order:

1. enable deterministic contracts first (team/orch/outcome/conflict).
2. enable feedback and provider audit.
3. enable long-horizon objective tracking.
4. tune model routing and background refinement after quality gates pass.

## 17) Final Honest Verdict

This blueprint can fit Spark well and produce meaningful gains if implemented with strict gates.  
It will not deliver reliable "anticipatory intelligence" from architecture alone. It needs first-class, measured prediction and intent modeling from day one.

If those are treated as core deliverables (not later optimizations), this system can become both fast and meaningfully proactive.
