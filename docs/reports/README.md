# Reports

Point-in-time analysis reports live here.

Reports are evidence snapshots, not policy truth.
For current operational truth, start with:
- `docs/DOCS_INDEX.md`
- `docs/CHANGE_AND_UPGRADE_WORKFLOW.md`
- `TUNEABLES.md`
- `VIBESHIP_OPTIMIZER.md`

## Start Here

- `docs/reports/LATEST.md`: curated list of current high-signal reports.
- `docs/reports/PROMPT_SYSTEM_MASTER_LOG.md`: canonical cross-run prompt-system spine (coverage, decisions, next actions).

## Retention Layout

- `docs/reports/`: current/high-signal reports and curated summaries.
- `docs/archive/docs/reports_self_review/`: archived repetitive self-review logs (tracked history).
- `docs/reports/openclaw/`: OpenClaw-specific benchmark/audit run artifacts.

## Naming Convention

- Use dated report names: `YYYY-MM-DD_<topic>.md` (or timestamped variants where needed).
- Keep generated JSON companions near their report when they are direct evidence.

## Hygiene Rules

- Do not treat report conclusions as permanent policy without promotion into canonical docs.
- Move repetitive run logs into `docs/archive/docs/reports_self_review/` to keep top-level scanning efficient.
- Keep `LATEST.md` short and decision-focused.

### Archive helper

Use:
`python scripts/archive_self_reviews.py --apply --keep-latest 3`
