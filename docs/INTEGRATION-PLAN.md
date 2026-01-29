# Spark Integration Plan (Mind + Skills + Orchestration)

This document turns the prior analysis into a concrete architecture and
implementation plan. It keeps the system lightweight, stable, and maintainable,
while making learnings actually influence decisions.

---

## 1) Goals (KISS)

- Use learnings at decision time, not just store them.
- Keep dependencies minimal (stdlib + existing stack).
- Preserve graceful fallbacks (if a subsystem is off, nothing breaks).
- Make improvements observable and testable.

---

## 2) Target Architecture (Lightweight and Stable)

Single decision context pipeline, refreshed continuously:

Events (hooks or sparkd)
  -> queue.jsonl
  -> bridge_worker (every 30s)
      -> cognitive insights (local JSON)
      -> memory banks (local JSONL)
      -> Mind retrieval (optional, lightweight)
      -> skills routing (optional, lightweight)
      -> aha lessons (local JSON)
      -> advisor notes (local JSON)
      -> orchestration hints (local JSON)
  -> SPARK_CONTEXT.md
  -> injected into runtime context (host hook)

Fail-safe rule:
If any subsystem is unavailable, the context still renders (empty section),
and the system behaves as it does today.

---

## 3) Current State and Gaps

What exists:
- Event capture + queue
- Cognitive insights + promotions
- Memory banks + Mind sync
- Orchestration core (agents, goals, handoffs)
- Bridge worker + SPARK_CONTEXT.md

Gaps:
- Skills are not loaded or used at all
- Advice is not surfaced consistently at decision time
- Feedback loop is weak (reliability does not converge)
- Orchestration is not tied to skill selection

---

## 4) Minimal New Components (KISS Additions)

1) skills_registry.py
- Reads H70-C+ YAML skills from SPARK_SKILLS_DIR
- Extracts only low-weight fields: name, description, owns, delegates,
  anti_patterns titles, detection commands
- Caches index at ~/.spark/skills_index.json (refresh on mtime)

2) skills_router.py
- Simple lexical scoring (overlap with task text + owns)
- Returns top N skill IDs
- Uses effectiveness stats to boost or downrank

3) advisor.py (already exists, needs fixes)
- Query order: memory banks -> cognitive -> Mind -> skills
- Cached output; returns short advice block (3-5 bullets max)
- Guard with Mind health check

4) effectiveness stats (tiny JSON)
- skills_effectiveness.json: {skill_id: success, fail}
- advice_effectiveness.json: {source: total, helpful}

---

## 5) Step-by-Step Implementation Plan

### Phase 0: Baseline Safety (1-2 days)
Goal: stabilize existing code before integration.
- Fix advisor bugs (Aha tracker access, Mind health check)
- Normalize Windows paths in infer_project_key
- Ensure all subsystems fail gracefully (no crash, no hard dependency)

### Phase 1: Skills Index + Router (2-3 days)
Goal: load skills without heavy parsing.
- Add lib/skills_registry.py
- Add lib/skills_router.py
- Add SPARK_SKILLS_DIR env var to config docs
- Add SPARK_DEBUG note: off by default, enable only for troubleshooting
- Add simple unit tests for index + router

### Phase 2: Context Injection (1-2 days)
Goal: skills show up in SPARK_CONTEXT.md reliably.
- Extend lib/bridge.generate_active_context() with:
  - "Relevant Skills" section (top 3)
  - "Delegates" hints if present
- Keep output short; do not include full skill text

### Phase 3: Advisor Activation (1-2 days)
Goal: advice reaches decision-time context.
- Fix and simplify lib/advisor.py
- Bridge worker adds "Advisor Notes" section
- Cap advice to max 5 bullets

### Phase 4: Feedback Loop (2-3 days)
Goal: learn from outcomes without heavy ML.
- On tool success/failure, update:
  - advice effectiveness counters
  - skill effectiveness counters
  - cognitive times_validated / times_contradicted
- Only adjust when advice was surfaced

### Phase 5: Orchestration Link (2-3 days)
Goal: route work to the right skills/agents.
- Allow agent registration with capabilities = skill IDs
- When routing/handing off, prefer agents matching top skill
- Record outcome in orchestration stats

---

## 6) Validation Plan (Make Sure It Works)

### Compatibility Matrix
Mind | Skills | Advisor | Expected
---- | ------ | ------- | --------
OFF  | OFF    | OFF     | base behavior
OFF  | ON     | OFF     | context includes skills
ON   | OFF    | ON      | advice uses cognitive + mind
ON   | ON     | ON      | full loop, all sections visible

### Tests
- Unit:
  - skills_registry loads YAML and caches
  - skills_router stable ranking
  - advisor falls back when Mind unavailable
- Integration:
  - bridge_worker writes SPARK_CONTEXT.md with expected sections
- Regression:
  - dashboard and CLI remain functional

### Runtime Metrics (cheap)
- Advice surfaced rate (% of tasks with advice block)
- Advice helpfulness rate
- Skill success/failure rate
- Error recurrence rate (by tool)
- Promotion count trend

---

## 7) Design Rules (Keep It Maintainable)

- No new servers
- No heavy dependencies
- No large context dumps (cap to 3-5 bullets)
- One source of truth for context: SPARK_CONTEXT.md
- All new features must degrade gracefully
- Prefer JSON and JSONL over databases

---

## 8) Attainable Systems (What This Enables)

- Skills are actually used in live decisions
- Memory and learnings influence behavior, not just logs
- Orchestration chooses the right agent for the task
- Reliability improves over time with feedback
- System remains stable even when optional components are offline

---

## 9) Proposed File Changes (Initial Scope)

- Add: lib/skills_registry.py
- Add: lib/skills_router.py
- Update: lib/bridge.py (inject skills + advisor notes)
- Update: bridge_worker.py (advisor context + memory capture)
- Update: lib/advisor.py (fix + integrate memory banks + skills)
- Update: lib/orchestration.py (skill-based routing)
- Add: tests/test_skills_registry.py
- Add: tests/test_skills_router.py

---

## 10) Quick Start (After Implementation)

1) Set skills path:
   SPARK_SKILLS_DIR=C:\Users\USER\Desktop\vibeship-skills-lab

2) Start Spark:
   python sparkd.py
   python bridge_worker.py --interval 30

3) Verify:
   - SPARK_CONTEXT.md includes "Relevant Skills" and "Advisor Notes"
   - Dashboard shows updated stats

---

If you want this implemented, we can execute Phase 1-2 first (skills index + context),
then Phase 3 (advisor), then Phase 4-5 (feedback + orchestration).

---

## 11) Detailed Phase Plan (Build-Ready)

Each phase includes: scope, tasks, acceptance criteria, and tests.
All changes must preserve graceful fallbacks.

### Phase 0: Baseline Safety (1-2 days)
Scope:
- Fix known correctness bugs and stabilize defaults.

Tasks:
- Fix advisor Aha access (use AhaTracker.get_recent_surprises)
- Add Mind health check before retrieval in advisor
- Normalize Windows path separators in infer_project_key
- Ensure any failure in bridge_worker does not stop loop

Acceptance:
- No new exceptions in normal usage
- SPARK_CONTEXT.md still updates with existing data

Tests:
- Unit test: infer_project_key handles backslashes
- Manual: run bridge_worker for 5 minutes, no crash

---

### Phase 1: Skills Index + Router (2-3 days)
Scope:
- Make skills discoverable and queryable from SPARK_SKILLS_DIR.

Tasks:
- Add lib/skills_registry.py
  - Index on startup with cached JSON
  - Only read low-weight fields
  - Refresh when mtimes change
- Add lib/skills_router.py
  - Simple lexical scoring
  - Return top N skill IDs
- Add tests for indexing + routing stability
- Add docs: SPARK_SKILLS_DIR in README or docs

Acceptance:
- Can query skills by task text without loading full YAML bodies
- Index updates when a skill file changes

Tests:
- Unit: load temp skills YAML, verify index
- Unit: router ranks expected skills top-3

---

### Phase 2: Context Injection (1-2 days)
Scope:
- Surface relevant skills in SPARK_CONTEXT.md.

Tasks:
- Extend lib/bridge.generate_active_context:
  - "Relevant Skills" (top 3)
  - "Delegates" hints (if any)
  - Cap length to avoid prompt bloat
- Update bridge_worker to include skills section

Acceptance:
- SPARK_CONTEXT.md contains skill section when skills available
- Context remains < ~1k chars added

Tests:
- Integration: generate_active_context returns skills block

---

### Phase 3: Advisor Activation (1-2 days)
Scope:
- Make advice actionable at decision time without blocking execution.

Tasks:
- Fix and simplify lib/advisor.py:
  - Query order: memory banks -> cognitive -> mind -> skills
  - Cap output to 3-5 bullets
  - Guard Mind retrieval with health check
  - Add cache + TTL (already there)
- Add "Advisor Notes" section to SPARK_CONTEXT.md

Acceptance:
- Advice appears for relevant tasks
- No latency impact to hooks (advice runs in bridge_worker)

Tests:
- Unit: advisor returns empty list when subsystems are off
- Integration: SPARK_CONTEXT includes Advisor Notes

---

### Phase 4: Feedback Loop (2-3 days)
Scope:
- Lightweight self-improvement without heavy ML.

Tasks:
- Track advice usage in a small JSON file:
  - total surfaced
  - total followed (manual or inferred)
  - helpful rate
- Update cognitive insight reliability:
  - times_validated++ on matching successes
  - times_contradicted++ on matching failures
- Track skill effectiveness:
  - skills_effectiveness.json (success/fail)

Acceptance:
- Stats change over time with tool outcomes
- No noisy or unstable updates (only when confidence high)

Tests:
- Unit: reliability updates for known patterns
- Regression: no changes when advice absent

---

### Phase 5: Orchestration Integration (2-3 days)
Scope:
- Use skills to guide agent routing and coordination.

Tasks:
- Allow agent capabilities to be skill IDs
- Add routing helper: choose agent that matches top skill
- Record handoff outcomes in orchestration patterns

Acceptance:
- Routing uses skills when available, else falls back
- Coordination stats still compute as before

Tests:
- Unit: recommend_next_agent uses skill match
- Integration: handoff record includes skill context

---

## 12) Definition of Done (Project-Level)

- SPARK_CONTEXT.md includes: insights, memory banks, mind, skills, advisor notes
- Skills are indexed and routed (top-3) without heavy parsing
- Advice is surfaced and does not block tool execution
- Effectiveness counters update and can be inspected
- Orchestration can route based on skills
- All subsystems degrade gracefully when disabled

---

## 13) Risks and Mitigations

- Risk: Context bloat
  - Mitigation: Hard cap per section, top-3 skills, top-5 advice
- Risk: Noisy feedback loop
  - Mitigation: Only update on high-confidence matches
- Risk: Skills repo path invalid
  - Mitigation: Skip skills section, log debug only
- Risk: Mind latency
  - Mitigation: Run Mind retrieval in bridge_worker only

---

## 14) Recommended Build Order

1) Phase 0 (safety fixes)
2) Phase 1 (skills index + router)
3) Phase 2 (context injection)
4) Phase 3 (advisor activation)
5) Phase 4 (feedback loop)
6) Phase 5 (orchestration link)

Build in this order to keep each step stable and testable.
