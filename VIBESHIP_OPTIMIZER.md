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

- Config file (tracked): `vibeship_optimizer.json`
- Output reports (tracked): `reports/optimizer/`

---

## Optimization Log

<!-- Append change records here via vibeship-optimizer. -->

