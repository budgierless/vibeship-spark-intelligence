"""
Spark Chips Runtime - Domain-Specific Intelligence

Chips teach Spark how to learn about specific domains:
- Marketing, Sales, Engineering, Operations, etc.
- Each chip defines: triggers, observers, learners, outcomes
- Chips are YAML specs that run without changing core code

Components:
- loader.py: YAML parsing + schema validation
- registry.py: Installed/active chip tracking
- router.py: Event-to-chip trigger matching
- runner.py: Observer execution and field extraction
- store.py: Per-chip insight storage
"""

from .loader import ChipLoader, ChipSpec, QuestionSpec, load_chip
from .registry import ChipRegistry, get_registry
from .router import ChipRouter, get_router
from .runner import ChipRunner
from .store import ChipStore, get_chip_store

__all__ = [
    "ChipLoader",
    "ChipSpec",
    "QuestionSpec",
    "load_chip",
    "ChipRegistry",
    "get_registry",
    "ChipRouter",
    "get_router",
    "ChipRunner",
    "ChipStore",
    "get_chip_store",
]
