"""
Spark Research Integration

Provides commands for Spark/Claude to research domains
and enrich mastery definitions with web knowledge.

Usage in Claude:
    1. User asks about a domain
    2. Claude searches the web for best practices
    3. Results are passed to process_research_results()
    4. Mastery definition is enriched
    5. Intent is set for learning
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .mastery import get_researcher, DomainMastery
from .web_research import get_web_researcher, QUERY_TEMPLATES
from .intents import set_learning_intent

log = logging.getLogger("spark.research")


def get_research_queries(domain: str, purpose: str = "all") -> List[str]:
    """
    Get research queries for Claude to execute.

    Returns queries that Claude can run with WebSearch.
    """
    queries = []

    if purpose == "all":
        purposes = ["best_practices", "anti_patterns", "expert_insights"]
    else:
        purposes = [purpose]

    for p in purposes:
        templates = QUERY_TEMPLATES.get(p, [])
        for template in templates[:2]:
            queries.append(template.format(domain=domain, year=datetime.now().year))

    return queries


def process_research_results(
    domain: str,
    results: List[Dict],
    purpose: str = "best_practices",
) -> Dict[str, Any]:
    """
    Process web search results from Claude.

    Call this with results from WebSearch tool.

    Args:
        domain: The domain being researched
        results: List of dicts with {title, snippet, url}
        purpose: What kind of research (best_practices, anti_patterns, etc.)

    Returns:
        Dict with extracted insights and updated mastery
    """
    researcher = get_researcher()
    web_researcher = get_web_researcher()

    # Process results
    research = web_researcher.research_domain_sync(domain, results, purpose)

    # Update mastery
    mastery = researcher.research_online(domain, results, purpose=purpose)

    return {
        "domain": domain,
        "purpose": purpose,
        "insights_extracted": {
            "best_practices": research.best_practices,
            "anti_patterns": research.anti_patterns,
            "expert_insights": research.expert_insights,
            "common_mistakes": research.common_mistakes,
        },
        "mastery_updated": True,
        "markers_count": len(mastery.markers),
        "principles_count": len(mastery.core_principles),
        "sources_count": research.total_sources,
    }


def research_and_set_intent(
    domain: str,
    project_path: str,
    search_results: List[Dict] = None,
    purpose: str = "best_practices",
    user_focus: List[str] = None,
) -> Dict[str, Any]:
    """
    Full workflow: research domain and set learning intent.

    1. Research mastery (from built-in or web results)
    2. Set learning intent
    3. Return focus summary

    Args:
        domain: Domain to research
        project_path: Current project path
        search_results: Optional web search results
        user_focus: User-specified focus areas

    Returns:
        Dict with intent summary and research status
    """
    researcher = get_researcher()

    # Research mastery
    if search_results:
        mastery = researcher.research_online(domain, search_results, purpose=purpose)
        research_source = "web"
    else:
        mastery = researcher.research_domain(domain)
        research_source = "built-in" if len(mastery.markers) > 0 else "placeholder"

    # Set learning intent
    intent = set_learning_intent(domain, project_path, user_focus)

    return {
        "domain": domain,
        "research_source": research_source,
        "mastery": {
            "markers": len(mastery.markers),
            "principles": len(mastery.core_principles),
            "anti_patterns": len(mastery.common_mistakes),
        },
        "intent": {
            "watch_for": intent.watch_for[:5],
            "warn_about": intent.warn_about[:5],
            "user_focus": intent.user_focus,
        },
        "ready_for_learning": not mastery.needs_refresh,
    }


def get_mastery_summary(domain: str) -> str:
    """
    Get a markdown summary of mastery for a domain.

    Useful for showing what Spark knows about excellence in a domain.
    """
    researcher = get_researcher()
    mastery = researcher.get_mastery(domain)

    if not mastery:
        return f"No mastery definition for {domain}. Research needed."

    lines = [
        f"# Mastery: {domain}",
        "",
        f"*{mastery.description}*",
        "",
    ]

    if mastery.core_principles:
        lines.extend([
            "## Core Principles",
            "",
        ])
        for principle in mastery.core_principles[:5]:
            lines.append(f"- {principle}")
        lines.append("")

    if mastery.markers:
        lines.extend([
            "## Mastery Markers",
            "",
        ])
        for marker in mastery.markers[:3]:
            lines.append(f"### {marker.name}")
            lines.append(f"*{marker.description}*")
            lines.append("")
            lines.append("**Look for:**")
            for ind in marker.indicators[:3]:
                lines.append(f"- {ind}")
            lines.append("")
            lines.append("**Avoid:**")
            for anti in marker.anti_patterns[:3]:
                lines.append(f"- {anti}")
            lines.append("")

    if mastery.common_mistakes:
        lines.extend([
            "## Common Mistakes",
            "",
        ])
        for mistake in mastery.common_mistakes[:5]:
            lines.append(f"- {mistake}")
        lines.append("")

    if mastery.expert_insights:
        lines.extend([
            "## Expert Insights",
            "",
        ])
        for insight in mastery.expert_insights[:5]:
            lines.append(f"> {insight}")
            lines.append("")

    return "\n".join(lines)


def suggest_research_queries(domain: str) -> Dict[str, List[str]]:
    """
    Suggest research queries for Claude to run.

    Returns queries organized by purpose.
    """
    researcher = get_researcher()
    mastery = researcher.get_mastery(domain)

    # Determine what we need
    needs = []
    if not mastery or mastery.needs_refresh:
        needs = ["best_practices", "anti_patterns", "expert_insights"]
    elif len(mastery.markers) < 3:
        needs = ["best_practices"]
    elif len(mastery.common_mistakes) < 5:
        needs = ["anti_patterns", "common_mistakes"]

    suggestions = {}
    for purpose in needs:
        suggestions[purpose] = get_research_queries(domain, purpose)

    return {
        "domain": domain,
        "needs_research": len(needs) > 0,
        "queries_by_purpose": suggestions,
        "current_mastery": {
            "markers": len(mastery.markers) if mastery else 0,
            "principles": len(mastery.core_principles) if mastery else 0,
        },
    }


# Convenience functions for Spark hooks
def on_domain_detected(domain: str, project_path: str) -> Dict[str, Any]:
    """
    Called when a new domain is detected.

    Returns research suggestions if needed.
    """
    suggestions = suggest_research_queries(domain)

    if suggestions["needs_research"]:
        return {
            "action": "research_suggested",
            "domain": domain,
            "message": f"New domain detected: {domain}. Consider researching best practices.",
            "queries": suggestions["queries_by_purpose"],
        }
    else:
        # Set intent with existing mastery
        intent = set_learning_intent(domain, project_path)
        return {
            "action": "intent_set",
            "domain": domain,
            "message": f"Learning intent set for {domain}",
            "watch_for": intent.watch_for[:3],
        }


def on_research_complete(domain: str, project_path: str, results: List[Dict]) -> Dict[str, Any]:
    """
    Called when web research is complete.

    Processes results and sets learning intent.
    """
    # Process all results
    processed = process_research_results(domain, results, purpose="best_practices")

    # Set intent
    intent = set_learning_intent(domain, project_path)

    return {
        "action": "research_processed",
        "domain": domain,
        "insights": processed["insights_extracted"],
        "intent_set": True,
        "watch_for": intent.watch_for[:5],
        "warn_about": intent.warn_about[:5],
    }
