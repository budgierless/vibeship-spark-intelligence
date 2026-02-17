"""
Web Research - Online research for domain mastery.

When Spark encounters a new domain or needs to refresh
understanding, this module searches for best practices,
anti-patterns, and expert insights.
"""

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

log = logging.getLogger("spark.research.web")

RESEARCH_CACHE = Path.home() / ".spark" / "research" / "web_cache"


@dataclass
class ResearchQuery:
    """A research query with context."""
    query: str
    purpose: str  # "best_practices", "anti_patterns", "expert_insights", "common_mistakes"
    domain: str
    timestamp: str = ""


@dataclass
class ResearchResult:
    """A result from web research."""
    title: str
    snippet: str
    url: str
    source: str
    relevance: float = 0.8
    extracted_insights: List[str] = field(default_factory=list)


@dataclass
class DomainResearch:
    """Complete research results for a domain."""
    domain: str
    queries_run: List[ResearchQuery] = field(default_factory=list)
    results: List[ResearchResult] = field(default_factory=list)

    # Extracted knowledge
    best_practices: List[str] = field(default_factory=list)
    anti_patterns: List[str] = field(default_factory=list)
    expert_insights: List[str] = field(default_factory=list)
    common_mistakes: List[str] = field(default_factory=list)
    key_concepts: List[str] = field(default_factory=list)

    # Metadata
    researched_at: str = ""
    total_sources: int = 0
    confidence: float = 0.5

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'DomainResearch':
        queries = [ResearchQuery(**q) for q in data.pop("queries_run", [])]
        results = [ResearchResult(**r) for r in data.pop("results", [])]
        return cls(queries_run=queries, results=results, **{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# Query templates for different research purposes
QUERY_TEMPLATES = {
    "best_practices": [
        "{domain} best practices {year}",
        "{domain} expert tips professional",
        "how to master {domain} guide",
        "{domain} what separates good from great",
    ],
    "anti_patterns": [
        "{domain} common mistakes to avoid",
        "{domain} anti-patterns pitfalls",
        "{domain} what not to do beginners",
        "{domain} bad practices examples",
    ],
    "expert_insights": [
        "{domain} expert advice professionals",
        "{domain} lessons learned experience",
        "{domain} wisdom from experts",
        "{domain} senior developer tips",
    ],
    "common_mistakes": [
        "{domain} beginner mistakes",
        "{domain} why projects fail",
        "{domain} debugging common issues",
        "{domain} troubleshooting guide",
    ],
    "success_indicators": [
        "{domain} how to measure success",
        "{domain} quality metrics KPIs",
        "{domain} signs of good work",
        "{domain} excellence criteria",
    ],
}

# Patterns to extract insights from text
INSIGHT_PATTERNS = [
    # Best practices
    (r"(?:always|should|must|important to|best practice[s]?[:\s]+)([^.!?]+[.!?])", "best_practice"),
    (r"(?:key is|secret is|trick is)([^.!?]+[.!?])", "best_practice"),

    # Anti-patterns
    (r"(?:never|avoid|don't|do not|mistake[s]?[:\s]+)([^.!?]+[.!?])", "anti_pattern"),
    (r"(?:bad practice|anti-pattern|pitfall)[s]?[:\s]+([^.!?]+[.!?])", "anti_pattern"),

    # Expert insights
    (r"(?:expert[s]? say|professional[s]? recommend|senior developer[s]? suggest)([^.!?]+[.!?])", "expert"),
    (r"(?:in my experience|after years of|lesson learned)([^.!?]+[.!?])", "expert"),

    # Numbered lists (often contain actionable advice)
    (r"(?:\d+[\.\)]\s*)([A-Z][^.!?]+[.!?])", "list_item"),
]


def _safe_cache_key(domain: str) -> str:
    """Create a filesystem-safe cache key from a domain name."""
    raw = str(domain or "").strip().lower()
    if not raw:
        return "domain"
    key = re.sub(r"[^a-z0-9._-]+", "_", raw)
    key = key.strip("._-")
    return key or "domain"


def _unique_preserve_order(items: List[str], *, limit: int) -> List[str]:
    """Return first-seen unique strings in deterministic order."""
    seen = set()
    out: List[str] = []
    for item in items:
        text = re.sub(r"\s+", " ", str(item or "").strip())
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
        if len(out) >= max(0, int(limit)):
            break
    return out


class WebResearcher:
    """Conduct web research for domain mastery."""

    def __init__(self, search_function=None):
        """
        Initialize with optional custom search function.

        search_function should be async and take (query: str) -> List[Dict]
        where each dict has: title, snippet, url
        """
        self._search = search_function
        self._cache: Dict[str, DomainResearch] = {}
        self._load_cache()

    def _load_cache(self):
        """Load cached research results."""
        if RESEARCH_CACHE.exists():
            for path in RESEARCH_CACHE.glob("*.json"):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        research = DomainResearch.from_dict(data)
                        self._cache[research.domain] = research
                except Exception as e:
                    log.warning(f"Failed to load research cache {path}: {e}")

    def _save_research(self, research: DomainResearch):
        """Save research to cache."""
        try:
            RESEARCH_CACHE.mkdir(parents=True, exist_ok=True)
            path = RESEARCH_CACHE / f"{_safe_cache_key(research.domain)}.json"
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(research.to_dict(), f, indent=2)
        except Exception as e:
            log.error(f"Failed to save research: {e}")

    def get_cached_research(self, domain: str) -> Optional[DomainResearch]:
        """Get cached research for a domain."""
        return self._cache.get(domain)

    def generate_queries(self, domain: str, purposes: List[str] = None) -> List[ResearchQuery]:
        """Generate research queries for a domain."""
        if purposes is None:
            purposes = ["best_practices", "anti_patterns", "expert_insights"]

        current_year = datetime.now().year
        queries = []
        for purpose in purposes:
            templates = QUERY_TEMPLATES.get(purpose, [])
            for template in templates[:2]:  # Limit to 2 per purpose
                query = template.format(domain=domain, year=current_year)
                queries.append(ResearchQuery(
                    query=query,
                    purpose=purpose,
                    domain=domain,
                    timestamp=datetime.now().isoformat(),
                ))

        return queries

    def extract_insights(self, text: str) -> Dict[str, List[str]]:
        """Extract insights from research text."""
        insights = {
            "best_practices": [],
            "anti_patterns": [],
            "expert_insights": [],
            "list_items": [],
        }

        text_clean = re.sub(r'\s+', ' ', text)

        for pattern, category in INSIGHT_PATTERNS:
            matches = re.findall(pattern, text_clean, re.IGNORECASE)
            for match in matches:
                insight = match.strip()
                if len(insight) > 20 and len(insight) < 300:
                    if category == "best_practice":
                        insights["best_practices"].append(insight)
                    elif category == "anti_pattern":
                        insights["anti_patterns"].append(insight)
                    elif category == "expert":
                        insights["expert_insights"].append(insight)
                    elif category == "list_item":
                        insights["list_items"].append(insight)

        return insights

    def process_search_results(self, results: List[Dict], purpose: str) -> List[ResearchResult]:
        """Process raw search results into structured data."""
        processed = []

        for result in results:
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            url = result.get("url", "")

            # Extract insights from snippet
            insights = self.extract_insights(snippet)
            extracted = []
            if purpose == "best_practices":
                extracted = insights["best_practices"] + insights["list_items"][:2]
            elif purpose == "anti_patterns":
                extracted = insights["anti_patterns"]
            elif purpose == "expert_insights":
                extracted = insights["expert_insights"]
            else:
                extracted = insights["list_items"]

            # Determine source type
            source = "web"
            url_lower = url.lower()
            if "stackoverflow" in url_lower:
                source = "stackoverflow"
            elif "github" in url_lower:
                source = "github"
            elif "medium" in url_lower:
                source = "medium"
            elif any(x in url_lower for x in ["dev.to", "hashnode", "blog"]):
                source = "blog"

            processed.append(ResearchResult(
                title=title,
                snippet=snippet[:500],
                url=url,
                source=source,
                extracted_insights=extracted,
            ))

        return processed

    async def research_domain_async(
        self,
        domain: str,
        purposes: List[str] = None,
        max_queries: int = 6,
    ) -> DomainResearch:
        """
        Conduct web research for a domain (async version).

        Requires a search function to be set.
        """
        if not self._search:
            log.warning("No search function configured")
            return self._create_placeholder(domain)

        queries = self.generate_queries(domain, purposes)[:max_queries]

        all_results = []
        all_insights = {
            "best_practices": [],
            "anti_patterns": [],
            "expert_insights": [],
            "common_mistakes": [],
            "key_concepts": [],
        }

        for query in queries:
            try:
                raw_results = await self._search(query.query)
                processed = self.process_search_results(raw_results, query.purpose)
                all_results.extend(processed)

                # Collect insights by purpose
                for result in processed:
                    target_list = all_insights.get(query.purpose, all_insights["key_concepts"])
                    target_list.extend(result.extracted_insights)

            except Exception as e:
                log.warning(f"Research query failed: {query.query}: {e}")

        # Deduplicate insights
        for key in all_insights:
            all_insights[key] = _unique_preserve_order(all_insights[key], limit=10)

        research = DomainResearch(
            domain=domain,
            queries_run=queries,
            results=all_results,
            best_practices=all_insights["best_practices"],
            anti_patterns=all_insights["anti_patterns"],
            expert_insights=all_insights["expert_insights"],
            common_mistakes=all_insights["common_mistakes"],
            key_concepts=all_insights["key_concepts"],
            researched_at=datetime.now().isoformat(),
            total_sources=len(set(r.url for r in all_results)),
            confidence=min(0.9, 0.3 + len(all_results) * 0.05),
        )

        self._cache[domain] = research
        self._save_research(research)

        log.info(f"Researched {domain}: {len(all_results)} results, {sum(len(v) for v in all_insights.values())} insights")
        return research

    def research_domain_sync(
        self,
        domain: str,
        search_results: List[Dict],
        purpose: str = "best_practices",
    ) -> DomainResearch:
        """
        Process pre-fetched search results (sync version).

        Use this when you've already done the search elsewhere.
        """
        processed = self.process_search_results(search_results, purpose)

        all_insights = {
            "best_practices": [],
            "anti_patterns": [],
            "expert_insights": [],
            "common_mistakes": [],
        }

        for result in processed:
            all_insights[purpose].extend(result.extracted_insights)

        # Deduplicate
        for key in all_insights:
            all_insights[key] = _unique_preserve_order(all_insights[key], limit=10)

        research = self.get_cached_research(domain) or DomainResearch(domain=domain)

        # Update with new findings
        research.results.extend(processed)
        research.best_practices.extend(all_insights["best_practices"])
        research.anti_patterns.extend(all_insights["anti_patterns"])
        research.expert_insights.extend(all_insights["expert_insights"])
        research.common_mistakes.extend(all_insights["common_mistakes"])

        # Deduplicate all
        research.best_practices = _unique_preserve_order(research.best_practices, limit=15)
        research.anti_patterns = _unique_preserve_order(research.anti_patterns, limit=15)
        research.expert_insights = _unique_preserve_order(research.expert_insights, limit=15)
        research.common_mistakes = _unique_preserve_order(research.common_mistakes, limit=15)

        research.researched_at = datetime.now().isoformat()
        research.total_sources = len(set(r.url for r in research.results))

        self._cache[domain] = research
        self._save_research(research)

        return research

    def _create_placeholder(self, domain: str) -> DomainResearch:
        """Create placeholder when no search available."""
        return DomainResearch(
            domain=domain,
            researched_at=datetime.now().isoformat(),
            confidence=0.1,
        )

    def merge_into_mastery(self, research: DomainResearch) -> Dict[str, Any]:
        """
        Merge research results into mastery format.

        Returns data that can be used to update DomainMastery.
        """
        from .mastery import MasteryMarker

        markers = []

        # Create markers from research categories
        if research.best_practices:
            markers.append(MasteryMarker(
                name="Best Practices (Researched)",
                description=f"Best practices for {research.domain} from web research",
                indicators=research.best_practices[:5],
                anti_patterns=research.anti_patterns[:5] if research.anti_patterns else [],
                source=f"Web research ({research.total_sources} sources)",
                confidence=research.confidence,
            ))

        return {
            "markers": markers,
            "core_principles": research.best_practices[:5],
            "common_mistakes": research.common_mistakes + research.anti_patterns[:5],
            "expert_insights": research.expert_insights,
            "sources": [r.url for r in research.results[:10]],
        }


# Singleton researcher
_researcher: Optional[WebResearcher] = None


def get_web_researcher() -> WebResearcher:
    """Get singleton web researcher instance."""
    global _researcher
    if _researcher is None:
        _researcher = WebResearcher()
    return _researcher


def set_search_function(search_fn):
    """Set the search function for web research."""
    global _researcher
    if _researcher is None:
        _researcher = WebResearcher(search_function=search_fn)
    else:
        _researcher._search = search_fn
