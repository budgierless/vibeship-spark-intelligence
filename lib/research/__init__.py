"""
Domain Research System

Researches what mastery looks like in a domain BEFORE
trying to learn from observation. Sets intent for learning.

"You can't recognize excellence if you don't know what it looks like."

Now with MULTI-DOMAIN support:
- Projects need success across multiple interconnected domains
- Game = design + tech + art + audio + marketing + business
- SaaS = product + tech + ux + marketing + operations
- Neglecting any critical domain can sink the whole project
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
from .domains import (
    MultiDomainManager,
    ProjectProfile,
    DomainWeight,
    DomainInterconnection,
    DomainHealth,
    get_domain_manager,
    detect_project_domains,
    get_project_health,
)
from .holistic_intents import (
    HolisticIntentSetter,
    HolisticIntent,
    CrossDomainInsight,
    get_holistic_setter,
    set_holistic_intent,
    check_against_all_domains,
    get_project_focus,
)

__all__ = [
    # Mastery
    'MasteryResearcher',
    'MasteryMarker',
    'DomainMastery',
    'research_domain',
    'get_researcher',

    # Intents (single domain)
    'IntentSetter',
    'DomainIntent',
    'set_learning_intent',

    # Web Research
    'WebResearcher',
    'DomainResearch',
    'ResearchResult',
    'get_web_researcher',
    'set_search_function',

    # Multi-Domain (NEW)
    'MultiDomainManager',
    'ProjectProfile',
    'DomainWeight',
    'DomainInterconnection',
    'DomainHealth',
    'get_domain_manager',
    'detect_project_domains',
    'get_project_health',

    # Holistic Intents (NEW)
    'HolisticIntentSetter',
    'HolisticIntent',
    'CrossDomainInsight',
    'get_holistic_setter',
    'set_holistic_intent',
    'check_against_all_domains',
    'get_project_focus',
]
