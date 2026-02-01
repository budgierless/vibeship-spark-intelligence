"""
Domain Research System

Researches what mastery looks like in a domain BEFORE
trying to learn from observation. Sets intent for learning.

"You can't recognize excellence if you don't know what it looks like."
"""

from .mastery import MasteryResearcher, DomainMastery, MasteryMarker, research_domain, get_researcher
from .intents import IntentSetter, DomainIntent, set_learning_intent
from .web_research import (
    WebResearcher,
    DomainResearch,
    ResearchResult,
    get_web_researcher,
    set_search_function,
)

__all__ = [
    # Mastery
    'MasteryResearcher',
    'MasteryMarker',
    'DomainMastery',
    'research_domain',
    'get_researcher',

    # Intents
    'IntentSetter',
    'DomainIntent',
    'set_learning_intent',

    # Web Research
    'WebResearcher',
    'DomainResearch',
    'ResearchResult',
    'get_web_researcher',
    'set_search_function',
]
