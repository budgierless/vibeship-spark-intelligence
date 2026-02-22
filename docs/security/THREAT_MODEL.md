# Spark Intelligence Threat Model (Public Alpha)

Date: 2026-02-15
Scope: vibeforge1111/vibeship-spark-intelligence (local-first services + hooks + dashboards)

This threat model is intentionally practical. It focuses on likely failures and abuse paths for a public alpha.

## System Summary

Spark Intelligence is a local-first learning/evolution layer for coding agents. It:
- Captures local agent/tool events (hooks + tailers)
- Stores/derives learnings (memory, distillation, advisories)
- Exposes local services (sparkd, dashboards, optional Mind bridge)

The system is dual-use: the same automation/memory primitives can be misused for harmful automation.
See `docs/RESPONSIBLE_PUBLIC_RELEASE.md` for release-mode options.

## Assets To Protect

- Secrets and credentials on operator machine:
  - SSH keys, cloud keys, API tokens, wallet secrets
- Code and repositories:
  - proprietary source, user data inside repos
- Safety posture:
  - guardrail engine, default deny behaviors, enforcement switches
- Integrity of learnings:
  - stored insights, distillations, policy patches, evidence links
- Service availability:
  - sparkd, bridge workers, dashboards

## Attackers / Abuse Cases

- Curious user:
  - enables unsafe flags or copies “power user” configs without understanding blast radius
- Malicious user (local):
  - disables guardrails and uses Spark as a wrapper for automation they already intended
- External attacker on same network:
  - abuses exposed ports if bound to 0.0.0.0 or auth is missing
- Supply chain attacker:
  - dependency compromise, malicious npm/pip packages, installer tampering
- Prompt injection / tool metadata injection:
  - adversarial content in tool input causes unsafe actions

## Trust Boundaries

- Boundary A: Hook event input (untrusted; comes from the host/tool runtime)
- Boundary B: Local HTTP APIs (sparkd/dashboards)
- Boundary C: Local filesystem (read/write surfaces)
- Boundary D: External network calls (optional integrations)

## Primary Threats and Mitigations

### T1: Secret Exfiltration via Tool Use (Read/Glob/Search)
Risk: agent reads `~/.ssh`, browser profiles, wallet files, etc.
Mitigations:
- Guardrails block likely-secret paths by default; require explicit override.
- Document overrides clearly and discourage in public alpha docs.

### T2: Destructive Shell Commands
Risk: `rm -rf`, disk wipe, credential deletion, destructive git actions.
Mitigations:
- Guardrails block obviously destructive shell commands by default.
- Provide a “DIAGNOSE mode” escape hatch only with explicit user intent and warnings.

### T3: Remote Abuse of Local Services
Risk: if services bind to all interfaces, attacker hits endpoints.
Mitigations:
- Bind dashboards locally by default (`127.0.0.1`).
- Require token auth for mutating endpoints by default (`SPARKD_TOKEN` or `~/.spark/sparkd.token`).
- Treat Origin/Referer + `Sec-Fetch-Site` checks as browser-focused CSRF hardening, not standalone client authentication.
- Rate limit and bound invalid payload retention.

### T4: Guardrail Bypass / “Paper Guardrails”
Risk: docs say safe, runtime is permissive; or guardrails exist but not used in execution path.
Mitigations:
- Guardrails run in the hook execution path (pre-tool).
- Optional strict enforcement:
  - `SPARK_EIDOS_ENFORCE_BLOCK=1` makes blocked decisions exit non-zero.
- Unit tests cover core guardrail blocks (see `tests/test_safety_guardrails.py`).

### T5: Denial of Service (Queue Growth, Reconnect Storms, Slow Clients)
Risk: unbounded queues, SSE/WS connection storms, memory growth.
Mitigations:
- Enforce queue size/byte limits and rotation.
- SSE endpoints must implement keepalive and cleanup; avoid unbounded buffering.
- Rate limit inbound HTTP requests.

### T6: Unsafe Autonomy Escalation
Risk: users run Spark in higher autonomy modes without understanding limits.
Mitigations:
- Responsible release docs explicitly describe non-goals and constraints.
- Prefer safe local-first alpha; defer higher-blast-radius features.

## Residual Risks (Honest)

- A fork can remove guardrails and ship unsafe defaults.
- A local user can set permissive flags; the system cannot prevent intentional misuse.
- Prompt injection remains a constant risk in any tool-using agent system.

## Minimum Bar For Public Alpha

Must pass:
- `docs/RESPONSIBLE_PUBLIC_RELEASE.md` is accurate to runtime behavior
- `SECURITY.md` has a real security contact before public distribution
- `tests/test_safety_guardrails.py` and `tests/test_sparkd_hardening.py` pass
- Default binding is localhost for dashboards and APIs intended to be local-only
- No secrets committed; `.env` and credential files are ignored
