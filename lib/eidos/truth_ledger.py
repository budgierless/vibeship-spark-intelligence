"""
EIDOS Truth Ledger: Prevents Hallucinated Learning

The strict distinction between:
- CLAIMS (unverified) - things we believe but haven't proven
- FACTS (validated) - things we've proven with evidence
- RULES (distilled) - generalizations from multiple facts

Every memory artifact has:
- evidence_level: none | weak | strong
- evidence_ref: step IDs / test output hash / artifact ID

RULE: Only FACTS and RULES with strong evidence can be used for high-impact actions.

This prevents the system from "learning" things it never proved.
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .store import get_store


class EvidenceLevel(Enum):
    """Evidence strength for claims/facts/rules."""
    NONE = "none"           # No evidence, pure claim
    WEAK = "weak"           # Some evidence, not conclusive
    STRONG = "strong"       # Multiple corroborating evidence points


class TruthStatus(Enum):
    """The status of a truth entry."""
    CLAIM = "claim"         # Unverified belief
    FACT = "fact"           # Validated with evidence
    RULE = "rule"           # Generalized from multiple facts
    STALE = "stale"         # Was fact/rule but evidence expired
    CONTRADICTED = "contradicted"  # Evidence now contradicts


@dataclass
class EvidenceRef:
    """Reference to evidence supporting a truth."""
    ref_type: str           # "step", "test", "artifact", "manual"
    ref_id: str             # The ID of the evidence
    ref_hash: str = ""      # Hash of evidence content (for integrity)
    timestamp: float = field(default_factory=time.time)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ref_type": self.ref_type,
            "ref_id": self.ref_id,
            "ref_hash": self.ref_hash,
            "timestamp": self.timestamp,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceRef":
        return cls(
            ref_type=data["ref_type"],
            ref_id=data["ref_id"],
            ref_hash=data.get("ref_hash", ""),
            timestamp=data.get("timestamp", time.time()),
            description=data.get("description", ""),
        )


@dataclass
class TruthEntry:
    """
    An entry in the Truth Ledger.

    Can be a CLAIM, FACT, or RULE with associated evidence.
    """
    truth_id: str
    statement: str
    status: TruthStatus = TruthStatus.CLAIM
    evidence_level: EvidenceLevel = EvidenceLevel.NONE

    # Evidence references
    evidence_refs: List[EvidenceRef] = field(default_factory=list)

    # Source tracking
    source_distillation_id: Optional[str] = None
    source_step_ids: List[str] = field(default_factory=list)

    # Validation tracking
    times_validated: int = 0
    times_contradicted: int = 0
    last_validated: Optional[float] = None

    # Decay and revalidation
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    revalidate_by: Optional[float] = None

    # Domain
    domains: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.truth_id:
            self.truth_id = self._generate_id()

    def _generate_id(self) -> str:
        key = f"{self.statement[:50]}:{self.created_at}"
        return f"truth_{hashlib.md5(key.encode()).hexdigest()[:10]}"

    @property
    def is_trustworthy(self) -> bool:
        """Can this be used for high-impact decisions?"""
        if self.status == TruthStatus.CONTRADICTED:
            return False
        if self.status == TruthStatus.STALE:
            return False
        if self.status == TruthStatus.CLAIM:
            return False
        return self.evidence_level in (EvidenceLevel.STRONG, EvidenceLevel.WEAK)

    @property
    def is_high_confidence(self) -> bool:
        """Can this be used without warning?"""
        return (
            self.status in (TruthStatus.FACT, TruthStatus.RULE) and
            self.evidence_level == EvidenceLevel.STRONG and
            not self.is_expired
        )

    @property
    def is_expired(self) -> bool:
        """Has this truth expired?"""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    @property
    def needs_revalidation(self) -> bool:
        """Does this need revalidation?"""
        if self.revalidate_by is None:
            return False
        return time.time() > self.revalidate_by

    def add_evidence(self, ref: EvidenceRef):
        """Add evidence and update evidence level."""
        self.evidence_refs.append(ref)
        self._recalculate_evidence_level()

    def _recalculate_evidence_level(self):
        """Recalculate evidence level based on refs."""
        if not self.evidence_refs:
            self.evidence_level = EvidenceLevel.NONE
        elif len(self.evidence_refs) >= 3:
            self.evidence_level = EvidenceLevel.STRONG
        else:
            self.evidence_level = EvidenceLevel.WEAK

    def validate(self, evidence_ref: Optional[EvidenceRef] = None):
        """Record a validation."""
        self.times_validated += 1
        self.last_validated = time.time()

        if evidence_ref:
            self.add_evidence(evidence_ref)

        # Promote from CLAIM to FACT if enough evidence
        if self.status == TruthStatus.CLAIM:
            if self.evidence_level in (EvidenceLevel.WEAK, EvidenceLevel.STRONG):
                self.status = TruthStatus.FACT

        # Remove STALE status on revalidation
        if self.status == TruthStatus.STALE:
            self.status = TruthStatus.FACT

    def contradict(self, evidence_ref: Optional[EvidenceRef] = None):
        """Record a contradiction."""
        self.times_contradicted += 1

        if evidence_ref:
            self.add_evidence(evidence_ref)

        # Mark as contradicted if contradictions outweigh validations
        if self.times_contradicted > self.times_validated:
            self.status = TruthStatus.CONTRADICTED

    def mark_stale(self):
        """Mark as stale (needs revalidation)."""
        if self.status in (TruthStatus.FACT, TruthStatus.RULE):
            self.status = TruthStatus.STALE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "truth_id": self.truth_id,
            "statement": self.statement,
            "status": self.status.value,
            "evidence_level": self.evidence_level.value,
            "evidence_refs": [e.to_dict() for e in self.evidence_refs],
            "source_distillation_id": self.source_distillation_id,
            "source_step_ids": self.source_step_ids,
            "times_validated": self.times_validated,
            "times_contradicted": self.times_contradicted,
            "last_validated": self.last_validated,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "revalidate_by": self.revalidate_by,
            "domains": self.domains,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TruthEntry":
        return cls(
            truth_id=data["truth_id"],
            statement=data["statement"],
            status=TruthStatus(data.get("status", "claim")),
            evidence_level=EvidenceLevel(data.get("evidence_level", "none")),
            evidence_refs=[EvidenceRef.from_dict(e) for e in data.get("evidence_refs", [])],
            source_distillation_id=data.get("source_distillation_id"),
            source_step_ids=data.get("source_step_ids", []),
            times_validated=data.get("times_validated", 0),
            times_contradicted=data.get("times_contradicted", 0),
            last_validated=data.get("last_validated"),
            created_at=data.get("created_at", time.time()),
            expires_at=data.get("expires_at"),
            revalidate_by=data.get("revalidate_by"),
            domains=data.get("domains", []),
        )


class TruthLedger:
    """
    The Truth Ledger - prevents hallucinated learning.

    Maintains strict separation between claims, facts, and rules.
    Only allows high-confidence truths for high-impact decisions.
    """

    def __init__(self, ledger_path: Optional[Path] = None):
        self.ledger_path = ledger_path or (Path.home() / ".spark" / "truth_ledger.json")
        self.entries: Dict[str, TruthEntry] = {}
        self._load()

    def _load(self):
        """Load ledger from disk."""
        try:
            if self.ledger_path.exists():
                data = json.loads(self.ledger_path.read_text(encoding='utf-8'))
                self.entries = {
                    k: TruthEntry.from_dict(v) for k, v in data.items()
                }
        except Exception:
            self.entries = {}

    def _save(self):
        """Save ledger to disk."""
        try:
            self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
            data = {k: v.to_dict() for k, v in self.entries.items()}
            self.ledger_path.write_text(json.dumps(data, indent=2), encoding='utf-8')
        except Exception:
            pass

    def add_claim(
        self,
        statement: str,
        domains: List[str] = None,
        source_step_ids: List[str] = None
    ) -> TruthEntry:
        """Add an unverified claim."""
        entry = TruthEntry(
            truth_id="",
            statement=statement,
            status=TruthStatus.CLAIM,
            evidence_level=EvidenceLevel.NONE,
            domains=domains or [],
            source_step_ids=source_step_ids or [],
        )
        self.entries[entry.truth_id] = entry
        self._save()
        return entry

    def add_fact(
        self,
        statement: str,
        evidence_refs: List[EvidenceRef],
        domains: List[str] = None,
        source_step_ids: List[str] = None,
        revalidate_days: int = 30
    ) -> TruthEntry:
        """Add a validated fact with evidence."""
        entry = TruthEntry(
            truth_id="",
            statement=statement,
            status=TruthStatus.FACT,
            evidence_refs=evidence_refs,
            domains=domains or [],
            source_step_ids=source_step_ids or [],
            times_validated=1,
            last_validated=time.time(),
            revalidate_by=time.time() + (revalidate_days * 24 * 3600),
        )
        entry._recalculate_evidence_level()
        self.entries[entry.truth_id] = entry
        self._save()
        return entry

    def add_rule(
        self,
        statement: str,
        source_facts: List[str],
        domains: List[str] = None,
        revalidate_days: int = 60
    ) -> TruthEntry:
        """Add a rule generalized from facts."""
        # Gather evidence from source facts
        evidence_refs = []
        for fact_id in source_facts:
            if fact_id in self.entries:
                evidence_refs.append(EvidenceRef(
                    ref_type="fact",
                    ref_id=fact_id,
                    description=f"Derived from: {self.entries[fact_id].statement[:50]}"
                ))

        entry = TruthEntry(
            truth_id="",
            statement=statement,
            status=TruthStatus.RULE,
            evidence_refs=evidence_refs,
            domains=domains or [],
            source_step_ids=source_facts,
            times_validated=len(source_facts),
            last_validated=time.time(),
            revalidate_by=time.time() + (revalidate_days * 24 * 3600),
        )
        entry._recalculate_evidence_level()
        self.entries[entry.truth_id] = entry
        self._save()
        return entry

    def validate_entry(self, truth_id: str, evidence_ref: Optional[EvidenceRef] = None):
        """Validate an existing entry."""
        if truth_id in self.entries:
            self.entries[truth_id].validate(evidence_ref)
            self._save()

    def contradict_entry(self, truth_id: str, evidence_ref: Optional[EvidenceRef] = None):
        """Record contradiction for an entry."""
        if truth_id in self.entries:
            self.entries[truth_id].contradict(evidence_ref)
            self._save()

    def get_trustworthy(self, domains: List[str] = None) -> List[TruthEntry]:
        """Get all trustworthy entries for given domains."""
        results = []
        for entry in self.entries.values():
            if not entry.is_trustworthy:
                continue
            if domains:
                if not any(d in entry.domains for d in domains):
                    continue
            results.append(entry)
        return results

    def get_high_confidence(self, domains: List[str] = None) -> List[TruthEntry]:
        """Get only high-confidence entries (safe for high-impact decisions)."""
        results = []
        for entry in self.entries.values():
            if not entry.is_high_confidence:
                continue
            if domains:
                if not any(d in entry.domains for d in domains):
                    continue
            results.append(entry)
        return results

    def get_needing_revalidation(self) -> List[TruthEntry]:
        """Get entries that need revalidation."""
        return [e for e in self.entries.values() if e.needs_revalidation]

    def get_stale(self) -> List[TruthEntry]:
        """Get stale entries."""
        return [e for e in self.entries.values() if e.status == TruthStatus.STALE]

    def run_decay(self):
        """Run decay on all entries - mark expired as stale."""
        for entry in self.entries.values():
            if entry.is_expired and entry.status not in (TruthStatus.STALE, TruthStatus.CONTRADICTED):
                entry.mark_stale()
        self._save()

    def check_before_use(self, truth_id: str, high_impact: bool = False) -> tuple:
        """
        Check if a truth can be used.

        Returns: (allowed, warning_message)
        """
        if truth_id not in self.entries:
            return False, "Truth not found"

        entry = self.entries[truth_id]

        if entry.status == TruthStatus.CONTRADICTED:
            return False, f"CONTRADICTED: {entry.statement[:50]}"

        if high_impact:
            if not entry.is_high_confidence:
                if entry.status == TruthStatus.CLAIM:
                    return False, f"Cannot use unverified CLAIM for high-impact: {entry.statement[:50]}"
                if entry.evidence_level == EvidenceLevel.NONE:
                    return False, f"No evidence for high-impact action: {entry.statement[:50]}"
                if entry.status == TruthStatus.STALE:
                    return False, f"STALE truth needs revalidation: {entry.statement[:50]}"

        if entry.needs_revalidation:
            return True, f"WARNING: Needs revalidation: {entry.statement[:50]}"

        if entry.status == TruthStatus.STALE:
            return True, f"WARNING: STALE - use with caution: {entry.statement[:50]}"

        if entry.status == TruthStatus.CLAIM:
            return True, f"WARNING: Unverified CLAIM: {entry.statement[:50]}"

        return True, ""

    def get_stats(self) -> Dict[str, Any]:
        """Get ledger statistics."""
        claims = len([e for e in self.entries.values() if e.status == TruthStatus.CLAIM])
        facts = len([e for e in self.entries.values() if e.status == TruthStatus.FACT])
        rules = len([e for e in self.entries.values() if e.status == TruthStatus.RULE])
        stale = len(self.get_stale())
        needs_revalidation = len(self.get_needing_revalidation())
        high_confidence = len(self.get_high_confidence())

        return {
            "total": len(self.entries),
            "claims": claims,
            "facts": facts,
            "rules": rules,
            "stale": stale,
            "needs_revalidation": needs_revalidation,
            "high_confidence": high_confidence,
            "trustworthy": len(self.get_trustworthy()),
        }


# Singleton
_truth_ledger = None


def get_truth_ledger() -> TruthLedger:
    """Get singleton truth ledger."""
    global _truth_ledger
    if _truth_ledger is None:
        _truth_ledger = TruthLedger()
    return _truth_ledger
