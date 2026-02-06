# Spark Intelligence

Spark is a self-evolving intelligence layer for agent workflows.
It captures signals, distills learnings, validates outcomes, and reuses proven guidance in future decisions.

Navigation hub: `docs/GLOSSARY.md`

## Start

1. Install and boot services: `docs/QUICKSTART.md`
2. Read runtime architecture: `Intelligence_Flow.md`
3. Tune behavior: `TUNEABLES.md`
4. Use full docs map: `docs/DOCS_INDEX.md`

## Production Hardening Notes

- `sparkd` now enforces `SPARKD_TOKEN` across all mutating `POST` routes (`/ingest`, `/process`, `/reflect`, etc.).
- Bridge cycles run both prompt validation and outcome-linked validation.
- Queue rotation and queue consumption use temp-file + replace semantics to reduce data-loss windows.
- Meta-Ralph dashboard binds to `127.0.0.1` by default.
- CI workflow is defined in `.github/workflows/ci.yml` (`ruff` critical checks + pytest gates).

## Core Runtime Docs

- `Intelligence_Flow.md`
- `Intelligence_Flow_Map.md`
- `EIDOS_GUIDE.md`
- `META_RALPH.md`
- `SEMANTIC_ADVISOR_DESIGN.md`
- `docs/PROGRAM_STATUS.md`
- `PRODUCTION_READINESS.md`
- `docs/VISION.md`

## Strategic Docs Kept Active

- `MoE_Plan.md`
- `Path to AGI.md`
- `EVOLUTION_CHIPS_RESEARCH.md`

## Documentation Consolidation

Superseded planning and historical docs have been moved to:
- `docs/archive/`
- `docs/reports/`

Use `docs/DOCS_INDEX.md` as the source of truth for active docs.
