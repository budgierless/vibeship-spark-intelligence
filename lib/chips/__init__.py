"""
Spark Chips Runtime - Domain-Specific Intelligence

The missing piece: turns chip YAML specs into actual learning.

What didn't work before:
- Chips were just YAML files sitting in a folder
- No runtime to load, match triggers, or capture insights
- Generic pattern detection only captured tool sequences
- Domain knowledge (game dev, marketing, etc.) was never extracted

What this fixes:
- Loader: Parses chip YAML files into usable objects
- Registry: Tracks which chips are active per project
- Router: Matches events to chip triggers
- Runtime: Executes observers and stores domain insights
"""

from .loader import ChipLoader, Chip, ChipObserver
from .registry import ChipRegistry, get_registry
from .router import ChipRouter, TriggerMatch, get_router
from .runtime import ChipRuntime, process_chip_events, get_runtime
from .runner import ChipRunner
from .store import get_chip_store

__all__ = [
    'ChipLoader', 'Chip', 'ChipObserver',
    'ChipRegistry', 'get_registry',
    'ChipRouter', 'TriggerMatch', 'get_router',
    'ChipRuntime', 'process_chip_events', 'get_runtime',
    'get_chip_store',
    'ChipRunner'
]
