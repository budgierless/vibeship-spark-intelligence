# Spark Intelligence â€” Optimization Checker

This file is the **post-optimization validation playbook**.

This repo also uses `vibeship-optimizer` as the standard optimization change tracker:
- Durable optimization logbook: `VIBESHIP_OPTIMIZER.md`
- Config (tracked): `vibeship_optimizer.yml`
- Reports (tracked): `reports/optimizer/`

---

## Shipped optimization changelog (rollback map)

These optimizations were shipped as isolated commits so we can `git revert <sha>` one-at-a-time.

### Current optimization batch (2026-02-14)

1) `e4c1473` â€” Bound semantic retrieval log growth (rotation)
2) `f094b59` â€” Avoid rewrite-on-append in capped advisor logs
3) `437b383` â€” Fix queue lock release to not unlink when unacquired
4) `2ad3d28` â€” Stream queue reads to avoid full-file loads
5) `63729d7` â€” Reuse shared executor for bridge steps
6) `e687f8a` â€” Reduce bridge cycle GC frequency (configurable)
7) `2c4a31f` â€” Cache advisor prefilter tokenization
8) `cca5c76` â€” Add sampling knob for semantic retrieval logging
9) `7340030` â€” Add optimization checker playbook
10) `3619dd4` â€” Docs: add rollback-map changelog to optimization checker

### Phase-1 behavior upgrades (2026-02-14)
11) `7ceca23` â€” Advisory: require agreement before warning escalation (flagged)
12) `9439361` â€” Pipeline: importance-sample low-priority events under backlog (flagged)
13) `81d627e` â€” Pipeline: mine successful tool macros (flagged)

### Phase-2 memory upgrades (2026-02-14)
14) `fec25da` â€” Memory store: patchified (chunked) storage and parent dedupe (flagged)
15) `7c05d8b` â€” Memory store: optional delta compaction for near-duplicate memories (flagged)

### Phase-3 advisory intelligence (2026-02-14)
16) `5c69b10` â€” Outcome predictor: lightweight risk scoring + advisory gate boost (flagged)
17) `043e81b` â€” Tools: offline tune replay harness (safe suggest-by-default)

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
cd /path/to/vibeship-spark-intelligence
python -c "import json; from lib.service_control import service_status; print(json.dumps(service_status(include_pulse_probe=True), indent=2))"
```

Expect:
- `sparkd/dashboard/pulse/meta_ralph/bridge_worker/scheduler/watchdog` â†’ `running: true`
- bridge_worker + scheduler heartbeats should be fresh (typically < 60s)

### API health endpoints
- sparkd: `http://127.0.0.1:8787/health` â†’ `ok`
- sparkd status: `http://127.0.0.1:8787/status` â†’ JSON, no obvious errors

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
  - under backlog: processing_rate_eps â†‘, queue_depth_after stabilizes
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
- Make sure cognitive insights don't explode in count (bounded by min_count + the â€œone per cycleâ€ cap).

**Knobs:**
- `SPARK_MACROS_ENABLED=1|0`
- `SPARK_MACRO_MIN_COUNT=3` (default)

---

### Phase 2 memory upgrades (precision + size control)

#### K) Patchified memory store (chunked storage + parent dedupe)
**Change:** `SPARK_MEMORY_PATCHIFIED=1` stores long memories as multiple chunk entries for more precise retrieval, while returning at most one hit per parent group.

**What to look for:**
- Retrieval results feel *more specific* (less giant irrelevant blobs).
- Memory store size growth slows (fewer huge content rows).

**Checks:**
- DB exists: `%USERPROFILE%\.spark\memory_store.sqlite`
- Spot-check retrieval:
  ```powershell
  python -c "from lib.memory_store import retrieve; import json; print(json.dumps(retrieve('oauth', limit=6), indent=2)[:1200])"
  ```
- Ensure results donâ€™t include multiple `#pN` chunks from the same parent in the top-k.

**Knobs:**
- `SPARK_MEMORY_PATCHIFIED=1|0`
- `SPARK_MEMORY_PATCH_MAX_CHARS=600` (default)
- `SPARK_MEMORY_PATCH_MIN_CHARS=120` (default)

---

#### L) Delta memory compaction (store updates as deltas when near-duplicate)
**Change:** `SPARK_MEMORY_DELTAS=1` attempts to store only the â€œdeltaâ€ when a new memory is very similar to a recent one (same scope/project/category).

**What to look for:**
- Repeated re-statements become short â€œUpdate (delta from â€¦)â€ rows.
- Retrieval stays useful (deltas still understandable).

**Checks:**
- Search for delta entries:
  ```powershell
  python -c "import sqlite3; from pathlib import Path; db=Path.home()/'.spark'/'memory_store.sqlite'; conn=sqlite3.connect(str(db)); rows=conn.execute(\"select memory_id, content from memories where content like 'Update (delta from %' order by created_at desc limit 5\").fetchall(); print(rows); conn.close()"
  ```

**Knobs:**
- `SPARK_MEMORY_DELTAS=1|0`
- `SPARK_MEMORY_DELTA_MIN_SIM=0.86` (default)

---

### Phase 3 advisory intelligence

#### M) Outcome predictor (world-model-lite) for risk-aware advisories
**Change:** `SPARK_OUTCOME_PREDICTOR=1` enables a tiny success/failure predictor keyed by `(phase, intent_family, tool)`.

**What to look for:**
- Cautionary advisories become slightly more insistent when Spark has evidence that a tool/intent combo often fails.
- No added latency spikes on PreTool (predictor is just counters + cache).

**Checks:**
- Predictor file exists and grows slowly:
  - `%USERPROFILE%\.spark\outcome_predictor.json`
- Optional: print predictor stats:
  ```powershell
  python -c "from lib.outcome_predictor import get_stats; import json; print(json.dumps(get_stats(), indent=2))"
  ```

**Knobs:**
- `SPARK_OUTCOME_PREDICTOR=1|0`

---

#### N) Offline tune replay harness (suggest-by-default)
**Change:** `scripts/tune_replay.py` generates a report combining KPI + tuning suggestions. It is safe by default and does **not** apply changes unless `--apply` is passed.

**What to look for:**
- Running the script produces a markdown report you can skim in under a minute.
- No tuneables changes unless explicitly requested.

**Checks:**
- Generate report:
  ```powershell
  python scripts/tune_replay.py --out reports\\tune_replay_latest.md
  ```
- (Optional) apply recommendations (not default):
  ```powershell
  python scripts/tune_replay.py --apply --mode moderate
  ```
  This uses the built-in tuneable history snapshots for rollback.
- (Optional) also apply source boost tuning (touches many sources; keep off unless intended):
  ```powershell
  python scripts/tune_replay.py --apply --apply-boosts --mode moderate
  ```

**Knobs:**
- CLI-only: `--apply`, `--mode {conservative|moderate|aggressive}`, `--out <path>`

---

### A) Semantic retrieval logging bounded (rotation + sampling)
**Change(s):**
- Rotate `~/.spark/logs/semantic_retrieval.jsonl` when it exceeds a size cap.
- Optional sampling knob to reduce disk I/O.

**What can break:**
- nothing functional; only observability/logging.

**Checks:**
1) File doesnâ€™t grow unbounded:
```powershell
$path = "$env:USERPROFILE\.spark\logs\semantic_retrieval.jsonl"; if(Test-Path $path){ (Get-Item $path).Length } else { "missing" }
```
2) Confirm rotation artifacts appear when large:
- `semantic_retrieval.jsonl.1`, `.2`, ...

**Knobs:**
- `~/.spark/tuneables.json` â†’ `semantic.log_retrievals` (on/off)
- `~/.spark/tuneables.json` â†’ `semantic.log_max_bytes`, `semantic.log_backups`, `semantic.log_sample_rate`

**Symptom â†’ likely cause:**
- â€œsemantic logs missingâ€ â†’ `log_sample_rate=0` or `log_retrievals=false`

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

**Symptom â†’ likely cause:**
- â€œadvisor logs slightly over capâ€ â†’ expected until compaction window.

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

**Symptom â†’ likely cause:**
- â€œqueue stops progressing + lock file persistsâ€ â†’ dead process holding lock; restart bridge worker.

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

**Symptom â†’ likely cause:**
- â€œbridge cycle stalls / timeouts increaseâ€ â†’ a step is blocking and tying up workers; increase workers or investigate the blocking step.

---

### F) Reduced GC frequency (configurable)
**Change(s):**
- GC runs every N cycles (default 3) instead of every cycle.

**What can break:**
- memory could drift upward if GC is actually needed every cycle.

**Checks:**
1) Observe memory over time while running normally (15â€“60 min).
2) If memory grows unbounded, temporarily set:
   - `SPARK_BRIDGE_GC_EVERY=1`

**Symptom â†’ likely cause:**
- â€œRAM grows steadily after updateâ€ â†’ GC too infrequent OR a real leak; revert this commit or set env override.

---

### G) Advisor prefilter caching
**Change(s):**
- Cache tokens/blobs for advisor prefilter to avoid repeated regex tokenization.

**What can break:**
- incorrect cache invalidation could surface stale tokens (should be low-risk because we hash the full blob).

**Checks:**
1) Advisor still returns advice.
2) No exceptions in advisor path.

**Symptom â†’ likely cause:**
- â€œadvice seems irrelevant after editsâ€ â†’ bug in blob hashing/invalidation; revert this item.

---

## 2) Regression triage flow (when something feels off)

1) Confirm service health (`service_status`).
2) Check `~/.spark/logs/watchdog.log` for restart loops.
3) Check queue depth and whether itâ€™s being consumed.
4) If needed: roll back one optimization at a time via `git revert <sha>` (keep history).

---

## 3) Rollback notes

We ship each optimization as an isolated commit so rollback is one command:

```bash
git revert <commit_sha>

git push origin main
```

Prefer `revert` (keeps history) over `reset`.

### chg-20260214-190329-repo-lightweight-untrack-large-gener â€” Repo lightweight: untrack large generated artifacts

- Status: **PLANNED**
- Started: `2026-02-14T19:03:29Z`
- Commit: ``
- Baseline snapshot: ``
- After snapshot: ``

**Hypothesis:**
Removing generated mp4/auto-score artifacts from git reduces repo bloat and speeds clones.

**Risk:**
Low: untracks only generated artifacts; files remain local.

**Rollback:**
git revert <sha>

**Validation Today:**
Confirm Spark still runs; visuals/out is regenerable; advisory auto score can be regenerated.

**Validation Next Days:**
No issues; artifacts continue to be generated locally but not committed.

**Verification log:**
- Day 0: 
- Day 1: 
- Day 2: 
- Day 3: 

- Mark verified: [ ]

### chg-20260214-190824-advisory-quick-fallback-when-time-bu â€” Advisory: quick fallback when time budget is low

- Status: **PLANNED**
- Started: `2026-02-14T19:08:24Z`
- Commit: ``
- Baseline snapshot: ``
- After snapshot: ``

**Hypothesis:**
When live advisory is slow or budget is tight, a quick deterministic hint increases real-time advisory delivery + usage without adding latency.

**Risk:**
Low: uses baseline/quick advice only when remaining_ms is low; still gated + duplicate-suppressed; flagged.

**Rollback:**
git revert <sha>

**Validation Today:**
Run services; check advisories still appear; ensure no new crashes; check advisory_engine logs for route=live_quick.

**Validation Next Days:**
Monitor for increased delivered advisories with stable noise burden; ensure no spam via repeat cooldown.

**Verification log:**
- Day 0: 
- Day 1: 
- Day 2: 
- Day 3: 

- Mark verified: [ ]

### chg-20260214-192454-advisory-action-first-formatting-nex â€” Advisory: action-first formatting (Next check first line)

- Status: **PLANNED**
- Started: `2026-02-14T19:24:54Z`
- Commit: ``
- Baseline snapshot: ``
- After snapshot: ``

**Hypothesis:**
Putting the actionable Next check command first increases real-time advisory follow-through without increasing noise.

**Risk:**
Low: formatting-only; no new advice content; flagged.

**Rollback:**
git revert <sha>

**Validation Today:**
Trigger advisories; confirm format shows Next check first line; check duplicate suppression still works; ensure no crashes.

**Validation Next Days:**
Watch advice_followed rate + noise_burden; ensure no spam.

**Verification log:**
- Day 0: 
- Day 1: 
- Day 2: 
- Day 3: 

- Mark verified: [ ]

#### Verification update: chg-20260214-192454-advisory-action-first-formatting-nex Day 0
- Date (UTC): `2026-02-14`
- Report: `<REPO_ROOT>/.optcheck/reports/2026-02-14_day0_chg-20260214-192454-advisory-action-first-formatting-nex.md`
- Summary: sizes delta=+8362 bytes

#### Verification update: chg-20260214-192454-advisory-action-first-formatting-nex Day 3
- Date (UTC): `2026-02-17`
- Report: `<REPO_ROOT>/.optcheck/reports/2026-02-17_day3_chg-20260214-192454-advisory-action-first-formatting-nex.md`
- Summary: sizes delta=+60372784 bytes

