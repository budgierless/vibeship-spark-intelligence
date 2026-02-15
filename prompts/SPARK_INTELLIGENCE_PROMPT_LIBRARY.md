# Spark Intelligence Prompt Library (10)

These are paste-ready prompts intended for operating and improving Spark Intelligence. Each one is optimized for: evidence-first reasoning, minimal feature-addition, and fast iteration via tuneables/ablation.

---

## 1) Stuck-State Triage (Fast Unblock)

**Use when:** the system is failing repeatedly, looping, or producing low-signal behavior.

**Prompt:**
You are my Spark operator. Run a stuck-state triage using `STUCK_STATE_PLAYBOOK.md` as the policy.

Context:
- What I was trying to do:
- What happened instead (symptoms):
- Last known good behavior (date/time):
- Recent commands/tool calls (copy/paste):
- Any relevant trace ids (if available):

Constraints:
- Prefer tuning/rollback/ablation over new features.
- No claims without evidence. If you cannot verify, label it `unverified`.

Output format:
## Diagnosis
- Primary failure mode:
- Secondary contributors:
- Evidence:

## 3-Step Unblock Plan (Do Now)
1.
2.
3.

## Rollback/Safety
- Fast rollback:
- "Stop the bleeding" toggle(s):
- Verification check:

## If Still Broken
- Next minimal probe:

---

## 2) Memory Retrieval Audit (Wins/Misses With Evidence)

**Use when:** you suspect Spark "had the knowledge" but did not surface it, or retrieval is noisy.

**Prompt:**
Audit memory retrieval quality for the last [TIME WINDOW]. Use evidence from on-disk artifacts (logs, jsonl, reports) and reference `docs/RETRIEVAL_LEVELS.md` and `docs/memory-retrieval-status.md`.

Inputs I can provide:
- Goal/task:
- Time window:
- Candidate files to inspect (optional):

Rules:
- Every win/miss must cite at least one trace id OR a concrete file path + line(s) reference. If missing, mark `unverified`.
- Recommend tuneables/policy changes first. Avoid adding new components.

Output format:
## Evidence Summary
- Window:
- Sources checked:
- Coverage gaps:

## Retrieval Wins
- Evidence:
- What was retrieved:
- Why it helped:

## Retrieval Misses
- Evidence:
- What should have been retrieved:
- Likely miss reason (router, embedding, policy, noise, schema):

## Tuning Actions (Ordered)
1. change, expected metric movement, rollback condition
2.
3.

---

## 3) Turn an Observation Into a Schema-First Chip

**Use when:** you have a recurring pattern worth capturing as a chip, but want it to be high-quality and mergeable.

**Prompt:**
Convert the following observation into a schema-first chip candidate. Follow `docs/CHIPS_SCHEMA_FIRST_PLAYBOOK.md` and `docs/CHIP_WORKFLOW.md`.

Observation:
- What happened:
- Why it matters:
- Example(s) (copy/paste):

Constraints:
- The chip must be specific, testable, and low-noise.
- Include a tight trigger. Prefer "evidence infrastructure" over vibes.

Output format:
## Chip Spec
- Name:
- Purpose:
- Trigger (exact):
- Inputs required:
- Exclusions (when NOT to fire):

## Schema (JSON)
```json
{
  "..."
}
```

## Distillation Rule
- What gets promoted to learnings:
- What gets discarded:

## Validation
- 3 positive examples:
- 3 negative examples:

---

## 4) Meta-Ralph Quality Gate for a Candidate Learning

**Use when:** you want to decide whether an insight should become a long-lived learning or be discarded as noise.

**Prompt:**
Act as Meta-Ralph. Evaluate this candidate learning for usefulness, specificity, and evidence. Use `META_RALPH.md` as the governing philosophy.

Candidate learning:
- Statement:
- Evidence (trace ids, logs, examples):
- How often it occurs:
- What decision it changes:

Output format:
## Verdict
- Promote / Hold / Discard:
- Confidence:

## Evidence
- What supports it:
- What would falsify it:

## Rewrite (If Promote)
- Learning (crisp, actionable):
- Scope boundaries:

## Validation Plan (If Hold)
1.
2.
3.

---

## 5) DEPTH Session Designer (Better Questions, Better Signal)

**Use when:** you want to run DEPTH training on a topic and avoid wasting cycles on low-signal questions.

**Prompt:**
Design a DEPTH session for:
- Domain id:
- Topic:
- Mode (classic/vibe):
- Max depth:
- Goal (what capability should improve):

Constraints:
- Questions must be deduplicated and progressively deepen.
- Include failure probes (ways the model might shortcut or hallucinate).
- Include scoring hooks (what "good" looks like).

Output format:
## Session Spec
- 10 questions (depth 1..N):
- For each: what it tests, common failure mode, what evidence to look for

## Anti-Gaming Checks
- 3 traps for shallow pattern-matching:

---

## 6) Tuneables Experiment Plan (A/B/C/D With Rollback)

**Use when:** you want to change tuneables/policies and measure impact, not vibes.

**Prompt:**
Create a minimal experiment plan to test the following change:
- Proposed change:
- Where it lives (file/env/tuneable name):
- Hypothesis:
- Risk:

Use `docs/ADVISORY_BENCHMARK_SYSTEM.md` and any relevant reports under `docs/reports/`.

Output format:
## Experiment Design
- Variants (A/B/C/D):
- Metrics (primary/secondary):
- Sample size/timebox:
- Stop conditions:
- Rollback criteria:

## Execution Steps
1.
2.
3.

## Interpretation Rules
- If metrics disagree, decide using:

---

## 7) "Cut List" Prompt (Ship by Removing, Not Adding)

**Use when:** scope is exploding, performance is degrading, or you're about to add a feature "because it might help."

**Prompt:**
Given this goal, produce a cut list that achieves the goal with fewer moving parts.

Goal:
- Desired outcome:
- Current approach:
- Constraints (time, risk, infra):

Rules:
- Prefer deleting/simplifying over adding.
- Propose the smallest viable surface area.
- Call out what you are refusing to do and why.

Output format:
## Minimal Path
- Keep:
- Cut:
- Defer:

## Risks
- Biggest risk:
- Mitigation:

## Next 3 Actions
1.
2.
3.

---

## 8) Docs-to-Implementation Task Breakdown (File-Level)

**Use when:** you have a design/spec doc and need a concrete, safe implementation plan.

**Prompt:**
Turn this spec into an implementation plan with file-level steps and test hooks.

Spec doc(s):
- [PATHS]

Constraints:
- Prefer small PR-sized steps.
- Every step must include a verification method (test, script, metric, or observable artifact).
- If a step touches runtime behavior, include a rollback.

Output format:
## Steps
1. change, files, verification, rollback
2.
3.

## Open Questions
- What must be decided before coding:

---

## 9) Tool Error Forensics (Root Cause, Not Workarounds)

**Use when:** you hit recurring tool errors (timeouts, parsing, "tool_X_error") and want to stop them permanently.

**Prompt:**
Investigate this recurring tool failure and propose a durable fix.

Error:
- Exact error text:
- Frequency:
- When it happens:
- What input triggered it:

Constraints:
- Prefer fixing the cause (input shaping, retries, timeouts, serialization) over adding special cases.
- Provide a reproduction recipe.

Output format:
## Root Cause Hypotheses (Ranked)
1.
2.
3.

## Reproduction
- Minimal steps:

## Fix Plan
1. code/config change, files, test
2.

## Guardrail
- What prevents regression:

---

## 10) "Compound the Learnings" Weekly Review

**Use when:** you want Spark to actually improve week-over-week instead of accumulating noise.

**Prompt:**
Run a weekly compounding review for [DATE RANGE]. Use evidence from learnings, reports, and runtime artifacts.

Inputs:
- Primary objectives this week:
- What shipped/changed:
- Known incidents:

Rules:
- No claims without evidence.
- Prefer a small number of high-leverage tuneables/chips over many changes.

Output format:
## What Improved (Evidence-Backed)
- item, evidence, why it matters

## What Regressed (Evidence-Backed)
- item, evidence, likely cause

## Top 5 Learnings to Keep
- learning, how it changes operator behavior

## Top 5 Learnings to Kill/Suppress
- learning, why it is noise, suppression method

## Next Week: 3 Bets
1. bet, expected impact, metric, rollback
2.
3.

