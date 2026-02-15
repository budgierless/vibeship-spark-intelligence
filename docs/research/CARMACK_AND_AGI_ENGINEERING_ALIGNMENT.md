# Carmack And AGI Engineering Alignment (Spark Research)

Date: 2026-02-15
Repo: vibeship-spark-intelligence
Audience: Spark operators/engineers
Goal: Extract "Carmack-style" (tight, measured, low-complexity) AGI-adjacent principles and map them onto Spark's existing intelligence flow, with concrete optimization and stability recommendations.

This document is intentionally pragmatic:
- prefer bounded, testable changes over conceptual rewrites
- prefer a smaller number of mechanisms with better instrumentation over a large surface area
- treat "self-evolving intelligence" as: measurable loops that improve outcomes under constraints

---

## 1) Current Spark Intelligence Flow (What We Are Actually Doing)

Spark already has the core building blocks most AGI roadmaps talk about, but expressed as an applied "production agent memory + advisory" system rather than a trained end-to-end policy.

Canonical runtime map: `Intelligence_Flow.md`

Critical path (already formalized in Spark docs):

`retrieval -> advisory -> action -> outcome attribution`

Key subsystems in the active data path:
- Event ingest: hooks/adapters -> `sparkd.py` -> `lib/queue.py`
- Orchestration: `bridge_worker.py` -> `lib.bridge_cycle.run_bridge_cycle`
- Memory and representation:
  - durable cognitive insights + reliability: `lib/cognitive_learner.py`
  - semantic index + retrieval: `lib/semantic_retriever.py`
  - structured "episodes" and distilled rules: `lib/eidos/*`, `lib/pattern_detection/*`
- Advisory (online decision support):
  - pre-tool advisor invocation + gating: `lib/advisory_engine.py`, `lib/advisor.py`
  - packet store + feedback: `lib/advisory_packet_store.py`
  - memory fusion bundles: `lib/advisory_memory_fusion.py`
- Accountability loop:
  - predictions/outcomes: `lib/prediction_loop.py`, outcomes storage, `lib/validation_loop.py`
  - quality gate / critique: `lib/meta_ralph.py`
- Optional: chips (domain intelligence), external research, multiple sync adapters

The repo already applied several "Carmack" downgrades:
- keep sync default to core adapters only
- make advisory fallback emission opt-in
- filter tool-error telemetry from memory fusion
- throttle duplicate-only chip merge churn

See: `docs/SPARK_CARMACK_OPTIMIZATION_IMPLEMENTATION.md` and `docs/SPARK_LIGHTWEIGHT_OPERATING_MODE.md`

---

## 2) John Carmack: What He Did, What He Brought, Why It Matters Here

### 2.1 What Carmack Did (Career, Notability)

John Carmack is best known for:
- shipping multiple era-defining game engines (real-time 3D rendering, performance-first engineering)
- leading core engineering at Oculus/Meta VR
- leaving Meta in 2022 to focus on AGI work via Keen Technologies

These aren't "AGI research contributions" in the academic sense, but the engineering style is highly relevant:
- obsessive profiling and performance budgets
- minimal, deterministic systems
- ruthless removal of optional complexity without measurable lift

Why he is relevant to Spark:
- Spark is not "just prompts"; it is a runtime system with budgets, backpressure, multiple data stores, and failure modes.
- Carmack's primary advantage is not ideology, it is relentless insistence that systems be measurable, bounded, and debuggable.

### 2.2 What Carmack Brought To The Table (Engineering Principles)

These principles show up consistently across Carmack's public writing and in how he built systems:

1. Critical-path obsession
   - if it is not on the critical path, it should be optional or deleted

2. Boundedness
   - hard time/memory limits, graceful degradation, fail fast

3. Determinism and debuggability
   - predictable failure modes, classified reasons, reproducible behavior

4. Measurement over argument
   - prefer "build a harness, measure in real usage" over theoretical debates

5. "Less with better defaults"
   - shrink the number of knobs and pathways; make the default mode reliable and valuable

Spark already encodes these as policy in `docs/SPARK_LIGHTWEIGHT_OPERATING_MODE.md`. The gap is making them the "organizing force" for every new feature.

### 2.3 Carmack's AGI Work (Keen) And The Adjacent Research Cluster

Publicly reported facts (high-level, not internal details):
- Carmack founded Keen Technologies in late 2022 to work on AGI.
- Early public reporting connected Keen with reinforcement-learning-style ideas and the "agent" framing, and noted ongoing reading of modern world-model / self-supervised work.
- Richard Sutton is publicly associated with Keen (as of 2023).

This matters because Carmack's paper-reading cluster overlaps with Spark's architecture choices:
- world models (Dreamer/PlaNet style) -> "predict/plan with compact latent state"
- JEPA / predictive representation learning -> "learn state representations that support downstream action"
- training stability and optimizer research -> "reduce noise, get better learning signals"

Spark does not train end-to-end policies today, but it DOES:
- form a state representation (context pack + memory bundle)
- choose actions (advisory emits, tool gating, escalation decisions)
- observe outcomes (tool success/failure, user feedback, engagement)
- update future behavior (tuneables, reliability, packet store, promotion)

So we can adopt the *engineering lessons* even if we are not doing the same training regime.

### 2.4 What Carmack Seems To Emphasize (Based On Public Statements)

From publicly available partnership announcements and reporting, several themes keep showing up:
- agency: systems that act over time (not just one-shot prediction)
- temporal credit assignment: learning what helped after delayed outcomes
- skepticism of fashion: a willingness to pursue non-mainstream bets if they are coherent and testable

In Spark terms, that maps cleanly to:
- the advisory engine as the policy surface
- the prediction/outcome loop as credit assignment scaffolding
- a stable "keep/kill" loop as the antidote to fashionable complexity

---

## 3) Quick Source Pack (So This Doc Is Auditable)

This doc is not trying to be exhaustive biography. It is trying to be traceable enough that we can ground decisions.

Keen / Carmack / Sutton:
- TechCrunch (2019): Carmack steps down at Oculus to pursue AGI: https://techcrunch.com/2019/11/13/john-carmack-steps-down-at-oculus-to-pursue-ai-passion-project-before-i-get-too-old/
- TechCrunch (2022): Carmack's AGI startup Keen raises $20M: https://techcrunch.com/2022/08/19/john-carmack-agi-keen-raises-20-million-from-sequoia-nat-friedman-and-others/
- AMII (2024/2025): Sutton update referencing 2023 partnership with Carmack/Keen: https://www.amii.ca/updates-insights/rich-sutton-turing
- AMII (2025): Carmack talk (Upper Bound 2025) on Keen research directions: https://www.amii.ca/videos/keen-technologies-research-directions-john-carmack-upper-bound-2025
- The Register (2023): reporting on Sutton joining Keen + Carmack timeline: https://www.theregister.com/2023/09/26/john_carmack_agi/

Alberta Plan:
- Sutton, Bowling, Pilarski (2022): "The Alberta Plan for AI Research" (arXiv): https://arxiv.org/abs/2208.11173

World models / planning:
- Hafner et al (2023): DreamerV3 (arXiv): https://arxiv.org/abs/2301.04104
- Silver et al (2016): AlphaGo Nature paper: https://www.nature.com/articles/nature16961
- Schrittwieser et al (2020): MuZero Nature paper: https://www.nature.com/articles/s41586-020-03051-4

Predictive representation:
- Assran et al (2023): I-JEPA (arXiv): https://arxiv.org/abs/2301.08243

Active inference:
- Friston (2010): Free Energy Principle review (Nat Rev Neurosci): https://www.nature.com/articles/nrn2787

Bottleneck / "consciousness prior":
- Bengio (2017): The Consciousness Prior (arXiv): https://arxiv.org/abs/1709.08568

---

## 4) Other AGI-Adjacent Scientists: What They Did, What They Contributed, How Spark Connects

This is a deliberately curated set: each one maps to something Spark already has, or something Spark can implement without becoming a research lab.

### 3.1 Richard Sutton (Reinforcement Learning, "Bitter Lesson", The Alberta Plan)

What he did:
- foundational RL methods (temporal-difference learning, policy/value framing)
- argued repeatedly that scalable learning and computation beat hand-built heuristics ("the bitter lesson")
- proposed "The Alberta Plan" as a long-lived agent research agenda (continual learning, planning, representation, and interaction)

What he brought:
- a clean interface for self-improvement: rewards/outcomes + policies + value
- the insistence that the agent must be long-lived, continually learning, and measured on real interaction

Useful Alberta Plan framing for Spark operators:
- build agents that run for a long time, not single episodes
- learn continually from interaction, not static datasets
- use prediction and planning, not just reactive behavior
- focus on the "right abstractions" (state representation) and credit assignment over time

How Spark connects:
- Spark's "outcome attribution" is a proto-reward signal.
- The advisory router is a policy: when to stay embeddings-only vs escalate.
- Reliability scoring + Meta-Ralph are value proxies: do we trust this advice source?

Where Spark differs:
- Spark's "learning" is currently mostly symbolic/statistical (reliability weights, promotion rules, gating), not gradient-based policy learning.
- Rewards/outcomes are sparse/noisy and often not formally captured.

Low-complexity utilizations:
1. Formalize a reward-like signal for advisory actions
   - when advice is shown and acted on, score it; when ignored or harmful, penalize it
2. Treat tuneables as a policy vector and move from "static" to "suggested deltas"
   - keep auto-apply conservative; auto-suggest plus human gate first
3. Enforce "continual learning with bounded memory"
   - cap memory growth and require pruning/decay policies tied to measured usefulness

### 3.2 Demis Hassabis + David Silver (DeepMind: AlphaGo, Search + Value, Scaling RL Systems)

What they did:
- built systems combining representation learning, planning/search, and value estimation in large-scale RL settings

What they brought:
- the idea that "fast heuristics" (policy prior) and "expensive reasoning" (search) can be combined, but must be bounded and justified

The AlphaGo decomposition is a useful mental model for Spark (even though the mechanisms differ):
- policy prior: quickly proposes a small set of "good next moves"
- value estimate: scores positions/moves
- search: spends extra compute only when it will likely pay off

How Spark connects:
- Spark already has a hybrid retrieval regime:
  - fast path: embeddings-first semantic retrieval
  - expensive path: bounded hybrid-agentic facet fanout
- The gating thresholds in `TUNEABLES.md` are Spark's "when do we search deeper?"

Where Spark differs:
- Spark's "search" is LLM fanout, not tree search in a formal environment.
- Spark's "value" is a mixture of heuristics and quality gates, not learned value functions.

Low-complexity utilizations:
1. Make "search" opt-in by signal
   - keep the minimal gate strategy as default
2. Track cost/benefit per route
   - maintain per-route telemetry: latency + downstream usefulness delta
3. Keep the fast path extremely strong
   - invest in embeddings retrieval quality so "agentic" is rare and high-leverage

### 3.3 Yann LeCun (Self-Supervised Representation, JEPA/I-JEPA)

What he did:
- major contributions to deep learning and modern self-supervised representation learning

What he brought:
- predictive representations: learn compact state that is useful for downstream tasks without relying on labels/rewards

How Spark connects:
- Spark's semantic index is effectively a representation layer for "what we learned".
- The advisory engine is a downstream task using that representation.

Where Spark differs:
- Spark uses frozen embeddings and heuristics rather than learning a task-specific representation of "advice usefulness".

Low-complexity utilizations:
1. "Predictive representation" at the system level
   - represent each event/action/outcome as a state transition; store compact features
2. Make retrieval scoring more outcome-grounded
   - lift items that historically improved outcomes for similar intents

One concrete JEPA-inspired move that stays Carmack-simple:
- separate "representation" from "language"
- store and retrieve from the representation space
- only decode to language at the final step (advisory synthesis)

Spark already approximates this:
- embeddings index is representation space
- advisory synthesis is language decode
The optimization is to minimize how often you "decode" (emit text) without high confidence.

### 3.4 Karl Friston (Free Energy Principle, Predictive Processing)

What he did:
- proposed the Free Energy Principle as a unifying theory for biological inference and action

What he brought:
- a simple operational metaphor: systems act to reduce prediction error (surprise) under constraints

How Spark connects:
- Spark already tracks "surprise" (`aha_tracker`, prediction/outcome mismatches) and uses it for memory gating.

Where Spark differs:
- Spark does not yet close the loop so that prediction error directly updates routing/gating policies in a disciplined way.

Low-complexity utilizations:
1. Use prediction error as a first-class trigger for:
   - "store this" (memory gate)
   - "change a knob suggestion" (tuneable delta suggestion)
2. Force more explicit predictions on high-stakes actions
   - a lightweight "expected outcome" field in traces for key actions improves learning signals

### 3.5 Yoshua Bengio (System 2, Consciousness Prior, GFlowNets)

What he did:
- foundational deep learning work and modern proposals for more structured reasoning and learning

What he brought:
- the "bottleneck" intuition: limited working set, selective attention, and structured latent variables can help generalization and reasoning

How Spark connects:
- Spark already has a "bottleneck": the advisory output limit (`advisor.max_items`, actionability enforcement, suppression policies).
- Spark's chips and distillations are attempts to create structured, re-usable concepts.

Low-complexity utilizations:
1. Stronger bottleneck discipline
   - fewer items, higher threshold, better dedupe, clearer "why this now" explanations
2. Explicit "working set" construction
   - build a tiny scratchpad of: top intent, top 3 evidence items, top 1 constraint, top 1 next check

### 3.6 Geoffrey Hinton and Ilya Sutskever (Representation Learning, Sequence Modeling, Scaling)

What they did:
- core deep learning ideas enabling modern neural sequence models

What they brought:
- representation learning as the engine; scaling and optimization as the practical path

How Spark connects:
- even without training large models, Spark is a *system-level* learner:
  - it builds representations (memory, embeddings)
  - it optimizes policies (tuneables, routing, gating)

Low-complexity utilizations:
1. Reduce reliance on hand-written heuristics when the data is strong
   - use benchmark outcomes to pick policies rather than personal preference
2. Keep optimization surfaces small
   - fewer knobs; more stable defaults; auto-suggest deltas with hard guardrails

---

## 5) How Our Approach Connects With Carmack (And Where It Conflicts)

### 4.1 The Good News: Spark Is Already "Carmack-Shaped"

From `Intelligence_Flow.md`, Spark already does the parts Carmack would demand:
- a clearly defined critical path for value delivery (advisory before action)
- bounded escalation (`agentic_deadline_ms`, rate caps, max_queries)
- deterministic suppression/failure reasons (no-emit reason codes)
- a benchmark harness for advisory quality (`docs/ADVISORY_BENCHMARK_SYSTEM.md`)

### 4.2 The Conflict Risk: Intelligence Surface Area Expands Faster Than Measured Lift

Where complexity creep tends to appear in systems like this:
- multiple parallel memory stores with subtle drift in "what counts"
- optional adapters producing operational noise and mental overhead
- additional detectors/observers that increase stored volume faster than usefulness
- knobs added faster than instrumentation and regression tests

Spark has already seen this and started to fix it (lightweight mode).
The remaining work is enforcing the rule across all future features:

If it does not move a KPI on the critical path, it is not allowed to become default.

---

## 6) Concrete, Low-Complexity Reuse: What To Steal And Implement (Carmack-Style)

These are the "steal it today" moves that align with Carmack + Sutton + LeCun without turning Spark into a research project.

### 5.1 Make Outcomes Sharper (Better Learning Signal With Less Code)

Problem:
- outcome signals exist, but they can be too implicit to drive policy changes reliably.

Steal:
- RL framing: actions should have measured outcomes.

Minimal implementation direction:
- standardize a small set of outcome tags for advice:
  - `acted`, `ignored`, `blocked`, `harmful`, `confusing`, `too_noisy`
- make advisory emit log carry a stable advice_id and route_id
- attach an outcome within a bounded time window
- update: packet score, reliability weights, and/or a "tuneable suggestion"

### 5.2 Policy As Data, Not Code (And Keep It Bounded)

Problem:
- policies live partly as code heuristics and partly as tuneables; drift is easy.

Steal:
- Carmack: fewer code paths, more obvious switches.

Minimal implementation direction:
- define a single "policy surface" for the critical path:
  - retrieval router thresholds
  - advisory gate thresholds
  - max_items, min_rank_score
  - rate caps and timeouts
- everything else becomes:
  - off by default
  - or only active in non-default experimental profiles

### 5.3 Build A "Keep Or Kill" Weekly Delete Pass That Is Actually Executable

Problem:
- delete passes often become aspirational.

Steal:
- Carmack: remove systems that don't pay rent.

Minimal direction:
- choose 1-3 measurable indicators per subsystem:
  - cost: latency, queue volume, CPU, log size
  - benefit: acted-on rate, benchmark delta, decreased fallback ratio
- if benefit is not measurable within 7 days, subsystem is downgraded or removed from default mode

### 5.4 Invest In Fast Path Quality So Escalation Stays Rare

Problem:
- hybrid-agentic paths can silently become the default if fast path is weak.

Steal:
- DeepMind style: expensive search should be rare and justified.

Minimal direction:
- improve embeddings-first retrieval (index hygiene, candidate quality, dedupe, MMR)
- keep escalation gates minimal and hard-bounded

### 5.5 Stabilize The "Working Set" For Advice (Bengio Bottleneck Discipline)

Problem:
- advice bundles can get long; long bundles increase user cognitive load and reduce actionability.

Steal:
- "conscious bottleneck": small set of high-value items.

Minimal direction:
- enforce a short template:
  - 1 sentence diagnosis
  - 1 recommended next action (command/check)
  - up to 2 memory items with 1-line "why"
  - 1 safety/constraint if relevant

---

## 7) Stability And Scalability: Architecture Moves That Keep Spark From Collapsing Under Its Own Growth

This is where Carmack's discipline is most valuable: stability is not an afterthought, it is the product.

### 6.1 Bound Everything That Can Fan Out

In Spark, the dangerous expanders are:
- agentic retrieval (fanout queries)
- research ingestion (external sources)
- chip observers (large event volume)
- sync adapters (multiple sinks)

Rule:
- every expander must have:
  - a budget (ms, max items, max bytes)
  - a rate limit
  - a deterministic backoff or drop policy
  - a traceable reason when it drops

### 6.2 Make The Default Mode Single-Path And Deterministic

Default should be:
- one retrieval strategy (embeddings-first)
- one gating strategy (minimal)
- one packet policy (packet-first)
- one sync policy (core-only)

Everything else should be:
- profile-only (benchmarks)
- or operator-enabled with explicit goals/expiration

### 6.3 Use "Invariants" As Guardrails, Not More Logic

Examples of invariants that reduce complexity:
- every advice emit has: `trace_id`, `route`, `reason`, `budget_ms`, `sources_used`
- every stored memory item has: `source`, `evidence`, `reliability`, `last_used_at`
- every tuneable change has: `why`, `expected delta`, `rollback trigger`

Invariants reduce debugging time and prevent silent drift.

---

## 8) "Carmack Questions": The Set Of Questions That Keep The System From Getting Fake-Smart

Use these as a recurring review checklist:

1. What is the single KPI this change is supposed to move?
2. What is the latency or compute cost, and where is it measured?
3. If we turn this off, what real user harm occurs?
4. Is this in the critical path, or optional?
5. Does this create a new code path that can drift?
6. What is the deterministic failure classification when this fails?
7. What is the rollback trigger and how do we detect it quickly?
8. What evidence do we store that will let us learn from the outcome?
9. Are we increasing the "working set" presented to the user?
10. Did we reduce the number of knobs or increase them?

---

## 9) Suggested Next Research Deepening (Only If It Serves The Critical Path)

If you want to go deeper into the research cluster Carmack is reading, focus only on what can translate into:
- better state representation for retrieval
- better credit assignment for "advice usefulness"
- better bounded planning (rare escalation, strict budgets)

High-leverage clusters:
- world models (Dreamer/PlaNet) as inspiration for "state transition logging"
- JEPA as inspiration for "predictive embeddings" (outcome-aligned retrieval scoring)
- optimizer stability work as inspiration for "reduce noisy deltas and churn"

Do not expand the system until the critical-path KPIs are trending in the right direction for at least 7 days.

---

## 10) References

See section "3) Quick Source Pack".
