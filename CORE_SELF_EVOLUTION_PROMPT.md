# Spark Intelligence — Core Self-Evolution Implementation Prompt

> **Give this to a separate Claude Code terminal working on the same codebase.**
> While this terminal builds core auto-tuning, the other terminal is building X/social evolution.

---

## Context

Spark Intelligence is a self-evolving AI learning system at `C:\Users\USER\Desktop\vibeship-spark-intelligence`. It has 100+ Python modules that observe, process, store, and surface learnings. The system is architecturally sound but **does not actually self-evolve yet** — it collects data beautifully but never closes the feedback loop.

### The Three Gaps

1. **Auto-Tuning Gap**: `~/.spark/tuneables.json` has configurable thresholds (advisor weights, promotion thresholds, quality gates) but nothing auto-adjusts them. A human manually edits them.

2. **Behavioral Re-injection Gap**: EIDOS distillations (extracted rules from experience) are stored in SQLite (`~/.spark/eidos.db`) but never fed back into advisor ranking or decision-making. Only 7 distillations from 1,564 insights (0.4% success rate).

3. **Feedback Loop Gap**: The advisor surfaces advice pre-action, but only 1.4% of outcomes are tracked as "advice was followed and helped." The system can't learn which advice works.

### What Already Works
- Event capture via `hooks/observe.py` — captures everything
- Quality gating via `lib/meta_ralph.py` — scores insights 0-10
- Cognitive learning via `lib/cognitive_learner.py` — 700+ insights, 41 noise filters
- Advisory retrieval via `lib/advisor.py` — 10 advice sources, ranked by fusion score
- Promotion via `lib/promoter.py` — writes high-value insights to CLAUDE.md
- EIDOS episodes via `lib/eidos/` — prediction→outcome→evaluation (architecture works)
- Tuneables system via `~/.spark/tuneables.json` — all thresholds configurable
- Effectiveness tracking via `~/.spark/advisor/effectiveness.json` — metrics exist

---

## Task: Build the Auto-Tuner

Create `lib/auto_tuner.py` — a module that closes the self-evolution loop by:

### 1. Measuring What Works

Read existing effectiveness data:
- `~/.spark/advisor/effectiveness.json` — has `total_advice_given`, `total_followed`, `total_helpful`, `by_source` breakdown
- `~/.spark/cognitive_insights.json` — has per-insight `times_validated`, `times_contradicted`, `reliability`
- `~/.spark/eidos.db` — has episodes with outcomes, distillations with validation counts
- `~/.spark/meta_ralph.json` — has quality scores and outcome linkage

Key function: `measure_system_health() -> SystemHealth`
```python
@dataclass
class SystemHealth:
    advice_action_rate: float      # Currently 1.4%, target 14%+
    distillation_rate: float       # Currently 0.4%, target 6%+
    promotion_throughput: int      # Insights promoted per day
    top_sources: List[str]         # Best-performing advice sources
    weak_sources: List[str]        # Underperforming sources
    cognitive_growth: float        # New insights per hour
    feedback_loop_closure: float   # % of predictions with matched outcomes
```

### 2. Computing Tune Recommendations

Based on measurements, compute adjustments:

**Advisor tuning** (`lib/advisor.py` loads from tuneables at lines 68-102):
- Source boost weights (currently hardcoded: EIDOS 1.4x, self-awareness 1.3x, etc.)
  - Boost sources with high helpful rate, demote low performers
  - Formula: `new_boost = base_boost × (helpful_rate / avg_helpful_rate)`
- `MIN_RANK_SCORE` (currently 0.35)
  - If action rate < 5%: lower to 0.25 (more advice surfaces)
  - If action rate > 20%: raise to 0.45 (tighter filtering)
- `MAX_ADVICE_ITEMS` (currently 8)
  - If most advice ignored: reduce to 5
  - If user follows most: allow 10

**Promotion tuning** (`lib/promoter.py` reads from tuneables):
- `DEFAULT_PROMOTION_THRESHOLD` (currently 0.7)
  - If throughput < 2/day: lower to 0.6
  - If too noisy: raise to 0.8
- `DEFAULT_MIN_VALIDATIONS` (currently 3)
  - If queue is backing up: lower to 2
  - If promotions are flaky: raise to 5
- `confidence_floor` for fast-track (currently 0.9)
  - If no fast-tracks happening: lower to 0.85

**EIDOS tuning** (`lib/eidos/distillation_engine.py`):
- Anti-pattern penalty (currently ×0.8 at line 238)
  - If anti-patterns prove useful: raise to ×0.9
- Sharp-edge penalty (currently ×0.7 at line 250)
  - If sharp-edges prevent errors: raise to ×0.85
- Playbook confidence (currently 0.6 hardcoded at line 287)
  - Replace with: `min(0.9, 0.5 + (success_steps / total_steps) × 0.4)`

**Meta-Ralph tuning**:
- `quality_threshold` (currently 4)
  - If too many insights pass but are useless: raise to 5
  - If pipeline is starving: lower to 3

Key function: `compute_recommendations(health: SystemHealth) -> List[TuneRecommendation]`
```python
@dataclass
class TuneRecommendation:
    section: str          # "advisor", "promotion", "eidos", "meta_ralph"
    key: str              # "min_rank_score", "quality_threshold", etc.
    current_value: Any
    recommended_value: Any
    reason: str           # Human-readable justification
    confidence: float     # 0-1, how sure we are
    impact: str           # "high", "medium", "low"
```

### 3. Applying Tunings (with safety)

**Never auto-apply blindly.** Use graduated approach:

```python
def apply_recommendations(recs: List[TuneRecommendation], mode: str = "suggest"):
    """
    Modes:
    - "suggest": Log recommendations, don't apply (default)
    - "conservative": Apply only high-confidence (>0.8), low-impact changes
    - "moderate": Apply medium+ confidence changes
    - "aggressive": Apply all recommendations
    """
```

Safety constraints:
- Never change more than 3 tuneables per cycle
- Never change a value by more than 30% in one step
- Log every change with before/after + reasoning to `~/.spark/auto_tune_log.jsonl`
- Keep last 5 tuneable snapshots for rollback in `~/.spark/tuneable_history/`
- If any metric degrades >10% after a change, auto-revert

### 4. Wiring Into Bridge Cycle

Add auto-tuning as an optional step in `lib/bridge_cycle.py` (after line 320, before flush):

```python
# Step 17: Auto-tune (every N cycles)
if cycle_count % auto_tune_interval == 0:
    health = auto_tuner.measure_system_health()
    recs = auto_tuner.compute_recommendations(health)
    auto_tuner.apply_recommendations(recs, mode=tune_mode)
```

Add to `~/.spark/tuneables.json`:
```json
"auto_tuner": {
    "enabled": true,
    "mode": "conservative",
    "interval_cycles": 50,
    "max_changes_per_cycle": 3,
    "max_change_percent": 30,
    "revert_on_degradation_percent": 10
}
```

### 5. Closing the EIDOS Loop

The distillation engine creates rules but they're never re-injected. Fix this:

In `lib/advisor.py`, the EIDOS source (line 586) already retrieves distillations. But they need better ranking:

- Add to `report_action_outcome()` (line 1534): when a distillation-based advice leads to success, call `distillation_engine.validate_distillation(distillation_id, helped=True)`
- This bumps confidence by +0.05 per validation (line 369 in distillation_engine.py)
- After 3 validations, reliability crosses 0.7 threshold → promoter picks it up

Also lower the initial confidence penalties:
- Anti-pattern: ×0.8 → ×0.9 (they're valuable if they prevent errors)
- Sharp-edge: ×0.7 → ×0.85
- Playbook: 0.6 → dynamic based on step quality

### 6. Making Promotions Runtime-Active

Currently CLAUDE.md promotions are read by Claude Code at session start (this IS a form of self-modification — Claude reads CLAUDE.md and follows those instructions). But the connection should be explicit:

In `lib/advisor.py`, add a source that reads promoted insights from CLAUDE.md sections:
```python
def _get_promoted_advice(self, tool_name, tool_input):
    """Read insights Spark previously promoted to CLAUDE.md."""
    # Parse SPARK_LEARNINGS section
    # Return as Advice objects with source="promoted"
    # These represent Spark's own accumulated wisdom
```

This closes the circle: observe → learn → promote → advise from promotions.

---

## Architecture Diagram

```
                    ┌──────────────────────┐
                    │   AUTO-TUNER (NEW)   │
                    │                      │
    ┌──────────┐    │  measure_health()    │    ┌──────────────┐
    │ Advisor   │◄──┤  compute_recs()      ├──►│ tuneables.json│
    │ effective-│    │  apply_recs()        │    │  (read+write)│
    │ ness.json │    │  rollback()          │    └──────────────┘
    └──────────┘    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │    BRIDGE CYCLE       │
                    │  (Step 17: auto-tune) │
                    └──────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                 ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │   Advisor    │  │   EIDOS      │  │  Promoter    │
    │ (source      │  │ (distill     │  │ (threshold   │
    │  boosts)     │  │  thresholds) │  │  adjusts)    │
    └──────────────┘  └──────────────┘  └──────────────┘
```

---

## Files to Create/Modify

### Create
- `lib/auto_tuner.py` — The auto-tuner module (main deliverable)
- `tests/test_auto_tuner.py` — Unit tests

### Modify
- `lib/bridge_cycle.py` — Add auto-tune step (~10 lines)
- `lib/advisor.py` — Add promoted-advice source, wire distillation validation
- `lib/eidos/distillation_engine.py` — Lower confidence penalties, add dynamic playbook scoring
- `~/.spark/tuneables.json` — Add `auto_tuner` section

### Do NOT Modify
- `hooks/observe.py` — The other terminal is handling X-related observe changes
- `lib/x_research.py`, `lib/x_voice.py` — X modules handled by other terminal
- `dashboard/` — Dashboard changes handled by other terminal

---

## Success Metrics

After implementation, running the system for a session should show:
1. `auto_tune_log.jsonl` has entries with reasoning
2. `tuneables.json` shows at least 1 auto-adjusted value
3. Distillation rate trends upward from 0.4%
4. Advice action rate trends upward from 1.4%
5. `tuneable_history/` has snapshots for rollback

---

## Key Principles

1. **Measure before tuning** — never guess, always compute from real data
2. **Small steps** — max 30% change per cycle, max 3 tuneables per cycle
3. **Reversible** — every change logged and rollbackable
4. **Observable** — every decision has a human-readable `reason` field
5. **Conservative default** — start in "suggest" mode, graduate to "conservative"
6. **No hallucinated improvements** — only claim improvement with before/after metrics

---

## Getting Started

```bash
cd C:\Users\USER\Desktop\vibeship-spark-intelligence

# 1. Read current tuneables
cat ~/.spark/tuneables.json

# 2. Read effectiveness data
cat ~/.spark/advisor/effectiveness.json

# 3. Check EIDOS state
python -c "import sqlite3; c=sqlite3.connect('C:/Users/USER/.spark/eidos.db'); print(c.execute('SELECT COUNT(*) FROM distillations').fetchone())"

# 4. Read the core architecture docs
# - Intelligence_Flow.md
# - Intelligence_Flow_Map.md
# - COMPREHENSIVE_ANALYSIS.md

# 5. Start building lib/auto_tuner.py
```
