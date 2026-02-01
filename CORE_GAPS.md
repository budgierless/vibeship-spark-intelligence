# Core Gaps: What Exists vs What We Need

This document is the definitive gap map from today's Spark to superintelligent
evolving AI. It focuses on:
- What already exists (code or docs)
- What can be transformed from existing code
- What must be built new
- What must be cleaned or removed

This is paired with CORE_GAPS_PLAN.md for how we will fill these gaps.

---

## 1) Primitive vs Cognitive Separation

What exists now:
- Mixed insights in `~/.spark/cognitive_insights.json`
- Promotion pipeline in `lib/promoter.py`
- Pattern pipeline in `lib/pattern_detection/*`

What can be transformed:
- Treat sequence/tool telemetry as operational-only.
- Add a promotion filter that blocks tool sequences.

What is new:
- Explicit operational insight store (separate file or namespace).
- Simple classifier to flag "operational" vs "cognitive".

What to clean:
- Remove or reclassify sequence-based "reasoning" insights.
- Stop adding tool-sequence learnings to CLAUDE.md.

---

## 2) Domain Intelligence (Chips Runtime)

What exists now:
- Chip spec design doc: `docs/SPARK_CHIPS_ARCHITECTURE.md`
- Example chip: `chips/moltbook.chip.yaml`

What can be transformed:
- Existing pattern detection into "core chip".

What is new:
- Chip loader + schema validation.
- Chip registry (installed + active).
- Chip router + runner.
- Per-chip insight storage.
- CLI commands: `spark chips list/install/activate/status/insights`.

What to clean:
- Document "chips runtime future repo" and reconcile with in-repo runtime.

---

## 3) Outcome-Driven Learning

What exists now:
- Outcome log: `lib/outcome_log.py`
- Outcome check-in CLI: `spark.cli outcome`
- Validation loop: `lib/validation_loop.py`

What can be transformed:
- Wire outcome checks to task completion.
- Tie outcomes to specific insights or chips.

What is new:
- Outcome ingestion hooks (project- or chip-specific).
- Outcome attribution logic to validate insights.

What to clean:
- Reduce "confidence-only" learning when no outcomes are present.

---

## 4) "Why" Capture (Reasoning, Wisdom, Context)

What exists now:
- Correction and sentiment detectors.
- Semantic intent detector.

What can be transformed:
- Extract reasoning from corrections and success messages.

What is new:
- "Why capture" detector in `lib/pattern_detection/`.
- Principle extraction rules for wisdom and context.

What to clean:
- Sequence-based "reasoning" should not crowd true reasoning.

---

## 5) Preference Validation

What exists now:
- User understanding insights are captured.

What can be transformed:
- Add a validation cadence and decay for prefs.

What is new:
- Preference validation workflow (explicit confirmation).
- Per-preference confidence decay rules.

What to clean:
- Low-signal preferences without validation.

---

## 6) Project Questioning Intelligence

What exists now:
- Project profile: `lib/project_profile.py`
- Domain inference and questions (basic).

What can be transformed:
- Use chips to define project questions.

What is new:
- Chip-driven question sets at project init.
- Continuous question suggestions as context shifts.

What to clean:
- Generic questions that do not change learning behavior.

---

## 7) Promotion Hygiene

What exists now:
- Auto promotion thresholds and targets in `lib/promoter.py`.

What can be transformed:
- Add quality gates (category, evidence, validation count).

What is new:
- Promotion review queue (optional).
- Promotion suppression list (sequence patterns, telemetry).

What to clean:
- Clean CLAUDE.md/AGENTS.md of sequence noise.

---

## 8) SparkNet Integration (Future)

What exists now:
- Mention of SparkNet (external repo).

What can be transformed:
- Local chip registry to sync with SparkNet later.

What is new:
- Chip sync protocol (opt-in).
- Shared benchmarks and outcome metrics.

What to clean:
- No hard dependency. Spark must run offline.

---

## 9) Data Quality and Deduping

What exists now:
- Deduping for some signals in `lib/cognitive_learner.py`.

What can be transformed:
- Improve normalization rules for repeated struggles.

What is new:
- Deduping for similar preference statements.
- Schema validation for chip inputs.

What to clean:
- Collapsed or duplicated struggle variants in promoted docs.

---

## 10) Metrics and Evaluation

What exists now:
- Basic stats in CLI and dashboard.

What can be transformed:
- Per-chip metrics and confidence reporting.

What is new:
- Precision/recall per chip.
- Outcome coverage per chip.

What to clean:
- Remove or de-emphasize metrics that reward spam.

---

## 11) Importance Scoring Foundation ✅ IMPLEMENTED

**Status: Phase 2 Complete (2026-02-02)**

The core problem: Spark was deciding importance at PROMOTION time, not INGESTION time.
This meant critical one-time insights were lost because they didn't repeat.

**The Key Insight: Importance != Frequency**

| Old Approach | New Approach |
|--------------|--------------|
| Learn if it repeats | Learn if it's important |
| Confidence = repetition | Importance = semantic value |
| Filter at promotion | Score at ingestion |
| Miss one-time critical insights | Elevate first-mention signals |

What now exists:
- `lib/importance_scorer.py` - Semantic importance scoring at ingestion
- Integration in `lib/pattern_detection/aggregator.py`
- CLI command: `spark importance --text "..."` for testing

How importance is scored:
1. **Critical Signals** (0.9+): "remember this", corrections, explicit decisions
2. **High Signals** (0.7-0.9): preferences, principles, reasoning with "because"
3. **Medium Signals** (0.5-0.7): observations, context, weak preferences
4. **Low Signals** (0.3-0.5): acknowledgments, trivial statements
5. **Ignore** (<0.3): tool sequences, metrics, operational noise

Domain-driven importance:
- Active domain (game_dev, fintech, etc.) weights relevant terms
- "balance" in game_dev context gets 1.5x boost

First-mention elevation:
- Critical insights on first mention get captured immediately
- No need to wait for repetition

Question-guided capture:
- Project onboarding questions guide what to pay attention to
- "What does success look like?" patterns get elevated

What to evolve next:
- Semantic clustering for similar insights
- Outcome attribution to validate importance predictions
- LLM-assisted importance scoring for edge cases

