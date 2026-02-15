# Escalation Ladder

## P0 (Immediate)

Examples:
- secrets leaked
- guardrails bypassed by default
- remote exposure or auth bypass
- data loss/corruption

Actions:
- stop distribution (pause launch)
- contain: reduce surface area (`spark down`, `spark up --lite`)
- open a private security report path (see `SECURITY.md`)

## P1 (Same Day)

Examples:
- services cannot start on a clean machine
- pipeline health gates fail
- crash-loop or watchdog thrash

Actions:
- assign owner
- create a minimal repro
- ship hotfix or document workaround

## P2/P3 (Queue)

Examples:
- docs confusion
- minor dashboard bugs
- feature polish

Actions:
- label and schedule
- prioritize based on frequency and impact

