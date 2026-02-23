# PR Review Automation System (Spark Intelligence)

## Goal
Build a combined automation for:
1) PR triage/review queue automation
2) bug/repro/fix-plan automation

This system must prioritize **high-value PRs**, reduce review noise, and enforce security gates for open-source contribution safety.

## Observed Repo State (initial research)
- Repository: `vibeforge1111/vibeship-spark-intelligence`
- Open PR queue is very large and heavily skewed toward test-only PRs.
- Many PRs are single-file, test-heavy contributions from one contributor pattern.
- This creates review debt and can hide high-impact code/security changes.
- Open issue #92 indicates a security hardening need (`plugins.allow` empty warning).

## Combined System: "Spark PR Sentinel"

### Stage A — Intake & Classification
For each open PR, compute:
- `change_type`: test-only | docs-only | runtime-code | infra | config | mixed
- `security_surface`: none | low | medium | high
- `blast_radius`: low | medium | high
- `review_cost`: estimated minutes
- `novelty`: duplicate pattern vs unique contribution

### Stage B — Value & Risk Scoring
Compute two independent scores (0-100):
- `value_score`: strategic usefulness (runtime impact, bug fixes, reliability gains)
- `risk_score`: security/operational risk (secrets, auth, plugin loading, shell/system calls, dependency drift)

Derived queue class:
- **P0 security**: risk >= 80
- **P1 high-impact**: value >= 70 and risk < 80
- **P2 routine**: tests/docs/low-risk
- **P3 low-value**: repetitive low-impact PRs

### Stage C — Automated Review Routing
- P0 → Security agent + maintainer approval required
- P1 → Code-review agent + verifier agent
- P2 → Fast-path policy checks + optional batch merge strategy
- P3 → Auto-comment with consolidation request / hold queue

### Stage D — Bug/Issue Fusion (#3)
When issues are open:
1) map issues ↔ candidate PRs
2) detect duplicate fixes
3) auto-generate repro checklist for unmatched issues
4) spawn fix-plan mission when no suitable PR exists

### Stage E — Merge Policy Enforcement
- Required checks must pass
- Security gate must pass for runtime/config changes
- Optional batch mode for test-only PRs from trusted contributor pattern

## Initial Security Rules (must-have)
Flag as high-risk if PR touches:
- auth/session/token handling
- plugin loading/execution policies
- subprocess/shell execution paths
- file-system writes outside expected dirs
- dependency manifests or lockfiles with suspicious deltas
- CI/deployment/workflow permissions

## Daily Output (Discord + Spawner)
Daily report should include:
- queue summary by class (P0/P1/P2/P3)
- top 5 PRs to review today
- blocked PRs and exact blockers
- recommended batch actions (e.g., grouped test-only PRs)
- issue-to-PR mismatch alerts

## v1 Implementation Plan
1) `scripts/pr_sentinel_collect.py` — fetch PR + issue metadata via `gh`
2) `scripts/pr_sentinel_score.py` — classify + score + output JSON report
3) `scripts/pr_sentinel_report.py` — summarize to markdown/Discord format
4) Spawner mission template: `pr-sentinel-daily`
5) Cron schedule: daily 09:15 Asia/Dubai

## Success Criteria
- Review queue reduced by >=40% in first week
- P0/P1 PRs always surfaced same day
- Test-only PR handling throughput improves via batch policy
- Fewer irrelevant PR review cycles
- Security-sensitive changes always gated
