# Vibecoding Chip (v1)

Status: documentation only. No implementation has started.

## Purpose
Teach Spark how to learn from engineering signals: code changes, reviews, tests,
deploys, incidents, and user outcomes. The chip should be useful even without
external integrations, but grow in value when MCP data is available.

## Inputs
### Required event schema
All inputs must be valid SparkEventV1 (see `lib/events.py`):
- v, source, kind, ts, session_id, payload

### MCP profiles and categories (v1)
- VibeShip: Idearalph, Mind, Spawner, Scanner, Suparalph, Knowledge Base.
- Repo / PR / diff / review signals.
- CI / tests / coverage signals.
- Deploy / release signals.
- Runtime / observability signals.
- Product analytics signals.
- Design / UX signals.
- Support / feedback signals.

## MCP schemas (draft)
These are the minimal payload fields the chip expects per profile. All fields are
optional unless marked required by an observer.

### VibeShip MCPs
- Idearalph: idea_id, title, spec_summary, risk_tags, decisions
- Mind: memory_id, query, results_count, top_memories
- Spawner: route_id, skills, stack_recommendations, confidence
- Scanner: scan_id, target, findings_count, severity_counts, fix_suggestions
- Suparalph: test_id, db_target, security_findings, migrations, query_profile
- Knowledge Base: doc_id, topic, snippets, citations

### Engineering categories
- Repo/PR: repo, pr_id, author, review_state, merge_state, changed_files, line_stats
- CI/Test: build_id, status, duration_s, failed_tests, coverage_delta
- Deploy: release_id, env, status, rollback, deploy_duration_s
- Runtime: service, metric_name, metric_value, threshold, incident_id
- Product: feature_id, metric_name, metric_delta, period
- Design/UX: design_id, figma_file, accessibility_score, lighthouse_score
- Support: ticket_id, category, severity, resolution_time_s, sentiment

## Scopes (draft)
All scopes are opt-in and disabled by default.

### VibeShip MCP scopes
- mcp.idearalph.read
- mcp.mind.read
- mcp.spawner.read
- mcp.scanner.read
- mcp.suparalph.read
- mcp.knowledge_base.read

### Engineering data scopes
- repo.read
- repo.diff.read
- pr.read
- ci.read
- deploy.read
- observability.read
- product_analytics.read
- design.read
- support.read

## Triggers (high level)
- Code change events: commit, diff, file change, refactor, lint/format.
- Review events: PR opened, review requested, comments resolved, merge status.
- CI events: test failures, flaky tests, coverage change, build warnings.
- Deploy events: rollout, rollback, canary, release notes.
- Runtime events: errors, latency spikes, SLO breaches.
- Product signals: feature adoption, churn, funnel changes.
- Design signals: accessibility regressions, Lighthouse score drops.
- Support signals: bug themes, top complaints, escalation spikes.

## Extraction (example fields)
| Field | Notes |
|------|-------|
| repo | repo or service name |
| branch | branch name |
| pr_id | PR number or URL |
| commit_id | commit SHA |
| files_changed | count |
| diff_lines | added/removed |
| test_name | failing test identifier |
| error_code | exception or status code |
| release_id | build/release identifier |
| incident_id | incident ticket or pager |
| metric_name | latency/error_rate/etc |
| metric_delta | change or % |
| user_impact | adoption/churn/CSAT delta |

## Outcomes (examples)
- PR merged without rollback within N days.
- CI failure rate drops after a fix.
- Incident resolved with a documented prevention.
- Latency/error rate improves and stays within SLO.
- Feature adoption increases without support spikes.

## Prediction linking
Each prediction includes:
- prediction_id (stable)
- entity refs: repo, pr_id, incident_id, release_id
- time window: observed_at -> max_age_s

Outcomes link by entity + time window with an optional text match.

## Permissions and scopes
Default to least-privilege. Explicit opt-in for:
- Repo access, PR metadata, diff content
- CI logs and test output
- Deploy history and release notes
- Runtime metrics and incident logs
- Product analytics data
- Support tickets or feedback logs
- Design files (e.g., Figma or Lighthouse)

## Evaluation and replay
- Run against a saved event log.
- Report: precision, recall, outcome coverage, false positives.
- Emit a short, human-readable summary per chip run.

## Minimal YAML skeleton (v1)
```yaml
chip:
  id: vibecoding
  name: Vibecoding Intelligence
  version: 1.0.0
  description: Learns engineering signals from code to outcomes.
  author: Vibeship
  license: MIT
  domains: [engineering, code, delivery, reliability]

triggers:
  events: [code_change, pr_opened, test_failed, deploy_finished, incident_opened]
  patterns: ["refactor", "rollback", "flaky test", "latency spike"]

observers:
  - name: code_change
    required: [repo, commit_id]
    optional: [files_changed, diff_lines]
  - name: ci_failure
    required: [repo, test_name, error_code]
    optional: [branch, pr_id]

outcomes:
  success:
    - name: stable_merge
      when: "pr_merged && no_rollback_in_7d"
  failure:
    - name: rollback
      when: "deploy_rollback"
```

## Open questions
- Which MCPs are available immediately and which are planned?
- What is the default time window for PR and deploy outcomes?
- Do we store chip-level predictions in core Spark or per-chip files?
