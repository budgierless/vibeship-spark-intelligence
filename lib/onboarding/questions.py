"""
Onboarding Questions - Templates and logic for project onboarding.

Generates contextual questions based on detected domain
and what we already know.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

log = logging.getLogger("spark.onboarding")


@dataclass
class Question:
    """A single onboarding question."""
    id: str
    question: str
    type: str  # "text", "choice", "multi_choice"
    required: bool = True
    options: List[str] = field(default_factory=list)
    default: Optional[str] = None
    help_text: Optional[str] = None
    domain_specific: Optional[str] = None  # Only ask for this domain


# Core questions asked for every project
CORE_QUESTIONS = [
    Question(
        id="domain",
        question="What are we building? (1-2 words)",
        type="text",
        required=True,
        help_text="e.g., 'game', 'api', 'dashboard', 'cli tool'",
    ),
    Question(
        id="success",
        question="What does success look like?",
        type="text",
        required=True,
        help_text="Describe the end goal or ship criteria",
    ),
]

# Optional context questions
CONTEXT_QUESTIONS = [
    Question(
        id="focus",
        question="What should I pay special attention to?",
        type="multi_choice",
        required=False,
        options=["performance", "security", "UX/polish", "maintainability", "testing", "docs"],
    ),
    Question(
        id="avoid",
        question="What mistakes should I help you avoid?",
        type="text",
        required=False,
        help_text="e.g., 'scope creep', 'over-engineering', 'breaking tests'",
    ),
    Question(
        id="constraints",
        question="Any hard constraints?",
        type="text",
        required=False,
        help_text="e.g., 'no new dependencies', 'must work offline'",
    ),
    Question(
        id="prior_art",
        question="Similar to anything you've built before?",
        type="text",
        required=False,
        help_text="Helps transfer relevant learnings",
    ),
]

# Domain-specific questions
DOMAIN_QUESTIONS = {
    "game": [
        Question(
            id="game_loop",
            question="What's the core game loop?",
            type="text",
            domain_specific="game",
        ),
        Question(
            id="game_platform",
            question="Target platform?",
            type="choice",
            options=["web", "mobile", "desktop", "console"],
            domain_specific="game",
        ),
        Question(
            id="game_multiplayer",
            question="Multiplayer or single-player?",
            type="choice",
            options=["single-player", "local multiplayer", "online multiplayer"],
            domain_specific="game",
        ),
    ],
    "web": [
        Question(
            id="web_framework",
            question="What framework?",
            type="choice",
            options=["React", "Next.js", "Vue", "Svelte", "vanilla", "other"],
            domain_specific="web",
        ),
        Question(
            id="web_type",
            question="What type of web app?",
            type="choice",
            options=["dashboard", "landing page", "e-commerce", "SaaS", "blog", "other"],
            domain_specific="web",
        ),
    ],
    "api": [
        Question(
            id="api_style",
            question="API style?",
            type="choice",
            options=["REST", "GraphQL", "gRPC", "WebSocket"],
            domain_specific="api",
        ),
        Question(
            id="api_auth",
            question="Authentication approach?",
            type="choice",
            options=["JWT", "API keys", "OAuth", "session", "none yet"],
            domain_specific="api",
        ),
    ],
    "ml": [
        Question(
            id="ml_type",
            question="What type of ML?",
            type="choice",
            options=["classification", "generation", "embeddings", "fine-tuning", "RAG"],
            domain_specific="ml",
        ),
        Question(
            id="ml_framework",
            question="ML framework?",
            type="choice",
            options=["PyTorch", "TensorFlow", "scikit-learn", "HuggingFace", "OpenAI API"],
            domain_specific="ml",
        ),
    ],
    "marketing": [
        Question(
            id="mkt_audience",
            question="Who is the target audience?",
            type="text",
            domain_specific="marketing",
        ),
        Question(
            id="mkt_voice",
            question="Brand voice/tone?",
            type="choice",
            options=["professional", "casual", "playful", "technical", "inspirational"],
            domain_specific="marketing",
        ),
        Question(
            id="mkt_channels",
            question="Primary channels?",
            type="multi_choice",
            options=["social media", "email", "blog", "ads", "video"],
            domain_specific="marketing",
        ),
    ],
}


class OnboardingQuestions:
    """Generate and manage onboarding questions."""

    def __init__(self):
        self.answered: Dict[str, Any] = {}

    def get_core_questions(self) -> List[Question]:
        """Get core questions (always asked)."""
        return [q for q in CORE_QUESTIONS if q.id not in self.answered]

    def get_context_questions(self) -> List[Question]:
        """Get optional context questions."""
        return [q for q in CONTEXT_QUESTIONS if q.id not in self.answered]

    def get_domain_questions(self, domain: str) -> List[Question]:
        """Get domain-specific questions."""
        questions = DOMAIN_QUESTIONS.get(domain, [])
        return [q for q in questions if q.id not in self.answered]

    def get_all_pending(self, domain: Optional[str] = None) -> List[Question]:
        """Get all pending questions in priority order."""
        questions = []

        # Core first (required)
        questions.extend(self.get_core_questions())

        # Domain-specific next
        if domain:
            questions.extend(self.get_domain_questions(domain))

        # Context last (optional)
        questions.extend(self.get_context_questions())

        return questions

    def get_quick_onboarding(self, inferred_domain: Optional[str] = None) -> List[Question]:
        """Get minimal questions for quick onboarding (30 seconds)."""
        questions = []

        # Always need domain if not inferred
        if not inferred_domain and "domain" not in self.answered:
            questions.append(CORE_QUESTIONS[0])  # domain question

        # Always need success criteria
        if "success" not in self.answered:
            questions.append(CORE_QUESTIONS[1])  # success question

        return questions

    def record_answer(self, question_id: str, answer: Any):
        """Record an answer."""
        self.answered[question_id] = answer
        log.info(f"Recorded answer for {question_id}")

    def record_answers(self, answers: Dict[str, Any]):
        """Record multiple answers."""
        self.answered.update(answers)

    def get_context_dict(self) -> Dict[str, Any]:
        """Get answers as context dict."""
        return dict(self.answered)

    def needs_onboarding(self) -> bool:
        """Check if we still need core questions answered."""
        core_ids = {q.id for q in CORE_QUESTIONS if q.required}
        return not core_ids.issubset(set(self.answered.keys()))

    def generate_chip_activations(self) -> List[str]:
        """Suggest chips to activate based on answers."""
        chips = []

        domain = self.answered.get("domain", "").lower()

        # Map domains to chips
        domain_chip_map = {
            "game": ["game_dev"],
            "web": ["vibecoding"],
            "api": ["vibecoding"],
            "marketing": ["marketing"],
            "ml": ["spark-core"],
            "ai": ["spark-core"],
            "cli": ["vibecoding"],
            "tool": ["vibecoding"],
            "business": ["biz-ops"],
            "startup": ["biz-ops"],
        }

        for key, chip_list in domain_chip_map.items():
            if key in domain:
                chips.extend(chip_list)

        # Check focus areas for additional chips
        focus = self.answered.get("focus", [])
        if isinstance(focus, str):
            focus = [focus]

        if "security" in focus:
            chips.append("spark-core")
        if "performance" in focus:
            chips.append("spark-core")

        return list(set(chips))
