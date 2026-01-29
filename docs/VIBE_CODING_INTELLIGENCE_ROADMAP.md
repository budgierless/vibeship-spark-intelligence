# Vibe Coding Intelligence Roadmap (Comparison)

Purpose: compare the current Spark improvement plans with a day-to-day, "vibe coding" focused roadmap, and define what it takes to make Spark a true evolving intelligence for building projects and managing agents.

## Current Plans (What Exists)

Sources:
- docs/IMPLEMENTATION_ROADMAP.md
- docs/INTEGRATION-PLAN.md
- docs/SPARK_GAPS_AND_SOLUTIONS.md

Current status highlights:
- DONE: Session bootstrap, pattern detection, decay/conflicts, project context, worker health.
- IN PROGRESS: Validation loop v1 (preference + communication validation).
- PENDING: Skills index/router, advisor activation, feedback loop (skill effectiveness), full prediction->outcome validation.

## Proposed Day-to-Day Improvements (What We Want)

1) Focus Mode (session goal + filtering)
2) Decision snapshots (micro "why" after key changes)
3) Outcome check-ins (Did that work? Yes/Partially/No)
4) Auto-apply user constraints (no gradients, tone rules, format)
5) True prediction->outcome validation (reliability becomes real)
6) Noise control + consolidation (merge duplicates)
7) Context gating (surface only relevant learnings)
8) Agent routing learns from outcomes
9) Team memory across agents (shared learnings)
10) Vibe-coding playbooks (repeatable successful workflows)

## Comparison Matrix (Existing vs Proposed)

| Proposed Improvement | Related Existing Plan | Current Status | Notes |
|---|---|---|---|
| Focus Mode (session goal + filtering) | Session Bootstrap + Context Sync | Missing | We inject context but do not set goal; output is generic. |
| Decision snapshots (micro "why") | None | Missing | No systematic capture of reasoning. |
| Outcome check-ins | Validation Loop | Partial | v1 exists but does not ask for outcomes explicitly. |
| Auto-apply constraints | Context Sync + SPARK_CONTEXT | Partial | Preferences are present but not enforced automatically. |
| True prediction->outcome validation | Phase 6 Validation Loop | Partial | Prediction->outcome not implemented. |
| Noise control + consolidation | Dedupe signals, decay | Partial | Dedupe exists for signals; duplicates still common. |
| Context gating | Context Sync + Bridge | Partial | Relevance matching exists but weak; needs stronger gating. |
| Agent routing learns from outcomes | Orchestration + Feedback Loop | Missing | Feedback loop exists but not tied to routing. |
| Team memory across agents | Orchestration | Missing | No shared agent memory or tagging. |
| Vibe-coding playbooks | Skills/Advisor | Missing | Skills exist conceptually but not enforced as workflows. |

## Application Levels (What Actually Changes Behavior)

1) Live context injection (SPARK_CONTEXT.md) - strongest impact
2) Bootstrap outputs (CLAUDE.md/USER.md/.cursorrules) - startup only
3) Advisor/Skills hints - helpful but optional
4) Validation stats + promotions - indirect behavior changes

Most "intelligence" is only effective if it lands in (1) or (2).

## Roadmap to True Vibe-Coding Intelligence

### Phase A (Next, highest ROI)
- Focus Mode: add a session goal and use it to filter context output.
- Outcome check-ins: add a lightweight end-of-chunk prompt and feed validation loop.
- Auto-apply constraints: inject hard constraints into prompts/templates.
- Improve context gating: stricter relevance filtering, reduce noise.

### Phase B (Core Intelligence Upgrade)
- True prediction->outcome validation for insights.
- Auto-boost/decay based on real outcomes.
- Surprise capture based on failed predictions (not just tool failure).

### Phase C (Team + Agent Evolution)
- Agent routing learns from outcomes.
- Shared team memory with tags per agent role.
- Playbooks: convert successful sequences into reusable workflows.

## What Gets Better (Measurable)

- Preference adherence rate (target: >90%)
- Tool failure rate (target: reduced by 30-50%)
- Validation accuracy (target: rising over time)
- Context relevance (target: >80% of injected items used)
- Agent routing success rate (target: >70% on best-fit agent)

## Recommendation

Start with Phase A. Without focus, outcome check-ins, and enforced constraints, the learnings are mostly passive memory. Phase B makes the intelligence "self-correcting." Phase C turns it into a collaborative system.
