# Core Implementation Plan (Context-Rich)

This plan operationalizes CORE.md + CORE_GAPS.md into buildable steps.
It is intentionally detailed, but avoids heavyweight infrastructure by default.

---

## Guiding Constraints

- Default must run on a laptop.
- No external services required for core functionality.
- Every added subsystem must improve measurable outcomes.
- Operational telemetry never pollutes cognitive memory.

---

## Architecture Baseline (Current)

Inputs:
- Tool + prompt events -> queue (`~/.spark/queue/events.jsonl`)

Core:
- Pattern detection (`lib/pattern_detection/*`)
- Cognitive learner (`lib/cognitive_learner.py`)
- Validation loop (`lib/validation_loop.py`)
- Promotion pipeline (`lib/promoter.py`)

Outputs:
- `~/.spark/cognitive_insights.json`
- `CLAUDE.md`, `AGENTS.md`, `SOUL.md`

---

## Target Architecture (Minimum Viable)

Layer 1: Signals
- Event queue + schema validation

Layer 2: Intelligence
- Operational insights store (tool telemetry)
- Cognitive insights store (human-useful)
- Chip runtime for domain intelligence
- Outcome log + validation
- "Why" capture detector

Layer 3: Impact
- Promotion filter (human-useful only)
- Context sync (chip summaries)
- Dashboard metrics (quality over volume)

---

## Implementation Phases

### Phase 1: Promotion Filtering + Operational Split

Intent:
- Stop tool sequences from polluting cognition.

Scope:
- Add operational insight classification.
- Block operational insights in `lib/promoter.py`.

Deliverables:
- Promotion filter with allowlist.
- Sequence/telemetry insights are not promoted.

Success metrics:
- 90%+ of promoted insights are human-useful.

---

### Phase 2: Chips Runtime MVP

Intent:
- Domain-specific intelligence per project.

Scope:
- YAML loader + schema validation.
- Registry (installed/active).
- Router (trigger matching).
- Runner (observer execution).
- Per-chip insight store.
- CLI: `spark chips list/install/activate/status/insights`.

Deliverables:
- Minimal chips runtime in `lib/chips/`.
- One working chip (e.g. marketing or moltbook).

Success metrics:
- Chip produces validated insights without touching core code.

---

### Phase 3: Outcome-Driven Learning

Intent:
- Validate learnings with outcomes.

Scope:
- Link outcomes to insights.
- Use outcomes to validate/contradict.
- Add chip-scoped outcomes.

Deliverables:
- Outcome linking in `lib/outcome_log.py` and `lib/validation_loop.py`.
- CLI helpers for outcome linkage.

Success metrics:
- 50%+ of insights have validation evidence.

---

### Phase 4: "Why" Capture Detector

Intent:
- Extract reasoning and principles.

Scope:
- New detector in `lib/pattern_detection/`.
- Parse corrections and confirmations for reasoning.

Deliverables:
- `why.py` detector integrated into aggregator.

Success metrics:
- Reasoning insights outnumber sequence insights.

---

### Phase 5: Project Questioning Intelligence

Intent:
- Ask the right questions per project/domain.

Scope:
- Chips provide project questions.
- Project profile stores answers.

Deliverables:
- Chip-defined questions in YAML.
- CLI updates in `spark.cli project`.

Success metrics:
- Project questions directly affect what gets learned.

---

## Work Breakdown (Concrete Steps)

1) Promotion filtering
- Update `lib/promoter.py` to block sequence patterns.
- Add operational/cognitive classifier.

2) Chip runtime
- Create `lib/chips/loader.py`, `registry.py`, `router.py`, `runner.py`, `store.py`.
- Add `spark.cli chips` subcommands.
- Wire `bridge_worker.py` to run active chips.

3) Outcome wiring
- Extend `lib/outcome_log.py` to link insights + chips.
- Extend `lib/validation_loop.py` to read outcomes.

4) Why capture
- Add `lib/pattern_detection/why.py`.
- Update aggregator to include it.

5) Project questioning
- Extend chip spec with `questions`.
- Add chip question ingestion in `lib/project_profile.py`.

---

## Non-Heavyweight Defaults

- Use JSONL + local files by default.
- Manual outcome check-ins as baseline.
- Rule-based detection before ML-based.

---

## Risk Controls

- Audit logs for promotions and chip updates.
- Strict scope permissions for chips.
- Human confirmation for high-impact changes.

---

## Definition of "Superintelligence-Ready"

- Chips framework is stable and extensible.
- Insights are outcome-validated.
- Cognitive memory is mostly human-useful.
- SparkNet integration can sync chips safely.

