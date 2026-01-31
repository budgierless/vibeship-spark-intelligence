# Evolution Chips Research

This document captures the chip format options, the recommended chip system,
the 10 evolution methodologies, and the benchmarking plan discussed today.

---

## Chip Format Options (Pros/Cons)

### Option A — Single YAML File

Pros:
- Simple to share and install.
- Easy for non-technical creators.
- Works offline with zero dependencies.

Cons:
- Becomes large for complex chips.
- Hard to reuse shared logic.
- No clean separation of triggers/observers/outcomes.

---

### Option B — Multi-File Chip Bundle

Structure:
```
chips/
  marketing/
    chip.yaml
    triggers.yaml
    observers.yaml
    outcomes.yaml
    evolution.yaml
    questions.yaml
```

Pros:
- Clean modularity.
- Easier to update one part without breaking the rest.
- Better for team collaboration.

Cons:
- Harder to share (needs zip or folder).
- Loader is more complex.

---

### Option C — Hybrid (Single YAML + Includes)

Example:
```yaml
includes:
  - triggers.yaml
  - observers.yaml
```

Pros:
- Best of both: simple by default, modular when needed.
- Works with a zip or repo.
- Loaders can merge into one runtime spec.

Cons:
- Requires merge rules and strict validation.
- More edge cases to handle.

---

## Recommended Chip System (Hybrid)

Design goals:
- Simple to run locally.
- Easy to share.
- Scales to complex domains.
- Strict validation and quality gates.

Proposed spec (v0.2):
```yaml
chip:
  id: vibecoding
  name: Vibe Coding Intelligence
  version: 0.2.0
  description: >
    Learns what makes builds feel "good," fast, and reliable.

  domains: [engineering, product, shipping, ux]
  author: Vibeship
  license: MIT

includes:
  - triggers.yaml
  - observers.yaml
  - outcomes.yaml
  - evolution.yaml
  - questions.yaml

scopes:
  events: [tool_calls, user_feedback, code_changes]
  outputs: [insights, recommendations]

quality_gates:
  min_evidence: 2
  min_validations: 2
  allow_categories: [reasoning, wisdom, user_understanding, context]
  block_patterns:
    - "Sequence '.*' worked well"
```

Why this works:
- Single file is still enough for simple chips.
- Complex chips can opt into modularity.
- Governance and quality gates are built in.

---

## 10 Evolution Methodologies (Chip Learning Strategies)

1) Outcome-Driven Loop
   - Learn only when outcomes validate.

2) Correction-First Learning
   - Corrections are primary signals.

3) Causal Hypothesis Tracking
   - Track "If X then Y" with evidence.

4) Evidence Strength Scoring
   - Grade evidence as low/medium/high.

5) Risk and Tradeoff Modeling
   - Always record cost/benefit and risks.

6) Preference Decay + Revalidation
   - Preferences decay unless reconfirmed.

7) Cross-Domain Transfer
   - Promote insights when they generalize across chips.

8) Counterfactual Replay
   - Evaluate "what if we did X instead?"

9) Human Value Alignment
   - Only promote if human-useful.

10) Adaptive Questioning
   - Ask the highest-leverage questions as context shifts.

---

## Benchmarking Plan (Real Data)

Metrics:
- % human-useful promotions
- Validation rate (validated vs contradicted)
- Outcome coverage (insights with outcomes)
- Insight quality score (evidence + validation)
- Time-to-useful-insight
- Noise ratio (telemetry vs cognitive)

Workflow:
1) Baseline: run Spark as-is on recent events.
2) Methodology A: enable chip variant and run for 1 day.
3) Compare: replay the same event log with other methods.
4) Choose: use highest signal-to-noise and best outcome impact.

---

## Next Build Targets

1) Chip YAML loader + validator (hybrid spec).
2) Vibecoding chip and Game Dev chip in YAML.
3) Replay + evaluation tooling for methodology benchmarking.

---

## Deeper Integration Analysis (Chips Always-On)

We want chips to operate continuously, not as a one-off upload. Below is a
comparison of integration methods and how they interact with Spark, Memory, and
Mind.

### Option 1: Chips as Core Runtime (inside Spark)

How it works:
- Chips are loaded by Spark runtime and invoked in the bridge worker cycle.
- Events flow: queue -> chip router -> observers -> chip insights.

Pros:
- Lowest latency, full access to Spark signals.
- Works offline, no external dependency.
- Best for always-on learning.

Cons:
- More core code changes.

Best use:
- Primary path for all core chips.

---

### Option 2: Chips as MCP Tools (external)

How it works:
- Chips run as a separate MCP server.
- Spark calls MCP to analyze events or generate insights.

Pros:
- Language-agnostic; easy to scale.
- External teams can ship chips without touching Spark core.

Cons:
- Network latency and dependency.
- Harder to keep always-on without costs.

Best use:
- Advanced or heavy chips that require external compute.
- Optional, not the default.

---

### Option 3: Chips as Hooks

How it works:
- Chips run at hook points (pre/post tool use, prompt submit).

Pros:
- Easy to install in agent workflows.
- Works in multiple environments (Claude/Cursor/etc).

Cons:
- Hook timing can be noisy or incomplete.
- Risk of over-triggering or missing outcomes.

Best use:
- Light, high-value captures (preference, corrections, outcomes).

---

### Option 4: Chips as Context Injectors

How it works:
- Chip produces summaries that get injected into project context.

Pros:
- Low overhead in runtime.
- High visibility of chip learnings.

Cons:
- If chip insights are noisy, context is polluted.
- Not a learning mechanism by itself.

Best use:
- Final output stage (post-validation).

---

## Recommended Chip Methodology (Best for Self-Evolving Agents)

Primary path (default):
1) Chips run inside Spark runtime (always-on).
2) Outcomes are logged and validated against chip insights.
3) Chip insights are injected into context only after validation gates.

Optional path (scale):
4) Heavy chips can be hosted via MCP for advanced analysis.
5) MCP results are treated as evidence, not truth.

Why this is best:
- Always-on by default (local, offline).
- No dependency on external services.
- Clear evidence/validation loop with outcomes.

---

## Chips + Memory + Mind (Best Practices)

Memory (local):
- Store per-chip insights in a namespaced store (chip_id).
- Keep operational telemetry out of cognitive stores.

Mind (semantic):
- Sync only validated chip insights.
- Store chip_id and domain metadata.
- Support cross-chip retrieval (shared patterns).

Outcome integration:
- Outcomes always link back to chip_id and insight_id.
- Outcomes can validate or contradict chip insights.

---

## Benchmarking System (How We Prove It Works)

Goal:
- Compare chip methodologies based on data, not belief.

Core metrics:
- Signal-to-noise ratio (human-useful vs telemetry)
- Validation rate (validated vs contradicted)
- Outcome coverage (insights with outcomes)
- Time-to-useful-insight

Benchmark modes:
1) Live mode: enable chip for 24 hours and measure metrics.
2) Replay mode: re-run the same event log against multiple chip variants.

Data storage:
- Per-chip metrics log (JSONL).
- Daily aggregate report.

---

## Skills Augmentation (H70-C+)

Note:
- H70-C+ skills are not available in this repo by default.
- When provided, they should be used for:
  - Chip methodology review
  - Evaluation criteria design
  - Benchmark interpretation

Next step:
- Provide a path or install method for H70-C+ skills.

---

## Socratic Question Bank (For Deepening the Chip System)

Core questions:
- What does "always-on" mean in practice for chips, and what should be the default runtime path?
- What evidence would prove chips improved outcomes instead of just producing more insights?
- Which insights are valuable enough to deserve persistent memory?
- How do we prevent chips from amplifying noise or bias?
- What is the minimum architecture needed to keep chips lightweight but effective?

Architecture questions:
- Should chips run inside Spark runtime, via MCP, or via hooks, and why?
- When should chips be allowed to inject context, and what gates should apply?
- How do chips interact with Memory vs Mind without duplicating or leaking data?
- How do we isolate chip failures so one bad chip doesn't degrade the core system?

Validation questions:
- How do we measure "signal-to-noise" for chip learnings?
- What qualifies as "validated" in each domain?
- How often should preferences decay or be reconfirmed?
- When does a chip insight graduate to a core Spark insight?

Governance questions:
- What permissions or scopes should a chip declare before it runs?
- Which changes require human approval (promotion, evolution, context injection)?
- How do we prevent chips from becoming overly autonomous or misaligned?

Benchmarks questions:
- What metrics matter most for our top 3 domains (marketing, product, ops)?
- How do we compare chip variants fairly on the same dataset?
- Which chips should be "default-on" vs "opt-in"?

Extended questions:
- What is the smallest chip that still produces measurable value?
- Which domains are most sensitive to noisy learnings, and why?
- What should Spark refuse to learn (anti-learning policies)?
- When should chips be stopped or paused automatically?
- How do we ensure chips don't overfit to one team's habits?
- What is the "unit of learning" for each domain (campaign, sprint, experiment)?
- How do we capture "taste" vs "truth" without conflating them?
- What is the best user experience for onboarding chip questions?
- How do we prevent chip prompts from distracting real work?
- When should we merge insights across chips, and when should we keep them separate?
- How do we resolve contradictions between chips?
- Can a chip propose new chips, and if so, who approves?
- What is the evolution budget per chip (how much change per week)?
- What should "chip maturity" mean, and how do we measure it?
- What are the earliest signals that a chip is harmful?
- How do we allow chips to learn privately without weakening global intelligence?
- What does "general intelligence" mean across chips?
- How should chips interact with external data sources safely?
- What is the rollback strategy for bad chip evolution?
- How do we trace an outcome back to a chip decision?

Ethics and guardrails questions:
- What are the explicit red lines for chip learning (harm, deception, abuse)?
- How do we prevent chips from optimizing for short-term gains that harm users?
- What consent or disclosure is required when chips learn from human data?
- How do we enforce privacy boundaries across chips and projects?
- What is the process for auditing chip behavior and outcomes?
- How do we detect emergent harmful behavior early?
- What is the human override model when chips conflict with values?
- Should chips have different safety tiers based on domain risk?
- How do we ensure chips stay aligned with “useful to humanity” goals?

Multi-agent orchestration questions:
- How can chips define team roles, handoffs, and ownership boundaries?
- What signals indicate a task should be delegated to a subagent?
- How do chips coordinate skills across agents without duplication?
- What is the protocol for multi-agent conflict resolution?
- How do we measure team-level outcomes vs individual agent success?
- How can chips learn optimal orchestration strategies over time?
- What does a "handoff contract" look like for agent teams?
- How do chips prevent runaway delegation or agent sprawl?
- How do chips encode “when to ask vs act” across agent roles?
- Can chips recommend agent team composition based on project goals?

---

## Guardrail Policies (Draft)

Purpose:
- Prevent chips from learning harmful, deceptive, or manipulative behaviors.
- Keep intelligence aligned with human benefit and safety.

Policy tiers:
1) Hard bans (never learn or promote)
   - Harm facilitation, deception, coercion, exploitation.
   - Privacy violations or sensitive data leakage.

2) Soft bans (learn locally but never promote)
   - Aggressive persuasion patterns.
   - Dark‑pattern growth tactics.

3) Conditional learnings (allowed with explicit consent)
   - Any learning from user-provided private data.

Implementation hooks:
- Policy filter before insight creation.
- Policy filter before promotion and context injection.
- Audit log for every blocked insight.

---

## Multi-Agent Handoff Contract (Template)

Goal:
- Make agent handoffs explicit, reliable, and measurable.

Contract fields:
- Task owner (agent id)
- Scope (what is included vs excluded)
- Inputs (context, files, constraints)
- Success criteria (what "done" means)
- Risks (known uncertainties)
- Handoff triggers (when to escalate or delegate)
- Output format (expected artifact)
- Verification plan (who checks the result)

Why this matters:
- Prevents drift and duplicated effort.
- Creates measurable outcomes for validation.

---

## Chip Governance Model (Lightweight)

Levels:
1) Local chips (personal)
   - No sharing by default.
2) Team chips (internal)
   - Review required before activation.
3) Community chips (SparkNet)
   - Mandatory scope declaration + safety review.

Governance primitives:
- Scope permissions (data types and tools allowed).
- Approval gates for evolution and promotion.
- Rollback mechanism for bad chips.
- Audit trails (who changed what and why).

---

## Expanded Guardrails (Deep Cuts)

Ethical alignment:
- Require explicit human benefit statement per chip.
- Require "negative outcomes to avoid" per chip.

Drift control:
- Periodic revalidation of chip assumptions.
- Automatic throttling if contradiction rate rises.

Transparency:
- Every promoted insight must include evidence and confidence.
- Provide a clear "why this was learned" trail.

---

## Expanded Orchestration (Deep Cuts)

Coordination model:
- Chips define team topology (lead, support, reviewer).
- Chips define delegation thresholds (risk, complexity, scope size).

Conflict resolution:
- Disputes resolved by priority rules or human arbitration.
- Log all conflicts and outcomes for learning.

Load balancing:
- Track agent workload and availability.
- Avoid overload or redundant agents.

---

## Additional Areas to Deepen

- Safety test harness for chips (red-team prompts).
- Privacy boundary enforcement per chip.
- Trust scoring for chips based on outcome history.
- Bias detection and mitigation for domain learnings.
- Cross-chip knowledge transfer rules.

---

## Humanity-First Evolution Guardrails (Non-Negotiable)

Purpose:
- Ensure chip evolution always advances human well-being and avoids harm.

Core commitments:
- Human benefit first: every chip must declare how it helps humans.
- Non-maleficence: no chip should optimize for harm, deception, or exploitation.
- Dignity and autonomy: chips must not coerce, manipulate, or override human intent.
- Transparency: all high-impact evolutions are explainable and auditable.

Required fields (chip spec additions):
- `human_benefit`: short statement of how this chip benefits humans.
- `harm_avoidance`: list of outcomes the chip must not produce.
- `risk_level`: low / medium / high.
- `safety_tests`: required test suite for this chip.

Mandatory safety gates (before evolution):
1) Evidence threshold: only evolve if outcomes show net benefit.
2) Risk review: high-risk chips require human approval.
3) Harm check: any signal of harm blocks evolution until resolved.

Operational enforcement:
- Safety filter at insight creation (block harmful patterns).
- Safety filter at promotion and context injection.
- Auto-throttle or disable chip if contradiction or harm rate spikes.
- Human override always available.

Governance protocol:
- All evolutions logged with who/why/when.
- Rollback required for any negative outcome spikes.
- Revalidation cadence (quarterly at minimum).

Ethical audit checklist:
- Does it improve human outcomes measurably?
- Are there unintended negative incentives?
- Can it be misused or weaponized?
- Is consent required for data used?
- Does it respect privacy boundaries?

Success criteria:
- No harmful evolutions reach production contexts.
- Positive impact outweighs risk across measurable outcomes.
