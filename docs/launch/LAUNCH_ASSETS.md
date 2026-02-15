# Launch Assets Pack

Date: 2026-02-15

Goal: make Spark Intelligence understandable in 30 seconds and believable in 2 minutes.

## 30-Second Positioning

Spark Intelligence is a self-evolution layer for AI coding agents.
It captures how you work, distills validated learnings, and feeds them back into your agent so it improves over time.

Local-first. No API keys required (Claude OAuth). Safe-by-default with explicit guardrails.

## Landing Page (Structure + Copy)

### Hero
Headline:
- "Your AI coding agent gets smarter every day. Automatically."

Subhead:
- "Spark Intelligence turns real work into validated learnings, then reuses them so your agent stops repeating the same mistakes."

Primary CTA:
- "Install and run in 5 minutes"

Secondary CTA:
- "Watch the 90-second demo"

Trust chips (short):
- Local-first
- Safe-by-default guardrails
- Health + dashboards
- Works with Claude Code / Cursor

### Problem
- "Agents forget your preferences."
- "They repeat the same mistakes across sessions."
- "You end up re-teaching the same corrections."

### Solution (How it works)
1. Capture: hooks + tailers record tool events
2. Distill: EIDOS turns outcomes into durable learnings
3. Reuse: context files update; your agent reads them
4. Verify: dashboards + gates show the loop is healthy

### Proof (Show, do not claim)
- Screenshot: Spark Pulse dashboard
- Screenshot: `spark status` output
- Screenshot: advisory/evidence drilldown (trace-first)

### Safety
- Link: `docs/RESPONSIBLE_PUBLIC_RELEASE.md`
- Link: `docs/security/THREAT_MODEL.md`
- Callout: "Guardrails run in the execution path, not only docs."

### Quickstart
- "Copy-paste install"
- "Start services"
- "Check health"
- "Open dashboard"

Link: `docs/GETTING_STARTED_5_MIN.md`

## Demo Video (90 Seconds)

### Format
- Screen-recorded demo (fast cuts)
- Minimal talking, captions on-screen
- End with CTA + URL

### Script (beats)
0-10s: Problem
- "I keep re-teaching my agent the same preferences."

10-25s: Install + start
- Show: installer or `pip install -e .[services]`
- Show: `spark up` (or `start_spark.bat`)

25-40s: Health + visibility
- Show: `spark health` and `/status`
- Show: Pulse dashboard (services green)

40-65s: Learning loop
- Show: a real correction event -> a distilled learning -> promoted to context
- Show: agent reads updated context (file diff)

65-80s: Safety posture
- Show: a guardrail blocking an obviously destructive command (test or simulated)
- Mention: `SPARK_EIDOS_ENFORCE_BLOCK=1` exists for strict hosts

80-90s: CTA
- "Install, start services, code normally. Spark learns in the background."

## Cinematics (Optional B-Roll)

- Close-ups: terminal + dashboard cuts (no stock "AI brain" visuals)
- Macro shots: code review, diffs, trace ID drilldown
- Quick overlays: "validated", "reused", "measured"

## Screenshot/GIF Checklist

- `spark health` output (green)
- `spark services` output (shows ports + running components)
- Pulse dashboard landing view
- Meta-Ralph quality view (if public-safe)
- A “before/after” context file change (`SPARK_CONTEXT.md` or equivalent)

## Pricing Narrative (If Needed)

Align with `docs/OPEN_CORE_FREEMIUM_MODEL.md`:
- Core: local-first learning loop (free)
- Paid: premium modules/plugins that do not weaken safety (examples: team analytics, advanced dashboards, enterprise policy bundles)

