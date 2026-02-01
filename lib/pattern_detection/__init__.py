"""
Spark Pattern Detection Layer

Detects meaningful patterns from raw events:
- CorrectionDetector: "no, I meant..." signals
- SentimentDetector: satisfaction/frustration
- RepetitionDetector: same request 3+ times
- SemanticIntentDetector: polite redirects and implicit preferences
- WhyDetector: reasoning, causality, and principles (HIGH VALUE)

These feed into CognitiveLearner for insight synthesis.
"""

from .base import PatternDetector, DetectedPattern, PatternType
from .correction import CorrectionDetector
from .sentiment import SentimentDetector
from .repetition import RepetitionDetector
from .semantic import SemanticIntentDetector
from .why import WhyDetector
from .aggregator import PatternAggregator, get_aggregator
from .worker import process_pattern_events, get_pattern_backlog

__all__ = [
    "PatternDetector",
    "DetectedPattern",
    "PatternType",
    "CorrectionDetector",
    "SentimentDetector",
    "RepetitionDetector",
    "SemanticIntentDetector",
    "WhyDetector",
    "PatternAggregator",
    "get_aggregator",
    "process_pattern_events",
    "get_pattern_backlog",
]
