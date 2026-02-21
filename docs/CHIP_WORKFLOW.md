# Chip Workflow Guide
Navigation hub: `docs/GLOSSARY.md`

## The 5-Minute Chip Creation Flow

```
1. IDENTIFY     2. TRIGGER      3. CAPTURE      4. LEARN        5. VALIDATE
   What domain?    What signals?   What data?      What patterns?  How to measure?

   [Marketing]  -> [CTR, ROI]  -> [channel,     -> [channel     -> [conversion
                                  audience]        effectiveness]   > 2%]
```

## Step-by-Step Workflow

### Phase 1: Domain Discovery (2 min)

**Ask yourself:**
- What domain am I an expert in?
- What do I wish AI understood better about this field?
- What mistakes do beginners make?

**Example domains:**
- Marketing campaigns
- Sales outreach
- Product development
- Customer support
- DevOps/infrastructure
- Data analysis
- Content creation

### Phase 2: Signal Mapping (3 min)

**Identify trigger phrases people say when:**

| Situation | Example Phrases |
|-----------|-----------------|
| Something worked | "campaign performed well", "conversion was high" |
| Something failed | "bounce rate spiked", "audience didn't respond" |
| Making decisions | "we should target", "let's try" |
| Preferences | "always A/B test", "never launch Friday" |

**Write them down:**
```yaml
triggers:
  patterns:
    - "campaign performed"
    - "conversion rate"
    - "bounce rate"
    - "A/B test"
  events:
    - pre_tool
    - user_prompt
    - post_tool
    - post_tool_failure
```

### Phase 3: Data Capture Design (5 min)

**What information matters?**

For each trigger, what data should we capture?

| Trigger | Required Fields | Optional Fields |
|---------|-----------------|-----------------|
| "campaign performed" | metric, value | channel, audience, timing |
| "bounce rate" | rate | page, source |

**Write observers:**
```yaml
observers:
  - name: campaign_result
    triggers:
      - "campaign"
      - "performed"
    capture:
      required:
        metric: The metric measured
        value: The result
      optional:
        channel: Which channel
        audience: Target segment
```

### Phase 4: Learning Goals (3 min)

**What patterns should emerge?**

- "Which channels convert best?"
- "Which audiences engage most?"
- "What timing works?"

**Write learners:**
```yaml
learners:
  - name: channel_effectiveness
    type: correlation
    input:
      fields: [channel, audience]
    output:
      fields: [conversion_rate]
    learn:
      - "Best channels per audience"
      - "Optimal timing patterns"
```

### Phase 5: Success Metrics (2 min)

**How do we know learning is valid?**

| Outcome Type | Condition | What It Means |
|--------------|-----------|---------------|
| Positive | `conversion > 0.02` | Approach works |
| Negative | `bounce > 0.7` | Approach failed |
| Neutral | Everything else | More data needed |

**Write outcomes:**
```yaml
outcomes:
  positive:
    - condition: "conversion > 0.02"
      weight: 1.0
      insight: "High-converting approach"
  negative:
    - condition: "bounce > 0.7"
      weight: 0.8
      insight: "Messaging mismatch"
```

### Phase 6: Context Questions (2 min)

**What context helps learning?**

| Question | Category | Affects |
|----------|----------|---------|
| What is the primary KPI? | metric | All learners |
| Who is the audience? | goal | campaign_result |
| What's the budget range? | constraint | channel selection |

**Write questions:**
```yaml
questions:
  - id: mkt_kpi
    question: What is the primary KPI?
    category: metric
    affects_learning:
      - channel_effectiveness
```

## Complete Workflow Template

```yaml
# 1. IDENTITY
chip:
  id: your-domain
  name: Your Domain Intelligence
  version: 1.0.0
  description: |
    Brief description of what this chip learns.
  domains:
    - primary-domain
    - secondary-domain

# 2. TRIGGERS
triggers:
  patterns:
    - "success phrase 1"
    - "failure phrase 1"
    - "decision phrase 1"
  events:
    - pre_tool
    - user_prompt
    - post_tool
    - post_tool_failure

# 3. OBSERVERS
observers:
  - name: main_observation
    triggers:
      - "key phrase"
    capture:
      required:
        key_field: What this captures
      optional:
        context_field: Additional context

# 4. LEARNERS
learners:
  - name: main_learner
    type: correlation
    input:
      fields: [input1, input2]
    output:
      fields: [outcome1]
    learn:
      - "What patterns to detect"

# 5. OUTCOMES
outcomes:
  positive:
    - condition: "success_metric > threshold"
      insight: "What this validates"
  negative:
    - condition: "failure_metric > threshold"
      insight: "What this invalidates"

# 6. QUESTIONS
questions:
  - id: domain_context
    question: What context helps learning?
    category: goal
    affects_learning:
      - main_learner
```

## Testing Your Chip

Format tip:
- Start with a single-file chip for quick iteration.
- Move to `multifile` (`chip.yaml` + `triggers.yaml` + `observers.yaml`) once the chip grows.
- Use `hybrid` when you want one distributable file with `includes:` for modular authoring.

### 1. Install and Activate

```bash
# Install
spark chips install chips/my-chip.chip.yaml

# Activate
spark chips activate my-chip

# Verify
spark chips status my-chip
```

### 2. Test with Sample Input

```bash
# Test trigger matching
spark chips test my-chip --test-text "The campaign performed well with 3% CTR"
```

### 3. Check Questions

```bash
# See what questions it asks
spark chips questions my-chip
```

### 4. Monitor Insights

```bash
# After some usage
spark chips insights my-chip
```

## Real-World Examples

### Marketing Chip

```yaml
chip:
  id: marketing-growth
  name: Marketing Growth Intelligence
  domains: [marketing, growth]

triggers:
  patterns:
    - "CTR was"
    - "conversion rate"
    - "CAC is"
    - "ROAS"

observers:
  - name: metric_report
    triggers: ["CTR", "conversion", "CAC", "ROAS"]
    capture:
      required:
        metric: The metric name
        value: The value
      optional:
        channel: Marketing channel
        period: Time period

learners:
  - name: channel_roi
    type: correlation
    learn:
      - "Which channels have best ROI"
      - "Optimal spend allocation"

outcomes:
  positive:
    - condition: "ROAS > 3"
      insight: "Channel is profitable"
  negative:
    - condition: "CAC > LTV"
      insight: "Unsustainable acquisition"

questions:
  - id: growth_goal
    question: What is the primary growth metric?
    category: metric
```

### Sales Chip

```yaml
chip:
  id: sales-intelligence
  name: Sales Intelligence
  domains: [sales, deals]

triggers:
  patterns:
    - "deal closed"
    - "lost because"
    - "objection was"
    - "prospect said"

observers:
  - name: deal_outcome
    triggers: ["closed", "lost", "won"]
    capture:
      required:
        result: Won or lost
        size: Deal size
      optional:
        reason: Why
        cycle: Sales cycle length

learners:
  - name: win_patterns
    type: pattern
    learn:
      - "Common objection handlers"
      - "Optimal deal size"

questions:
  - id: sales_target
    question: What is the target deal size?
    category: goal
```

### DevOps Chip

```yaml
chip:
  id: devops-reliability
  name: DevOps Reliability
  domains: [devops, infrastructure]

triggers:
  patterns:
    - "incident"
    - "outage"
    - "latency"
    - "deployment"

observers:
  - name: incident_report
    triggers: ["incident", "outage"]
    capture:
      required:
        severity: P1/P2/P3
        service: Affected service
      optional:
        root_cause: What caused it
        resolution: How fixed

learners:
  - name: reliability_patterns
    type: pattern
    learn:
      - "Common failure modes"
      - "Effective incident response"

questions:
  - id: sla_target
    question: What is the SLA target?
    category: metric
```

## Chip Evolution (Premium feature)

The chip evolution workflow is a premium capability and is not enabled in the OSS package.

## Best Practices

### DO:
- Start with 3-5 specific triggers
- Capture only essential required fields
- Define measurable outcomes
- Ask questions that affect learning

### DON'T:
- Over-engineer with too many observers
- Capture data you won't use
- Make outcomes too strict initially
- Forget to activate the chip

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Chip not triggering | Check trigger patterns match user language |
| No insights generated | Verify chip is activated |
| Wrong data captured | Review observer trigger specificity |
| Low confidence insights | Add more outcome definitions |

---

*Create your first chip in 15 minutes. Iterate based on what you learn.*
