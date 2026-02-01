"""
Outcome System - Track success/failure and link to insights.

Detects outcome signals from events and links them to
recent insights for validation and scoring.
"""

from .signals import OutcomeSignals, detect_outcome, Outcome
from .linker import OutcomeLinker, link_outcomes
from .tracker import OutcomeTracker, get_tracker

__all__ = [
    'OutcomeSignals',
    'detect_outcome',
    'Outcome',
    'OutcomeLinker',
    'link_outcomes',
    'OutcomeTracker',
    'get_tracker',
]
