"""
ChipLoader: YAML parsing and schema validation for chip specs.

Chips are YAML files that define:
- Identity (id, name, version, description, domains)
- Triggers (patterns, events, tools)
- Observers (what data to capture)
- Learners (what patterns to detect)
- Outcomes (success/failure definitions)
- Evolution (self-improvement rules)
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class ObserverSpec:
    """Defines what data to capture when triggered."""
    name: str
    description: str = ""
    triggers: List[str] = field(default_factory=list)
    capture_required: Dict[str, str] = field(default_factory=dict)
    capture_optional: Dict[str, str] = field(default_factory=dict)
    extraction: List[Dict] = field(default_factory=list)


@dataclass
class LearnerSpec:
    """Defines what patterns to detect and learn."""
    name: str
    description: str = ""
    learner_type: str = "correlation"  # correlation, pattern, optimization
    input_observer: str = ""
    input_fields: List[str] = field(default_factory=list)
    output_observer: str = ""
    output_fields: List[str] = field(default_factory=list)
    learn: List[str] = field(default_factory=list)
    min_samples: int = 5
    confidence_threshold: float = 0.7


@dataclass
class OutcomeSpec:
    """Defines success/failure conditions."""
    condition: str
    weight: float = 1.0
    insight: str = ""
    action: str = ""


@dataclass
class QuestionSpec:
    """Defines a project question from a chip."""
    id: str
    question: str
    category: str = "goal"  # goal, done, risk, quality, metric, insight, etc.
    phase: str = ""  # Optional: discovery, prototype, polish, launch
    required: bool = False
    affects_learning: List[str] = field(default_factory=list)  # Which learners this affects


@dataclass
class TriggerSpec:
    """Defines what activates this chip."""
    patterns: List[str] = field(default_factory=list)
    events: List[str] = field(default_factory=list)
    tools: List[Dict] = field(default_factory=list)

    # Compiled regex patterns for efficiency
    _compiled_patterns: List[re.Pattern] = field(default_factory=list, repr=False)

    def compile_patterns(self):
        """Compile regex patterns for matching."""
        self._compiled_patterns = []
        for pattern in self.patterns:
            try:
                self._compiled_patterns.append(
                    re.compile(re.escape(pattern), re.IGNORECASE)
                )
            except re.error:
                pass

    def matches(self, text: str) -> bool:
        """Check if text matches any trigger pattern."""
        if not self._compiled_patterns:
            self.compile_patterns()

        text = (text or "").lower()
        for pattern in self._compiled_patterns:
            if pattern.search(text):
                return True
        return False


@dataclass
class ChipSpec:
    """Complete chip specification."""
    # Identity
    id: str
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    license: str = "MIT"
    domains: List[str] = field(default_factory=list)

    # Components
    triggers: TriggerSpec = field(default_factory=TriggerSpec)
    observers: List[ObserverSpec] = field(default_factory=list)
    learners: List[LearnerSpec] = field(default_factory=list)
    outcomes_positive: List[OutcomeSpec] = field(default_factory=list)
    outcomes_negative: List[OutcomeSpec] = field(default_factory=list)
    outcomes_neutral: List[OutcomeSpec] = field(default_factory=list)
    questions: List[QuestionSpec] = field(default_factory=list)

    # Metadata
    source_path: Optional[Path] = None
    raw_yaml: Dict = field(default_factory=dict)

    def get_observer(self, name: str) -> Optional[ObserverSpec]:
        """Get observer by name."""
        for obs in self.observers:
            if obs.name == name:
                return obs
        return None


class ChipLoader:
    """Loads and validates chip YAML specifications."""

    REQUIRED_FIELDS = ["chip"]
    CHIP_REQUIRED = ["id", "name"]

    def __init__(self):
        self._cache: Dict[str, ChipSpec] = {}

    def load(self, path: Path) -> ChipSpec:
        """Load a chip from YAML file."""
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Chip file not found: {path}")

        # Check cache
        cache_key = str(path.resolve())
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Load YAML
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        if not raw:
            raise ValueError(f"Empty or invalid YAML: {path}")

        # Validate and parse
        spec = self._parse_spec(raw, path)
        self._cache[cache_key] = spec

        return spec

    def _parse_spec(self, raw: Dict, path: Path) -> ChipSpec:
        """Parse raw YAML into ChipSpec."""
        # Validate required fields
        for field in self.REQUIRED_FIELDS:
            if field not in raw:
                raise ValueError(f"Missing required field: {field}")

        chip_data = raw.get("chip", {})
        for field in self.CHIP_REQUIRED:
            if field not in chip_data:
                raise ValueError(f"Missing required chip field: {field}")

        # Parse identity
        spec = ChipSpec(
            id=chip_data["id"],
            name=chip_data["name"],
            version=chip_data.get("version", "1.0.0"),
            description=chip_data.get("description", ""),
            author=chip_data.get("author", ""),
            license=chip_data.get("license", "MIT"),
            domains=chip_data.get("domains", []),
            source_path=path,
            raw_yaml=raw,
        )

        # Parse triggers
        triggers_data = raw.get("triggers", {})
        spec.triggers = TriggerSpec(
            patterns=triggers_data.get("patterns", []),
            events=triggers_data.get("events", []),
            tools=triggers_data.get("tools", []),
        )
        spec.triggers.compile_patterns()

        # Parse observers
        for obs_data in raw.get("observers", []):
            capture = obs_data.get("capture", {})
            spec.observers.append(ObserverSpec(
                name=obs_data.get("name", ""),
                description=obs_data.get("description", ""),
                triggers=obs_data.get("triggers", []),
                capture_required=capture.get("required", {}),
                capture_optional=capture.get("optional", {}),
                extraction=obs_data.get("extraction", []),
            ))

        # Parse learners
        for learner_data in raw.get("learners", []):
            input_data = learner_data.get("input", {})
            output_data = learner_data.get("output", {})
            spec.learners.append(LearnerSpec(
                name=learner_data.get("name", ""),
                description=learner_data.get("description", ""),
                learner_type=learner_data.get("type", "correlation"),
                input_observer=input_data.get("observer", ""),
                input_fields=input_data.get("fields", []),
                output_observer=output_data.get("observer", ""),
                output_fields=output_data.get("fields", []),
                learn=learner_data.get("learn", []),
                min_samples=learner_data.get("min_samples", 5),
                confidence_threshold=learner_data.get("confidence_threshold", 0.7),
            ))

        # Parse outcomes
        outcomes = raw.get("outcomes", {})
        for outcome_data in outcomes.get("positive", []):
            spec.outcomes_positive.append(OutcomeSpec(
                condition=outcome_data.get("condition", ""),
                weight=outcome_data.get("weight", 1.0),
                insight=outcome_data.get("insight", ""),
                action=outcome_data.get("action", ""),
            ))
        for outcome_data in outcomes.get("negative", []):
            spec.outcomes_negative.append(OutcomeSpec(
                condition=outcome_data.get("condition", ""),
                weight=outcome_data.get("weight", 1.0),
                insight=outcome_data.get("insight", ""),
                action=outcome_data.get("action", ""),
            ))
        for outcome_data in outcomes.get("neutral", []):
            spec.outcomes_neutral.append(OutcomeSpec(
                condition=outcome_data.get("condition", ""),
                weight=outcome_data.get("weight", 1.0),
                insight=outcome_data.get("insight", ""),
                action=outcome_data.get("action", ""),
            ))

        # Parse questions
        for q_data in raw.get("questions", []):
            spec.questions.append(QuestionSpec(
                id=q_data.get("id", ""),
                question=q_data.get("question", ""),
                category=q_data.get("category", "goal"),
                phase=q_data.get("phase", ""),
                required=q_data.get("required", False),
                affects_learning=q_data.get("affects_learning", []),
            ))

        return spec

    def validate(self, spec: ChipSpec) -> List[str]:
        """Validate a chip spec. Returns list of issues."""
        issues = []

        if not spec.id:
            issues.append("Chip ID is required")
        if not spec.name:
            issues.append("Chip name is required")
        if not spec.triggers.patterns and not spec.triggers.events:
            issues.append("Chip has no triggers defined")
        if not spec.observers:
            issues.append("Chip has no observers defined")

        # Validate learner references
        observer_names = {o.name for o in spec.observers}
        for learner in spec.learners:
            if learner.input_observer and learner.input_observer not in observer_names:
                issues.append(f"Learner '{learner.name}' references unknown observer: {learner.input_observer}")
            if learner.output_observer and learner.output_observer not in observer_names:
                issues.append(f"Learner '{learner.name}' references unknown observer: {learner.output_observer}")

        return issues


# Singleton loader
_loader: Optional[ChipLoader] = None


def get_loader() -> ChipLoader:
    """Get the global chip loader instance."""
    global _loader
    if _loader is None:
        _loader = ChipLoader()
    return _loader


def load_chip(path: Path) -> ChipSpec:
    """Load a chip from file."""
    return get_loader().load(path)
