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
]
