# Post-Launch Monitoring + Retro

This doc applies after launch. If you are still pre-launch, use it as a dry run to validate the monitoring loop.

## What To Monitor (Daily)

Reliability:
- `spark health` and `spark services`
- `/status` readiness JSON
- bridge worker heartbeat freshness
- queue depth and backlog trends

Safety:
- guardrail block counts (unexpected spikes)
- any reports of secret exposure or unsafe defaults (treat as SEV-0)

Quality:
- production loop gates (`scripts/production_loop_report.py`)
- Meta-Ralph quality band

Support:
- top 5 issues (see `docs/support/DAILY_SUPPORT_TRACKING.md`)

## Alert Thresholds (Minimal)

- `/status` fails 3 times in a row (30s) -> investigate
- heartbeat age > 120s -> investigate
- watchdog restart loop -> investigate
- any security/safety report -> SEV-0

## 48h Retro Template

Answer:
- what broke first?
- what we shipped as a hotfix?
- what should become an automated test/gate?
- what should become a runbook step?

Output:
- a short write-up under `docs/reports/` with evidence links

