"""
Mastery Researcher - Research what mastery looks like in a domain.

Before learning from observation, understand what excellence means.
This sets the intent for what Spark should be looking for.
"""

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

log = logging.getLogger("spark.research")

MASTERY_CACHE = Path.home() / ".spark" / "research" / "mastery"


def _safe_cache_key(domain: str) -> str:
    """Create a filesystem-safe cache key from a domain name."""
    raw = str(domain or "").strip().lower()
    if not raw:
        return "domain"
    key = re.sub(r"[^a-z0-9._-]+", "_", raw)
    key = key.strip("._-")
    return key or "domain"


@dataclass
class MasteryMarker:
    """A specific marker of mastery in a domain."""
    name: str
    description: str
    indicators: List[str]  # What to look for
    anti_patterns: List[str]  # What to avoid
    source: str  # Where this came from
    confidence: float = 0.8


@dataclass
class DomainMastery:
    """Complete mastery definition for a domain."""
    domain: str
    description: str

    # What mastery looks like
    markers: List[MasteryMarker] = field(default_factory=list)

    # Key principles
    core_principles: List[str] = field(default_factory=list)

    # Common pitfalls
    common_mistakes: List[str] = field(default_factory=list)

    # Success criteria
    success_indicators: List[str] = field(default_factory=list)

    # Expert recommendations
    expert_insights: List[str] = field(default_factory=list)

    # Research metadata
    researched_at: str = ""
    sources: List[str] = field(default_factory=list)
    needs_refresh: bool = False

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["markers"] = [asdict(m) for m in self.markers]
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> 'DomainMastery':
        markers = [MasteryMarker(**m) for m in data.pop("markers", [])]
        return cls(markers=markers, **{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# Built-in mastery definitions (can be expanded via research)
BUILTIN_MASTERY = {
    "game_dev": DomainMastery(
        domain="game_dev",
        description="Game Development - Creating engaging interactive experiences",
        markers=[
            MasteryMarker(
                name="Game Feel",
                description="The tactile, kinesthetic sensation of interacting with the game",
                indicators=[
                    "Responsive controls (< 100ms input lag)",
                    "Juice/polish effects (screen shake, particles, sounds)",
                    "Smooth animations with proper easing",
                    "Clear feedback for every action",
                ],
                anti_patterns=[
                    "Floaty or unresponsive controls",
                    "Silent actions with no feedback",
                    "Jarring or instant transitions",
                ],
                source="Game Feel by Steve Swink",
            ),
            MasteryMarker(
                name="Balance",
                description="Fair challenge that respects player skill",
                indicators=[
                    "Difficulty curves that teach through play",
                    "Multiple viable strategies",
                    "Risk/reward tradeoffs",
                    "Playtesting-driven adjustments",
                ],
                anti_patterns=[
                    "Arbitrary difficulty spikes",
                    "One dominant strategy",
                    "Luck-based outcomes for skill games",
                ],
                source="Game design literature",
            ),
            MasteryMarker(
                name="Player Psychology",
                description="Understanding what makes games engaging",
                indicators=[
                    "Clear goals and progress indicators",
                    "Meaningful choices with consequences",
                    "Flow state optimization",
                    "Appropriate challenge level",
                ],
                anti_patterns=[
                    "Unclear objectives",
                    "Meaningless choices",
                    "Frustration loops",
                ],
                source="Flow theory, MDA framework",
            ),
        ],
        core_principles=[
            "Fun is the goal, everything else is a means",
            "Playtest early, playtest often",
            "Every interaction should feel good",
            "Clarity over complexity",
            "Respect the player's time",
        ],
        common_mistakes=[
            "Adding features without playtesting",
            "Optimizing before fun is proven",
            "Ignoring player feedback",
            "Scope creep on core mechanics",
            "Polish before the fun loop works",
        ],
        success_indicators=[
            "Players want to play again",
            "Players talk about it positively",
            "Core loop is engaging before polish",
            "Difficulty feels fair, not frustrating",
        ],
        expert_insights=[
            "Find the fun first, then build around it",
            "Your first 10 ideas are usually wrong",
            "The best games teach through play, not tutorials",
            "Juice is the difference between good and great",
        ],
    ),

    "marketing": DomainMastery(
        domain="marketing",
        description="Marketing - Connecting products with people who need them",
        markers=[
            MasteryMarker(
                name="Audience Understanding",
                description="Deep knowledge of who you're talking to",
                indicators=[
                    "Specific persona definitions",
                    "Pain points clearly articulated",
                    "Language that resonates",
                    "Channel selection based on behavior",
                ],
                anti_patterns=[
                    "Generic 'everyone' targeting",
                    "Feature-focused messaging",
                    "Wrong channel for audience",
                ],
                source="Marketing fundamentals",
            ),
            MasteryMarker(
                name="Clear Value Proposition",
                description="Why this product, why now",
                indicators=[
                    "One clear benefit per message",
                    "Differentiation from alternatives",
                    "Addresses specific pain point",
                    "Easy to understand in 5 seconds",
                ],
                anti_patterns=[
                    "Feature lists instead of benefits",
                    "Jargon-heavy copy",
                    "Unclear call to action",
                ],
                source="Positioning literature",
            ),
        ],
        core_principles=[
            "Know your audience better than they know themselves",
            "Benefits over features",
            "Consistency builds trust",
            "Test everything, assume nothing",
            "Simple beats clever",
        ],
        common_mistakes=[
            "Talking about yourself instead of the customer",
            "Too many messages at once",
            "Ignoring data for gut feel",
            "Copying competitors blindly",
        ],
        success_indicators=[
            "Clear conversion path",
            "Engagement metrics improving",
            "Customer language in copy",
            "Measurable goals for every campaign",
        ],
        expert_insights=[
            "The best marketing doesn't feel like marketing",
            "Emotion drives action, logic justifies it",
            "Your competition is attention, not other products",
        ],
    ),

    "web": DomainMastery(
        domain="web",
        description="Web Development - Building fast, accessible, maintainable web apps",
        markers=[
            MasteryMarker(
                name="Performance",
                description="Fast, responsive user experience",
                indicators=[
                    "LCP < 2.5s, FID < 100ms, CLS < 0.1",
                    "Code splitting and lazy loading",
                    "Optimized images and assets",
                    "Efficient re-renders",
                ],
                anti_patterns=[
                    "Blocking main thread",
                    "Unnecessary re-renders",
                    "Unoptimized images",
                    "No loading states",
                ],
                source="Web Vitals, performance best practices",
            ),
            MasteryMarker(
                name="Maintainability",
                description="Code that's easy to understand and change",
                indicators=[
                    "Clear component boundaries",
                    "Consistent naming conventions",
                    "Appropriate abstraction levels",
                    "Good test coverage",
                ],
                anti_patterns=[
                    "God components",
                    "Prop drilling everywhere",
                    "Inconsistent patterns",
                    "No error boundaries",
                ],
                source="Clean code principles",
            ),
        ],
        core_principles=[
            "Progressive enhancement",
            "Accessibility is not optional",
            "Performance is a feature",
            "Simple > clever",
            "Composition over inheritance",
        ],
        common_mistakes=[
            "Premature optimization",
            "Over-engineering simple features",
            "Ignoring accessibility",
            "Not handling loading/error states",
        ],
        success_indicators=[
            "Core Web Vitals passing",
            "Accessible to screen readers",
            "Works without JavaScript (basic)",
            "Easy to onboard new developers",
        ],
        expert_insights=[
            "The best code is code you don't write",
            "Users don't care about your tech stack",
            "Ship, measure, iterate",
        ],
    ),

    "api": DomainMastery(
        domain="api",
        description="API Development - Building reliable, intuitive interfaces",
        markers=[
            MasteryMarker(
                name="Consistency",
                description="Predictable patterns throughout the API",
                indicators=[
                    "Consistent naming conventions",
                    "Predictable error formats",
                    "Standard HTTP semantics",
                    "Versioning strategy",
                ],
                anti_patterns=[
                    "Mixed naming styles",
                    "Inconsistent error handling",
                    "Wrong HTTP methods",
                ],
                source="REST/API design guides",
            ),
            MasteryMarker(
                name="Robustness",
                description="Handles edge cases gracefully",
                indicators=[
                    "Input validation",
                    "Rate limiting",
                    "Graceful degradation",
                    "Idempotency where needed",
                ],
                anti_patterns=[
                    "Trusting client input",
                    "No rate limits",
                    "Cascading failures",
                ],
                source="API security best practices",
            ),
        ],
        core_principles=[
            "Be liberal in what you accept, strict in what you send",
            "Fail fast, fail clearly",
            "Design for the consumer, not the implementer",
            "Backwards compatibility matters",
        ],
        common_mistakes=[
            "Breaking changes without versioning",
            "Exposing internal implementation",
            "Poor error messages",
            "No pagination on lists",
        ],
        success_indicators=[
            "Easy to use correctly, hard to use incorrectly",
            "Self-documenting with good naming",
            "Comprehensive error messages",
            "Good documentation with examples",
        ],
        expert_insights=[
            "Your API is a user interface for developers",
            "Every API is an abstraction - choose what to hide carefully",
        ],
    ),
}


class MasteryResearcher:
    """Research and manage domain mastery definitions."""

    def __init__(self):
        self._cache: Dict[str, DomainMastery] = {}
        self._load_cache()

    def _load_cache(self):
        """Load cached mastery definitions."""
        if MASTERY_CACHE.exists():
            for path in MASTERY_CACHE.glob("*.json"):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        mastery = DomainMastery.from_dict(data)
                        self._cache[mastery.domain] = mastery
                except Exception as e:
                    log.warning(f"Failed to load mastery {path}: {e}")

    def _save_mastery(self, mastery: DomainMastery):
        """Save mastery definition to cache."""
        try:
            MASTERY_CACHE.mkdir(parents=True, exist_ok=True)
            path = MASTERY_CACHE / f"{_safe_cache_key(mastery.domain)}.json"
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(mastery.to_dict(), f, indent=2)
        except Exception as e:
            log.error(f"Failed to save mastery: {e}")

    def get_mastery(self, domain: str) -> Optional[DomainMastery]:
        """Get mastery definition for a domain."""
        # Check cache first
        if domain in self._cache:
            return self._cache[domain]

        # Check built-in definitions
        if domain in BUILTIN_MASTERY:
            mastery = BUILTIN_MASTERY[domain]
            self._cache[domain] = mastery
            return mastery

        return None

    def research_domain(self, domain: str, research_queries: List[str] = None) -> DomainMastery:
        """
        Research what mastery looks like in a domain.

        This can be extended to do actual web research.
        For now, it uses built-in knowledge or creates a placeholder.
        """
        # Check if we already have it
        existing = self.get_mastery(domain)
        if existing and not existing.needs_refresh:
            return existing

        # Try to find related domain
        domain_lower = domain.lower()
        for key, mastery in BUILTIN_MASTERY.items():
            if key in domain_lower or domain_lower in key:
                self._cache[domain] = mastery
                return mastery

        # Create placeholder for unknown domain
        mastery = DomainMastery(
            domain=domain,
            description=f"{domain} - Domain mastery definition needed",
            core_principles=[
                "Quality over quantity",
                "Test assumptions early",
                "Iterate based on feedback",
            ],
            common_mistakes=[
                "Skipping validation",
                "Over-engineering",
                "Ignoring edge cases",
            ],
            success_indicators=[
                "Meets user needs",
                "Maintainable over time",
                "Performs well",
            ],
            researched_at=datetime.now().isoformat(),
            needs_refresh=True,  # Flag for future research
        )

        self._cache[domain] = mastery
        self._save_mastery(mastery)

        log.info(f"Created placeholder mastery for {domain} - needs research")
        return mastery

    def add_marker(self, domain: str, marker: MasteryMarker):
        """Add a mastery marker to a domain."""
        mastery = self.get_mastery(domain)
        if mastery:
            mastery.markers.append(marker)
            self._save_mastery(mastery)

    def add_insight(self, domain: str, insight: str, source: str = "observed"):
        """Add an expert insight from research or observation."""
        mastery = self.get_mastery(domain)
        if mastery:
            if insight not in mastery.expert_insights:
                mastery.expert_insights.append(insight)
                mastery.sources.append(f"{source}: {insight[:50]}")
                self._save_mastery(mastery)

    def get_indicators_for_chip(self, chip_id: str) -> List[str]:
        """Get mastery indicators relevant to a chip."""
        mastery = self.get_mastery(chip_id)
        if not mastery:
            return []

        indicators = []
        for marker in mastery.markers:
            indicators.extend(marker.indicators)
        indicators.extend(mastery.success_indicators)
        return indicators

    def get_anti_patterns_for_chip(self, chip_id: str) -> List[str]:
        """Get anti-patterns relevant to a chip."""
        mastery = self.get_mastery(chip_id)
        if not mastery:
            return []

        anti_patterns = []
        for marker in mastery.markers:
            anti_patterns.extend(marker.anti_patterns)
        anti_patterns.extend(mastery.common_mistakes)
        return anti_patterns

    def research_online(
        self,
        domain: str,
        search_results: List[Dict] = None,
        purpose: str = "best_practices",
    ) -> DomainMastery:
        """
        Research a domain using web search results.

        Can be called with pre-fetched results or will trigger search.
        """
        from .web_research import get_web_researcher

        researcher = get_web_researcher()

        # Get or create mastery
        mastery = self.get_mastery(domain)
        if not mastery:
            mastery = DomainMastery(
                domain=domain,
                description=f"{domain} - Researched from web",
                researched_at=datetime.now().isoformat(),
            )

        # Process search results if provided
        if search_results:
            research = researcher.research_domain_sync(
                domain,
                search_results,
                purpose=purpose,
            )
            merge_data = researcher.merge_into_mastery(research)

            # Add researched markers
            for marker in merge_data.get("markers", []):
                if marker.name not in [m.name for m in mastery.markers]:
                    mastery.markers.append(marker)

            # Add principles
            for principle in merge_data.get("core_principles", []):
                if principle not in mastery.core_principles:
                    mastery.core_principles.append(principle)

            # Add mistakes
            for mistake in merge_data.get("common_mistakes", []):
                if mistake not in mastery.common_mistakes:
                    mastery.common_mistakes.append(mistake)

            # Add expert insights
            for insight in merge_data.get("expert_insights", []):
                if insight not in mastery.expert_insights:
                    mastery.expert_insights.append(insight)

            # Add sources
            mastery.sources.extend(merge_data.get("sources", []))
            mastery.needs_refresh = False

        self._cache[domain] = mastery
        self._save_mastery(mastery)

        log.info(f"Enriched mastery for {domain} with web research")
        return mastery

    def list_domains(self) -> List[str]:
        """List all known domains."""
        domains = set(BUILTIN_MASTERY.keys())
        domains.update(self._cache.keys())
        return list(domains)


# Singleton researcher
_researcher: Optional[MasteryResearcher] = None


def get_researcher() -> MasteryResearcher:
    """Get singleton researcher instance."""
    global _researcher
    if _researcher is None:
        _researcher = MasteryResearcher()
    return _researcher


def research_domain(domain: str) -> DomainMastery:
    """Research a domain (convenience function)."""
    return get_researcher().research_domain(domain)
