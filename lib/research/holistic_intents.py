"""
Holistic Intent System

Sets learning intents across ALL relevant domains for a project.
Tracks interconnections and ensures nothing important is missed.

"Success in real projects requires excellence across multiple dimensions."
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from datetime import datetime

from .mastery import get_researcher, DomainMastery
from .intents import LearningIntent, DomainIntent
from .domains import get_domain_manager, ProjectProfile

log = logging.getLogger("spark.research.holistic")

HOLISTIC_INTENTS_FILE = Path.home() / ".spark" / "research" / "holistic_intents.json"


@dataclass
class CrossDomainInsight:
    """An insight that spans multiple domains."""
    content: str
    domains: List[str]
    relationship: str  # How the domains connect
    importance: float
    detected_at: str


@dataclass
class DomainCoverage:
    """Tracking what's been covered in each domain."""
    domain: str
    intents_set: int
    insights_captured: int
    warnings_triggered: int
    last_activity: str
    gaps: List[str] = field(default_factory=list)


@dataclass
class HolisticIntent:
    """Complete learning intent across all project domains."""
    project_path: str

    # Domain-specific intents
    domain_intents: Dict[str, DomainIntent] = field(default_factory=dict)

    # Cross-cutting concerns
    cross_domain_watch: List[str] = field(default_factory=list)
    cross_domain_warn: List[str] = field(default_factory=list)

    # Interconnection awareness
    dependency_checks: List[str] = field(default_factory=list)

    # Coverage tracking
    coverage: Dict[str, DomainCoverage] = field(default_factory=dict)

    # User priorities
    priority_domains: List[str] = field(default_factory=list)
    priority_intents: List[str] = field(default_factory=list)

    # Meta
    created_at: str = ""
    updated_at: str = ""
    domains_researched: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        d = {
            "project_path": self.project_path,
            "domain_intents": {k: v.to_dict() for k, v in self.domain_intents.items()},
            "cross_domain_watch": self.cross_domain_watch,
            "cross_domain_warn": self.cross_domain_warn,
            "dependency_checks": self.dependency_checks,
            "coverage": {k: asdict(v) for k, v in self.coverage.items()},
            "priority_domains": self.priority_domains,
            "priority_intents": self.priority_intents,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "domains_researched": self.domains_researched,
        }
        return d


# Cross-cutting concerns that span multiple domains
CROSS_CUTTING_CONCERNS = {
    "quality": {
        "watch_for": [
            "Consistent quality across all project areas",
            "Quality gates before integration",
            "Review processes that catch issues early",
        ],
        "warn_about": [
            "Quality varying wildly between domains",
            "Skipping quality checks under pressure",
            "Technical debt accumulating in one area",
        ],
    },
    "integration": {
        "watch_for": [
            "Clean interfaces between domains",
            "Early integration testing",
            "Consistent data models across boundaries",
        ],
        "warn_about": [
            "Integration postponed until the end",
            "Domains evolving independently without sync",
            "Breaking changes not communicated",
        ],
    },
    "user_focus": {
        "watch_for": [
            "User needs driving all domain decisions",
            "End-to-end user journeys considered",
            "Feedback loops from users to all domains",
        ],
        "warn_about": [
            "Domains optimizing for themselves not users",
            "Technical decisions ignoring user impact",
            "User feedback siloed to one domain",
        ],
    },
    "sustainability": {
        "watch_for": [
            "Balanced progress across domains",
            "Technical debt managed proactively",
            "Team capacity distributed appropriately",
        ],
        "warn_about": [
            "One domain racing ahead while others lag",
            "Burnout from constant firefighting",
            "Short-term fixes creating long-term problems",
        ],
    },
}


class HolisticIntentSetter:
    """Set and manage holistic intents across all project domains."""

    def __init__(self):
        self.researcher = get_researcher()
        self.domain_manager = get_domain_manager()
        self._intents: Dict[str, HolisticIntent] = {}
        self._load_intents()

    def _load_intents(self):
        """Load saved holistic intents."""
        if HOLISTIC_INTENTS_FILE.exists():
            try:
                with open(HOLISTIC_INTENTS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for path, intent_data in data.get("intents", {}).items():
                        # Simplified loading - full reconstruction would need more
                        self._intents[path] = HolisticIntent(
                            project_path=path,
                            created_at=intent_data.get("created_at", ""),
                            updated_at=intent_data.get("updated_at", ""),
                            cross_domain_watch=intent_data.get("cross_domain_watch", []),
                            cross_domain_warn=intent_data.get("cross_domain_warn", []),
                            priority_domains=intent_data.get("priority_domains", []),
                        )
            except Exception as e:
                log.warning(f"Failed to load holistic intents: {e}")

    def _save_intents(self):
        """Save intents to disk."""
        try:
            HOLISTIC_INTENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "intents": {k: v.to_dict() for k, v in self._intents.items()},
                "updated_at": datetime.now().isoformat(),
            }
            with open(HOLISTIC_INTENTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log.error(f"Failed to save holistic intents: {e}")

    def set_holistic_intent(
        self,
        project_path: str,
        user_priorities: List[str] = None,
        focus_areas: List[str] = None,
    ) -> HolisticIntent:
        """
        Set learning intents for ALL domains in a project.

        1. Gets project profile (all domains)
        2. Researches mastery for each domain
        3. Sets domain-specific intents
        4. Adds cross-cutting concerns
        5. Adds dependency checks
        """
        # Get or create project profile
        profile = self.domain_manager.get_profile(project_path)
        if not profile:
            profile = self.domain_manager.detect_project_domains(project_path)

        # Create holistic intent
        holistic = HolisticIntent(
            project_path=project_path,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            priority_domains=user_priorities or [],
        )

        # Set intents for each domain
        for domain_weight in profile.domains:
            domain = domain_weight.domain
            mastery = self.researcher.research_domain(domain)

            # Create domain intent
            intent = self._create_domain_intent(domain, mastery, project_path)
            holistic.domain_intents[domain] = intent
            holistic.domains_researched.append(domain)

            # Initialize coverage tracking
            holistic.coverage[domain] = DomainCoverage(
                domain=domain,
                intents_set=len(intent.intents),
                insights_captured=0,
                warnings_triggered=0,
                last_activity=datetime.now().isoformat(),
            )

        # Add cross-cutting concerns
        holistic.cross_domain_watch = self._build_cross_domain_watch(profile)
        holistic.cross_domain_warn = self._build_cross_domain_warn(profile)

        # Add dependency checks based on interconnections
        holistic.dependency_checks = self._build_dependency_checks(profile)

        # Add user-specified focus areas
        if focus_areas:
            holistic.priority_intents.extend(focus_areas)

        self._intents[project_path] = holistic
        self._save_intents()

        log.info(f"Set holistic intent for {project_path}: {len(holistic.domain_intents)} domains")
        return holistic

    def _create_domain_intent(
        self,
        domain: str,
        mastery: DomainMastery,
        project_path: str,
    ) -> DomainIntent:
        """Create intent for a single domain."""
        intents = []

        for marker in mastery.markers:
            intent = LearningIntent(
                name=marker.name,
                description=marker.description,
                triggers=self._extract_triggers(marker),
                positive_signals=marker.indicators,
                negative_signals=marker.anti_patterns,
                priority=marker.confidence,
                domain=domain,
            )
            intents.append(intent)

        watch_for = list(mastery.success_indicators)
        for marker in mastery.markers:
            watch_for.extend(marker.indicators[:2])

        warn_about = list(mastery.common_mistakes)
        for marker in mastery.markers:
            warn_about.extend(marker.anti_patterns[:2])

        return DomainIntent(
            domain=domain,
            project_path=project_path,
            intents=intents,
            watch_for=watch_for[:15],
            warn_about=warn_about[:15],
            mastery_focus=mastery.core_principles[:5],
            created_at=datetime.now().isoformat(),
            based_on_mastery=len(mastery.markers) > 0,
        )

    def _extract_triggers(self, marker) -> List[str]:
        """Extract trigger words from marker indicators."""
        triggers = []
        for indicator in marker.indicators:
            words = indicator.lower().split()
            for word in words:
                if len(word) > 4 and word.isalpha():
                    triggers.append(word)
        return list(set(triggers))[:10]

    def _build_cross_domain_watch(self, profile: ProjectProfile) -> List[str]:
        """Build cross-cutting watch patterns."""
        watch = []

        # Add from cross-cutting concerns
        for concern, patterns in CROSS_CUTTING_CONCERNS.items():
            watch.extend(patterns["watch_for"][:2])

        # Add interconnection-aware patterns
        for interconnection in profile.interconnections[:5]:
            if interconnection.positive_effects:
                watch.append(interconnection.positive_effects[0])

        return watch[:20]

    def _build_cross_domain_warn(self, profile: ProjectProfile) -> List[str]:
        """Build cross-cutting warning patterns."""
        warn = []

        # Add from cross-cutting concerns
        for concern, patterns in CROSS_CUTTING_CONCERNS.items():
            warn.extend(patterns["warn_about"][:2])

        # Add interconnection risks
        for interconnection in profile.interconnections[:5]:
            if interconnection.negative_effects:
                warn.append(interconnection.negative_effects[0])

        return warn[:20]

    def _build_dependency_checks(self, profile: ProjectProfile) -> List[str]:
        """Build checks for domain dependencies."""
        checks = []

        for interconnection in profile.interconnections:
            if interconnection.strength >= 0.7:
                checks.append(
                    f"When working on {interconnection.to_domain}, "
                    f"check impact from {interconnection.from_domain} "
                    f"({interconnection.relationship})"
                )

        return checks[:10]

    def get_holistic_intent(self, project_path: str) -> Optional[HolisticIntent]:
        """Get holistic intent for a project."""
        return self._intents.get(project_path)

    def check_content(self, content: str, project_path: str) -> Dict[str, Any]:
        """
        Check content against ALL domain intents.

        Returns matches from every domain, not just primary.
        """
        holistic = self._intents.get(project_path)
        if not holistic:
            return {"has_intent": False}

        content_lower = content.lower()
        results = {
            "has_intent": True,
            "domain_matches": {},
            "cross_domain_matches": {
                "positive": [],
                "negative": [],
            },
            "dependency_alerts": [],
            "coverage_update": {},
        }

        # Check each domain
        for domain, intent in holistic.domain_intents.items():
            positive = [p for p in intent.watch_for if p.lower() in content_lower]
            negative = [n for n in intent.warn_about if n.lower() in content_lower]

            if positive or negative:
                results["domain_matches"][domain] = {
                    "positive": positive,
                    "negative": negative,
                    "score": len(positive) * 0.2 - len(negative) * 0.3,
                }

                # Update coverage
                if domain in holistic.coverage:
                    holistic.coverage[domain].last_activity = datetime.now().isoformat()
                    holistic.coverage[domain].insights_captured += len(positive)
                    holistic.coverage[domain].warnings_triggered += len(negative)

        # Check cross-domain patterns
        for pattern in holistic.cross_domain_watch:
            if pattern.lower() in content_lower:
                results["cross_domain_matches"]["positive"].append(pattern)

        for pattern in holistic.cross_domain_warn:
            if pattern.lower() in content_lower:
                results["cross_domain_matches"]["negative"].append(pattern)

        # Check for dependency concerns
        for check in holistic.dependency_checks:
            # Extract domain names from check
            for domain in holistic.domain_intents.keys():
                if domain in check.lower() and domain in content_lower:
                    results["dependency_alerts"].append(check)
                    break

        self._save_intents()
        return results

    def get_neglected_domains(self, project_path: str) -> List[Dict]:
        """Get domains that aren't getting enough attention."""
        holistic = self._intents.get(project_path)
        if not holistic:
            return []

        neglected = []
        profile = self.domain_manager.get_profile(project_path)
        if not profile:
            return []

        for domain_weight in profile.domains:
            domain = domain_weight.domain
            coverage = holistic.coverage.get(domain)

            if coverage:
                # Important domain with low coverage
                if domain_weight.weight >= 0.5 and coverage.insights_captured < 3:
                    neglected.append({
                        "domain": domain,
                        "weight": domain_weight.weight,
                        "insights": coverage.insights_captured,
                        "reason": f"Critical domain with only {coverage.insights_captured} insights captured",
                    })

        return sorted(neglected, key=lambda x: x["weight"], reverse=True)

    def get_focus_summary(self, project_path: str) -> str:
        """Get a summary of what to focus on across all domains."""
        holistic = self._intents.get(project_path)
        if not holistic:
            return "No holistic intent set. Run set_holistic_intent() first."

        lines = [
            "# Holistic Learning Intent",
            "",
            f"**Project:** {Path(project_path).name}",
            f"**Domains:** {len(holistic.domain_intents)}",
            "",
        ]

        # Domain summaries
        lines.append("## Domain Focus Areas")
        lines.append("")

        for domain, intent in holistic.domain_intents.items():
            coverage = holistic.coverage.get(domain)
            status = ""
            if coverage and coverage.insights_captured < 3:
                status = " (needs attention)"

            lines.append(f"### {domain}{status}")
            lines.append(f"*Watch for:* {', '.join(intent.watch_for[:3])}")
            lines.append(f"*Avoid:* {', '.join(intent.warn_about[:2])}")
            lines.append("")

        # Cross-cutting concerns
        lines.append("## Cross-Cutting Concerns")
        lines.append("")
        lines.append("*These patterns span multiple domains:*")
        lines.append("")
        for pattern in holistic.cross_domain_watch[:5]:
            lines.append(f"- {pattern}")
        lines.append("")

        # Dependency alerts
        if holistic.dependency_checks:
            lines.append("## Domain Dependencies")
            lines.append("")
            for check in holistic.dependency_checks[:5]:
                lines.append(f"- {check}")
            lines.append("")

        # Neglected areas
        neglected = self.get_neglected_domains(project_path)
        if neglected:
            lines.append("## Needs Attention")
            lines.append("")
            for n in neglected[:3]:
                lines.append(f"- **{n['domain']}**: {n['reason']}")
            lines.append("")

        return "\n".join(lines)

    def record_domain_activity(
        self,
        project_path: str,
        domain: str,
        activity_type: str,  # "insight", "warning", "decision"
        content: str = None,
    ):
        """Record activity in a domain for coverage tracking."""
        holistic = self._intents.get(project_path)
        if not holistic:
            return

        if domain not in holistic.coverage:
            holistic.coverage[domain] = DomainCoverage(
                domain=domain,
                intents_set=0,
                insights_captured=0,
                warnings_triggered=0,
                last_activity=datetime.now().isoformat(),
            )

        coverage = holistic.coverage[domain]
        coverage.last_activity = datetime.now().isoformat()

        if activity_type == "insight":
            coverage.insights_captured += 1
        elif activity_type == "warning":
            coverage.warnings_triggered += 1

        # Update domain manager too
        quality = 0.7 if activity_type == "insight" else 0.3
        self.domain_manager.update_domain_health(
            project_path, domain, activity_type, quality
        )

        self._save_intents()


# Singleton setter
_setter: Optional[HolisticIntentSetter] = None


def get_holistic_setter() -> HolisticIntentSetter:
    """Get singleton holistic intent setter."""
    global _setter
    if _setter is None:
        _setter = HolisticIntentSetter()
    return _setter


def set_holistic_intent(
    project_path: str,
    user_priorities: List[str] = None,
    focus_areas: List[str] = None,
) -> HolisticIntent:
    """Set holistic intent for a project."""
    return get_holistic_setter().set_holistic_intent(
        project_path, user_priorities, focus_areas
    )


def check_against_all_domains(content: str, project_path: str) -> Dict[str, Any]:
    """Check content against all domain intents."""
    return get_holistic_setter().check_content(content, project_path)


def get_project_focus(project_path: str) -> str:
    """Get focus summary for project."""
    return get_holistic_setter().get_focus_summary(project_path)
