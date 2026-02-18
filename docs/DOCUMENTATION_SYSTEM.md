# Spark Documentation System

Date: 2026-02-18
Scope: `vibeship-spark-intelligence` + integration touchpoints with `vibeship-spark-consciousness`

## Why This Exists

Documentation volume grew faster than documentation governance.
This file defines the mandatory system for keeping docs clean, non-contradictory, and current.

## Documentation Layers (Authority Order)

1. Runtime truth (highest)
- Code behavior, tests, and live health/status endpoints.

2. Canonical operator docs
- `docs/DOCS_INDEX.md`
- `docs/CHANGE_AND_UPGRADE_WORKFLOW.md`
- `TUNEABLES.md`
- `VIBESHIP_OPTIMIZER.md`
- `docs/PROGRAM_STATUS.md`

3. Domain runbooks/specs
- Integration and subsystem docs (OpenClaw, advisory, retrieval, observability, security, support).

4. Point-in-time reports
- `docs/reports/` (evidence snapshots, not policy truth).

5. Archive
- `docs/archive/` (historical reference only).

If a lower layer conflicts with a higher layer, update or archive the lower layer.

## Mandatory Change Rule

Any runtime behavior change is incomplete unless these are updated in the same change set:
- runtime code/tests,
- impacted canonical docs/runbooks,
- optimizer evidence (`before`, `after`, compare, decision).

Use:
- `docs/CHANGE_AND_UPGRADE_WORKFLOW.md`
- `VIBESHIP_OPTIMIZER.md`

## Doc Hygiene Rules

1. One canonical source per topic
- Avoid parallel "how it works" docs for the same surface.
- Non-canonical docs must point to the canonical one in the first section.

2. Keep index curated
- `docs/DOCS_INDEX.md` lists canonical/active docs only.
- Do not list every historical report.

3. Keep reports structured
- Current highlights live in `docs/reports/LATEST.md`.
- Historical runs stay in dated files and `docs/archive/docs/reports_self_review/`.

4. Archive stale documents
- Archive when a doc is superseded, duplicated, or no longer operationally used.
- Move, do not delete, unless explicitly approved.

5. Minimize contradiction risk
- If docs conflict, treat as incident-level documentation bug and fix in the next commit.

## Archive Policy

Archive candidates:
- superseded implementation plans,
- duplicated operational guides,
- repetitive generated reports no longer used for daily operation.

Archive method:
1. Move file to `docs/archive/...` (preserve relative category where possible).
2. Add a one-line pointer in the active replacement doc if needed.
3. Record the change in a short report note under `docs/reports/`.

## Reports Retention Policy

- Keep current-facing summary in `docs/reports/LATEST.md`.
- Keep historical evidence in date-stamped files.
- Move repetitive run artifacts (for example repeated self-reviews) into tracked archive folders under `docs/archive/docs/`.
- Keep only recent quick-access runs at `docs/reports/` root when useful.

## Cross-Repo Sync (Spark Consciousness)

For any contract/interface touching both repos:
1. Update docs in both repos in the same change window.
2. Validate bridge contracts with tests/smoke.
3. Log evidence in the Spark Intelligence report for traceability.

Minimum cross-repo references to keep aligned:
- `docs/architecture/CONSCIOUSNESS_INTELLIGENCE_ALIGNMENT_TASK_SYSTEM.md`
- `docs/CONSCIOUSNESS_BRIDGE_V1.md`
- `docs/reports/LATEST.md` (latest integration verification pointer)

## Operating Cadence

Daily:
1. Confirm new changes updated affected docs.
2. Add latest report pointer if a major validation ran.

Weekly:
1. Archive stale/duplicate docs and repetitive run artifacts.
2. Re-check `docs/DOCS_INDEX.md` against active operational reality.

Monthly:
1. Full docs integrity pass: contradictions, stale commands/ports/paths, missing references.
2. Cross-repo contract review with Spark Consciousness.

## Definition Of Done For Documentation

A change is complete only when:
- canonical docs are updated,
- historical evidence is linked (if behavior changed),
- rollback path is documented,
- stale parallel docs are either updated to pointer form or archived.
