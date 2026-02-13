# Spark Intelligence — Optimization Checker

This file is the **post-optimization validation playbook**.

---

## Shipped optimization changelog (rollback map)

These optimizations were shipped as isolated commits so we can `git revert <sha>` one-at-a-time.

### Current optimization batch (2026-02-14)

1) `e4c1473` — Bound semantic retrieval log growth (rotation)
2) `f094b59` — Avoid rewrite-on-append in capped advisor logs
3) `437b383` — Fix queue lock release to not unlink when unacquired
4) `2ad3d28` — Stream queue reads to avoid full-file loads
5) `63729d7` — Reuse shared executor for bridge steps
6) `e687f8a` — Reduce bridge cycle GC frequency (configurable)
7) `2c4a31f` — Cache advisor prefilter tokenization
8) `cca5c76` — Add sampling knob for semantic retrieval logging
9) `7340030` — Add optimization checker playbook
10) `3619dd4` — Docs: add rollback-map changelog to optimization checker

### Phase-1 behavior upgrades (2026-02-14)
11) `7ceca23` — Advisory: require agreement before warning escalation (flagged)
12) `9439361` — Pipeline: importance-sample low-priority events under backlog (flagged)
13) `81d627e` — Pipeline: mine successful tool macros (flagged)

Notes:
- Prefer `git revert <sha>` (keeps history) instead of reset.
- For GC behavior specifically, you can override without rollback: `SPARK_BRIDGE_GC_EVERY=1`.


Goal: after each performance/correctness optimization, we run a tight set of checks to confirm:
- services are still healthy
- learning/advisory loops still function
- no new log spam, deadlocks, or memory/disk blowups
- we can quickly attribute regressions to a specific commit/optimization

Keep this file updated as we ship more optimizations.

---

## 0) Quick snapshot (run first)

### Service health
Run (Python):

```powershell
cd $env:USERPROFILE\Desktop\vibeship-spark-intelligence
python -c "import json; from lib.service_control import service_status; print(json.dumps(service_status(include_pulse_probe=True), indent=2))"
```

Expect:
- `sparkd/dashboard/pulse/meta_ralph/bridge_worker/scheduler/watchdog` → `running: true`
- bridge_worker + scheduler heartbeats should be fresh (typically < 60s)

### API health endpoints
- sparkd: `http://127.0.0.1:8787/health` → `ok`
- sparkd status: `http://127.0.0.1:8787/status` → JSON, no obvious errors

### Logs directory: last modified
```powershell
Get-ChildItem $env:USERPROFILE\.spark\logs | Sort-Object LastWriteTime -Descending | Select-Object -First 10 Name,Length,LastWriteTime
```

Look for:
- unexpected rapid growth
- repeated crash loops

---

## 1) Optimization items shipped (what to validate)

### Phase 1 behavior upgrades (advisory + learning)

#### H) Agreement-gated advisory escalation (warnings require corroboration)
**Change:** `SPARK_ADVISORY_AGREEMENT_GATE=1` makes WARNING-level advisories require agreement across multiple sources.

**What to look for:**
- You still see **whispers/notes**, but fewer noisy warnings.
- Warnings that appear should have strong backing (multiple sources).

**Checks:**
- Watch GAUR + noise burden via `lib/carmack_kpi.py` scorecard.
- If warnings disappeared completely: either agreement gate too strict or you don't have multi-source overlap yet.

**Knobs:**
- `SPARK_ADVISORY_AGREEMENT_GATE=1|0`
- `SPARK_ADVISORY_AGREEMENT_MIN_SOURCES=2` (default)

---

#### I) Importance sampling under backlog (skip low-priority pattern detection)
**Change:** `SPARK_PIPELINE_IMPORTANCE_SAMPLING=1` skips LOW-priority events in the expensive pattern detection loop when backlog is `critical|emergency`.

**What to look for:**
- Queue drains faster during spikes.
- No drop in learning from **user prompts / failures**.

**Checks:**
- `~/.spark/pipeline_metrics.json`:
  - under backlog: processing_rate_eps ↑, queue_depth_after stabilizes
- Watchdog log should not show new error loops.

**Knobs:**
- `SPARK_PIPELINE_IMPORTANCE_SAMPLING=1|0`
- `SPARK_PIPELINE_LOW_KEEP_RATE=0.25` (default)

---

#### J) Macro mining (temporal tool-sequence abstractions)
**Change:** `SPARK_MACROS_ENABLED=1` mines frequent successful tool n-grams and stores at most one macro insight per cycle.

**What to look for:**
- Over time, you should see macro-style insights appear in cognitive insights (META_LEARNING).

**Checks:**
- Inspect `~/.spark/cognitive_insights.json` for entries starting with `Macro (often works):`.
- Make sure cognitive insights don't explode in count (should be bounded by the min_count + “one per cycle” cap).

**Knobs:**
- `SPARK_MACROS_ENABLED=1|0`
- `SPARK_MACRO_MIN_COUNT=3` (default)

---

### A) Semantic retrieval logging bounded (rotation + sampling)
**Change(s):**
- Rotate `~/.spark/logs/semantic_retrieval.jsonl` when it exceeds a size cap.
- Optional sampling knob to reduce disk I/O.

**What can break:**
- nothing functional; only observability/logging.

**Checks:**
1) File doesn’t grow unbounded:
```powershell
$path = "$env:USERPROFILE\.spark\logs\semantic_retrieval.jsonl"; if(Test-Path $path){ (Get-Item $path).Length } else { "missing" }
```
2) Confirm rotation artifacts appear when large:
- `semantic_retrieval.jsonl.1`, `.2`, ...

**Knobs:**
- `~/.spark/tuneables.json` → `semantic.log_retrievals` (on/off)
- `~/.spark/tuneables.json` → `semantic.log_max_bytes`, `semantic.log_backups`, `semantic.log_sample_rate`

**Symptom → likely cause:**
- “semantic logs missing” → `log_sample_rate=0` or `log_retrievals=false`

---

### B) Advisor capped log writes no longer rewrite every append
**Change(s):**
- `_append_jsonl_capped()` is append-only; compaction is rate-limited.

**What can break:**
- worst case: a capped log can temporarily exceed `max_lines` until compaction runs.
- functional behavior should not change.

**Checks:**
1) No CPU spikes attributable to log rewriting.
2) `~/.spark/advisor/*.jsonl` still gets entries.

**Symptom → likely cause:**
- “advisor logs slightly over cap” → expected until compaction window.

---

### C) Queue lock release correctness fix
**Change(s):**
- queue lock file is only unlinked when acquired.

**What can break:**
- if anything previously relied on the buggy behavior (unlikely).

**Checks:**
1) Queue continues to ingest events.
2) No stuck `.queue.lock` remaining forever.

Inspect:
```powershell
Get-ChildItem $env:USERPROFILE\.spark\queue -Force | Select-Object Name,LastWriteTime
```

**Symptom → likely cause:**
- “queue stops progressing + lock file persists” → dead process holding lock; restart bridge worker.

---

### D) Queue reads stream instead of loading full file
**Change(s):**
- readers stream from disk; avoids full-file list materialization.

**What can break:**
- regression would show up as missing events in consumers or exceptions in processing.

**Checks:**
1) Queue stats look sane:
```powershell
python -c "from lib.queue import get_queue_stats; import json; print(json.dumps(get_queue_stats(), indent=2))"
```
2) Bridge worker continues to process/consume events (queue depth should not grow forever).
3) No repeated exceptions in `bridge_worker.log` / `watchdog.log`.

---

### E) Bridge cycle executor reuse
**Change(s):**
- `_run_step` uses a shared thread pool instead of creating a new one per step.

**What can break:**
- if steps hang, shared workers can become saturated.

**Checks:**
1) `sparkd /status` shows bridge health OK.
2) `bridge_worker_heartbeat.json` stays fresh.
3) Watchdog does not repeatedly restart bridge worker.

**Knobs:**
- `SPARK_BRIDGE_STEP_EXECUTOR_WORKERS` (default 4)
- `SPARK_BRIDGE_STEP_TIMEOUT_S`

**Symptom → likely cause:**
- “bridge cycle stalls / timeouts increase” → a step is blocking and tying up workers; increase workers or investigate the blocking step.

---

### F) Reduced GC frequency (configurable)
**Change(s):**
- GC runs every N cycles (default 3) instead of every cycle.

**What can break:**
- memory could drift upward if GC is actually needed every cycle.

**Checks:**
1) Observe memory over time while running normally (15–60 min).
2) If memory grows unbounded, temporarily set:
   - `SPARK_BRIDGE_GC_EVERY=1`

**Symptom → likely cause:**
- “RAM grows steadily after update” → GC too infrequent OR a real leak; revert this commit or set env override.

---

### G) Advisor prefilter caching
**Change(s):**
- Cache tokens/blobs for advisor prefilter to avoid repeated regex tokenization.

**What can break:**
- incorrect cache invalidation could surface stale tokens (should be low-risk because we hash the full blob).

**Checks:**
1) Advisor still returns advice.
2) No exceptions in advisor path.

**Symptom → likely cause:**
- “advice seems irrelevant after edits” → bug in blob hashing/invalidation; revert this item.

---

## 2) Regression triage flow (when something feels off)

1) Confirm service health (`service_status`).
2) Check `~/.spark/logs/watchdog.log` for restart loops.
3) Check queue depth and whether it’s being consumed.
4) If needed: roll back one optimization at a time via `git revert <sha>` (keep history).

---

## 3) Rollback notes

We ship each optimization as an isolated commit so rollback is one command:

```bash
git revert <commit_sha>

git push origin main
```

Prefer `revert` (keeps history) over `reset`.
