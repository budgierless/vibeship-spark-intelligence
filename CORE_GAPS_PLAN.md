# Core Gaps Plan: How We Fill Them

This document explains how we fill the gaps identified in CORE_GAPS.md.
It is the actionable path from today's Spark to superintelligent evolution.

---

## 1) Primitive vs Cognitive Separation

Intent:
- Stop operational telemetry from polluting cognition.

How we fill it:
- Add an "operational" bucket for sequence/telemetry insights.
- Add a promotion filter to block operational insights.

Workflows:
- Pattern detection tags insights as operational vs cognitive.
- Promotion checks reject operational insights.

Minimal architecture:
- Rule-based classifier (sequence patterns, tool-heavy strings).
- Separate file or namespace for operational insights.

Code transformations:
- Retire sequence-based detection; filter operational telemetry at ingestion.
- `lib/promoter.py` -> reject operational insights.
- `lib/cognitive_learner.py` -> optional store split.

---

## 2) Chips Runtime MVP

Intent:
- Make Spark domain-aware without changing core code.

How we fill it:
- Implement loader, registry, router, runner, and storage.

Workflows:
- Install chip YAML.
- Activate chip for a project.
- Chip triggers on events, captures fields, writes insights.

Minimal architecture:
- `lib/chips/loader.py` (YAML schema validation).
- `lib/chips/registry.py` (installed + active chips).
- `lib/chips/router.py` (trigger matching).
- `lib/chips/runner.py` (observer execution).
- `lib/chips/store.py` (per-chip insights).
- `spark/cli.py` new `chips` commands.

Code transformations:
- `bridge_worker.py` to run active chips per cycle.
- `lib/context_sync.py` to inject chip summaries.

---

## 3) Outcome-Driven Learning

Intent:
- Validate insights with real-world outcomes.

How we fill it:
- Wire outcome check-ins to task completion.
- Allow chips to define domain outcomes (CTR, ROI, churn, etc.).

Workflows:
- User completes task -> outcome check-in prompt.
- Outcome links to insight(s) and validates or contradicts.

Minimal architecture:
- Extend `lib/outcome_log.py` with chip namespaces.
- Extend `lib/validation_loop.py` to use outcome evidence.

Code transformations:
- Add outcome linking in `lib/bridge_cycle.py`.
- Add CLI helpers for outcome linking by insight.

---

## 4) "Why" Capture Detector

Intent:
- Capture reasoning and principles, not just events.

How we fill it:
- Add detector to parse corrections and success language.
- Convert to reasoning and wisdom insights.

Workflows:
- When user corrects, extract "why".
- When user approves, extract "what made it good".

Minimal architecture:
- `lib/pattern_detection/why.py`.
- Rule-based extraction for cause, constraint, preference.

Code transformations:
- Plug into `lib/pattern_detection/aggregator.py`.

---

## 5) Preference Validation

Intent:
- Avoid untrusted preferences becoming policy.

How we fill it:
- Add preference confirmation prompts.
- Decay unvalidated prefs faster.

Workflows:
- Periodically ask "still prefer X?"
- Validate or decay based on answer.

Minimal architecture:
- Preference validation queue.
- Decay rules by age/validation count.

Code transformations:
- Extend `lib/validation_loop.py` with preference checks.

---

## 6) Project Questioning Intelligence

Intent:
- Spark should ask what matters for this project.

How we fill it:
- Each chip defines onboarding questions.
- Project profile stores answers.

Workflows:
- Project init -> chip questions.
- Mid-project -> suggestion engine for new questions.

Minimal architecture:
- Add `questions` block to chip spec.
- Extend `lib/project_profile.py`.

Code transformations:
- Update CLI `spark project` to load chip questions.

---

## 7) Promotion Hygiene

Intent:
- Promote only human-useful cognition.

How we fill it:
- Add quality gates for evidence + validation + category.
- Suppress promotion of sequences/telemetry.

Workflows:
- Promotion preview -> human approval (optional).
- Auto-promotion only for verified categories.

Minimal architecture:
- Promotion filter + allowlist.

Code transformations:
- `lib/promoter.py` gating and suppression rules.

---

## 8) SparkNet Integration (Future)

Intent:
- Share chips and benchmarks without locking users in.

How we fill it:
- Local registry mirrors to SparkNet only by opt-in.
- Sync chip metadata, not raw data, by default.

Workflows:
- `spark chips sync` -> push/pull registry metadata.

Minimal architecture:
- Registry sync API client (future).

---

## 9) Data Quality and Deduping

Intent:
- Prevent duplicate insights and noisy promotion.

How we fill it:
- Normalize repeated struggle patterns.
- Deduplicate preferences by semantic similarity.

Workflows:
- Normalize before insert.
- Merge duplicates instead of adding new rows.

Minimal architecture:
- Normalizer in `lib/cognitive_learner.py`.

---

## 10) Metrics and Evaluation

Intent:
- Measure intelligence quality, not just volume.

How we fill it:
- Per-chip precision/recall from outcomes.
- Insight quality score (validation + evidence).

Workflows:
- Weekly evaluation report by chip.

Minimal architecture:
- Aggregator stats + outcome coverage.

Code transformations:
- Extend dashboard and CLI stats.

---

## Sequencing Plan (Lean and Safe)

1) Promotion filter + operational split
2) Chip runtime MVP
3) Outcome wiring
4) "Why capture" detector
5) Project questioning intelligence

Each step should be usable standalone and remain lightweight.
