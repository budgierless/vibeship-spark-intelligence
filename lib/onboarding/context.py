"""
Project Context - Store and retrieve project context.

Manages the context gathered from onboarding questions
and continuous inference during sessions.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime

from .detector import ProjectDetector

log = logging.getLogger("spark.onboarding")

CONTEXTS_DIR = Path.home() / ".spark" / "project_contexts"


@dataclass
class ProjectContext:
    """Full context for a project."""
    project_id: str
    project_path: str

    # From onboarding
    domain: str = ""
    success_criteria: str = ""
    focus_areas: List[str] = field(default_factory=list)
    avoid_patterns: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)

    # Domain-specific context
    domain_context: Dict[str, Any] = field(default_factory=dict)

    # Inferred during sessions
    inferred_patterns: List[str] = field(default_factory=list)
    active_chips: List[str] = field(default_factory=list)
    tech_stack: List[str] = field(default_factory=list)

    # Session tracking
    session_count: int = 0
    total_insights: int = 0
    last_session: str = ""
    created_at: str = ""

    # Flags
    needs_onboarding: bool = True
    pending_questions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'ProjectContext':
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def update_from_answers(self, answers: Dict[str, Any]):
        """Update context from onboarding answers."""
        if "domain" in answers:
            self.domain = answers["domain"]
        if "success" in answers:
            self.success_criteria = answers["success"]
        if "focus" in answers:
            focus = answers["focus"]
            self.focus_areas = focus if isinstance(focus, list) else [focus]
        if "avoid" in answers:
            avoid = answers["avoid"]
            self.avoid_patterns = avoid if isinstance(avoid, list) else [avoid] if avoid else []
        if "constraints" in answers:
            constraints = answers["constraints"]
            self.constraints = constraints if isinstance(constraints, list) else [constraints] if constraints else []

        # Store domain-specific answers
        domain_keys = ["game_loop", "game_platform", "game_multiplayer",
                       "web_framework", "web_type", "api_style", "api_auth",
                       "ml_type", "ml_framework", "mkt_audience", "mkt_voice", "mkt_channels"]
        for key in domain_keys:
            if key in answers:
                self.domain_context[key] = answers[key]

        # Update onboarding status
        if self.domain and self.success_criteria:
            self.needs_onboarding = False
            self.pending_questions = []

    def add_inferred_pattern(self, pattern: str):
        """Add a pattern inferred from session."""
        if pattern not in self.inferred_patterns:
            self.inferred_patterns.append(pattern)

    def add_tech(self, tech: str):
        """Add detected technology."""
        if tech not in self.tech_stack:
            self.tech_stack.append(tech)

    def activate_chip(self, chip_id: str):
        """Activate a chip for this project."""
        if chip_id not in self.active_chips:
            self.active_chips.append(chip_id)

    def start_session(self):
        """Record session start."""
        self.session_count += 1
        self.last_session = datetime.now().isoformat()


def _get_context_path(project_id: str) -> Path:
    """Get path to context file for a project."""
    return CONTEXTS_DIR / f"{project_id}.json"


def load_context(project_id: str) -> Optional[ProjectContext]:
    """Load context for a project."""
    path = _get_context_path(project_id)
    if not path.exists():
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return ProjectContext.from_dict(data)
    except Exception as e:
        log.warning(f"Failed to load context for {project_id}: {e}")
        return None


def save_context(context: ProjectContext):
    """Save context to disk."""
    try:
        CONTEXTS_DIR.mkdir(parents=True, exist_ok=True)
        path = _get_context_path(context.project_id)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(context.to_dict(), f, indent=2)
        log.info(f"Saved context for {context.project_id}")
    except Exception as e:
        log.error(f"Failed to save context: {e}")


def get_or_create_context(project_path: str) -> ProjectContext:
    """Get existing context or create new one for a project."""
    detector = ProjectDetector()
    project_id = detector.get_project_id(project_path)

    # Try to load existing
    context = load_context(project_id)
    if context:
        context.start_session()
        save_context(context)
        return context

    # Create new context
    inferred_domain = detector.infer_domain_from_path(project_path)

    context = ProjectContext(
        project_id=project_id,
        project_path=str(Path(project_path).resolve()),
        domain=inferred_domain or "",
        created_at=datetime.now().isoformat(),
        needs_onboarding=True,
        pending_questions=["domain", "success"] if not inferred_domain else ["success"],
    )

    # If domain was inferred, we only need success criteria
    if inferred_domain:
        context.domain = inferred_domain

    context.start_session()
    save_context(context)

    # Register with detector
    detector.register_project(project_path, context.to_dict())

    return context


def update_context(project_path: str, updates: Dict[str, Any]) -> ProjectContext:
    """Update context with new information."""
    context = get_or_create_context(project_path)
    context.update_from_answers(updates)
    save_context(context)
    return context


def list_all_contexts() -> List[ProjectContext]:
    """List all saved contexts."""
    contexts = []
    if CONTEXTS_DIR.exists():
        for path in CONTEXTS_DIR.glob("*.json"):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    contexts.append(ProjectContext.from_dict(data))
            except Exception as e:
                log.warning(f"Failed to load {path}: {e}")
    return contexts
