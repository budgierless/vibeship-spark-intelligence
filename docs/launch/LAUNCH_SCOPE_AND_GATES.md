# Spark Intelligence Launch Scope + Gates

Date: 2026-02-15
Mission: mission-1771186081212

This document defines what we ship now vs later, and the strict gates for go-live.

## 1) Release Mode

Target: Public alpha (local-first) with controlled growth.

Principle: Ship the learning loop + safety posture + reliability. Defer anything that increases blast radius without clear user value.

## 2) Ship Now (Must-Haves)

### Core value
- Local-first self-evolution layer for AI coding agents (Spark + EIDOS) that improves through validated learnings.
- New user can install, start services, and see the system working within 10 minutes.

### Operator surface area
- Service runner: `start_spark.bat` (Windows) + `spark up/down/services` (CLI).
- Observability: Spark Pulse (web), Obsidian Observatory (file-based), CLI scripts.
- Health endpoints: `sparkd /health` and Mind `/health` (when enabled).

### Reliability + integrity
- Queue durability and bounded growth (size + byte caps).
- Startup readiness checks: service can be “up” but report unhealthy.
- Production loop gates exist and are runnable (see `PRODUCTION_READINESS.md`).

### Security + responsible release minimum bar
- Safe-by-default posture with documented guardrails (see `docs/RESPONSIBLE_PUBLIC_RELEASE.md`).
- Security reporting path documented (see `SECURITY.md`).

## 3) Ship Later (Explicit Deferrals)

These are intentionally out-of-scope for the first public alpha unless promoted to “Ship Now” with an owner + test plan:
- Cloud sync / multi-tenant hosted Spark
- Automated “agent runs jobs for you” features that act without a human in the loop
- Arbitrary remote tool execution or remote file operations
- Any “one-click” external integrations that expand capability surface (must be gated behind explicit opt-in + threat model)
- Large-scale multi-user realtime collaboration features (presence/chat/rooms) beyond what’s required for Spark’s own dashboards

## 4) Release Gates (Fail-Closed)

### Gate A: Install + First Run
PASS only if a fresh machine can:
- Install via docs (`docs/QUICKSTART.md` or installer) without manual debugging.
- Start services.
- Verify health:
  - `http://127.0.0.1:${SPARKD_PORT:-8787}/health` returns 200 (liveness, plain `ok`).
  - `http://127.0.0.1:${SPARKD_PORT:-8787}/status` returns 200 with JSON (readiness + pipeline fields).
  - If Mind enabled, `http://127.0.0.1:${SPARK_MIND_PORT:-8080}/health` returns 200.
- Open Pulse dashboard and see non-empty status.

### Gate B: Production Loop Gates
PASS only if all required checks from `PRODUCTION_READINESS.md` pass on this commit:
1. `python tests/test_pipeline_health.py quick`
2. `python tests/test_learning_utilization.py quick`
3. `python tests/test_metaralph_integration.py`
4. `python -m lib.integration_status`
5. `python scripts/production_loop_report.py`
6. `python -m pytest -q tests/test_production_loop_gates.py tests/test_advisor_effectiveness.py tests/test_sparkd_hardening.py`

### Gate C: Realtime/SSE Survivability (Dashboards)
PASS only if:
- SSE endpoints (`/api/status/stream`, `/api/ops/stream`) do not leak memory with reconnect loops.
- Server emits periodic keepalive/heartbeat events and closes dead clients.
- No unbounded per-client buffering (backpressure required).

### Gate D: Abuse Controls
PASS only if:
- Mutating `sparkd` endpoints require bearer auth by default (`SPARKD_TOKEN` or `~/.spark/sparkd.token`).
- Rate limiting is enabled (per-IP at minimum).
- Invalid-event quarantine retention is bounded.

### Gate E: Responsible Release
PASS only if:
- `docs/RESPONSIBLE_PUBLIC_RELEASE.md` matches actual runtime behavior (no “paper guardrails”).
- `SPARK_EIDOS_ENFORCE_BLOCK=1` behavior is documented and works end-to-end.

## 5) Go / No-Go Criteria

GO only if:
- All gates A-E are green.
- No P0 bugs open.
- No known data corruption paths.
- Rollback plan is written and tested.

NO-GO if any of the below are true:
- Any gate is red.
- Any crash-loop or queue corruption observed in a 30-minute soak.
- Any obvious secrets leakage or unsafe default that expands tool capability silently.

## 6) Timeline (Default)

- T-7 days: scope freeze for “Ship Now” list.
- T-3 days: RC cut, run full gates + 30-minute soak.
- T-1 day: docs proofread + launch comms final.
- T day: launch.

## 7) Owners (Roles)

- Release Captain: owns scope freeze, RC, and go/no-go call.
- Safety Lead: owns Gate E and security review.
- Reliability Lead: owns Gate B/C and pipeline health.
- Docs Lead: owns Quickstart and newcomer success.
- Growth/Comms Lead: owns launch story, distribution, support readiness.

## 8) Rollback (Minimum)

- Tag RC and launch commit.
- Ability to revert to last-green tag quickly.
- Ability to disable risky behavior via env flags (documented) while keeping core services up.
