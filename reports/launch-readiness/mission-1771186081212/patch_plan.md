# Patch Plan (Post-Launch / Pre-Launch Remediation)

Date: 2026-02-16

Current state:
- GO/NO-GO is **NO-GO** (see `GO_NO_GO.md`).

## P0 Fixes (Blockers)

### 1) Hooks Not Firing (Integration Status DEGRADED)

Symptom:
- `python -m lib.integration_status` reports no `pre_tool` / `post_tool` events.

Why it matters:
- Without pre/post tool events, the learning loop does not observe real work, so the product value collapses.

Fix plan:
- Create a “clean machine” hook verification checklist:
  - correct `.claude/settings.json` hook command paths
  - `observe.py` executable and reachable
  - Python in PATH for the host app
  - restart host app after config changes
- Add a dedicated verification command (candidate): `spark validate-ingest` or similar (already exists in CLI list) and document it in `docs/GETTING_STARTED_5_MIN.md`.
- Add one small “hook smoke test” in docs that users can run to confirm events are flowing.

Success criteria:
- `integration_status` shows non-zero pre/post tool events within 5 minutes of a normal session.

### 2) Meta-Ralph Quality Band (Production Gates NOT READY)

Symptom:
- `scripts/production_loop_report.py` fails `meta_ralph_quality_band`.

Why it matters:
- Quality gates must be trustworthy. A permanently-low band means either:
  - the input stream is mostly primitive/noise, OR
  - thresholds are miscalibrated, OR
  - the classifier is mislabeling.

Fix plan:
- Reduce primitive/noise at the source:
  - ensure trivial tool calls are filtered before reaching Meta-Ralph
  - confirm dedupe + primitive filtering is enabled
- Calibrate thresholds based on a representative evaluation window.
- Verify after each change by re-running:
  - `python scripts/production_loop_report.py`

Success criteria:
- `meta_ralph_quality_band` passes within target range without gaming the metric.

## P1 (Before Launch)

- Set a real security contact email in `SECURITY.md`.
- Add a short “first run” section that explicitly mentions `/status` (JSON readiness) vs `/health` (liveness).

## Re-Run Checklist

- `python tests/test_pipeline_health.py`
- `python -m lib.integration_status`
- `python scripts/production_loop_report.py`

