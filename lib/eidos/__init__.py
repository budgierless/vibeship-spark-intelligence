"""
EIDOS: Explicit Intelligence with Durable Outcomes & Semantics

The self-evolving intelligence system that forces learning through:
- Mandatory decision packets (not just logs)
- Prediction → Outcome → Evaluation loops
- Memory binding (retrieval is required, not optional)
- Distillation (experience → reusable rules)
- Control plane (watchers, phases, budgets)

The Six Layers:
0. Evidence Store - Ephemeral audit trail (NEW)
1. Canonical Memory (SQLite) - Source of truth
2. Semantic Index - Embeddings for retrieval
3. Control Plane - Deterministic enforcement
4. Reasoning Engine - LLM (constrained by Control Plane)
5. Distillation Engine - Post-episode rule extraction

The Vertical Loop:
Action → Prediction → Outcome → Evaluation → Policy Update → Distillation → Mandatory Reuse

Guardrails:
1. Progress Contract
2. Memory Binding
3. Outcome Enforcement
4. Loop Watchers
5. Phase Control
6. Evidence Before Modification (NEW)
"""

from .models import (
    Episode, Step, Distillation, Policy,
    Budget, Phase, Outcome, Evaluation,
    DistillationType, ActionType
)
from .control_plane import (
    ControlPlane, get_control_plane,
    ControlDecision, WatcherAlert,
    WatcherType, BlockType
)
from .memory_gate import (
    MemoryGate, score_step_importance,
    ImportanceScore
)
from .distillation_engine import (
    DistillationEngine, get_distillation_engine,
    ReflectionResult, DistillationCandidate
)
from .store import EidosStore, get_store

# New components
from .guardrails import (
    GuardrailEngine, GuardrailResult,
    EvidenceBeforeModificationGuard, PhaseViolationGuard,
    ViolationType, PHASE_ALLOWED_ACTIONS
)
from .evidence_store import (
    EvidenceStore, Evidence, EvidenceType,
    get_evidence_store, create_evidence_from_tool,
    RETENTION_POLICY
)
from .escalation import (
    Escalation, EscalationType, RequestType,
    EscalationBuilder, build_escalation,
    Attempt, EvidenceGathered, MinimalReproduction, SuggestedOption
)
from .validation import (
    ValidationMethod, ValidationResult, DeferredValidation,
    DeferredValidationTracker, get_deferred_tracker,
    validate_step, is_positive_validation, is_negative_validation,
    DEFERRAL_LIMITS
)
from .metrics import (
    MetricsCalculator, get_metrics_calculator,
    CompoundingMetrics, ReuseMetrics, EffectivenessMetrics,
    LoopMetrics, DistillationMetrics, WeeklyReport
)
from .migration import (
    migrate_cognitive_insights, archive_patterns,
    migrate_user_policies, run_full_migration,
    validate_migration, MigrationStats
)

# Elevated Control Layer (v1)
from .elevated_control import (
    ElevatedControlPlane, get_elevated_control_plane,
    WatcherEngine, WatcherAlert, WatcherType, WatcherSeverity,
    EscapeProtocol, EscapeProtocolResult,
    StateMachine, validate_step_envelope, StepEnvelopeValidation,
    ControlMetrics, calculate_control_metrics,
)
from .models import VALID_TRANSITIONS

# Truth Ledger (prevents hallucinated learning)
from .truth_ledger import (
    TruthLedger, get_truth_ledger,
    TruthEntry, TruthStatus, EvidenceLevel, EvidenceRef,
)

# Acceptance Compiler (Definition of Done)
from .acceptance_compiler import (
    AcceptanceCompiler, get_acceptance_compiler,
    AcceptancePlan, AcceptanceTest, AcceptanceType, AcceptanceStatus,
)

# Policy Patches (explicit behavior change)
from .policy_patches import (
    PolicyPatchEngine, get_policy_patch_engine,
    PolicyPatch, PatchTrigger, PatchAction, PatchResult,
)

# Minimal Mode (fallback when stuck)
from .minimal_mode import (
    MinimalModeController, get_minimal_mode_controller,
    MinimalModeState, MinimalModeReason,
    MINIMAL_MODE_ALLOWED_TOOLS, MINIMAL_MODE_BASH_PATTERNS,
)

__all__ = [
    # Core Models
    "Episode",
    "Step",
    "Distillation",
    "Policy",
    "Budget",
    "Phase",
    "Outcome",
    "Evaluation",
    "DistillationType",
    "ActionType",

    # Control Plane
    "ControlPlane",
    "get_control_plane",
    "ControlDecision",
    "WatcherAlert",
    "WatcherType",
    "BlockType",

    # Memory Gate
    "MemoryGate",
    "score_step_importance",
    "ImportanceScore",

    # Distillation Engine
    "DistillationEngine",
    "get_distillation_engine",
    "ReflectionResult",
    "DistillationCandidate",

    # Store
    "EidosStore",
    "get_store",

    # Guardrails (NEW)
    "GuardrailEngine",
    "GuardrailResult",
    "EvidenceBeforeModificationGuard",
    "PhaseViolationGuard",
    "ViolationType",
    "PHASE_ALLOWED_ACTIONS",

    # Evidence Store (NEW)
    "EvidenceStore",
    "Evidence",
    "EvidenceType",
    "get_evidence_store",
    "create_evidence_from_tool",
    "RETENTION_POLICY",

    # Escalation (NEW)
    "Escalation",
    "EscalationType",
    "RequestType",
    "EscalationBuilder",
    "build_escalation",
    "Attempt",
    "EvidenceGathered",
    "MinimalReproduction",
    "SuggestedOption",

    # Validation (NEW)
    "ValidationMethod",
    "ValidationResult",
    "DeferredValidation",
    "DeferredValidationTracker",
    "get_deferred_tracker",
    "validate_step",
    "is_positive_validation",
    "is_negative_validation",
    "DEFERRAL_LIMITS",

    # Metrics (NEW)
    "MetricsCalculator",
    "get_metrics_calculator",
    "CompoundingMetrics",
    "ReuseMetrics",
    "EffectivenessMetrics",
    "LoopMetrics",
    "DistillationMetrics",
    "WeeklyReport",

    # Migration (NEW)
    "migrate_cognitive_insights",
    "archive_patterns",
    "migrate_user_policies",
    "run_full_migration",
    "validate_migration",
    "MigrationStats",

    # Elevated Control Layer (v1)
    "ElevatedControlPlane",
    "get_elevated_control_plane",
    "WatcherEngine",
    "WatcherAlert",
    "WatcherType",
    "WatcherSeverity",
    "EscapeProtocol",
    "EscapeProtocolResult",
    "StateMachine",
    "validate_step_envelope",
    "StepEnvelopeValidation",
    "ControlMetrics",
    "calculate_control_metrics",
    "VALID_TRANSITIONS",

    # Truth Ledger
    "TruthLedger",
    "get_truth_ledger",
    "TruthEntry",
    "TruthStatus",
    "EvidenceLevel",
    "EvidenceRef",

    # Acceptance Compiler
    "AcceptanceCompiler",
    "get_acceptance_compiler",
    "AcceptancePlan",
    "AcceptanceTest",
    "AcceptanceType",
    "AcceptanceStatus",

    # Policy Patches
    "PolicyPatchEngine",
    "get_policy_patch_engine",
    "PolicyPatch",
    "PatchTrigger",
    "PatchAction",
    "PatchResult",

    # Minimal Mode
    "MinimalModeController",
    "get_minimal_mode_controller",
    "MinimalModeState",
    "MinimalModeReason",
    "MINIMAL_MODE_ALLOWED_TOOLS",
    "MINIMAL_MODE_BASH_PATTERNS",
]
