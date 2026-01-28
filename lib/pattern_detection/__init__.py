"""
Spark Pattern Detection Layer

Detects meaningful patterns from raw events:
- CorrectionDetector: "no, I meant..." signals
- SentimentDetector: satisfaction/frustration
- RepetitionDetector: same request 3+ times
- SequenceDetector: successful tool patterns

These feed into CognitiveLearner for insight synthesis.
"""

from .base import PatternDetector, DetectedPattern, PatternType
from .correction import CorrectionDetector
from .sentiment import SentimentDetector
from .repetition import RepetitionDetector
from .sequence import SequenceDetector
from .aggregator import PatternAggregator, get_aggregator

__all__ = [
    "PatternDetector",
    "DetectedPattern",
    "PatternType",
    "CorrectionDetector",
    "SentimentDetector",
    "RepetitionDetector",
    "SequenceDetector",
    "PatternAggregator",
    "get_aggregator",
]
