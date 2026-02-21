#!/usr/bin/env python3
"""Helpers for domain-sliced memory retrieval matrix evaluations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional


def infer_domain(*, query: str, notes: str = "") -> str:
    text = " ".join([query, notes]).lower()
    if not text:
        return "general"
    if any(k in text for k in ("memory", "cache", "retrieval", "index")):
        return "memory"
    if any(k in text for k in ("x", "tweet", "social", "reply", "post", "launch")):
        return "x_social"
    if any(k in text for k in ("code", "api", "debug", "python", "program", "deploy", "refactor")):
        return "coding"
    return "general"


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    query: str
    relevant_insight_keys: Optional[List[str]] = None
    relevant_contains: Optional[List[str]] = None
    notes: str = ""
    domain: Optional[str] = None


class _ModuleAlias:
    EvalCase = EvalCase


mra = _ModuleAlias()


@dataclass(frozen=True)
class DomainCase:
    domain: str
    case: EvalCase


@dataclass(frozen=True)
class DomainGateResult:
    checks: Dict[str, bool]
    all_pass: bool
    domain: str


def group_cases(
    cases: Iterable[DomainCase],
    *,
    min_cases: int,
    allow_domains: Optional[set[str]] = None,
) -> Dict[str, List[DomainCase]]:
    grouped: Dict[str, List[DomainCase]] = {}
    threshold = max(1, int(min_cases))
    for case in cases:
        domain = getattr(case, "domain", "") or "general"
        if allow_domains is not None and domain not in allow_domains:
            continue
        grouped.setdefault(domain, []).append(case)
    return {domain: rows for domain, rows in grouped.items() if len(rows) >= threshold}


def evaluate_domain_gates(summary: Mapping[str, Any], gates: Mapping[str, float]) -> DomainGateResult:
    checks = {
        "mrr_min": float(summary.get("mrr") or 0.0) >= float(gates.get("mrr_min", 0.0)),
        "top1_hit_rate_min": float(summary.get("top1_hit_rate") or 0.0) >= float(gates.get("top1_hit_rate_min", 0.0)),
        "non_empty_rate_min": float(summary.get("non_empty_rate") or 0.0) >= float(gates.get("non_empty_rate_min", 0.0)),
        "error_rate_max": float(summary.get("error_rate") or 0.0) <= float(gates.get("error_rate_max", 1.0)),
    }
    all_pass = all(bool(v) for v in checks.values())
    return DomainGateResult(checks=checks, all_pass=all_pass, domain="")
