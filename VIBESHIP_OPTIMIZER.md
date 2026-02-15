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

### chg-20260215-132034-advisory-speed-force-programmatic-sy — Advisory speed: force programmatic synth + packet index cache

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
