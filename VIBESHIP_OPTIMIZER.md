# vibeship-optimizer (Spark Intelligence)

This is the durable optimization logbook for this repo.

Rules:
- One optimization per commit (easy revert).
- Prefer flags/knobs. Risky changes must be opt-in.
- Always capture before/after snapshots (vibeship-optimizer).
- Always capture domain KPIs for advisory (Spark).
- Monitor 3+ days before marking VERIFIED.

---

## Quick Loop (Operator Commands)

1) Init (idempotent):

```powershell
python -m vibeship_optimizer init --no-prompt
```

2) Start a change record:

```powershell
python -m vibeship_optimizer change start --title "..."
```

3) Snapshot before:

```powershell
python -m vibeship_optimizer snapshot --label before --change-id <chg-id> --as before
```

4) Make one optimization + commit (Spark repo).

5) Snapshot after:

```powershell
python -m vibeship_optimizer snapshot --label after --change-id <chg-id> --as after
```

6) Compare snapshots:

```powershell
python -m vibeship_optimizer compare --before <before.json> --after <after.json> --out reports/optimizer/<chg-id>_compare.md
```

7) Spark-specific advisory KPI capture (critical path):

```powershell
python scripts/advisory_controlled_delta.py --rounds 80 --label <chg-id> --force-live --out reports/optimizer/<chg-id>_advisory_delta.json
```

8) Verify (after 3+ days monitoring):

```powershell
python -m vibeship_optimizer change verify --change-id <chg-id>
python -m vibeship_optimizer change verify --change-id <chg-id> --apply --summary "..."
```

---

## Canonical Config

- Config file (tracked): `vibeship_optimizer.yml`
- Output reports (tracked): `reports/optimizer/`

---

## Optimization Log

<!-- Append change records here via vibeship-optimizer. -->

### chg-20260215-132034-advisory-speed-force-programmatic-sy - Advisory speed: force programmatic synth + packet index cache

- Status: **SHIPPED**
- Started: `2026-02-15T13:20:34Z`
- Commit: `79c9895`
- Baseline snapshot: `reports/optimizer/chg-20260215-132034_before_snapshot.json`
- After snapshot: `reports/optimizer/chg-20260215-132034_after_snapshot.json`
- Snapshot compare: `reports/optimizer/chg-20260215-132034_compare.md`
- Advisory KPI (before): `reports/optimizer/chg-20260215-132034_advisory_delta_before.json`
- Advisory KPI (after): `reports/optimizer/chg-20260215-132034_advisory_delta_after.json` (run with `SPARK_ADVISORY_FORCE_PROGRAMMATIC_SYNTH=1`)

**Hypothesis:**
- Reduce advisory hot-path time by removing AI synthesis from the critical path (programmatic-only option) and making packet lookup faster (index cache).

**Risk:**
- Advisory text quality may regress in cases where AI synthesis helped. Keep `force_programmatic_synth` opt-in.

**Rollback:**
git revert <sha>

**Validation Today:**
- `scripts/advisory_controlled_delta.py` run saved (before/after JSON above).
- `vibeship-optimizer compare` saved (snapshot compare above).

**Validation Next Days:**
- Monitor advisory usefulness vs noise, and watch for any increased `no_emit` share.

**Verification log:**
- Day 0: 
- Day 1: 
- Day 2: 
- Day 3: 

- Mark verified: [ ]

### chg-20260215-142935-step1-advisory-speed-default-force_p - Step1: advisory speed default (force_programmatic_synth default true)

- Status: **SHIPPED**
- Started: `2026-02-15T14:29:35Z`
- Commit: `a50bda1`
- Baseline snapshot: `reports/optimizer/chg-20260215-142935-step1-advisory-speed-default-force_p_before_snapshot.json`
- After snapshot: `reports/optimizer/chg-20260215-142935-step1-advisory-speed-default-force_p_after_snapshot.json`
- Snapshot compare: `reports/optimizer/chg-20260215-142935-step1-advisory-speed-default-force_p_compare.md`
- Advisory KPI: `reports/optimizer/chg-20260215-142935-step1-advisory-speed-default-force_p_advisory_delta.json`

**Hypothesis:**
- Advisory should be fast and deterministic by default. Network/LLM synthesis becomes an explicit opt-in for cases that can afford it.

**Risk:**
- Advisory text quality may regress for complex scenarios. Override with `SPARK_ADVISORY_FORCE_PROGRAMMATIC_SYNTH=0` or `advisory_engine.force_programmatic_synth=false`.

**Rollback:**
git revert <sha>

**Validation Today:**
- `python -m pytest -q tests/test_advisory_dual_path_router.py`
- `scripts/advisory_controlled_delta.py` run saved (KPI JSON above)
- `vibeship-optimizer compare` saved (snapshot compare above)

**Validation Next Days:**
- Watch advisory usefulness vs repetition/noise, and confirm no tail-latency regressions on real sessions.

**Verification log:**
- Day 0: 
- Day 1: 
- Day 2: 
- Day 3: 

- Mark verified: [ ]

### chg-20260215-144142-step2-self-evolution-speed-stable-se - Step2: self-evolution speed (stable session_context_key)

- Status: **SHIPPED**
- Started: `2026-02-15T14:41:42Z`
- Commit: `4ba134b`
- Baseline snapshot: `reports/optimizer/chg-20260215-144142-step2-self-evolution-speed-stable-se_before_snapshot.json`
- After snapshot: `reports/optimizer/chg-20260215-144142-step2-self-evolution-speed-stable-se_after_snapshot.json`
- Snapshot compare: `reports/optimizer/chg-20260215-144142-step2-self-evolution-speed-stable-se_compare.md`
- Advisory KPI (live): `reports/optimizer/chg-20260215-144142-step2-self-evolution-speed-stable-se_advisory_delta.json`
- Advisory KPI (cached): `reports/optimizer/chg-20260215-144142-step2-self-evolution-speed-stable-se_advisory_delta_cached.json`

**Hypothesis:**
- If inline prefetch processes the newest job first (and only scans a bounded tail of the queue), packet creation aligns with the current session and `packet_exact` hit rate rises quickly.

**Risk:**
- Tail-reading and newest-first prefetch can starve older queued jobs. This is intentional for interactive sessions but should be revisited if we ever need strict background processing.

**Rollback:**
git revert <sha>

**Validation Today:**
- `python -m pytest -q tests/test_advisory_dual_path_router.py`
- `scripts/advisory_controlled_delta.py` runs saved (KPI JSONs above)
- `vibeship-optimizer compare` saved (snapshot compare above)

**Validation Next Days:**
- Monitor packet exact-hit rate in real sessions and confirm inline prefetch does not increase hook latency tails.

**Verification log:**
- Day 0: 
- Day 1: 
- Day 2: 
- Day 3: 

- Mark verified: [ ]

### chg-20260215-150244-step3-latency-tail-deny-agentic-esca - Step3: latency tail (deny agentic escalation when over budget)

- Status: **SHIPPED**
- Started: `2026-02-15T15:02:44Z`
- Commit: `3b7f457`
- Baseline snapshot: `reports/optimizer/chg-20260215-150244-step3-latency-tail-deny-agentic-esca_before_snapshot.json`
- After snapshot: `reports/optimizer/chg-20260215-150244-step3-latency-tail-deny-agentic-esca_after_snapshot.json`
- Snapshot compare: `reports/optimizer/chg-20260215-150244-step3-latency-tail-deny-agentic-esca_compare.md`
- Advisory KPI (live): `reports/optimizer/chg-20260215-150244-step3-latency-tail-deny-agentic-esca_advisory_delta.json`
- Advisory KPI (cached): `reports/optimizer/chg-20260215-150244-step3-latency-tail-deny-agentic-esca_advisory_delta_cached.json`

**Hypothesis:**
- Reduce p95/p99 tail by cutting agentic escalation in auto mode when the semantic fast path is already weak/slow.

**Risk:**
- Retrieval quality may regress for borderline queries that benefited from agentic facet queries.

**Rollback:**
git revert <sha>

**Validation Today:**
- `python -m pytest -q tests/test_advisory_dual_path_router.py`
- `scripts/advisory_controlled_delta.py` runs saved (KPI JSONs above)
- `vibeship-optimizer compare` saved (snapshot compare above)

**Validation Next Days:**
- Monitor `~/.spark/advisor/retrieval_router.jsonl` for reduced `semantic-agentic` share and validate quality on hard queries.

**Verification log:**
- Day 0: 
- Day 1: 
- Day 2: 
- Day 3: 

- Mark verified: [ ]
