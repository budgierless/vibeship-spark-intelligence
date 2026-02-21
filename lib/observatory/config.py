"""Observatory configuration — loads from tuneables.json."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

_SPARK_DIR = Path.home() / ".spark"
_DEFAULT_VAULT = str(Path.home() / "Documents" / "Obsidian Vault" / "Spark-Intelligence-Observatory")


@dataclass
class ObservatoryConfig:
    enabled: bool = True
    auto_sync: bool = True
    sync_cooldown_s: int = 120
    vault_dir: str = _DEFAULT_VAULT
    generate_canvas: bool = True
    max_recent_items: int = 20
    # Explorer limits (configurable per data type)
    explore_cognitive_max: int = 200
    explore_distillations_max: int = 200
    explore_episodes_max: int = 100
    explore_verdicts_max: int = 100
    explore_promotions_max: int = 200
    explore_advice_max: int = 200
    explore_routing_max: int = 100
    explore_tuning_max: int = 200
    explore_decisions_max: int = 200
    explore_feedback_max: int = 200


def load_config() -> ObservatoryConfig:
    """Load observatory config from tuneables.json (runtime or versioned)."""
    for p in [_SPARK_DIR / "tuneables.json",
              Path(__file__).resolve().parent.parent.parent / "config" / "tuneables.json"]:
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8-sig"))
                section = data.get("observatory", {})
                if section:
                    return ObservatoryConfig(
                        enabled=section.get("enabled", True),
                        auto_sync=section.get("auto_sync", True),
                        sync_cooldown_s=int(section.get("sync_cooldown_s", 120)),
                        vault_dir=str(section.get("vault_dir", _DEFAULT_VAULT)),
                        generate_canvas=section.get("generate_canvas", True),
                        max_recent_items=int(section.get("max_recent_items", 20)),
                        explore_cognitive_max=int(section.get("explore_cognitive_max", 200)),
                        explore_distillations_max=int(section.get("explore_distillations_max", 200)),
                        explore_episodes_max=int(section.get("explore_episodes_max", 100)),
                        explore_verdicts_max=int(section.get("explore_verdicts_max", 100)),
                        explore_promotions_max=int(section.get("explore_promotions_max", 200)),
                        explore_advice_max=int(section.get("explore_advice_max", 200)),
                        explore_routing_max=int(section.get("explore_routing_max", 100)),
                        explore_tuning_max=int(section.get("explore_tuning_max", 200)),
                        explore_decisions_max=int(section.get("explore_decisions_max", 200)),
                        explore_feedback_max=int(section.get("explore_feedback_max", 200)),
                    )
            except Exception:
                pass
    return ObservatoryConfig()


def spark_dir() -> Path:
    """Return the ~/.spark/ directory."""
    return _SPARK_DIR
