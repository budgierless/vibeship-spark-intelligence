# Launch Comms Pack (X + One-Pager)

Date: 2026-02-15

Goal: explain Spark Intelligence in 30 seconds, prove it works in 2 minutes, and drive a single CTA (install + run).

## Message Pillars

1. Compounding improvement: the agent learns from real outcomes, not vibes.
2. Local-first: your data stays on your machine.
3. Measurable loops: health, dashboards, and gates (not magic).
4. Safe defaults: guardrails in the execution path.

## Primary CTA

- "Install and run in 5 minutes" -> `docs/GETTING_STARTED_5_MIN.md`

## X Thread (Draft, 10 Posts)

1) Most AI coding agents repeat the same mistakes because they don't actually learn your workflow.

2) We built Spark Intelligence: a local-first self-evolution layer for coding agents.

3) It captures real signals (tool usage + outcomes), distills them into validated learnings, and reuses them so your agent improves over time.

4) Not a wrapper. Not “prompt engineering.” A learning loop with gates.

5) You can see it working:
- `spark health`
- `/status`
- dashboards for services, loops, and outcomes

6) Safe-by-default:
- guardrails run in the execution path
- responsible public release docs + threat model included

7) No API keys required for the default path (Claude OAuth only).

8) Install + run in 5 minutes:
- Windows: `start_spark.bat`
- Mac/Linux: `spark up`

9) If you want to follow along, we share daily operator notes and what we learned building it (including what broke).

10) Try it. Break it. Send issues.
CTA: start here -> `docs/GETTING_STARTED_5_MIN.md`

## Short Posts (Drafts)

- "Spark Intelligence: local-first learning loop for coding agents. Install, run, and watch your agent improve through validated learnings. Start: `docs/GETTING_STARTED_5_MIN.md`"

- "If your agent keeps repeating the same mistakes, it’s not your prompts. It’s missing a learning loop. Spark adds one. `docs/GETTING_STARTED_5_MIN.md`"

- "We shipped safety docs + guardrails that run in the execution path, not just on paper. `docs/RESPONSIBLE_PUBLIC_RELEASE.md`"

## Press-Style One-Pager (Draft)

### Spark Intelligence

Spark Intelligence is a self-evolution layer for AI coding agents. It captures interaction signals from real work, distills them into validated learnings, and feeds those learnings back into the agent so it improves over time.

Key points:
- Local-first: data stays on your machine.
- Measurable: health checks, dashboards, and strict release gates.
- Safe defaults: guardrails in the execution path; responsible release docs included.

Getting started:
- `docs/GETTING_STARTED_5_MIN.md`

Safety:
- `docs/RESPONSIBLE_PUBLIC_RELEASE.md`
- `docs/security/THREAT_MODEL.md`

## Tracking Plan (UTMs + Events)

UTM conventions:
- `utm_source`: `x`, `github`, `discord`, `telegram`, `newsletter`
- `utm_medium`: `social`, `community`, `repo`
- `utm_campaign`: `spark-intel-alpha`
- `utm_content`: `thread`, `shortpost1`, `demo`

Event schema (minimum):
- `landing_view`
- `cta_click_install`
- `docs_open_getting_started`
- `install_success` (self-reported or installer telemetry if added later)
- `spark_health_success` (self-reported in issue template if needed)

## Follow-Up Plan (7 Days)

Day 0: launch thread + demo
Day 1: “how it works” diagram + safety posture
Day 2: real user story (or internal dogfood) + metrics screenshot
Day 3: troubleshooting post (top 3 issues)
Day 4: build-in-public recap + roadmap (ship now vs later)
Day 7: alpha retro (what broke, what we fixed)

Optional faith note (keep it humble and non-coercive):
- short line of gratitude, avoid preaching in product posts

