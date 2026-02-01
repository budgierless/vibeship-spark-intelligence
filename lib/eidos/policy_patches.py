"""
EIDOS Policy Patches: Explicit Behavior Change

Turns learning into control, not just knowledge.

Every validated distillation should propose either:
- a new playbook step
- a sharp edge block
- or a policy patch

A policy patch is:
"When condition X, force behavior Y"

This ensures distillations actually CHANGE future behavior.
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .models import Phase, Episode, Step


class PatchTrigger(Enum):
    """What triggers a policy patch."""
    ERROR_COUNT = "error_count"         # After N errors
    PHASE_ENTRY = "phase_entry"         # When entering a phase
    TOOL_USE = "tool_use"               # When using a specific tool
    FILE_TOUCH = "file_touch"           # When touching a file
    CONFIDENCE_DROP = "confidence_drop" # When confidence drops
    PATTERN_MATCH = "pattern_match"     # When pattern detected
    TIME_ELAPSED = "time_elapsed"       # After N seconds
    STEP_COUNT = "step_count"           # After N steps


class PatchAction(Enum):
    """What action a patch enforces."""
    FORCE_PHASE = "force_phase"         # Force transition to phase
    BLOCK_TOOL = "block_tool"           # Block a tool
    BLOCK_FILE = "block_file"           # Block file modification
    REQUIRE_STEP = "require_step"       # Require a specific step type
    ADD_CONSTRAINT = "add_constraint"   # Add constraint to episode
    EMIT_WARNING = "emit_warning"       # Emit a warning
    FORCE_VALIDATION = "force_validation"  # Force validation step


@dataclass
class PolicyPatch:
    """
    A policy patch - explicit behavior change.

    "When condition X, force behavior Y"
    """
    patch_id: str
    name: str
    description: str

    # Trigger
    trigger_type: PatchTrigger
    trigger_condition: Dict[str, Any]  # Condition parameters

    # Action
    action_type: PatchAction
    action_params: Dict[str, Any]  # Action parameters

    # Source
    source_distillation_id: Optional[str] = None
    source_episode_id: Optional[str] = None

    # Status
    enabled: bool = True
    times_triggered: int = 0
    times_helped: int = 0
    last_triggered: Optional[float] = None

    # Metadata
    priority: int = 50  # Higher = checked first
    created_at: float = field(default_factory=time.time)

    def __post_init__(self):
        if not self.patch_id:
            self.patch_id = self._generate_id()

    def _generate_id(self) -> str:
        key = f"{self.name}:{self.trigger_type.value}:{self.created_at}"
        return f"patch_{hashlib.md5(key.encode()).hexdigest()[:8]}"

    @property
    def effectiveness(self) -> float:
        """How effective is this patch?"""
        if self.times_triggered == 0:
            return 0.5
        return self.times_helped / self.times_triggered

    def to_dict(self) -> Dict[str, Any]:
        return {
            "patch_id": self.patch_id,
            "name": self.name,
            "description": self.description,
            "trigger_type": self.trigger_type.value,
            "trigger_condition": self.trigger_condition,
            "action_type": self.action_type.value,
            "action_params": self.action_params,
            "source_distillation_id": self.source_distillation_id,
            "source_episode_id": self.source_episode_id,
            "enabled": self.enabled,
            "times_triggered": self.times_triggered,
            "times_helped": self.times_helped,
            "last_triggered": self.last_triggered,
            "priority": self.priority,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PolicyPatch":
        return cls(
            patch_id=data["patch_id"],
            name=data["name"],
            description=data["description"],
            trigger_type=PatchTrigger(data["trigger_type"]),
            trigger_condition=data["trigger_condition"],
            action_type=PatchAction(data["action_type"]),
            action_params=data["action_params"],
            source_distillation_id=data.get("source_distillation_id"),
            source_episode_id=data.get("source_episode_id"),
            enabled=data.get("enabled", True),
            times_triggered=data.get("times_triggered", 0),
            times_helped=data.get("times_helped", 0),
            last_triggered=data.get("last_triggered"),
            priority=data.get("priority", 50),
            created_at=data.get("created_at", time.time()),
        )


@dataclass
class PatchResult:
    """Result of evaluating a patch."""
    triggered: bool = False
    patch_id: str = ""
    action_type: Optional[PatchAction] = None
    action_params: Dict[str, Any] = field(default_factory=dict)
    message: str = ""


class PolicyPatchEngine:
    """
    Engine for managing and evaluating policy patches.

    Ensures distillations turn into actual behavior changes.
    """

    def __init__(self):
        self.patches: Dict[str, PolicyPatch] = {}
        self._load()
        self._init_default_patches()

    def _get_patches_path(self) -> Path:
        return Path.home() / ".spark" / "policy_patches.json"

    def _load(self):
        """Load patches from disk."""
        try:
            path = self._get_patches_path()
            if path.exists():
                data = json.loads(path.read_text(encoding='utf-8'))
                self.patches = {k: PolicyPatch.from_dict(v) for k, v in data.items()}
        except Exception:
            self.patches = {}

    def _save(self):
        """Save patches to disk."""
        try:
            path = self._get_patches_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            data = {k: v.to_dict() for k, v in self.patches.items()}
            path.write_text(json.dumps(data, indent=2), encoding='utf-8')
        except Exception:
            pass

    def _init_default_patches(self):
        """Initialize default policy patches."""
        defaults = [
            # Two failures = DIAGNOSE
            PolicyPatch(
                patch_id="default_two_failures",
                name="Two Failures Rule",
                description="After 2 failures on same error, force DIAGNOSE and freeze edits",
                trigger_type=PatchTrigger.ERROR_COUNT,
                trigger_condition={"threshold": 2, "same_signature": True},
                action_type=PatchAction.FORCE_PHASE,
                action_params={"phase": "diagnose", "freeze_edits": True},
                priority=90,
            ),
            # File touched 3x = freeze
            PolicyPatch(
                patch_id="default_file_thrash",
                name="File Thrash Prevention",
                description="After modifying same file 3x, block further modifications",
                trigger_type=PatchTrigger.FILE_TOUCH,
                trigger_condition={"threshold": 3},
                action_type=PatchAction.BLOCK_FILE,
                action_params={},
                priority=85,
            ),
            # Confidence drop = warning
            PolicyPatch(
                patch_id="default_confidence_drop",
                name="Confidence Drop Warning",
                description="Emit warning when confidence drops significantly",
                trigger_type=PatchTrigger.CONFIDENCE_DROP,
                trigger_condition={"threshold": 0.2},
                action_type=PatchAction.EMIT_WARNING,
                action_params={"message": "Confidence dropped significantly - consider changing approach"},
                priority=50,
            ),
            # Budget half = require validation
            PolicyPatch(
                patch_id="default_budget_half",
                name="Budget Half Validation",
                description="When budget 50% used, require validation before more execution",
                trigger_type=PatchTrigger.STEP_COUNT,
                trigger_condition={"percentage": 0.5},
                action_type=PatchAction.FORCE_VALIDATION,
                action_params={},
                priority=70,
            ),
        ]

        for patch in defaults:
            if patch.patch_id not in self.patches:
                self.patches[patch.patch_id] = patch

        self._save()

    def add_patch(self, patch: PolicyPatch):
        """Add a new policy patch."""
        self.patches[patch.patch_id] = patch
        self._save()

    def remove_patch(self, patch_id: str):
        """Remove a policy patch."""
        if patch_id in self.patches:
            del self.patches[patch_id]
            self._save()

    def enable_patch(self, patch_id: str):
        """Enable a patch."""
        if patch_id in self.patches:
            self.patches[patch_id].enabled = True
            self._save()

    def disable_patch(self, patch_id: str):
        """Disable a patch."""
        if patch_id in self.patches:
            self.patches[patch_id].enabled = False
            self._save()

    def evaluate(
        self,
        episode: Episode,
        step: Optional[Step] = None,
        context: Dict[str, Any] = None
    ) -> List[PatchResult]:
        """
        Evaluate all patches against current state.

        Returns list of triggered patch results.
        """
        results = []
        context = context or {}

        # Sort by priority (highest first)
        sorted_patches = sorted(
            [p for p in self.patches.values() if p.enabled],
            key=lambda p: p.priority,
            reverse=True
        )

        for patch in sorted_patches:
            result = self._evaluate_patch(patch, episode, step, context)
            if result.triggered:
                results.append(result)
                # Record trigger
                patch.times_triggered += 1
                patch.last_triggered = time.time()

        self._save()
        return results

    def _evaluate_patch(
        self,
        patch: PolicyPatch,
        episode: Episode,
        step: Optional[Step],
        context: Dict[str, Any]
    ) -> PatchResult:
        """Evaluate a single patch."""
        triggered = False
        cond = patch.trigger_condition

        if patch.trigger_type == PatchTrigger.ERROR_COUNT:
            threshold = cond.get("threshold", 2)
            same_sig = cond.get("same_signature", False)
            if same_sig:
                triggered = any(c >= threshold for c in episode.error_counts.values())
            else:
                triggered = sum(episode.error_counts.values()) >= threshold

        elif patch.trigger_type == PatchTrigger.FILE_TOUCH:
            threshold = cond.get("threshold", 3)
            triggered = any(c >= threshold for c in episode.file_touch_counts.values())

        elif patch.trigger_type == PatchTrigger.CONFIDENCE_DROP:
            threshold = cond.get("threshold", 0.2)
            if step and len(episode.confidence_history) > 0:
                last_conf = episode.confidence_history[-1] if episode.confidence_history else 0.5
                triggered = (last_conf - step.confidence_after) >= threshold

        elif patch.trigger_type == PatchTrigger.STEP_COUNT:
            percentage = cond.get("percentage", 0.5)
            triggered = episode.budget_percentage_used() >= percentage

        elif patch.trigger_type == PatchTrigger.PHASE_ENTRY:
            target_phase = cond.get("phase", "")
            triggered = episode.phase.value == target_phase

        elif patch.trigger_type == PatchTrigger.TOOL_USE:
            tool_name = cond.get("tool", "")
            if step:
                triggered = step.action_details.get("tool") == tool_name

        if triggered:
            return PatchResult(
                triggered=True,
                patch_id=patch.patch_id,
                action_type=patch.action_type,
                action_params=patch.action_params,
                message=patch.description,
            )

        return PatchResult(triggered=False)

    def record_effectiveness(self, patch_id: str, helped: bool):
        """Record whether a triggered patch helped."""
        if patch_id in self.patches:
            if helped:
                self.patches[patch_id].times_helped += 1
            self._save()

    def create_from_distillation(
        self,
        statement: str,
        distillation_id: str,
        distillation_type: str
    ) -> Optional[PolicyPatch]:
        """
        Create a policy patch from a distillation.

        Analyzes the distillation to determine appropriate trigger and action.
        """
        statement_lower = statement.lower()

        # Pattern: "After X failures..." or "When error occurs..."
        if "fail" in statement_lower or "error" in statement_lower:
            return PolicyPatch(
                patch_id="",
                name=f"From: {statement[:30]}",
                description=statement,
                trigger_type=PatchTrigger.ERROR_COUNT,
                trigger_condition={"threshold": 2, "same_signature": True},
                action_type=PatchAction.FORCE_PHASE,
                action_params={"phase": "diagnose"},
                source_distillation_id=distillation_id,
                priority=60,
            )

        # Pattern: "Always X before Y" or "Never X without Y"
        if "always" in statement_lower or "never" in statement_lower:
            return PolicyPatch(
                patch_id="",
                name=f"From: {statement[:30]}",
                description=statement,
                trigger_type=PatchTrigger.PATTERN_MATCH,
                trigger_condition={"pattern": statement[:50]},
                action_type=PatchAction.EMIT_WARNING,
                action_params={"message": statement},
                source_distillation_id=distillation_id,
                priority=50,
            )

        # Pattern: "When stuck..." or "If not progressing..."
        if "stuck" in statement_lower or "progress" in statement_lower:
            return PolicyPatch(
                patch_id="",
                name=f"From: {statement[:30]}",
                description=statement,
                trigger_type=PatchTrigger.CONFIDENCE_DROP,
                trigger_condition={"threshold": 0.1},
                action_type=PatchAction.FORCE_PHASE,
                action_params={"phase": "simplify"},
                source_distillation_id=distillation_id,
                priority=55,
            )

        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get patch statistics."""
        enabled = len([p for p in self.patches.values() if p.enabled])
        total_triggers = sum(p.times_triggered for p in self.patches.values())
        total_helped = sum(p.times_helped for p in self.patches.values())

        return {
            "total_patches": len(self.patches),
            "enabled": enabled,
            "disabled": len(self.patches) - enabled,
            "total_triggers": total_triggers,
            "total_helped": total_helped,
            "effectiveness": total_helped / total_triggers if total_triggers > 0 else 0,
        }


# Singleton
_policy_patch_engine = None


def get_policy_patch_engine() -> PolicyPatchEngine:
    """Get singleton policy patch engine."""
    global _policy_patch_engine
    if _policy_patch_engine is None:
        _policy_patch_engine = PolicyPatchEngine()
    return _policy_patch_engine
