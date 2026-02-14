# Docs + Tuneables Surface Sync v1

Date: 2026-02-14

## Goal

Reduce configuration + terminology confusion by aligning docs with the current runtime tuneables surfaces, and pruning telemetry-heavy observer logging so future sessions are easier to interpret.

## Changes Made

- Unified retrieval router docs to the canonical schema:
  - Canonical surface: `~/.spark/tuneables.json` -> `retrieval.overrides.*`
  - Added explicit docs for routing thresholds: `semantic_context_min`, `semantic_lexical_min`, `semantic_strong_override`
  - Updated: `TUNEABLES.md`, `docs/RETRIEVAL_LEVELS.md`, `Intelligence_Flow.md`
- Refreshed the recommended `~/.spark/tuneables.json` example block to match current shipped baseline sections/values (and removed stale/optional sections that are not present in the current baseline).
  - Updated: `TUNEABLES.md`
- Clarified Mind inclusion control:
  - `advisory_engine.include_mind` is the tuneable surface; `SPARK_ADVISORY_INCLUDE_MIND` is the default when tuneable is absent.
  - Updated: `TUNEABLES.md`, `Intelligence_Flow.md`
- Defined "shadow run" explicitly to avoid contract-benchmark confusion.
  - Updated: `docs/GLOSSARY.md`, `docs/ADVISORY_REALISM_PLAYBOOK.md`
- Updated older reports/docs that still claimed auto-tuner execution was missing.
  - Added explicit "Update (2026-02-14)" notes.
  - Updated: `docs/reports/EIDOS_REHABILITATION_REPORT_2026-02-07.md`, `docs/reports/EVOLUTION_FILTER_REPORT_V2_2026-02-07.md`, `docs/x-social/EVOLUTION.md`
- Pruned telemetry-heavy observer logging:
  - Chip observer runtime no longer logs every captured insight at INFO.
  - INFO is now reserved for `working` + `long_term` tiers; `session` tier is DEBUG.
  - Updated: `lib/chips/runtime.py`

## Tests

Ran:

```bash
python -m pytest -q tests/test_chips_runtime_filters.py tests/test_advisor_retrieval_routing.py tests/test_advisory_quality_ab.py
```

Result: 29 passed. (Non-fatal pytest atexit cleanup permission error on Windows temp dir was observed.)

