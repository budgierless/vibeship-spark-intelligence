"""
Multi-Domain Project Model

Real projects need success across multiple interconnected domains.
A game needs design, tech, art, marketing, business - all working together.

"You can't win by being great at one thing if you're failing at another."
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime

log = logging.getLogger("spark.research.domains")

DOMAINS_FILE = Path.home() / ".spark" / "research" / "project_domains.json"


@dataclass
class DomainWeight:
    """How important a domain is to a project."""
    domain: str
    weight: float  # 0-1, how critical
    reason: str  # Why this matters
    detected: bool = True  # Auto-detected vs user-specified


@dataclass
class DomainInterconnection:
    """How two domains affect each other."""
    from_domain: str
    to_domain: str
    relationship: str  # "enables", "constrains", "enhances", "requires"
    strength: float  # 0-1
    description: str

    # Examples of effects
    positive_effects: List[str] = field(default_factory=list)
    negative_effects: List[str] = field(default_factory=list)


@dataclass
class DomainHealth:
    """Current health of a domain in a project."""
    domain: str
    coverage: float  # 0-1, how much attention it's getting
    quality: float  # 0-1, quality of work in this domain
    last_activity: str  # ISO timestamp
    insights_count: int = 0
    warnings_count: int = 0
    gaps: List[str] = field(default_factory=list)


@dataclass
class ProjectProfile:
    """Multi-domain profile for a project."""
    project_path: str
    name: str

    # Primary and secondary domains
    primary_domain: str
    domains: List[DomainWeight] = field(default_factory=list)

    # How domains connect
    interconnections: List[DomainInterconnection] = field(default_factory=list)

    # Current health
    domain_health: Dict[str, DomainHealth] = field(default_factory=dict)

    # Overall project health
    overall_health: float = 0.5
    neglected_domains: List[str] = field(default_factory=list)

    # User preferences
    user_priorities: List[str] = field(default_factory=list)

    # Metadata
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> 'ProjectProfile':
        # Reconstruct nested dataclasses
        domains = [DomainWeight(**d) for d in data.pop("domains", [])]
        interconnections = [DomainInterconnection(**i) for i in data.pop("interconnections", [])]
        health = {k: DomainHealth(**v) for k, v in data.pop("domain_health", {}).items()}

        return cls(
            domains=domains,
            interconnections=interconnections,
            domain_health=health,
            **{k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        )


# Common domain interconnections (can be extended via research)
COMMON_INTERCONNECTIONS = {
    # Game Development
    ("game_design", "game_tech"): DomainInterconnection(
        from_domain="game_design",
        to_domain="game_tech",
        relationship="requires",
        strength=0.9,
        description="Good game feel requires solid technical implementation",
        positive_effects=[
            "Responsive controls enable tight gameplay",
            "Stable framerate supports timing-based mechanics",
        ],
        negative_effects=[
            "Technical debt limits design iteration",
            "Performance issues break immersion",
        ],
    ),
    ("game_design", "game_art"): DomainInterconnection(
        from_domain="game_design",
        to_domain="game_art",
        relationship="enhances",
        strength=0.7,
        description="Art reinforces and communicates game design",
        positive_effects=[
            "Visual feedback makes mechanics readable",
            "Art style sets player expectations",
        ],
        negative_effects=[
            "Mismatched art confuses players about mechanics",
        ],
    ),
    ("game_tech", "game_art"): DomainInterconnection(
        from_domain="game_tech",
        to_domain="game_art",
        relationship="enables",
        strength=0.8,
        description="Tech enables or constrains art possibilities",
        positive_effects=[
            "Good rendering pipeline supports art vision",
            "Optimization allows more visual detail",
        ],
        negative_effects=[
            "Tech limitations force art compromises",
        ],
    ),

    # Web/App Development
    ("web_frontend", "web_backend"): DomainInterconnection(
        from_domain="web_frontend",
        to_domain="web_backend",
        relationship="requires",
        strength=0.9,
        description="Frontend depends on backend APIs and data",
        positive_effects=[
            "Well-designed APIs make frontend development smooth",
            "Consistent data models reduce bugs",
        ],
        negative_effects=[
            "API changes break frontend",
            "Slow endpoints hurt UX",
        ],
    ),
    ("web_frontend", "ux_design"): DomainInterconnection(
        from_domain="web_frontend",
        to_domain="ux_design",
        relationship="implements",
        strength=0.85,
        description="Frontend implements UX design decisions",
        positive_effects=[
            "Good implementation preserves design intent",
            "Component reuse ensures consistency",
        ],
        negative_effects=[
            "Implementation shortcuts hurt usability",
        ],
    ),

    # Product/Business
    ("product", "marketing"): DomainInterconnection(
        from_domain="product",
        to_domain="marketing",
        relationship="enables",
        strength=0.8,
        description="Product quality enables marketing claims",
        positive_effects=[
            "Good product creates word of mouth",
            "Features give marketing hooks",
        ],
        negative_effects=[
            "Overpromising damages trust",
            "Missing features undermine campaigns",
        ],
    ),
    ("product", "business"): DomainInterconnection(
        from_domain="product",
        to_domain="business",
        relationship="drives",
        strength=0.9,
        description="Product success drives business outcomes",
        positive_effects=[
            "User retention enables monetization",
            "Product-market fit enables growth",
        ],
        negative_effects=[
            "Poor product kills business regardless of other factors",
        ],
    ),

    # Cross-cutting
    ("tech", "operations"): DomainInterconnection(
        from_domain="tech",
        to_domain="operations",
        relationship="constrains",
        strength=0.7,
        description="Technical choices affect operational complexity",
        positive_effects=[
            "Good architecture simplifies operations",
            "Automation reduces operational burden",
        ],
        negative_effects=[
            "Tech debt creates operational firefighting",
            "Complex systems are hard to operate",
        ],
    ),
}


# Domain categories and their typical sub-domains
DOMAIN_CATEGORIES = {
    "game": {
        "domains": ["game_design", "game_tech", "game_art", "game_audio", "game_narrative"],
        "description": "Game development project",
        "critical": ["game_design", "game_tech"],  # Must have
    },
    "web_app": {
        "domains": ["web_frontend", "web_backend", "ux_design", "devops", "security"],
        "description": "Web application project",
        "critical": ["web_frontend", "web_backend"],
    },
    "mobile_app": {
        "domains": ["mobile_dev", "ux_design", "backend", "devops"],
        "description": "Mobile application project",
        "critical": ["mobile_dev"],
    },
    "saas": {
        "domains": ["product", "tech", "ux_design", "marketing", "business", "operations"],
        "description": "SaaS business",
        "critical": ["product", "tech", "business"],
    },
    "content": {
        "domains": ["content_creation", "marketing", "distribution", "community"],
        "description": "Content/media project",
        "critical": ["content_creation", "distribution"],
    },
    "ai_ml": {
        "domains": ["ml_research", "ml_engineering", "data", "infrastructure", "product"],
        "description": "AI/ML project",
        "critical": ["ml_engineering", "data"],
    },
}


class MultiDomainManager:
    """Manage multi-domain project profiles."""

    def __init__(self):
        self._profiles: Dict[str, ProjectProfile] = {}
        self._load_profiles()

    def _load_profiles(self):
        """Load saved profiles."""
        if DOMAINS_FILE.exists():
            try:
                with open(DOMAINS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for path, profile_data in data.get("profiles", {}).items():
                        self._profiles[path] = ProjectProfile.from_dict(profile_data)
            except Exception as e:
                log.warning(f"Failed to load domain profiles: {e}")

    def _save_profiles(self):
        """Save profiles to disk."""
        try:
            DOMAINS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "profiles": {k: v.to_dict() for k, v in self._profiles.items()},
                "updated_at": datetime.now().isoformat(),
            }
            with open(DOMAINS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log.error(f"Failed to save domain profiles: {e}")

    def detect_project_domains(
        self,
        project_path: str,
        files: List[str] = None,
        package_json: Dict = None,
        user_description: str = None,
    ) -> ProjectProfile:
        """
        Detect all relevant domains for a project.

        Uses file patterns, dependencies, and user input to build
        a complete multi-domain profile.
        """
        domains = []
        primary = None
        category = None

        # Detect from files
        if files:
            file_domains = self._detect_from_files(files)
            domains.extend(file_domains)

        # Detect from dependencies
        if package_json:
            dep_domains = self._detect_from_deps(package_json)
            domains.extend(dep_domains)

        # Detect from description
        if user_description:
            desc_domains = self._detect_from_description(user_description)
            domains.extend(desc_domains)

        # Determine category and fill gaps
        category = self._infer_category(domains)
        if category:
            # Add critical domains from category
            cat_info = DOMAIN_CATEGORIES[category]
            for domain in cat_info["critical"]:
                if not any(d.domain == domain for d in domains):
                    domains.append(DomainWeight(
                        domain=domain,
                        weight=0.8,
                        reason=f"Critical for {category} projects",
                        detected=True,
                    ))

            # Add other category domains with lower weight
            for domain in cat_info["domains"]:
                if not any(d.domain == domain for d in domains):
                    domains.append(DomainWeight(
                        domain=domain,
                        weight=0.4,
                        reason=f"Common in {category} projects",
                        detected=True,
                    ))

        # Determine primary domain
        if domains:
            primary = max(domains, key=lambda d: d.weight).domain
        else:
            primary = "general"
            domains.append(DomainWeight(
                domain="general",
                weight=1.0,
                reason="Default domain",
                detected=True,
            ))

        # Build interconnections
        interconnections = self._build_interconnections(domains)

        # Create profile
        profile = ProjectProfile(
            project_path=project_path,
            name=Path(project_path).name,
            primary_domain=primary,
            domains=domains,
            interconnections=interconnections,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )

        # Initialize health tracking
        for domain in domains:
            profile.domain_health[domain.domain] = DomainHealth(
                domain=domain.domain,
                coverage=0.0,
                quality=0.5,
                last_activity=datetime.now().isoformat(),
            )

        self._profiles[project_path] = profile
        self._save_profiles()

        log.info(f"Detected {len(domains)} domains for {project_path}, primary: {primary}")
        return profile

    def _detect_from_files(self, files: List[str]) -> List[DomainWeight]:
        """Detect domains from file patterns."""
        domains = []
        file_str = " ".join(files).lower()

        patterns = {
            "game_design": ["game", "level", "player", "enemy", "spawn"],
            "game_tech": ["physics", "collision", "renderer", "engine"],
            "game_art": ["sprite", "texture", "model", "animation", "asset"],
            "game_audio": ["sound", "music", "audio", "sfx"],
            "web_frontend": ["component", "page", "style", "css", "tsx", "jsx"],
            "web_backend": ["api", "route", "controller", "service", "model"],
            "ux_design": ["design", "figma", "sketch", "wireframe"],
            "devops": ["docker", "kubernetes", "deploy", "ci", "cd", "terraform"],
            "security": ["auth", "security", "permission", "role"],
            "ml_engineering": ["model", "train", "inference", "dataset"],
            "data": ["data", "pipeline", "etl", "warehouse"],
            "marketing": ["marketing", "campaign", "analytics", "seo"],
            "content_creation": ["content", "blog", "article", "video"],
        }

        for domain, keywords in patterns.items():
            matches = sum(1 for kw in keywords if kw in file_str)
            if matches >= 2:
                weight = min(1.0, 0.3 + matches * 0.15)
                domains.append(DomainWeight(
                    domain=domain,
                    weight=weight,
                    reason=f"Detected from file patterns ({matches} matches)",
                    detected=True,
                ))

        return domains

    def _detect_from_deps(self, package_json: Dict) -> List[DomainWeight]:
        """Detect domains from package.json dependencies."""
        domains = []

        deps = {**package_json.get("dependencies", {}), **package_json.get("devDependencies", {})}
        dep_str = " ".join(deps.keys()).lower()

        patterns = {
            "game_tech": ["phaser", "three", "pixi", "babylon", "matter-js"],
            "web_frontend": ["react", "vue", "angular", "svelte", "next", "nuxt"],
            "web_backend": ["express", "fastify", "nest", "koa", "hono"],
            "devops": ["docker", "kubernetes", "terraform", "pulumi"],
            "ml_engineering": ["tensorflow", "pytorch", "transformers", "onnx"],
            "mobile_dev": ["react-native", "expo", "capacitor", "ionic"],
        }

        for domain, libs in patterns.items():
            matches = sum(1 for lib in libs if lib in dep_str)
            if matches >= 1:
                weight = min(1.0, 0.5 + matches * 0.2)
                domains.append(DomainWeight(
                    domain=domain,
                    weight=weight,
                    reason=f"Detected from dependencies ({matches} matches)",
                    detected=True,
                ))

        return domains

    def _detect_from_description(self, description: str) -> List[DomainWeight]:
        """Detect domains from user description."""
        domains = []
        desc_lower = description.lower()

        patterns = {
            "game_design": ["game", "play", "fun", "balance", "mechanics"],
            "game_tech": ["engine", "performance", "physics", "render"],
            "web_frontend": ["ui", "interface", "frontend", "responsive"],
            "web_backend": ["api", "backend", "server", "database"],
            "ux_design": ["ux", "user experience", "usability", "design"],
            "marketing": ["market", "growth", "users", "acquisition"],
            "business": ["revenue", "monetize", "business", "profit"],
            "product": ["product", "feature", "roadmap", "user needs"],
            "operations": ["operate", "maintain", "scale", "reliability"],
        }

        for domain, keywords in patterns.items():
            matches = sum(1 for kw in keywords if kw in desc_lower)
            if matches >= 1:
                weight = min(1.0, 0.4 + matches * 0.2)
                domains.append(DomainWeight(
                    domain=domain,
                    weight=weight,
                    reason=f"Detected from description",
                    detected=True,
                ))

        return domains

    def _infer_category(self, domains: List[DomainWeight]) -> Optional[str]:
        """Infer project category from detected domains."""
        domain_names = {d.domain for d in domains}

        scores = {}
        for cat, info in DOMAIN_CATEGORIES.items():
            overlap = len(domain_names & set(info["domains"]))
            critical_overlap = len(domain_names & set(info["critical"]))
            scores[cat] = overlap + critical_overlap * 2

        if scores:
            best = max(scores, key=scores.get)
            if scores[best] >= 2:
                return best

        return None

    def _build_interconnections(self, domains: List[DomainWeight]) -> List[DomainInterconnection]:
        """Build interconnection map for project domains."""
        interconnections = []
        domain_names = {d.domain for d in domains}

        # Check for known interconnections
        for (from_d, to_d), interconnection in COMMON_INTERCONNECTIONS.items():
            if from_d in domain_names and to_d in domain_names:
                interconnections.append(interconnection)

        # Add implicit interconnections for same-category domains
        for d1 in domains:
            for d2 in domains:
                if d1.domain != d2.domain:
                    key = (d1.domain, d2.domain)
                    if key not in COMMON_INTERCONNECTIONS:
                        # Check if they're in same category
                        for cat_info in DOMAIN_CATEGORIES.values():
                            if d1.domain in cat_info["domains"] and d2.domain in cat_info["domains"]:
                                interconnections.append(DomainInterconnection(
                                    from_domain=d1.domain,
                                    to_domain=d2.domain,
                                    relationship="related",
                                    strength=0.3,
                                    description=f"Both part of the same project",
                                ))
                                break

        return interconnections

    def update_domain_health(
        self,
        project_path: str,
        domain: str,
        activity_type: str,
        quality_signal: float = None,
    ):
        """Update health tracking for a domain."""
        profile = self._profiles.get(project_path)
        if not profile:
            return

        if domain not in profile.domain_health:
            profile.domain_health[domain] = DomainHealth(
                domain=domain,
                coverage=0.0,
                quality=0.5,
                last_activity=datetime.now().isoformat(),
            )

        health = profile.domain_health[domain]
        health.last_activity = datetime.now().isoformat()
        health.coverage = min(1.0, health.coverage + 0.1)

        if quality_signal is not None:
            # Exponential moving average
            health.quality = health.quality * 0.7 + quality_signal * 0.3

        if activity_type == "insight":
            health.insights_count += 1
        elif activity_type == "warning":
            health.warnings_count += 1

        # Recalculate overall health
        self._recalculate_health(profile)
        self._save_profiles()

    def _recalculate_health(self, profile: ProjectProfile):
        """Recalculate overall project health and detect neglected domains."""
        if not profile.domain_health:
            return

        # Weight health by domain importance
        weighted_health = 0.0
        total_weight = 0.0

        for domain_weight in profile.domains:
            health = profile.domain_health.get(domain_weight.domain)
            if health:
                domain_score = (health.coverage * 0.4 + health.quality * 0.6)
                weighted_health += domain_score * domain_weight.weight
                total_weight += domain_weight.weight

        if total_weight > 0:
            profile.overall_health = weighted_health / total_weight

        # Detect neglected domains
        profile.neglected_domains = []
        for domain_weight in profile.domains:
            if domain_weight.weight >= 0.5:  # Important domain
                health = profile.domain_health.get(domain_weight.domain)
                if health and health.coverage < 0.3:
                    profile.neglected_domains.append(domain_weight.domain)

    def get_profile(self, project_path: str) -> Optional[ProjectProfile]:
        """Get project profile."""
        return self._profiles.get(project_path)

    def get_neglected_domains(self, project_path: str) -> List[str]:
        """Get list of neglected domains that need attention."""
        profile = self._profiles.get(project_path)
        if not profile:
            return []
        return profile.neglected_domains

    def get_interconnection_risks(self, project_path: str) -> List[Dict]:
        """Get risks from domain interconnections."""
        profile = self._profiles.get(project_path)
        if not profile:
            return []

        risks = []
        for interconnection in profile.interconnections:
            from_health = profile.domain_health.get(interconnection.from_domain)
            to_health = profile.domain_health.get(interconnection.to_domain)

            if from_health and to_health:
                # If a domain is struggling, check what it affects
                if from_health.quality < 0.4 and interconnection.strength >= 0.7:
                    risks.append({
                        "type": "dependency_risk",
                        "from_domain": interconnection.from_domain,
                        "to_domain": interconnection.to_domain,
                        "relationship": interconnection.relationship,
                        "description": f"Poor {interconnection.from_domain} may affect {interconnection.to_domain}",
                        "negative_effects": interconnection.negative_effects,
                        "severity": interconnection.strength * (1 - from_health.quality),
                    })

        return sorted(risks, key=lambda r: r["severity"], reverse=True)

    def add_user_priority(self, project_path: str, domain: str, reason: str = None):
        """Add a user-specified priority domain."""
        profile = self._profiles.get(project_path)
        if not profile:
            return

        # Add to priorities
        if domain not in profile.user_priorities:
            profile.user_priorities.append(domain)

        # Increase weight if domain exists
        for dw in profile.domains:
            if dw.domain == domain:
                dw.weight = min(1.0, dw.weight + 0.2)
                if reason:
                    dw.reason = reason
                break
        else:
            # Add new domain
            profile.domains.append(DomainWeight(
                domain=domain,
                weight=0.8,
                reason=reason or "User priority",
                detected=False,
            ))

        self._save_profiles()

    def get_holistic_summary(self, project_path: str) -> Dict:
        """Get holistic health summary for a project."""
        profile = self._profiles.get(project_path)
        if not profile:
            return {"error": "No profile found"}

        return {
            "project": profile.name,
            "primary_domain": profile.primary_domain,
            "overall_health": profile.overall_health,
            "domains": [
                {
                    "domain": dw.domain,
                    "weight": dw.weight,
                    "health": profile.domain_health.get(dw.domain, DomainHealth(dw.domain, 0, 0.5, "")).quality,
                    "coverage": profile.domain_health.get(dw.domain, DomainHealth(dw.domain, 0, 0.5, "")).coverage,
                }
                for dw in sorted(profile.domains, key=lambda d: d.weight, reverse=True)
            ],
            "neglected": profile.neglected_domains,
            "risks": self.get_interconnection_risks(project_path)[:3],
            "recommendations": self._generate_recommendations(profile),
        }

    def _generate_recommendations(self, profile: ProjectProfile) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Neglected domains
        for domain in profile.neglected_domains[:2]:
            recommendations.append(f"Increase focus on {domain} - currently under-covered")

        # Quality issues
        for dw in profile.domains:
            health = profile.domain_health.get(dw.domain)
            if health and health.quality < 0.4 and dw.weight >= 0.6:
                recommendations.append(f"Improve quality in {dw.domain} - critical domain struggling")

        # Interconnection risks
        risks = self.get_interconnection_risks(profile.project_path)
        if risks:
            top_risk = risks[0]
            recommendations.append(
                f"Address {top_risk['from_domain']} issues before they impact {top_risk['to_domain']}"
            )

        return recommendations[:5]


# Singleton manager
_manager: Optional[MultiDomainManager] = None


def get_domain_manager() -> MultiDomainManager:
    """Get singleton domain manager."""
    global _manager
    if _manager is None:
        _manager = MultiDomainManager()
    return _manager


def detect_project_domains(
    project_path: str,
    files: List[str] = None,
    package_json: Dict = None,
    user_description: str = None,
) -> ProjectProfile:
    """Detect all domains for a project."""
    return get_domain_manager().detect_project_domains(
        project_path, files, package_json, user_description
    )


def get_project_health(project_path: str) -> Dict:
    """Get holistic health summary."""
    return get_domain_manager().get_holistic_summary(project_path)
