# Spark Intelligence Dashboard Playbook

Purpose: keep the control layer visible, enforceable, and traceable.

## Core rule
Every metric must drill down to trace_id -> steps -> evidence -> validation.

## Daily operator loop (10 minutes)
1. Open Mission Control and confirm green status for services, queue, and EIDOS activity.
2. Scan Watchers feed for new red/yellow alerts and click into the triggering episode.
3. Check Learning Factory funnel. If retrieved >> used or helped drops, investigate top ignored items.
4. Check Acceptance Board for pending critical tests or expired deferrals.

## Per-change checklist (before and after edits)
1. Run pipeline health check.
2. Verify trace_id is present on new steps and outcomes.
3. Validate that the dashboard drilldown shows evidence for the change.
4. If validation is missing, add a test or explicit evidence link.

## Mission Control usage
Goal: answer "Are we stable and learning?"
1. If any service is stale or down, fix ops first.
2. If queue oldest event age spikes, inspect bridge cycle health.
3. If EIDOS activity is zero, check EIDOS enabled flag and bridge cycle errors.
4. Use trace_id drilldown to see the latest active episode timeline.

## Rabbit Hole Recovery usage
Goal: detect and exit loops.
1. Use the repeat failure scoreboard to identify top error signatures.
2. Open the offending trace_id and confirm if evidence is missing.
3. Trigger Escape Protocol if the same signature repeats 2+ times.
4. After escape, ensure a learning artifact was created and linked.

## Learning Factory usage
Goal: compound intelligence, not just store it.
1. Follow the funnel: retrieved -> cited -> used -> helped -> promoted.
2. If retrieved is high but helped is low, demote or refine the top offenders.
3. If promoted is zero, check validation counts and outcome links.
4. Review contradicted items weekly and schedule revalidation.

## Acceptance and Validation Board usage
Goal: turn "done" into a contract.
1. Ensure every active episode has an approved acceptance plan.
2. Prioritize P1 tests and close validation gaps before new work.
3. If deferrals are expiring, resolve or explicitly re-defer.

## Trace-first drilldown
1. Start from a metric or alert.
2. Open the trace_id for that event.
3. Review steps in order and confirm evidence exists for each step.
4. If evidence is missing, log a validation gap and block promotion.

## Weekly maintenance
1. Review top repeated failures and add a distillation or guardrail.
2. Review top contradicted insights and downgrade reliability.
3. Audit evidence store for expiring high-value artifacts and extend retention.

