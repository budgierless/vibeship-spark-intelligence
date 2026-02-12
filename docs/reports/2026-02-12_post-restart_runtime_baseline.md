# Post-Restart Runtime Baseline (Spark)

Date: 2026-02-12
Baseline captured at: 2026-02-12T10:48:41Z
Scope: verify new lightweight defaults are active after service restart and establish 24h comparison baseline.

## Restart Actions Executed

1. Stopped services via lib.service_control.stop_services.
2. Started services via lib.service_control.start_services.
3. Forced bridge relaunch using python -m spark.cli up --bridge-stale-s 1.

## Current Health Snapshot

- sparkd: running and healthy
- dashboard: running and healthy
- pulse: running and healthy
- meta_ralph: running and healthy
- ridge_worker: running (fresh PID file + process match)
- scheduler: running (heartbeat fresh)
- watchdog: running
- queue backlog at capture: low (single-digit)

## Baseline Metrics

### Sync policy status (post-restart)

A forced context sync returned:
- claude_code: disabled
- cursor: disabled
- windsurf: disabled
- clawdbot: disabled
- openclaw: written
- exports: written

~/.spark/sync_stats.json after capture:
- optional adapters now show disabled
- core adapters show success

Interpretation:
- core-only default policy is active in runtime.

### Advisory telemetry

Historical recent window (last 200 events before baseline sample):
- allback_emit: 144
- emitted: 52
- 
o_emit: 2
- synth_empty: 2

Since bridge restart cutoff (using bridge PID mtime):
- events observed: 1
- event mix: emitted=1
- route: live
- delivery_mode: live

Interpretation:
- fallback-heavy history still exists in prior telemetry.
- post-restart sample is too small for trend conclusions, but confirms live emission path works on new runtime.

### Chip merge status

Latest ~/.spark/chip_merge_state.json snapshot:
- processed: 20
- merged: 0
- skipped_duplicate: 0
- duplicate_ratio: 0.0
- duplicate-churn throttle: inactive at capture

Interpretation:
- no duplicate churn pressure in this immediate slice.

## 24h Watch Targets

1. Advisory fallback share:
- target: reduce below 50% of delivered advisories (allback_emit / (fallback_emit + emitted)) over next 24h.

2. Core sync health:
- target: keep openclaw and exports at success with optional adapters remaining disabled (not error noise).

3. Chip duplicate churn:
- target: duplicate throttle either inactive or low-hit while maintaining non-zero merge yield when new chip signal exists.

## Runbook Commands (for next check)

`powershell
python scripts/status_local.py
python -m lib.context_sync --limit 5
python -c "from pathlib import Path;import json,collections; p=Path.home()/'.spark'/'advisory_engine.jsonl'; lines=p.read_text(encoding='utf-8').splitlines()[-500:]; c=collections.Counter(json.loads(l).get('event','unknown') for l in lines if l.strip()); print(dict(c))"
python -c "from pathlib import Path;import json; p=Path.home()/'.spark'/'sync_stats.json'; print(json.loads(p.read_text(encoding='utf-8')))"
python -c "from pathlib import Path;import json; p=Path.home()/'.spark'/'chip_merge_state.json'; print(json.loads(p.read_text(encoding='utf-8')).get('last_stats'))"
`

## Assessment

System state right now: stable and improved at architecture/runtime-default level, with advisory quality trend still requiring live-session evidence over the next 24h.
