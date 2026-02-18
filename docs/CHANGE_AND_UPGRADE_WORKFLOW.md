# Spark Change And Upgrade Workflow (Mandatory Optimizer Path)

Date: 2026-02-18
Applies to: `vibeship-spark-intelligence` + integrations with `vibeship-spark-consciousness`

## Purpose

This is the standard workflow for making any Spark runtime change and proving whether it helped.

Hard rule:
- Every change must be tracked through `vibeship-optimizer`.
- No direct "silent" tuneable/code rollout without before/after evidence.

## Control Hierarchy (What Sits Above Tuneables)

Tuneables are important, but they are not the only control layer.

1. Code safety and invariants (highest authority)
- Runtime guards in code (safety, auth, hard bounds, schema checks).
- Example surfaces: `sparkd.py`, `lib/consciousness_bridge.py`.

2. Contract docs and architecture rules
- These define source-of-truth behavior and precedence.
- Example: `docs/CONSCIOUSNESS_BRIDGE_V1.md`, architecture task-system docs.

3. Environment variable overrides (operational override layer)
- Used for emergency mitigation, canary forcing, and temporary rollback behavior.
- In many modules, env overrides tuneables at runtime.

4. Tuneables (`~/.spark/tuneables.json`) (primary operating knobs)
- Default route for thresholds/weights/cooldowns/limits that already exist.
- Reference: `TUNEABLES.md`.

5. Benchmark/CLI overlays (experiment layer)
- One-off benchmark flags or scripts; should not become permanent runtime behavior unless promoted.

## Decision Tree: Where A Change Should Go

Use this before touching anything.

1. Existing threshold/weight/cooldown already available?
- Yes: change via tuneables first.
- No: continue to step 2.

2. Behavior/contract precedence needs to change?
- Yes: code + docs + tests (not tuneables-only).
- No: continue to step 3.

3. Urgent mitigation needed right now?
- Yes: temporary env override, then convert to tuneable or code fix in next commit.
- No: tuneables or code by normal path.

4. Experiment only (not production candidate)?
- Use benchmark/CLI overlay only; do not promote to defaults yet.

## Mandatory Change Workflow

## 0) Open a tracked change (required)

```powershell
python -m vibeship_optimizer init --no-prompt
python -m vibeship_optimizer change start --title "<short-hypothesis>"
```

## 1) Define change contract before editing

For each change, write:
- hypothesis (what should improve),
- primary KPI (quality),
- guardrails (latency/error/safety),
- rollback trigger,
- rollback action.

Use one change per commit.

## 2) Capture baseline (before)

```powershell
python -m vibeship_optimizer snapshot --label before --change-id <chg-id> --as before
```

Always include task-specific baseline artifacts:
- advisory path: `scripts/advisory_controlled_delta.py`
- day-trial/gates: `scripts/advisory_day_trial.py start`
- memory/emotion experiments: benchmark outputs under `benchmarks/out/`

## 3) Implement the smallest valid delta

Allowed patterns:
- tuneables-only patch,
- tuneables + helper script (`scripts/apply_advisory_wow_tuneables.py`, `scripts/apply_chip_profile_r3.py`),
- code + test + docs when behavior/contract changes.

## 4) Local validation gate (must pass before after-snapshot)

Run:
- targeted tests for touched subsystem,
- health smoke (`/health`, `/status`),
- relevant benchmark/check script.

If validation fails: rollback immediately and keep change as rejected.

## 5) Capture after-state and compare

```powershell
python -m vibeship_optimizer snapshot --label after --change-id <chg-id> --as after
python -m vibeship_optimizer compare --before <before.json> --after <after.json> --out reports/optimizer/<chg-id>_compare.md
```

## 6) Promotion gate decision

Promote only if all are true:
- quality improved or target KPI reached,
- latency guardrails pass,
- error/safety guardrails pass,
- no contract regressions.

Otherwise:
- revert or keep as non-promoted experiment,
- record "why rejected" in optimizer change notes.

## 7) Controlled rollout

Use canary -> short live window -> full rollout.

Recommended:
- `scripts/advisory_day_trial.py` for day-level gating and close report.
- Keep rollback command ready (`git revert <sha>` or tuneable rollback).

## 8) Monitor and verify (minimum 3-day rule)

Use optimizer verification workflow:

```powershell
python -m vibeship_optimizer change verify --change-id <chg-id>
python -m vibeship_optimizer change verify --change-id <chg-id> --apply --summary "<observed-result>"
```

Do not mark "VERIFIED" before the monitoring window closes.

## Required Artifacts Per Change

Every change must leave:
- `reports/optimizer/<chg-id>_before_snapshot.json`
- `reports/optimizer/<chg-id>_after_snapshot.json`
- `reports/optimizer/<chg-id>_compare.md`
- subsystem KPI output (for example advisory delta/day-trial/benchmark report)
- explicit rollback note + trigger

## Change Classes And Required Evidence

| Change Class | Default Route | Required Evidence |
|---|---|---|
| Threshold/weight/cooldown update | Tuneables | before/after snapshots + relevant KPI script |
| Routing/contract precedence change | Code + docs + tests | tests + smoke + contract doc update + optimizer compare |
| Emergency risk control | Env override (temporary) | incident note + follow-up commit moving to tuneable/code |
| Benchmark-only experiment | CLI overlay only | benchmark report; no default promotion until gate pass |

## Daily Operating Discipline (Short Version)

At start of day:
1. Check service health and queue/advisory status.
2. Confirm tuneables are applied as expected.
3. Review open optimizer changes and their current gate status.

At end of day:
1. Update active change logs (Day 0/1/2/3 evidence).
2. Record promote/hold/rollback decision with reason.
3. Queue next smallest delta only if current gate is stable.

## What To Avoid

- Tuneables changes without optimizer record.
- Multi-feature commits (destroys attribution).
- Promoting benchmark winners without live guardrail checks.
- Leaving env emergency overrides undocumented.
- Changing contracts without updating docs/tests.

## Canonical References

- `VIBESHIP_OPTIMIZER.md`
- `TUNEABLES.md`
- `OPTIMIZATION_CHECKER.md`
- `docs/ADVISORY_DAY_TRIAL.md`
- `docs/ADVISORY_BENCHMARK_SYSTEM.md`
- `docs/CONSCIOUSNESS_BRIDGE_V1.md`
