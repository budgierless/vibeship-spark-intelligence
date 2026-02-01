"""
Project Onboarding System

Asks questions at project start to understand context,
then continuously refines understanding during sessions.
"""

from .detector import ProjectDetector, is_new_project
from .questions import OnboardingQuestions, Question
from .context import ProjectContext, get_or_create_context, save_context

__all__ = [
    'ProjectDetector',
    'is_new_project',
    'OnboardingQuestions',
    'Question',
    'ProjectContext',
    'get_or_create_context',
    'save_context',
]
