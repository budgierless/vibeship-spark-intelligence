# Tomorrow Plan (Spark Intelligence)

Date written: 2026-02-16

## Zoomed-Out State (Where We Are Now)

What is working:
- Tuneables are being applied consistently (UTF-8 BOM issue fixed + loader hardened).
- Retrieval routing is no longer dominated by `route=empty` in the current tuned profile (observed `balanced_spend` / level 2).
- Escalation is now controllable with tuneables (`escalate_on_weak_primary`, `agentic_rate_limit`), and the dominance of `agentic_rate_cap` has been reduced from earlier baselines.

What is still not working (highest impact):
- Advisory emissions are often suppressed or absent:
  - `AE_NO_ADVICE` (no-hit) is common.
  - `AE_GATE_SUPPRESSED` (policy gate) is common.
  - Global/low-auth dedupe can suppress emissions across churny sessions (mitigated for bench runs via `advisory-bench-*` prefixes, but still relevant in real usage).

Single source of truth for recent decisions + experiments:
- `docs/reports/2026-02-15_233443_prompt_run_10_2_6.md`

## Current Tuneables Snapshot (Local Machine)

File:
- `%USERPROFILE%\\.spark\\tuneables.json`

Key retrieval overrides (current):
- `semantic_context_min`: 0.12
- `semantic_lexical_min`: 0.02
- `escalate_on_weak_primary`: true
- `agentic_rate_limit`: 0.35
- `min_top_score_no_escalation`: 0.02

Backups created during this session:
- `%USERPROFILE%\\.spark\\backups\\tuneables.json.variantB_20260215_234717.bak`
- `%USERPROFILE%\\.spark\\backups\\tuneables.json.variantC_20260216_004521.bak`
- `%USERPROFILE%\\.spark\\backups\\tuneables.json.variantCplus_20260216_005907.bak`
- `%USERPROFILE%\\.spark\\backups\\tuneables.json.variantD_20260216_015256.bak`
- `%USERPROFILE%\\.spark\\backups\\tuneables.json.variantE_20260216_024440.bak`

## Tomorrow’s Priorities (In Order)

### 1) Advisory Suppression Audit (Root Cause + Fix Plan)

Goal:
- Turn “we have retrieval” into “we reliably emit useful advice”, without disabling safety gates.

Evidence to collect (1 hour window):
- Count of `AE_NO_ADVICE`, `AE_GATE_SUPPRESSED`, and (if present) dedupe suppressions.
- Examples of `AE_GATE_SUPPRESSED` rows (what gate + what metadata).

Commands:
```powershell
# 1-hour breakdown by error_code
python -c "import os,json,time; from collections import Counter; p=os.path.join(os.environ['USERPROFILE'],'.spark','advisory_engine.jsonl'); cut=time.time()-3600; by=Counter(); n=0; \
f=open(p,'r',encoding='utf-8',errors='ignore'); \
import sys; \
for ln in f: \
  ln=ln.strip(); \
  (ln and 1) or None; \
  \
  \
"
```

Notes:
- If `AE_NO_ADVICE` dominates, focus on advisor candidate generation and `MIN_RANK_SCORE` / filtering.
- If `AE_GATE_SUPPRESSED` dominates, inspect `lib/advisory_gate.py` thresholds/cooldowns and the authority banding logic.

Output to save:
- Append a short “Suppression Audit” section into `docs/reports/2026-02-15_233443_prompt_run_10_2_6.md` with:
  - a histogram of error codes
  - 3-5 representative JSONL row excerpts (redact nothing sensitive, but keep it minimal)
  - a concrete hypothesis + next experiment

### 2) Make the Measurement Harness Reliable (So We Can Trust KPIs)

Goal:
- Ensure controlled runs aren’t being dominated by cross-session dedupe artifacts and log retention truncation.

Action:
- Use `scripts/advisory_controlled_delta.py` with:
  - `--prompt-mode vary`
  - `--tool-input-mode repo`
  - session prefix `advisory-bench-*` (already set) to bypass global/low-auth dedupe for benchmark runs.

Rule of thumb:
- Keep `--rounds <= 250` if you want stable advisory-engine event/latency coverage, due to local log retention behavior.

Artifacts:
- Save each run to `docs/reports/` and link it from the main report.

### 3) Decide Whether to Keep Variant E (min_top_score_no_escalation)

Goal:
- Confirm Variant E reduces unnecessary escalations while keeping quality and emissions acceptable.

Checkpoints:
- Compare router reason mix (`weak_primary_score`, `agentic_rate_cap`) before/after.
- Confirm emissions don’t collapse in real usage (not just synthetic bench).

Rollback:
- Set `retrieval.overrides.min_top_score_no_escalation` back to 0.72 (use the Variant D backup) if emissions/quality regress.

### 4) Improve Advice-ID Stability and Outcome Tracking (Quality Over Time)

Why:
- If advice IDs churn, global dedupe becomes noisy and outcomes fragment, harming learning loops.

Tasks:
- Verify advice IDs for durable sources follow `source:insight_key` and semantic/trigger are canonicalized.
- Run unit tests:
```powershell
python -m pytest -q tests/test_advice_id_stability.py
```

### 5) Repo Hygiene (So Tomorrow Starts Clean)

Tasks:
- Review `git status` and decide what’s “real work” vs scratch artifacts.
- Keep “evidence artifacts” that are referenced by `docs/reports/2026-02-15_233443_prompt_run_10_2_6.md`.
- Delete or ignore scratch run JSONs not referenced by any report.

## Optional “If Time” Items

- Context sync coverage: decide whether to enable additional adapters (CLAUDE/Cursor/Windsurf) to improve retrieval variety, and record before/after in the main report.
- Re-run `scripts/advisory_self_review.py` for a tight window (15-30 minutes) after any gate changes to ensure no new suppression loops.

## Tomorrow’s Success Criteria (Concrete)

- Advisory engine: `AE_GATE_SUPPRESSED` share decreases or becomes explainable (policy doing the right thing).
- Advisory engine: `AE_NO_ADVICE` decreases, or we can point to a clear retrieval/candidate generation issue with a fix.
- Retrieval router: `empty` remains near 0, `primary_count>0` remains near 100%.
- Everything new is written into `docs/reports/2026-02-15_233443_prompt_run_10_2_6.md` with links to artifacts.

