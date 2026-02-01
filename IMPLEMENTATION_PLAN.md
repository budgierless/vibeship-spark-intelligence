# Implementation Plan: Self-Improving Learning System

## Goal

Build a system where Spark and Chips **continuously get better at understanding what to learn**. This is meta-learning: learning how to learn.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         SESSION                                  │
├─────────────────────────────────────────────────────────────────┤
│  1. ONBOARDING          2. CAPTURE           3. SYNTHESIS       │
│  ┌─────────────┐        ┌─────────────┐      ┌─────────────┐   │
│  │ Quick Qs    │───────▶│ Event       │─────▶│ Score       │   │
│  │ Domain hint │        │ Processing  │      │ Insights    │   │
│  │ Success def │        │ Chip routing│      │ Link outcomes│   │
│  └─────────────┘        └─────────────┘      └─────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      META-LEARNING LOOP                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐        ┌─────────────┐      ┌─────────────┐   │
│  │ Evaluate    │───────▶│ Evolve      │─────▶│ Update      │   │
│  │ What worked │        │ Chips       │      │ Strategies  │   │
│  └─────────────┘        └─────────────┘      └─────────────┘   │
│         ▲                                           │           │
│         └───────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Project Onboarding (Day 1)

### Files to Create/Modify

```
lib/onboarding/
├── __init__.py
├── detector.py      # Detect new project vs existing
├── questions.py     # Question templates and logic
├── context.py       # Store and retrieve project context
└── integration.py   # Hook into bridge_cycle
```

### Core Logic

```python
# detector.py - Detect if this is a new project
class ProjectDetector:
    def is_new_project(self, cwd: str) -> bool:
        """Check if we've seen this project before."""

    def get_project_context(self, cwd: str) -> Optional[ProjectContext]:
        """Get stored context for known project."""

# questions.py - Generate onboarding questions
class OnboardingQuestions:
    CORE_QUESTIONS = [
        {
            "id": "domain",
            "question": "What are we building? (1-2 words)",
            "type": "text",
            "required": True,
        },
        {
            "id": "success",
            "question": "What does done look like?",
            "type": "text",
            "required": True,
        },
        {
            "id": "focus",
            "question": "What should I pay attention to?",
            "type": "multi_choice",
            "options": ["performance", "security", "UX", "maintainability"],
            "required": False,
        },
        {
            "id": "avoid",
            "question": "What mistakes should I avoid?",
            "type": "text",
            "required": False,
        },
    ]

    def get_questions_for_context(self, context: Dict) -> List[Question]:
        """Get relevant questions based on detected context."""

# context.py - Store project context
@dataclass
class ProjectContext:
    project_path: str
    domain: str
    success_criteria: str
    focus_areas: List[str]
    avoid_patterns: List[str]
    active_chips: List[str]
    created_at: str
    updated_at: str
```

### Integration Point

In `bridge_cycle.py`, before processing events:

```python
def run_bridge_cycle(...):
    # NEW: Check for project context
    from lib.onboarding import get_or_create_context

    project_path = extract_project_path(events)
    context = get_or_create_context(project_path)

    if context.needs_onboarding:
        # Signal to frontend to ask questions
        stats["onboarding_needed"] = context.pending_questions

    # Pass context to chip processing
    stats["chips"] = process_chip_events(events, project_path, context)
```

---

## Phase 2: Insight Value Scoring (Day 1-2)

### Files to Create/Modify

```
lib/chips/
├── scoring.py       # Score insight value
└── runtime.py       # Modify to use scoring
```

### Scoring Dimensions

```python
# scoring.py
@dataclass
class InsightScore:
    cognitive_value: float    # 0-1: Is this human-useful?
    outcome_linkage: float    # 0-1: Can we link to success/failure?
    uniqueness: float         # 0-1: Is this new information?
    actionability: float      # 0-1: Can this guide future actions?
    transferability: float    # 0-1: Applies beyond this project?

    @property
    def total(self) -> float:
        weights = {
            "cognitive_value": 0.3,
            "outcome_linkage": 0.25,
            "uniqueness": 0.2,
            "actionability": 0.15,
            "transferability": 0.1,
        }
        return sum(getattr(self, k) * v for k, v in weights.items())

class InsightScorer:
    def score(self, insight: ChipInsight, context: ProjectContext) -> InsightScore:
        """Score an insight for promotion."""

    def _score_cognitive_value(self, insight: ChipInsight) -> float:
        """Is this human-useful vs operational noise?"""
        # Low: tool sequences, timing, file counts
        # High: decisions, rationale, domain knowledge

    def _score_outcome_linkage(self, insight: ChipInsight) -> float:
        """Can we link this to success/failure?"""
        # Check if insight relates to known outcomes

    def _score_uniqueness(self, insight: ChipInsight) -> float:
        """Is this new vs duplicate?"""
        # Compare to existing insights
```

### Promotion Thresholds

```python
PROMOTION_THRESHOLDS = {
    "immediate_to_working": 0.5,   # Session → Project memory
    "working_to_longterm": 0.75,   # Project → Permanent memory
}
```

---

## Phase 3: Outcome Linking (Day 2)

### Files to Create/Modify

```
lib/outcomes/
├── __init__.py
├── tracker.py       # Track success/failure signals
├── linker.py        # Link insights to outcomes
└── signals.py       # Detect outcome signals
```

### Outcome Detection

```python
# signals.py
class OutcomeSignals:
    """Detect success/failure from events."""

    SUCCESS_PATTERNS = [
        r"(?i)\b(perfect|great|exactly|works|done|shipped)\b",
        r"(?i)thank",
        r"tests? pass",
        r"build succeed",
    ]

    FAILURE_PATTERNS = [
        r"(?i)\b(wrong|broken|failed|error|bug|ugh|damn)\b",
        r"(?i)doesn't work",
        r"(?i)try again",
        r"tests? fail",
    ]

    def detect_outcome(self, event: Dict) -> Optional[Outcome]:
        """Detect if event signals success or failure."""

# linker.py
class OutcomeLinker:
    """Link insights to outcomes for validation."""

    def link_outcome(self, outcome: Outcome, recent_insights: List[ChipInsight]):
        """Link an outcome to insights that preceded it."""

    def update_insight_scores(self, insight_id: str, outcome: Outcome):
        """Update insight reliability based on outcome."""
```

### Outcome Storage

```python
@dataclass
class LinkedOutcome:
    insight_id: str
    outcome_type: str  # "success" | "failure"
    confidence: float
    context: str
    timestamp: str
```

---

## Phase 4: Chip Self-Evolution (Day 2-3)

### Files to Create/Modify

```
lib/chips/
├── evolution.py     # Chip self-improvement logic
└── registry.py      # Modify to support dynamic updates
```

### Evolution Strategies

```python
# evolution.py
class ChipEvolution:
    """Enable chips to improve themselves."""

    def evolve_triggers(self, chip: Chip, insights: List[ChipInsight]):
        """Add/remove triggers based on insight performance."""

        # Find high-value insights not matched by existing triggers
        missed_valuable = self._find_missed_valuable(chip, insights)
        for pattern in missed_valuable:
            self._add_provisional_trigger(chip, pattern)

        # Find triggers that never produce value
        unproductive = self._find_unproductive_triggers(chip)
        for trigger in unproductive:
            self._deprecate_trigger(chip, trigger)

    def suggest_new_chip(self, unmatched_insights: List[ChipInsight]) -> Optional[ChipSpec]:
        """Suggest a new chip if we see patterns outside existing chips."""

        # Cluster unmatched insights by domain
        clusters = self._cluster_by_domain(unmatched_insights)

        for cluster in clusters:
            if len(cluster) >= 3 and self._coherence(cluster) > 0.7:
                return self._generate_chip_spec(cluster)

        return None

    def merge_chips(self, chip_a: Chip, chip_b: Chip) -> Optional[Chip]:
        """Merge two chips that co-activate frequently."""

    def split_chip(self, chip: Chip) -> Optional[Tuple[Chip, Chip]]:
        """Split a chip with too-broad triggers."""
```

### Evolution Storage

```yaml
# ~/.spark/chip_evolution.yaml
evolutions:
  game_dev:
    added_triggers:
      - pattern: "baseY"
        added_at: "2025-02-01"
        source_insight: "insight_123"
        validated: true
    deprecated_triggers:
      - pattern: "old_pattern"
        deprecated_at: "2025-01-15"
        reason: "10+ false positives"

  provisional_chips:
    - id: "aerospace"
      triggers: ["orbit", "delta-v", "trajectory"]
      confidence: 0.4
      created_at: "2025-02-01"
```

---

## Phase 5: Meta-Learning Loop (Day 3)

### Files to Create/Modify

```
lib/metalearning/
├── __init__.py
├── evaluator.py     # Evaluate learning effectiveness
├── strategist.py    # Adjust learning strategies
└── reporter.py      # Report on learning progress
```

### Meta-Learning Cycle

```python
# evaluator.py
class LearningEvaluator:
    """Evaluate how well we're learning."""

    def evaluate_session(self, session_insights: List[ChipInsight]) -> LearningReport:
        """Evaluate learning effectiveness for a session."""
        return LearningReport(
            total_insights=len(session_insights),
            high_value_ratio=self._high_value_ratio(session_insights),
            outcome_linked_ratio=self._outcome_linked_ratio(session_insights),
            promoted_ratio=self._promoted_ratio(session_insights),
            chip_coverage=self._chip_coverage(session_insights),
            new_domains_detected=self._new_domains(session_insights),
        )

    def evaluate_trends(self, reports: List[LearningReport]) -> TrendAnalysis:
        """Analyze trends across sessions."""
        return TrendAnalysis(
            value_trend=self._calculate_trend([r.high_value_ratio for r in reports]),
            coverage_trend=self._calculate_trend([r.chip_coverage for r in reports]),
            recommendations=self._generate_recommendations(reports),
        )

# strategist.py
class LearningStrategist:
    """Adjust learning strategies based on evaluation."""

    def adjust_strategies(self, evaluation: TrendAnalysis):
        """Adjust learning parameters based on performance."""

        if evaluation.value_trend < 0:
            # Getting worse at finding valuable insights
            self._tighten_promotion_threshold()
            self._expand_chip_triggers()

        if evaluation.coverage_trend < 0:
            # Missing more relevant events
            self._suggest_new_chips(evaluation)

        # Adjust question strategies
        if evaluation.onboarding_effectiveness < 0.5:
            self._improve_questions()
```

### Learning Metrics Storage

```yaml
# ~/.spark/metalearning/metrics.yaml
sessions:
  - id: "session_123"
    timestamp: "2025-02-01T10:00:00"
    project: "/path/to/project"
    metrics:
      total_insights: 15
      high_value_ratio: 0.6
      promoted_ratio: 0.4
      outcome_linked: 0.3

trends:
  weekly:
    value_ratio: [0.4, 0.5, 0.55, 0.6]
    trend: "improving"

adjustments:
  - timestamp: "2025-02-01"
    type: "promotion_threshold"
    old_value: 0.5
    new_value: 0.55
    reason: "Too much noise being promoted"
```

---

## File Structure Summary

```
lib/
├── onboarding/
│   ├── __init__.py
│   ├── detector.py
│   ├── questions.py
│   ├── context.py
│   └── integration.py
├── chips/
│   ├── __init__.py
│   ├── loader.py
│   ├── registry.py
│   ├── router.py
│   ├── runtime.py
│   ├── scoring.py      # NEW
│   └── evolution.py    # NEW
├── outcomes/
│   ├── __init__.py
│   ├── tracker.py
│   ├── linker.py
│   └── signals.py
├── metalearning/
│   ├── __init__.py
│   ├── evaluator.py
│   ├── strategist.py
│   └── reporter.py
└── bridge_cycle.py     # Modified to integrate all
```

---

## Integration Flow

```python
# bridge_cycle.py - Full integration
def run_bridge_cycle(...):
    # 1. Project context
    context = onboarding.get_or_create_context(project_path)

    # 2. Process events through chips
    raw_insights = chips.process_events(events, context)

    # 3. Score insights
    scored_insights = scoring.score_all(raw_insights, context)

    # 4. Detect outcomes
    outcomes = outcome_signals.detect(events)

    # 5. Link outcomes to insights
    outcome_linker.link(outcomes, scored_insights)

    # 6. Promote high-value insights
    promoted = promoter.promote(scored_insights, threshold=0.5)

    # 7. Evolve chips based on performance
    chip_evolution.evolve(chips, scored_insights)

    # 8. Update meta-learning metrics
    metalearning.record_session(scored_insights, outcomes)

    # 9. Adjust strategies if needed
    metalearning.adjust_strategies()

    return stats
```

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| High-value insight ratio | >60% | Promoted insights / Total insights |
| Outcome linkage | >40% | Insights linked to outcomes |
| Chip coverage | >80% | Events matched by chips |
| False positive rate | <20% | Insights later invalidated |
| User satisfaction | >70% | Insights marked helpful |

---

## Implementation Order

1. **Day 1 Morning**: Onboarding system (detector, questions, context)
2. **Day 1 Afternoon**: Insight scoring system
3. **Day 2 Morning**: Outcome detection and linking
4. **Day 2 Afternoon**: Chip evolution basics
5. **Day 3**: Meta-learning loop and integration

Each component can work independently, so we can ship incrementally.
