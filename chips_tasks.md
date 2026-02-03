# Chips Task Tracker

Purpose: track chip iteration work (done / doing / next) so we always know what's shipped vs. pending.

Last updated: 2026-02-02

Status legend: TODO | DOING | BLOCKED | DONE

## Recent Changes
- DONE: Added TOOLS tab to Spark Pulse right-rail (Episode / Tuneables / Chips / Tools). (2026-02-03)
  - Shows X Trends Radar status, patterns, predictions, accuracy
  - Lists MCP integrations (x-twitter, spark, spawner, h70-skills)
  - Added API endpoints: `/api/tools`, `/api/tools/xtrends/status`, `/api/tools/xtrends/patterns`, `/api/tools/xtrends/predictions`
- DONE: Added tabbed right-rail nav (Episode / Tuneables / Chips) in Spark Pulse. (2026-02-02)
- DONE: Aligned runtime trigger names across remaining chips and updated `docs/CHIP_WORKFLOW.md`. (2026-02-02)
- DONE: Clarified hook-name normalization in docs (`docs/CHIPS.md`, `docs/QUICKSTART.md`, `docs/claude_code.md`, `docs/SPARK_INFERENCE_ARCHITECTURE.md`, `docs/SPARK_ASSESSMENT_CHECKLIST.md`). (2026-02-02)
- DONE: Auto-activation now ignores event triggers (match patterns only) to avoid global activation on `post_tool`/`user_prompt`. (2026-02-02)
- DONE: Added tool triggers with `context_contains` gating for `vibecoding`, `marketing`, `game_dev`, `moltbook`, `biz-ops`. (2026-02-02)
- DONE: Spot-checked tool trigger gating; tuned `vibecoding` to avoid `.ts` matching `.tscn`. (2026-02-02)
- DONE: Tightened observer triggers and extraction regex boundaries for `moltbook` and `biz-ops`. (2026-02-02)
- DONE: Validated `biz-ops` outcomes/fields; added explicit missing-assumption detection. (2026-02-02)
- DONE: Updated `game_dev` retention metric extraction to handle % values. (2026-02-02)
- DONE: Relaxed `vibecoding` required fields to match queue/tool event reality. (2026-02-02)
- DONE: Updated `marketing` metric extraction + outcomes to avoid CAC false positives. (2026-02-02)
- DONE: Tightened `spark-core` preference triggers to reduce generic matches. (2026-02-02)
- DONE: Added warn-only chip schema validation on load. (2026-02-02)
- DONE: Set default activation policy (auto: `spark-core`, opt-in: all others + examples). (2026-02-02)
- DONE: Added schema validation mode switch via `SPARK_CHIP_SCHEMA_VALIDATION` (warn vs block). (2026-02-02)
- DONE: Ran benchmark replay (limit 500) and generated `benchmarks/out/report.md`. (2026-02-02)
- DONE: Added Spark Pulse chips + tuneables rail (right sidebar) and API. (2026-02-02)
- DONE: Documented chip tuneables in `TUNEABLES.md`. (2026-02-02)
- DONE: Wired Spark Pulse into services + dashboard nav for visibility. (2026-02-02)
- DONE: Updated Quick Start docs with Spark Pulse links + notes. (2026-02-02)
- DONE: Normalize `spark-core` triggers to include `post_tool`, `post_tool_failure`, `user_prompt` and add safety metadata. (2026-02-02)
- DONE: Precision pass on noisy triggers in `vibecoding`, `marketing`, `game-dev`, `market-intel`. (2026-02-02)
- DONE: Audit required chip identity fields across runtime chips (no missing fields found). (2026-02-02)
- DONE: Normalize example chip event triggers to `user_prompt` and update `docs/CHIPS.md`. (2026-02-02)
- DONE: Precision pass on `moltbook` and `biz-ops` top-level triggers. (2026-02-02)
- DONE: Ran chip tests for `moltbook` and `biz-ops`; generated benchmark reports in `benchmarks/out/`. (2026-02-02)

## In Progress
- (none)

## Next Up (priority order)
- (none)

## Step-by-Step Build
Status legend: TODO | DOING | DONE

Step 1 (DONE): Align runtime trigger names across remaining chips and docs.
- Scope: `vibecoding`, `marketing`, `game_dev`, `market-intel`, `moltbook`, `biz-ops`, `bench-core`, and `docs/CHIP_WORKFLOW.md`.
- Goal: ensure all chips and docs use `post_tool`, `post_tool_failure`, `user_prompt` (keep legacy hook names only if required for compatibility).
- Exit criteria: all listed chips updated + docs consistent + checklist items in this file marked DONE for runtime trigger names.

Step 2 (DONE): Add tool triggers with context gating to reduce noisy global events.
- Scope: `vibecoding`, `marketing`, `game_dev`, `moltbook`, `biz-ops` (reviewed `market-intel` tool triggers).
- Goal: prefer `triggers.tools` with `context_contains` for domain tools/files, reducing reliance on broad event triggers.
- Exit criteria: tool triggers added + event noise reduced (spot-check with `spark chips test`).

Step 3 (DONE): Tighten observer triggers and extraction regex for high-signal chips.
- Scope: `moltbook`, `biz-ops`.
- Goal: remove generic triggers and add word boundaries to reduce false positives.
- Exit criteria: observer triggers updated + regex boundaries added.

Step 4 (DONE): Wire chip schema validation (warn-only).
- Scope: chip loading.
- Goal: surface missing required identity/safety fields without breaking loads.
- Exit criteria: loader logs validation errors but still loads chips.

Step 5 (DONE): Set default activation policy for chips.
- Scope: all runtime + example chips.
- Goal: auto-activate only `spark-core`; keep others opt-in by default.
- Exit criteria: chips carry `chip.activation` and auto-activation respects it.

Step 6 (DONE): Add schema validation mode switch (warn vs block).
- Scope: chip loading.
- Goal: allow strict validation via config/env without breaking dev flows.
- Exit criteria: `SPARK_CHIP_SCHEMA_VALIDATION=block` prevents invalid chip loads.

Step 7 (DONE): Run benchmark replay to check signal quality.
- Scope: benchmark replay.
- Goal: quantify accept rates and outcome hits after trigger changes.
- Exit criteria: `benchmarks/out/report.md` generated and reviewed.

Step 8 (DONE): Add Spark Pulse chips + tuneables rail.
- Scope: Spark Pulse UI.
- Goal: expose chip activation + tuneables + integration actions in right sidebar.
- Exit criteria: Spark Pulse renders Episode, Tuneables, Chips rails.

Step 9 (DONE): Add tabbed right-rail navigation to Spark Pulse.
- Scope: Spark Pulse UI.
- Goal: make Episode / Tuneables / Chips discoverable as tabs.
- Exit criteria: right rail shows tabs and switches content.

## Chip-by-Chip Checklist

### spark-core
- DONE: Add safety metadata + runtime trigger names.
- DONE: Review observers/extraction for false positives.
  - Context: current triggers (`always`, `never`, `prefer`) can fire on generic text; consider requiring nearby verbs or tool context.

### vibecoding
- DONE: Remove overly generic `pr` trigger (use `pull request`).
- DONE: Add runtime trigger names if missing.
- DONE: Verify required fields are realistically extractable from queue events.
- DONE: Add tool triggers (`Bash`, `Edit`, `Write`) with context gates.
  - Context: queue events carry `tool_name`, `tool_input`, and `data.payload.text`; required fields should map to those.

### marketing
- DONE: Tighten observer triggers (avoid generic `brief` / `variant`).
- DONE: Add runtime trigger names if missing.
- DONE: Validate outcomes conditions against extracted field types.
  - Context: ensure numeric comparisons use numeric strings (e.g., CTR/CAC fields).

### game_dev
- DONE: Remove generic triggers (`bug`, `fun`) and add `not fun`.
- DONE: Add runtime trigger names if missing.
- DONE: Review extraction patterns for retention metrics.
  - Context: ensure `metric_value` extraction handles decimals and %.

### market-intel
- DONE: Replace overly generic triggers with specific phrases.
- DONE: Add runtime trigger names if missing.
  - Context: tool triggers already exist for X/Twitter; ensure they remain scoped by `context_contains`.

### moltbook
- DONE: Tighten top-level pattern triggers to reduce noise.
- DONE: Add runtime trigger names if missing.
- DONE: Ensure observer triggers match typical event content.
  - Context: avoid duplicate insights from overlapping observer triggers (post vs performance).

### biz-ops
- DONE: Tighten top-level pattern triggers to reduce noise.
- DONE: Add runtime trigger names if missing.
- DONE: Tighten observer triggers and extraction regex boundaries.
- DONE: Validate outcomes and required fields.
  - Context: `variant_id` regex fixed; confirm other fields map to `tool_input`/payload.

### bench-core (benchmark only)
- DONE: Ensure benchmark events align with current runtime trigger names.
  - Context: benchmarks emit `post_tool`/`user_prompt`; chip should match.

## Decisions
- Use runtime event types as primary (`post_tool`, `post_tool_failure`, `user_prompt`) and keep legacy hook names for compatibility.

## Hand-off (Terminal 2)
- (cleared)

## Open Questions
- Which chips should be active by default vs. opt-in?
- Should we enforce schema validation on install (blocking) or warn-only?
- Should we auto-sleep chips with persistent noise (high false positives)?

## Control Layer Spec (from user notes)
The following items were pasted and should be tracked for integration into chips/EIDOS:

### Required Operating Concepts
- Finite State Machine with explicit states (EXPLORE → PLAN → EXECUTE → VALIDATE → CONSOLIDATE; DIAGNOSE/SIMPLIFY/ESCALATE/HALT).
- Step Envelope required before/after every action (intent, hypothesis, prediction, stop condition, memory citations; then result, evidence, evaluation, lesson, confidence delta).
- Memory binding: retrieval at episode start and before plan/execute; block execution if memory exists but isn’t cited.
- Budgets: max steps, retries per error signature, file touch count, and time.

### Watchers (initial set)
- Repeat Failure Signature → force DIAGNOSE.
- No New Evidence → force DIAGNOSE.
- Diff Thrash → force SIMPLIFY.
- Confidence Stagnation → force PLAN w/ alternatives.
- Memory Bypass → block step, require retrieval.
- Budget Half-Spent, No Progress → force SIMPLIFY.
- Scope Creep → force SIMPLIFY.
- Validation Gap → force VALIDATE-only step.

### Escape Protocol
- Freeze edits, summarize facts, isolate smallest failing unit, generate ≤3 hypotheses, pick 1 discriminating test, execute test-only, then ESCALATE if still stuck.
- Mandatory learning artifact: sharp edge / anti-pattern / avoid-under-X.

### Distillation + Truth Ledger
- Evidence levels (claim/weak/strong); only strong evidence may influence policy.
- Distillations must include evidence references and revalidate-by timestamps.
- Revalidation/decay for stale intelligence.

### Policy Patches + Minimal Mode
- Policy patches proposed from validated distillations; human approval for high-impact.
- Minimal mode when repeated watcher firings or low evidence/confidence.

### Dashboard Must-Haves
- Mission Control (state, budgets, hypotheses, validation, watcher alerts).
- Intelligence Growth (reuse rate, success velocity, validated distillations/week).
- Thrash/Rabbit Hole Radar (repeated errors, no-evidence streaks, thrashed files).
- Memory Utilization (retrieved vs cited vs used; top impactful & wrong distillations).

## Hand-off Ideas (for another terminal/agent)
- Audit chip YAMLs for schema completeness (identity + safety fields).
- Normalize event trigger names across chips and update docs.
- Run benchmark replay to quantify trigger precision/recall drift.
