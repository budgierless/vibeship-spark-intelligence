"""Distillation refinement loop for advisory readiness.

Improves low-scoring distillation statements using deterministic rewrites:
1) score raw statement
2) elevation transforms
3) structure-driven rewrite
4) component composition
The best-scoring candidate is persisted with advisory quality metadata.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from .distillation_transformer import transform_for_advisory
from .elevation import elevate


def _rank_key(quality: Dict[str, Any]) -> Tuple[int, float, float, float]:
    """Sort key for candidate quality preference."""
    suppressed = bool(quality.get("suppressed", False))
    unified = float(quality.get("unified_score", 0.0) or 0.0)
    actionability = float(quality.get("actionability", 0.0) or 0.0)
    reasoning = float(quality.get("reasoning", 0.0) or 0.0)
    specificity = float(quality.get("specificity", 0.0) or 0.0)
    return (0 if suppressed else 1, unified, actionability + reasoning + specificity, -len(str(quality.get("advisory_text", "") or "")))


def _rewrite_from_structure(structure: Dict[str, Any], fallback: str) -> str:
    condition = str(structure.get("condition") or "").strip()
    action = str(structure.get("action") or "").strip()
    reasoning = str(structure.get("reasoning") or "").strip()
    outcome = str(structure.get("outcome") or "").strip()

    if not action:
        return fallback

    chunks = []
    if condition:
        chunks.append(f"When {condition}: {action}")
    else:
        chunks.append(action[0].upper() + action[1:] if len(action) > 1 else action)

    if reasoning:
        chunks.append(f"because {reasoning}")
    if outcome:
        chunks.append(f"to {outcome}")

    rewritten = " ".join(chunks).strip()
    return rewritten if len(rewritten) >= 20 else fallback


def _compose_from_structure(structure: Dict[str, Any]) -> str:
    condition = str(structure.get("condition") or "").strip()
    action = str(structure.get("action") or "").strip()
    reasoning = str(structure.get("reasoning") or "").strip()
    outcome = str(structure.get("outcome") or "").strip()

    if not action:
        return ""

    if condition:
        text = f"When {condition}: {action}"
    else:
        text = action[0].upper() + action[1:] if len(action) > 1 else action

    if reasoning:
        text = f"{text} because {reasoning}"
    if outcome:
        text = f"{text} ({outcome})"
    return text.strip()


def refine_distillation(
    statement: str,
    *,
    source: str = "eidos",
    context: Optional[Dict[str, Any]] = None,
    min_unified_score: float = 0.60,
) -> Tuple[str, Dict[str, Any]]:
    """Refine a distillation statement and return best text + advisory quality."""
    base = (statement or "").strip()
    if not base:
        aq = transform_for_advisory(base, source=source).to_dict()
        return "", aq

    best_text = base
    best_quality = transform_for_advisory(best_text, source=source).to_dict()

    def consider(candidate_text: str) -> None:
        nonlocal best_text, best_quality
        candidate = (candidate_text or "").strip()
        if not candidate:
            return
        quality = transform_for_advisory(candidate, source=source).to_dict()
        if _rank_key(quality) > _rank_key(best_quality):
            best_text = candidate
            best_quality = quality

    if float(best_quality.get("unified_score", 0.0) or 0.0) < min_unified_score:
        elevated = elevate(base, context or {})
        consider(elevated)

    if float(best_quality.get("unified_score", 0.0) or 0.0) < min_unified_score:
        rewrite = _rewrite_from_structure(best_quality.get("structure") or {}, best_text)
        consider(rewrite)

    if float(best_quality.get("unified_score", 0.0) or 0.0) < min_unified_score:
        composed = _compose_from_structure(best_quality.get("structure") or {})
        consider(composed)

    return best_text, best_quality
