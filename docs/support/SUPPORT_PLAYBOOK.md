# Support Playbook

This is the support readiness pack for Spark Intelligence (public alpha).

## Support Channels (Define Before Launch)

- GitHub issues: bug reports, feature requests
- Community: Discord/Telegram (if used) for questions and updates

Before public distribution, publish:
- a support intake URL
- expected response time
- where to report security issues (see `SECURITY.md`)

## Bug Triage Flow

1. Repro? (yes/no)
2. Severity:
   - P0: safety/security, data loss, remote exposure, crash-loop
   - P1: core services cannot start, health fails, unusable dashboards
   - P2: degraded learning quality, partial features broken
   - P3: docs issues, minor UI defects
3. Collect required info:
   - OS + Python version
   - `spark health` output
   - `spark services` output
   - relevant logs from `~/.spark/logs`
4. Assign owner and label:
   - `area:sparkd`, `area:hooks`, `area:eidos`, `area:docs`, `area:installer`
5. Close loop:
   - confirm fix in release notes
   - request reporter validation if possible

## KB (Top Issues)

See: `docs/support/TROUBLESHOOTING_KB.md`

## Canned Responses

See: `docs/support/MACROS.md`

## Escalation Ladder

See: `docs/support/ESCALATION.md`

