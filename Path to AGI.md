# Path to AGI (Narrow Domain: Vibe Coding)

This document is the actionable build plan to evolve Vibeship into a narrow-domain AGI for vibe coding. It is intentionally concrete so we can pick up tomorrow without re-deriving context.

**Scope**
We are not claiming general AGI. We are targeting narrow-domain AGI: autonomous end-to-end coding work with minimal human steering, backed by memory, feedback, and verification.

**Definition: “Narrow-Domain AGI for Vibe Coding”**
We can credibly say “AGI (narrow)” when the system can:
1. Plan, execute, verify, and recover across most coding tasks in the domain with minimal intervention.
2. Generalize across stacks and repos without custom prompt tuning for each project.
3. Improve its behavior over time based on outcomes (not just remember).
4. Handle novel tasks by decomposing and adapting, not just retrieving.

**Evidence Bar (measurable)**
1. ≥80% end-to-end completion on unseen coding tasks with verification gates passing.
2. ≥70% completion on multi-hour projects without human “rescue” steps.
3. Recovery success ≥60% when a phase fails (autonomous replanning and retry).
4. Skill selection accuracy ≥75% vs human-labeled gold set.
5. Outcome-weighted retrieval improves success rate by ≥15% over baseline.

---

**Current Assets and Honest Assessment**

**Repo: vibeship-spark-intelligence**
Strengths
1. Outcome-weighted semantic retrieval implemented in `lib/semantic_retriever.py`.
2. Structural retrieval for EIDOS distillations in `lib/eidos/retriever.py`.
3. Policy patches enable behavior change in `lib/eidos/policy_patches.py`.
4. Meta-Ralph provides quality gating and outcome tracking in `lib/meta_ralph.py`.

Gaps
1. Semantic retrieval is disabled by default and triggers are off unless explicitly enabled in `lib/semantic_retriever.py`.
2. Outcome tracking in `lib/outcomes/tracker.py` is not clearly wired into the active loop.
3. There is no direct ingestion of Spawner mission outcomes into Spark yet.

Build-On
1. Make Spark the global outcome authority for missions executed in Spawner.
2. Enable semantic retrieval by default for selected tools with safe guardrails.
3. Connect EIDOS policy patches to runtime enforcement in Spawner.

**Repo: spawner-ui**
Strengths
1. Mission execution engine with persistence and resume support in `src/lib/services/mission-executor.ts`.
2. End-to-end goal → analysis → skill matching → workflow in `src/lib/services/goal-to-workflow.ts`.
3. Task completion gates exist in `src/lib/services/completion-gates.ts`.
4. Learning reinforcement exists in `src/lib/services/learning-reinforcement.ts`.
5. Memory system documented in `MIND.md`.

Gaps
1. Completion gates are defined but not wired into execution.
2. Learning reinforcement is implemented but not called from mission completion.
3. Skill routing logic is fragmented across `src/lib/services/skill-matcher.ts`, `src/lib/services/skill-router.ts`, and `src/lib/utils/prd-analyzer.ts`.
4. README content appears unrelated and needs correction in `README.md`.

Build-On
1. Wire completion gates into mission completion in `src/lib/services/mission-executor.ts`.
2. Call `reinforceMission()` after mission completion and feed results into skill selection.
3. Select one canonical skill matching pipeline and treat others as signals.

**Repo: vibeship-skills-lab**
Strengths
1. Clear H70-C+ specification in `H70-PLUS-SPEC.md`.
2. Validation tooling exists in `tools/validate-h70-cplus.js`.
3. Rich example skills like `development/backend.yaml`.

Gaps
1. Conversion progress shows zero fully compliant H70-C+ skills in `CONVERSION-PROGRESS.md`.
2. Duplicates listed in `SKILL-CONVERSION-MAP.md` are not yet resolved.
3. No automated export pipeline into Spawner’s `static/skills.json`.

Build-On
1. Create a build pipeline from H70-C+ YAML → `spawner-ui/static/skills.json`.
2. Add validation as a gate in the pipeline.
3. Prioritize converting the skills actually used by Spawner’s routing and matching.

**Repo: vibeforge1111/vibeship-idearalph (IdeaRalph MCP)**
Strengths
1. Clean planning surface for ideation, validation, and PRD generation (MCP tools).

Gaps
1. No explicit execution feedback loop.
2. No native contract to Spawner mission schema.

Build-On
1. Define a plan schema that directly maps to Spawner missions.
2. Feed mission outcomes back into IdeaRalph for plan refinement.

---

**Target Architecture (Tomorrow’s North Star)**
1. IdeaRalph produces structured plans.
2. Spawner converts plan → mission → execution.
3. Completion gates verify progress.
4. Outcomes are sent to Spark.
5. Spark reweights retrieval and policy patches.
6. Spawner skill selection uses Spark’s effectiveness scores.

---

**Phased Build Plan**

**Phase 1: Execution Truth (Verification + Outcomes)**
Goal: “Completion” becomes real.
Tasks
1. Wire `getCompletionGates()` and `validateTaskCompletion()` into `src/lib/services/mission-executor.ts`.
2. Block task completion if critical gates fail.
3. Emit structured outcome events for each task and mission.
4. Call `reinforceMission()` in `src/lib/services/learning-reinforcement.ts` after mission completion.
5. Persist outcomes to Spark via a bridge API.

Exit Criteria
1. Tasks cannot complete without passing required gates.
2. Every mission generates a structured outcome payload.
3. Outcomes are ingested into Spark and visible in Meta-Ralph stats.

**Phase 2: Planning Integration (IdeaRalph → Spawner)**
Goal: Planner output becomes executable missions.
Tasks
1. Define a plan JSON schema compatible with Spawner’s mission format.
2. Add an adapter in Spawner to ingest IdeaRalph plan outputs.
3. Log plan quality metrics (task count, dependency correctness, gate coverage).

Exit Criteria
1. IdeaRalph plan can be executed end-to-end in Spawner.
2. Plan execution outcomes feed back to IdeaRalph.

**Phase 3: Skill Library Hardening**
Goal: Skill quality becomes reliable and measurable.
Tasks
1. Create a build pipeline to convert H70-C+ YAML into `spawner-ui/static/skills.json`.
2. Run `tools/validate-h70-cplus.js` as a mandatory gate.
3. Resolve duplicates from `SKILL-CONVERSION-MAP.md`.
4. Convert the top 50 most-used skills first.

Exit Criteria
1. Spawner uses H70-C+ skills as its primary skill source.
2. Validation passes with zero critical errors.

**Phase 4: Policy Learning and Retrieval Control**
Goal: System behavior changes from outcomes, not just ranking.
Tasks
1. Enable semantic retrieval for production-safe contexts in `lib/semantic_retriever.py`.
2. Connect Spark outcome effectiveness to skill selection weights in Spawner.
3. Apply EIDOS policy patches to real-time execution constraints.

Exit Criteria
1. Proven improvement in mission success rate vs baseline.
2. Negative outcomes visibly suppress related advice or skill choices.

---

**Explicit Integration Tasks (Concrete Starting Points)**
1. Add mission completion hooks in `src/lib/services/mission-executor.ts` to call completion gates from `src/lib/services/completion-gates.ts`.
2. Add a mission-end handler that calls `reinforceMission()` in `src/lib/services/learning-reinforcement.ts`.
3. Add a “Mission Outcome Event” emitter (JSON payload) and route it to Spark.
4. Create a Spark endpoint that ingests mission outcomes into `lib/meta_ralph.py` and `lib/outcomes/tracker.py`.
5. Normalize skill IDs between `vibeship-skills-lab` and `spawner-ui`.

---

**System Metrics to Track Weekly**
1. Mission completion rate with gates enabled.
2. Average retries per mission.
3. Skill selection precision (manual review sample).
4. Outcome-weighted retrieval lift vs baseline.
5. % of tasks blocked by gates and later resolved successfully.

---

**Risk Register (Reality Check)**
1. Gate strictness may stall progress if verification is too strict.
2. Outcome data may be noisy or biased without clear success criteria.
3. Skill conversion effort is large; lack of automation will stall progress.
4. Planner output quality may be inconsistent without feedback integration.

---

**Tomorrow Morning Start (Pick One Track)**
1. Wire completion gates into mission execution.
2. Add mission outcome event export to Spark.
3. Build H70-C+ export pipeline into Spawner.

---

**Claim Statement (Internal)**
We are building a compounding intelligence layer for vibe coding: adaptive memory + relevance + verification + feedback. It is not general AGI, but it is the minimal stack required for narrow-domain AGI behavior.
