"""
Spark Pattern Detection Layer

Detects meaningful patterns from raw events:
- CorrectionDetector: "no, I meant..." signals
- SentimentDetector: satisfaction/frustration
- RepetitionDetector: same request 3+ times
- SequenceDetector: successful tool patterns
- SemanticIntentDetector: polite redirects and implicit preferences

These feed into CognitiveLearner for insight synthesis.
"""

from .base import PatternDetector, DetectedPattern, PatternType
from .correction import CorrectionDetector
from .sentiment import SentimentDetector
from .repetition import RepetitionDetector
from .sequence import SequenceDetector
from .semantic import SemanticIntentDetector
from .aggregator import PatternAggregator, get_aggregator
from .worker import process_pattern_events

__all__ = [
    "PatternDetector",
    "DetectedPattern",
    "PatternType",
    "CorrectionDetector",
    "SentimentDetector",
    "RepetitionDetector",
    "SequenceDetector",
    "SemanticIntentDetector",
    "PatternAggregator",
    "get_aggregator",
    "process_pattern_events",
]
