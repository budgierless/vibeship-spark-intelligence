# Advisory Deep Diagnosis (Global Dedupe Tuneable)

Generated: 2026-02-22T22:28:18Z
Tuneables cutover unix: 1771799220

## Core Metrics
- Last hour outcomes: {'blocked': 58, 'emitted': 10}
- Last 24h outcomes: {'emitted': 781, 'blocked': 3395, 'error': 36}
- Post-cutover outcomes: {'emitted': 1, 'blocked': 5}
- Post-cutover in last hour outcomes: {'emitted': 1, 'blocked': 5}
- Last 24h follow rate: 100.0%

## Suppression Drivers (24h)
- shown_ttl: 4009
- global_dedupe: 1368
- tool_cooldown: 513
- budget_exhausted: 468
- other: 158
- context_phase_guard: 37

## Global Dedupe Cooldown Distribution
- 24h: {'600.0': 2381, '240.0': 4}
- post-cutover: {'240.0': 4}
- post-cutover last-hour: {'240.0': 4}

## Key Verification
- New rows now show `cooldown_s: 240.0` for `AE_GLOBAL_DEDUPE_SUPPRESSED`, confirming tuneable control.
- Category-aware shown TTL remains active (`TTL ... category=...` reasons present in recent rows).

## Recommendations
- Keep `global_dedupe_cooldown_s=240` for now; re-evaluate after a larger natural session sample (at least 24h).
- Add dedupe cooldown by authority/source (e.g., stricter for baseline/eidos, looser for security/mind).
- Add a deferred queue for budget-suppressed high-value advisories so they can surface on the next boundary.
- Add explicit per-reason counters in status output for fast operator tuning (`shown_ttl`, `global_dedupe`, `tool_cooldown`, `budget`).