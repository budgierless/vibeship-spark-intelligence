# Release Candidate (RC) Build

Date: 2026-02-15

This document defines how to cut a release candidate for Spark Intelligence and verify it is shippable.

## Versioning

Current package version: `0.1.0` (see `pyproject.toml`).

Recommended RC tags (git):
- `v0.1.0-rc.1`
- `v0.1.0-rc.2` ...

For the public alpha, prefer tagging RCs over bumping package version repeatedly.

## Reproducible Build (Local)

From repo root:

```bash
python -m build
```

Artifacts will appear under `dist/`:
- `vibeship_spark-0.1.0-py3-none-any.whl`
- `vibeship_spark-0.1.0.tar.gz`

## Smoke Test (RC)

1. Install the wheel into a clean venv
2. Start services
3. Verify health

Key commands:
```bash
python -m spark.cli health
python -m spark.cli services
```

Windows (repo operator flow):
```bat
start_spark.bat
```

## Rollback Plan (Minimum)

If launch/RC fails:

1. Roll back to last-green tag:
   - `v0.1.0-rc.N-1` (or last stable)
2. Restart services:
   - `spark down`
   - `spark up --lite` (if the failure involves dashboards/pulse)
3. Disable risky behavior via env flags if needed (document per-incident).

For incident procedure, use: `team/runbooks/INCIDENT_RESPONSE.md` (ops repo) and `runbooks/INCIDENT_RESPONSE.md` if present.

