"""
Meta-Learning System

The system that learns how to learn better.
Evaluates learning effectiveness and adjusts strategies.
"""

from .evaluator import LearningEvaluator, LearningReport, evaluate_session
from .strategist import LearningStrategist, adjust_strategies
from .reporter import MetaLearningReporter, generate_report

__all__ = [
    'LearningEvaluator',
    'LearningReport',
    'evaluate_session',
    'LearningStrategist',
    'adjust_strategies',
    'MetaLearningReporter',
    'generate_report',
]
