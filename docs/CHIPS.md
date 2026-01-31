# Spark Chips - Domain-Specific Intelligence

**Chips teach Spark *what* to learn, not just *how* to learn.**

```
+------------------+     +------------------+     +------------------+
|   spark-core     |     |   marketing      |     |   your-domain    |
|   (coding)       |     |   (campaigns)    |     |   (custom)       |
+------------------+     +------------------+     +------------------+
         |                        |                        |
         v                        v                        v
+------------------------------------------------------------------+
|                        SPARK RUNTIME                              |
|  Triggers -> Observers -> Learners -> Outcomes -> Insights        |
+------------------------------------------------------------------+
         |
         v
+------------------+
|  COGNITIVE       |
|  INSIGHTS        |
|  (validated)     |
+------------------+
```

## What Are Chips?

Chips are **YAML specifications** that tell Spark:
- What patterns to watch for (triggers)
- What data to capture (observers)
- What to learn from it (learners)
- How to measure success (outcomes)
- What questions to ask (questions)

Think of chips as **domain experts in a box** - each one knows what matters in its field.

## Quick Start

```bash
# List installed chips
spark chips list

# Install a chip
spark chips install chips/spark-core.chip.yaml

# Activate it
spark chips activate spark-core

# See what questions it asks
spark chips questions spark-core

# Check its insights
spark chips insights spark-core
```

## Anatomy of a Chip

```yaml
# Identity - Who is this chip?
chip:
  id: marketing-campaigns
  name: Marketing Campaign Intelligence
  version: 1.0.0
  description: |
    Learns what makes marketing campaigns succeed.
    Tracks metrics, messaging, and audience signals.
  author: Vibeship
  license: MIT
  human_benefit: "Improve marketing outcomes without manipulation."
  harm_avoidance:
    - "No deceptive or coercive messaging"
    - "No exploitation of vulnerable audiences"
  risk_level: medium
  safety_tests:
    - "no_deceptive_growth"
    - "no_harmful_targeting"
  domains:
    - marketing
    - growth
    - campaigns

# Triggers - When does this chip activate?
triggers:
  patterns:
    - "campaign performed"
    - "CTR was"
    - "conversion rate"
    - "audience responded"
  events:
    - UserPromptSubmit
    - PostToolUse

# Observers - What data to capture?
observers:
  - name: campaign_result
    description: Captures campaign performance
    triggers:
      - "campaign"
      - "performed"
      - "results"
    capture:
      required:
        metric: The key metric
        value: The result
      optional:
        channel: Marketing channel
        audience: Target audience

# Learners - What patterns to detect?
learners:
  - name: channel_effectiveness
    description: Learns which channels work best
    type: correlation
    input:
      fields:
        - channel
        - audience
    output:
      fields:
        - conversion_rate
        - engagement
    learn:
      - "Which channels convert best"
      - "Which audiences engage most"

# Outcomes - How to measure success?
outcomes:
  positive:
    - condition: "conversion_rate > 0.02"
      weight: 1.0
      insight: "High-converting campaign"
  negative:
    - condition: "bounce_rate > 0.7"
      weight: 0.8
      insight: "High bounce - messaging mismatch"

# Questions - What to ask the user?
questions:
  - id: mkt_kpi
    question: What is the primary KPI for this campaign?
    category: metric
    affects_learning:
      - channel_effectiveness

  - id: mkt_audience
    question: Who is the target audience?
    category: goal
    affects_learning:
      - campaign_result
```

## Core Concepts

### 1. Triggers

Triggers determine when a chip activates:

| Type | Example | Use Case |
|------|---------|----------|
| `patterns` | `"worked because"` | Natural language signals |
| `events` | `PostToolUse` | Hook events from Claude Code |
| `tools` | `{name: "Bash"}` | Specific tool usage |

### 2. Observers

Observers capture structured data when triggered:

```yaml
observers:
  - name: success_pattern
    triggers:
      - "worked because"
      - "fixed by"
    capture:
      required:
        pattern: What worked
      optional:
        reason: Why it worked
```

### 3. Learners

Learners detect patterns across observations:

| Type | Purpose |
|------|---------|
| `correlation` | Find relationships between inputs and outputs |
| `pattern` | Detect recurring patterns |
| `optimization` | Learn optimal approaches |

### 4. Outcomes

Outcomes validate insights with real results:

```yaml
outcomes:
  positive:
    - condition: "success == true"
      insight: "Approach validated"
  negative:
    - condition: "error_count > 3"
      insight: "Approach needs revision"
```

### 5. Questions

Questions scope what gets learned:

```yaml
questions:
  - id: core_stack
    question: What is the primary tech stack?
    category: goal
    phase: discovery
    affects_learning:
      - tool_effectiveness
```

## Built-in Chips

### spark-core (Coding Intelligence)

**Domains:** coding, development, debugging, tools

**Triggers:**
- "worked because", "failed because"
- "fixed by", "the issue was"
- "prefer", "always", "never"

**Questions:**
- What is the primary tech stack?
- What quality signals matter most?
- What should we avoid?

**Learns:**
- Which tools work best
- Common error patterns and fixes
- User coding preferences

## Creating Your Own Chip

### Step 1: Define Identity

```yaml
chip:
  id: my-domain
  name: My Domain Intelligence
  version: 1.0.0
  domains:
    - my-area
```

### Step 2: Set Triggers

What signals indicate this domain?

```yaml
triggers:
  patterns:
    - "domain-specific phrase"
    - "another signal"
```

### Step 3: Define Observers

What data to capture?

```yaml
observers:
  - name: my_observation
    triggers:
      - "capture this"
    capture:
      required:
        key_field: Description
```

### Step 4: Add Learners

What patterns to detect?

```yaml
learners:
  - name: my_learner
    type: correlation
    learn:
      - "What correlates with success"
```

### Step 5: Define Outcomes

How to measure success?

```yaml
outcomes:
  positive:
    - condition: "metric > threshold"
      insight: "This approach works"
```

### Step 6: Add Questions

What context helps learning?

```yaml
questions:
  - id: domain_goal
    question: What is the goal?
    category: goal
    affects_learning:
      - my_learner
```

## CLI Reference

| Command | Description |
|---------|-------------|
| `spark chips list` | List all installed chips |
| `spark chips install <path>` | Install a chip |
| `spark chips uninstall <id>` | Remove a chip |
| `spark chips activate <id>` | Enable chip processing |
| `spark chips deactivate <id>` | Disable chip |
| `spark chips status <id>` | Show chip details |
| `spark chips insights <id>` | Show chip insights |
| `spark chips questions <id>` | Show chip questions |
| `spark chips test <id>` | Test chip with sample |

## How Chips Learn

```
User Action
    |
    v
+-------------------+
| Event Queue       |  <- Hook captures event
+-------------------+
    |
    v
+-------------------+
| Chip Router       |  <- Matches event to chips
+-------------------+
    |
    v
+-------------------+
| Chip Runner       |  <- Runs observers, captures data
+-------------------+
    |
    v
+-------------------+
| Pattern Detection |  <- Detects patterns in data
+-------------------+
    |
    v
+-------------------+
| Outcome Validation|  <- Links outcomes to insights
+-------------------+
    |
    v
+-------------------+
| Cognitive Store   |  <- Stores validated insights
+-------------------+
```

## Best Practices

1. **Start Specific** - Focus on one domain well before expanding
2. **Use Real Signals** - Triggers should match actual user language
3. **Capture What Matters** - Only required fields that affect learning
4. **Define Clear Outcomes** - Measurable success/failure conditions
5. **Ask Scoped Questions** - Questions that directly affect learners

## Example Chips

See the `chips/` directory for examples:
- `spark-core.chip.yaml` - Coding and development
- More coming soon...

## Architecture

```
chips/
  spark-core.chip.yaml     # Built-in coding chip
  my-custom.chip.yaml      # Your custom chips

lib/chips/
  loader.py                # YAML parsing, ChipSpec
  registry.py              # Install/activate tracking
  router.py                # Event-to-chip matching
  runner.py                # Observer execution
  store.py                 # Per-chip insight storage

~/.spark/chips/
  registry.json            # Installed chips registry
  chip_insights/           # Per-chip data storage
    spark-core/
      observations.jsonl
      insights.json
      outcomes.jsonl
```

---

*Chips are the foundation of domain-specific intelligence in Spark. They teach the system what matters in your field, making every interaction smarter.*
