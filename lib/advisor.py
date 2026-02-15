"""
Spark Advisor: The Missing Link Between Learning and Action

This module closes the critical gap in Spark's architecture:
  Storage → Analysis → [ADVISOR] → Decision Impact

The Problem:
  - Spark captures insights beautifully (cognitive_learner, aha_tracker)
  - Spark stores them persistently (Mind sync, JSON files)
  - But insights are NEVER USED during actual task execution

The Solution:
  - Advisor queries relevant insights BEFORE actions
  - Advisor tracks whether advice was followed
  - Advisor learns which advice actually helps

KISS Principle: Single file, simple API, maximum impact.
"""

import json
import time
import hashlib
import os
import sys
import re
import math
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field, asdict

# Import existing Spark components
from .cognitive_learner import get_cognitive_learner, CognitiveCategory
from .mind_bridge import get_mind_bridge, HAS_REQUESTS
from .memory_banks import retrieve as bank_retrieve, infer_project_key

# EIDOS integration for distillation retrieval
try:
    from .eidos import get_retriever, StructuralRetriever
    HAS_EIDOS = True
except ImportError:
    HAS_EIDOS = False
    get_retriever = None
    StructuralRetriever = None


# ============= Configuration =============
ADVISOR_DIR = Path.home() / ".spark" / "advisor"
ADVICE_LOG = ADVISOR_DIR / "advice_log.jsonl"
EFFECTIVENESS_FILE = ADVISOR_DIR / "effectiveness.json"
ADVISOR_METRICS = ADVISOR_DIR / "metrics.json"
RECENT_ADVICE_LOG = ADVISOR_DIR / "recent_advice.jsonl"
RECENT_ADVICE_MAX_AGE_S = 1200  # 20 min (was 15 min) - Ralph Loop tuning for better acted-on rate
RECENT_ADVICE_MAX_LINES = 200
CHIP_INSIGHTS_DIR = Path.home() / ".spark" / "chip_insights"
CHIP_ADVICE_FILE_TAIL = 40
CHIP_ADVICE_MAX_FILES = 6
CHIP_ADVICE_LIMIT = 4
CHIP_ADVICE_MIN_SCORE = 0.7
CHIP_TELEMETRY_BLOCKLIST = {"spark-core", "bench_core"}
CHIP_TELEMETRY_MARKERS = (
    "post_tool",
    "pre_tool",
    "tool_name:",
    "file_path:",
    "event_type:",
    "user_prompt_signal",
    "status: success",
    "cwd:",
)
RECENT_OUTCOMES_MAX = 5000

# Thresholds (Improvement #8: Advisor Integration tuneables)
# Defaults — overridden by ~/.spark/tuneables.json → "advisor" section at module load.
MIN_RELIABILITY_FOR_ADVICE = 0.5  # Lowered from 0.6 for more advice coverage
MIN_VALIDATIONS_FOR_STRONG_ADVICE = 2
# Default to a wider surface area; ranking/gates should keep quality high.
# Some experiments may tune this lower via config.
MAX_ADVICE_ITEMS = 8
ADVICE_CACHE_TTL_SECONDS = 120  # 2 minutes (lowered from 5 for fresher advice)
MIN_RANK_SCORE = 0.55  # Drop advice below this after ranking — tuned to reduce repeat/noise
MIND_MAX_STALE_SECONDS = float(os.environ.get("SPARK_ADVISOR_MIND_MAX_STALE_S", "0"))
MIND_STALE_ALLOW_IF_EMPTY = os.environ.get("SPARK_ADVISOR_MIND_STALE_ALLOW_IF_EMPTY", "1") != "0"
MIND_MIN_SALIENCE = float(os.environ.get("SPARK_ADVISOR_MIND_MIN_SALIENCE", "0.5"))
RETRIEVAL_ROUTE_LOG = ADVISOR_DIR / "retrieval_router.jsonl"
RETRIEVAL_ROUTE_LOG_MAX = 800

DEFAULT_RETRIEVAL_PROFILES: Dict[str, Dict[str, Any]] = {
    "1": {
        "profile": "local_free",
        "mode": "auto",  # auto | embeddings_only | hybrid_agentic
        "gate_strategy": "minimal",  # minimal | extended
        "semantic_limit": 8,
        "max_queries": 2,
        "agentic_query_limit": 2,
        "agentic_deadline_ms": 500,
        "agentic_rate_limit": 0.10,
        "agentic_rate_window": 50,
        "fast_path_budget_ms": 250,
        # Latency-tail guard: if primary semantic retrieval already exceeded budget, do not add
        # additional agentic facet queries (unless high-risk terms are present).
        "deny_escalation_when_over_budget": True,
        "prefilter_enabled": True,
        "prefilter_max_insights": 300,
        "lexical_weight": 0.25,
        "semantic_context_min": 0.15,
        "semantic_lexical_min": 0.03,
        "semantic_strong_override": 0.90,
        "bm25_k1": 1.2,
        "bm25_b": 0.75,
        "bm25_mix": 0.75,  # blend: bm25 vs overlap
        "complexity_threshold": 3,  # used only by extended gate
        "min_results_no_escalation": 3,
        "min_top_score_no_escalation": 0.68,
        "escalate_on_weak_primary": False,
        "escalate_on_high_risk": True,
        "escalate_on_trigger": False,  # ignored by minimal gate
    },
    "2": {
        "profile": "balanced_spend",
        "mode": "auto",
        "gate_strategy": "minimal",
        "semantic_limit": 10,
        "max_queries": 3,
        "agentic_query_limit": 3,
        "agentic_deadline_ms": 700,
        "agentic_rate_limit": 0.20,
        "agentic_rate_window": 80,
        "fast_path_budget_ms": 250,
        "deny_escalation_when_over_budget": True,
        "prefilter_enabled": True,
        "prefilter_max_insights": 500,
        "lexical_weight": 0.30,
        "semantic_context_min": 0.15,
        "semantic_lexical_min": 0.03,
        "semantic_strong_override": 0.90,
        "bm25_k1": 1.2,
        "bm25_b": 0.75,
        "bm25_mix": 0.75,
        "complexity_threshold": 2,  # used only by extended gate
        "min_results_no_escalation": 4,
        "min_top_score_no_escalation": 0.72,
        "escalate_on_weak_primary": False,
        "escalate_on_high_risk": True,
        "escalate_on_trigger": False,
    },
    "3": {
        "profile": "quality_max",
        "mode": "hybrid_agentic",
        "gate_strategy": "extended",
        "semantic_limit": 12,
        "max_queries": 4,
        "agentic_query_limit": 4,
        "agentic_deadline_ms": 1400,
        "agentic_rate_limit": 1.0,
        "agentic_rate_window": 80,
        "fast_path_budget_ms": 350,
        "deny_escalation_when_over_budget": False,
        "prefilter_enabled": True,
        "prefilter_max_insights": 800,
        "lexical_weight": 0.35,
        "semantic_context_min": 0.12,
        "semantic_lexical_min": 0.02,
        "semantic_strong_override": 0.88,
        "bm25_k1": 1.2,
        "bm25_b": 0.75,
        "bm25_mix": 0.75,
        "complexity_threshold": 1,
        "min_results_no_escalation": 5,
        "min_top_score_no_escalation": 0.78,
        "escalate_on_weak_primary": True,
        "escalate_on_high_risk": True,
        "escalate_on_trigger": True,
    },
}

# Live routing tuneables are loaded from ~/.spark/tuneables.json -> "retrieval".
# Historically, some reports referenced "advisor.retrieval_policy.*" which is a benchmark-only
# overlay (or in-process override) and not read from tuneables.json at runtime. Keep a light
# guardrail to prevent silent misconfiguration.
_WARNED_DEPRECATED_ADVISOR_RETRIEVAL_POLICY = False

DEFAULT_COMPLEXITY_HINTS = (
    "root cause",
    "multi hop",
    "multi-hop",
    "compare",
    "timeline",
    "repeated",
    "pattern",
    "tradeoff",
    "impact",
    "synthesis",
    "across",
    "between",
)

DEFAULT_HIGH_RISK_HINTS = (
    "auth",
    "token",
    "security",
    "prod",
    "production",
    "migration",
    "rollback",
    "deploy",
    "bridge",
    "session",
    "memory retrieval",
)
X_SOCIAL_MARKERS = (
    "x_social",
    "x-social",
    "twitter",
    "tweet",
    "retweet",
    "quote tweet",
    "timeline",
    "engagement",
    "multiplier granted",
    "fomo",
    "wallet",
    "social network",
    "social networks",
    "cryptographic proof",
    "ai identity",
    "human larping",
    "engagement bait",
    "tao subnet",
    "mac mini + ai",
)


def _parse_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return bool(default)


def _parse_iso_ts(value: Any) -> Optional[float]:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return float(datetime.fromisoformat(text).timestamp())
    except Exception:
        return None


def _chips_disabled() -> bool:
    return str(os.environ.get("SPARK_ADVISORY_DISABLE_CHIPS", "")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _load_advisor_config() -> None:
    """Load advisor tuneables from ~/.spark/tuneables.json → "advisor" section.

    Overrides module-level constants so all existing code picks up the values
    without any other changes.  Called once at module load.
    """
    global MIN_RELIABILITY_FOR_ADVICE, MIN_VALIDATIONS_FOR_STRONG_ADVICE
    global MAX_ADVICE_ITEMS, ADVICE_CACHE_TTL_SECONDS, MIN_RANK_SCORE
    global MIND_MAX_STALE_SECONDS, MIND_STALE_ALLOW_IF_EMPTY, MIND_MIN_SALIENCE
    try:
        # Tests should be deterministic and not depend on user-local ~/.spark state.
        # However, some unit tests *do* validate this loader by monkeypatching Path.home().
        # So we only skip when running under pytest AND Path.home() still points at the
        # real user profile directory (not a monkeypatched temp dir).
        if "pytest" in sys.modules and str(os.environ.get("SPARK_TEST_ALLOW_HOME_TUNEABLES", "")).strip().lower() not in {
            "1",
            "true",
            "yes",
            "on",
        }:
            try:
                real_home = Path(os.path.expanduser("~")).resolve()
                current_home = Path.home().resolve()
                if current_home == real_home:
                    return
            except Exception:
                return
        tuneables = Path.home() / ".spark" / "tuneables.json"
        if not tuneables.exists():
            return
        try:
            data = json.loads(tuneables.read_text(encoding="utf-8-sig"))
        except Exception:
            data = json.loads(tuneables.read_text(encoding="utf-8"))
        cfg = data.get("advisor") or {}
        if not isinstance(cfg, dict):
            cfg = {}
        # Fall back to top-level "values" for advice_cache_ttl (backward compat)
        values = data.get("values") or {}
        if isinstance(values, dict) and "advice_cache_ttl" in values and "cache_ttl" not in cfg:
            cfg["cache_ttl"] = values["advice_cache_ttl"]
        if "min_reliability" in cfg:
            MIN_RELIABILITY_FOR_ADVICE = float(cfg["min_reliability"])
        if "min_validations_strong" in cfg:
            MIN_VALIDATIONS_FOR_STRONG_ADVICE = int(cfg["min_validations_strong"])
        if "max_items" in cfg:
            MAX_ADVICE_ITEMS = int(cfg["max_items"])
        if "cache_ttl" in cfg:
            ADVICE_CACHE_TTL_SECONDS = int(cfg["cache_ttl"])
        if "min_rank_score" in cfg:
            MIN_RANK_SCORE = float(cfg["min_rank_score"])
        if "mind_max_stale_s" in cfg:
            MIND_MAX_STALE_SECONDS = max(0.0, float(cfg["mind_max_stale_s"] or 0.0))
        if "mind_stale_allow_if_empty" in cfg:
            MIND_STALE_ALLOW_IF_EMPTY = _parse_bool(
                cfg.get("mind_stale_allow_if_empty"),
                MIND_STALE_ALLOW_IF_EMPTY,
            )
        if "mind_min_salience" in cfg:
            MIND_MIN_SALIENCE = max(0.0, min(1.0, float(cfg["mind_min_salience"])))
    except Exception:
        pass  # Fail silently — keep hard-coded defaults


_load_advisor_config()


def _maybe_warn_deprecated_advisor_retrieval_policy(
    advisor_policy: Optional[Dict[str, Any]],
    retrieval_keys_present: Optional[set],
    effective_policy: Dict[str, Any],
) -> None:
    """Warn if user sets advisor.retrieval_policy.* in tuneables.json expecting it to apply."""
    global _WARNED_DEPRECATED_ADVISOR_RETRIEVAL_POLICY
    if _WARNED_DEPRECATED_ADVISOR_RETRIEVAL_POLICY:
        return
    if not isinstance(advisor_policy, dict):
        return

    keys = (
        "semantic_context_min",
        "semantic_lexical_min",
        "semantic_strong_override",
        "lexical_weight",
    )
    present = [k for k in keys if k in advisor_policy]
    if not present:
        return

    retrieval_keys_present = retrieval_keys_present if isinstance(retrieval_keys_present, set) else set()
    has_all_in_retrieval = all(k in retrieval_keys_present for k in present)

    mismatches: List[str] = []
    for k in present:
        try:
            want = float(advisor_policy.get(k))
            got = float(effective_policy.get(k))
        except Exception:
            continue
        if abs(want - got) > 1e-12:
            mismatches.append(f"{k}={want} (effective={got})")

    # If tuneables.json already sets retrieval.* for these keys and values match, avoid noisy warnings.
    if has_all_in_retrieval and not mismatches:
        return

    _WARNED_DEPRECATED_ADVISOR_RETRIEVAL_POLICY = True
    details = "; ".join(mismatches) if mismatches else ", ".join(present)
    sys.stderr.write(
        "[SPARK][warn] 'advisor.retrieval_policy.*' in ~/.spark/tuneables.json is ignored by runtime. "
        "Routing is loaded from the 'retrieval' section (prefer 'retrieval.overrides.*'). "
        f"Detected: {details}\n"
    )


def _tail_jsonl(path: Path, count: int) -> List[str]:
    """Tail-read JSONL lines without loading entire file in memory."""
    if count <= 0 or not path.exists():
        return []
    chunk_size = 64 * 1024
    try:
        with path.open("rb") as f:
            f.seek(0, os.SEEK_END)
            pos = f.tell()
            buffer = b""
            lines: List[bytes] = []
            while pos > 0 and len(lines) <= count:
                read_size = min(chunk_size, pos)
                pos -= read_size
                f.seek(pos)
                data = f.read(read_size)
                buffer = data + buffer
                if b"\n" in buffer:
                    parts = buffer.split(b"\n")
                    buffer = parts[0]
                    lines = parts[1:] + lines
            if buffer:
                lines = [buffer] + lines
        out = [
            ln.decode("utf-8", errors="replace").rstrip("\r")
            for ln in lines
            if ln != b""
        ]
        return out[-count:]
    except Exception:
        return []


# Avoid doing a read+rewrite of the entire bounded file on every append.
# We compact at most once per TTL per path.
_COMPACT_TTL_S = 30.0
_LAST_COMPACT_TS: Dict[str, float] = {}


def _append_jsonl_capped(path: Path, entry: Dict[str, Any], max_lines: int) -> None:
    """Append JSONL entry and keep file bounded.

    Optimized for the hot path:
    - Always append-only
    - Only compact (rewrite to last N lines) when needed AND rate-limited
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        if max_lines <= 0:
            return

        now = time.time()
        key = str(path)
        last = float(_LAST_COMPACT_TS.get(key, 0.0) or 0.0)
        if (now - last) < _COMPACT_TTL_S:
            return

        # Only compact when we likely exceeded the cap.
        probe = _tail_jsonl(path, max_lines + 1)
        if len(probe) <= max_lines:
            _LAST_COMPACT_TS[key] = now
            return

        # Rewrite to the last max_lines.
        path.write_text("\n".join(probe[-max_lines:]) + "\n", encoding="utf-8")
        _LAST_COMPACT_TS[key] = now
    except Exception:
        pass


def record_recent_delivery(
    *,
    tool: str,
    advice_list: List["Advice"],
    trace_id: Optional[str] = None,
    route: str = "",
    delivered: bool = True,
) -> None:
    """Record advice that was actually surfaced to the agent.

    This is intentionally separate from retrieval logging: advisory_engine may retrieve
    many candidates but only emit a small subset; recent_advice should reflect delivery.
    """
    if not tool or not advice_list:
        return
    recent = {
        "ts": time.time(),
        "tool": tool,
        "trace_id": trace_id,
        "advice_ids": [a.advice_id for a in advice_list],
        "advice_texts": [a.text[:160] for a in advice_list],
        "insight_keys": [a.insight_key for a in advice_list],
        "sources": [a.source for a in advice_list],
        "delivered": bool(delivered),
        "route": str(route or ""),
    }
    # Keep this bounded but roomy enough for short windows + debugging.
    _append_jsonl_capped(RECENT_ADVICE_LOG, recent, max_lines=max(500, RECENT_ADVICE_MAX_LINES * 10))


# ============= Data Classes =============
@dataclass
class Advice:
    """A piece of advice derived from learnings."""
    advice_id: str
    insight_key: str
    text: str
    confidence: float
    source: str  # "cognitive", "mind", "pattern", "surprise"
    context_match: float  # How well it matches current context
    reason: str = ""  # Task #13: WHY this advice matters (evidence/context)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AdviceOutcome:
    """Tracks whether advice was followed and if it helped."""
    advice_id: str
    was_followed: bool
    was_helpful: Optional[bool] = None
    outcome_notes: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ============= Core Advisor =============
class SparkAdvisor:
    """
    The advisor that makes learnings actionable.

    Usage:
        advisor = get_advisor()

        # Before action: get relevant advice
        advice = advisor.advise("Edit", {"file": "main.py"}, "fixing bug")

        # After action: report outcome
        advisor.report_outcome(advice.advice_id, followed=True, helpful=True)
    """

    def __init__(self):
        ADVISOR_DIR.mkdir(parents=True, exist_ok=True)
        self.cognitive = get_cognitive_learner()
        self.mind = get_mind_bridge()
        self.effectiveness = self._load_effectiveness()
        self._cache: Dict[str, Tuple[List[Advice], float]] = {}
        self.retrieval_policy = self._load_retrieval_policy()
        self._agentic_route_history: List[bool] = []

        # Prefilter cache: avoid per-query regex tokenization across large insight sets.
        # key -> (blob_hash, token_set, blob_lower)
        self._prefilter_cache: Dict[str, Tuple[str, set, str]] = {}

    def _load_effectiveness(self) -> Dict[str, Any]:
        """Load effectiveness tracking data."""
        if EFFECTIVENESS_FILE.exists():
            try:
                data = json.loads(EFFECTIVENESS_FILE.read_text(encoding="utf-8"))
                return self._normalize_effectiveness(data)
            except Exception:
                pass
        return self._normalize_effectiveness({
            "total_advice_given": 0,
            "total_followed": 0,
            "total_helpful": 0,
            "by_source": {},
            "by_category": {},
            "recent_outcomes": {},
        })

    def _normalize_effectiveness(self, data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Normalize and enforce invariants for effectiveness counters."""
        src = data if isinstance(data, dict) else {}

        def _as_int(value: Any) -> int:
            try:
                return max(0, int(value))
            except Exception:
                return 0

        total_advice_given = _as_int(src.get("total_advice_given", 0))
        total_followed = _as_int(src.get("total_followed", 0))
        total_helpful = _as_int(src.get("total_helpful", 0))

        # Invariants: helpful <= followed <= advice_given.
        total_followed = min(total_followed, total_advice_given)
        total_helpful = min(total_helpful, total_followed)

        by_source: Dict[str, Dict[str, int]] = {}
        for key, row in (src.get("by_source") or {}).items():
            if not isinstance(row, dict):
                continue
            total = _as_int(row.get("total", 0))
            helpful = min(_as_int(row.get("helpful", 0)), total)
            by_source[str(key)] = {"total": total, "helpful": helpful}

        by_category = src.get("by_category")
        if not isinstance(by_category, dict):
            by_category = {}

        recent_outcomes: Dict[str, Dict[str, Any]] = {}
        raw_recent = src.get("recent_outcomes") or {}
        if isinstance(raw_recent, dict):
            for advice_id, row in raw_recent.items():
                if not advice_id or not isinstance(row, dict):
                    continue
                ts_raw = row.get("ts")
                try:
                    ts = float(ts_raw)
                except Exception:
                    ts = 0.0
                recent_outcomes[str(advice_id)] = {
                    "followed_counted": bool(row.get("followed_counted")),
                    "helpful_counted": bool(row.get("helpful_counted")),
                    "ts": ts,
                }

        # Keep recent outcomes bounded by recency.
        if len(recent_outcomes) > RECENT_OUTCOMES_MAX:
            keep = sorted(
                recent_outcomes.items(),
                key=lambda item: float(item[1].get("ts", 0.0)),
                reverse=True,
            )[:RECENT_OUTCOMES_MAX]
            recent_outcomes = dict(keep)

        return {
            "total_advice_given": total_advice_given,
            "total_followed": total_followed,
            "total_helpful": total_helpful,
            "by_source": by_source,
            "by_category": by_category,
            "recent_outcomes": recent_outcomes,
        }

    def _load_metrics(self) -> Dict[str, Any]:
        if ADVISOR_METRICS.exists():
            try:
                return json.loads(ADVISOR_METRICS.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "total_retrievals": 0,
            "cognitive_retrievals": 0,
            "cognitive_surface_rate": 0.0,
            "cognitive_helpful_known": 0,
            "cognitive_helpful_true": 0,
            "cognitive_helpful_rate": None,
        }

    def _save_metrics(self, metrics: Dict[str, Any]) -> None:
        try:
            ADVISOR_METRICS.parent.mkdir(parents=True, exist_ok=True)
            ADVISOR_METRICS.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _record_cognitive_surface(self, advice_list: List["Advice"]) -> None:
        try:
            metrics = self._load_metrics()
            total = int(metrics.get("total_retrievals", 0)) + 1
            cognitive_sources = {
                "cognitive",
                "semantic",
                "semantic-hybrid",
                "semantic-agentic",
                "trigger",
                "chip",
            }
            has_cognitive = any(a.source in cognitive_sources for a in advice_list)
            cognitive = int(metrics.get("cognitive_retrievals", 0)) + (1 if has_cognitive else 0)
            metrics["total_retrievals"] = total
            metrics["cognitive_retrievals"] = cognitive
            metrics["cognitive_surface_rate"] = round(cognitive / max(total, 1), 4)
            metrics["last_updated"] = datetime.now().isoformat()
            self._save_metrics(metrics)
        except Exception:
            pass

    def _record_cognitive_helpful(self, advice_id: str, was_helpful: Optional[bool]) -> None:
        if was_helpful is None:
            return
        try:
            entry = self._find_recent_advice_by_id(advice_id)
            if not entry:
                return
            advice_ids = entry.get("advice_ids") or []
            sources = entry.get("sources") or []
            idx = advice_ids.index(advice_id) if advice_id in advice_ids else -1
            source = sources[idx] if 0 <= idx < len(sources) else None
            if source not in {"cognitive", "semantic", "semantic-hybrid", "semantic-agentic", "trigger"}:
                return

            metrics = self._load_metrics()
            metrics["cognitive_helpful_known"] = int(metrics.get("cognitive_helpful_known", 0)) + 1
            if was_helpful is True:
                metrics["cognitive_helpful_true"] = int(metrics.get("cognitive_helpful_true", 0)) + 1
            known = max(1, int(metrics.get("cognitive_helpful_known", 0)))
            metrics["cognitive_helpful_rate"] = round(
                int(metrics.get("cognitive_helpful_true", 0)) / known, 4
            )
            metrics["last_updated"] = datetime.now().isoformat()
            self._save_metrics(metrics)
        except Exception:
            pass

    def _save_effectiveness(self):
        """Save effectiveness data with atomic write to prevent race conditions.

        Uses read-modify-write pattern:
        1. Read current disk state
        2. Merge with in-memory deltas
        3. Write atomically via temp file
        """
        import tempfile
        import os

        try:
            # Read current disk state to merge (handles multiple processes)
            disk_data = self._load_effectiveness()
            mem_data = self._normalize_effectiveness(self.effectiveness)

            # Merge: take max of counters (monotonically increasing)
            merged = {
                "total_advice_given": max(
                    disk_data.get("total_advice_given", 0),
                    mem_data.get("total_advice_given", 0)
                ),
                "total_followed": max(
                    disk_data.get("total_followed", 0),
                    mem_data.get("total_followed", 0)
                ),
                "total_helpful": max(
                    disk_data.get("total_helpful", 0),
                    mem_data.get("total_helpful", 0)
                ),
                "by_source": {},
                "by_category": {},
                "recent_outcomes": {},
            }

            # Merge by_source
            for src in set(list(disk_data.get("by_source", {}).keys()) +
                          list(mem_data.get("by_source", {}).keys())):
                disk_src = disk_data.get("by_source", {}).get(src, {})
                mem_src = mem_data.get("by_source", {}).get(src, {})
                merged["by_source"][src] = {
                    "total": max(disk_src.get("total", 0), mem_src.get("total", 0)),
                    "helpful": max(disk_src.get("helpful", 0), mem_src.get("helpful", 0)),
                }

            # Merge by_category as shallow union.
            merged["by_category"] = dict(disk_data.get("by_category", {}))
            merged["by_category"].update(mem_data.get("by_category", {}))

            # Merge per-advice outcome index to avoid repeated counter inflation.
            recent_outcomes = dict(disk_data.get("recent_outcomes", {}))
            recent_outcomes.update(mem_data.get("recent_outcomes", {}))
            merged["recent_outcomes"] = recent_outcomes
            merged = self._normalize_effectiveness(merged)

            # Update in-memory state with merged values
            self.effectiveness = merged

            # Atomic write: write to temp file then rename
            EFFECTIVENESS_FILE.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_path = tempfile.mkstemp(
                dir=EFFECTIVENESS_FILE.parent,
                prefix=".effectiveness_",
                suffix=".tmp"
            )
            try:
                with os.fdopen(fd, 'w') as f:
                    json.dump(merged, f, indent=2)
                # Atomic replace (os.replace works on Windows without separate unlink)
                os.replace(temp_path, str(EFFECTIVENESS_FILE))
            except Exception:
                # Clean up temp file on error
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise
        except Exception:
            # Fallback to simple write if atomic fails
            fallback = self._normalize_effectiveness(self.effectiveness)
            self.effectiveness = fallback
            EFFECTIVENESS_FILE.write_text(json.dumps(fallback, indent=2), encoding="utf-8")

    def _mark_outcome_counted(
        self,
        advice_id: str,
        was_followed: bool,
        was_helpful: Optional[bool],
    ) -> Tuple[bool, bool]:
        """Return whether aggregate counters should increment for this advice_id."""
        outcomes = self.effectiveness.setdefault("recent_outcomes", {})
        key = str(advice_id or "").strip()
        now = time.time()

        # If advice_id is missing, keep legacy behavior.
        if not key:
            return bool(was_followed), bool(was_helpful)

        entry = outcomes.get(key) or {}
        followed_counted = bool(entry.get("followed_counted"))
        helpful_counted = bool(entry.get("helpful_counted"))

        inc_followed = bool(was_followed) and not followed_counted
        inc_helpful = bool(was_helpful) and not helpful_counted

        if was_followed:
            entry["followed_counted"] = True
        if was_helpful:
            entry["helpful_counted"] = True
        entry["ts"] = now
        outcomes[key] = entry

        # Keep bounded to avoid unbounded growth.
        if len(outcomes) > RECENT_OUTCOMES_MAX:
            oldest = min(outcomes.items(), key=lambda item: float(item[1].get("ts", 0.0)))[0]
            outcomes.pop(oldest, None)

        return inc_followed, inc_helpful

    def _generate_advice_id(
        self,
        text: str,
        *,
        insight_key: Optional[str] = None,
        source: Optional[str] = None,
    ) -> str:
        """Generate a stable advice ID.

        Important: this must be deterministic across sessions so we can:
        - dedupe repeats reliably (avoid advice spam)
        - attribute outcomes to the right learning over time

        When we have a durable `insight_key` for durable sources (cognitive/mind/bank/etc),
        prefer that as the stable ID anchor (so minor text edits don't reset the ID).
        """

        def _norm_text(value: str) -> str:
            t = str(value or "").strip().lower()
            t = re.sub(r"\s+", " ", t).strip()
            return t[:400]

        src = str(source or "").strip().lower()
        # Canonicalize semantic retrieval route labels back to the underlying learning store.
        # Otherwise the same insight would churn IDs when retrieval strategy changes.
        if src.startswith("semantic") or src == "trigger":
            src = "cognitive"

        key = str(insight_key or "").strip()
        if key and src in {"cognitive", "bank", "mind", "chip", "skill", "niche", "convo", "eidos", "engagement"}:
            return f"{src}:{key}"

        payload = "|".join([src, key, _norm_text(text)])
        return hashlib.sha256(payload.encode("utf-8", errors="replace")).hexdigest()[:12]

    def _cache_key(
        self,
        tool: str,
        context: str,
        tool_input: Optional[Dict[str, Any]] = None,
        task_context: str = "",
        include_mind: bool = False,
    ) -> str:
        """Generate stable cache key with collision-resistant hashing."""
        keys = ("command", "file_path", "path", "url", "pattern", "query")
        hint = {}
        if isinstance(tool_input, dict):
            for k in keys:
                v = tool_input.get(k)
                if v is not None:
                    hint[k] = str(v)[:200]
        payload = {
            "tool": (tool or "").strip().lower(),
            "context": (context or "").strip().lower(),
            "task_context": (task_context or "").strip().lower(),
            "input_hint": hint,
            "include_mind": bool(include_mind),
        }
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        digest = hashlib.sha1(encoded.encode("utf-8", errors="replace")).hexdigest()[:16]
        return f"{payload['tool']}:{digest}"

    def _get_cached_advice(self, key: str) -> Optional[List[Advice]]:
        """Get cached advice if still valid."""
        if key in self._cache:
            advice, timestamp = self._cache[key]
            if time.time() - timestamp < ADVICE_CACHE_TTL_SECONDS:
                return advice
            del self._cache[key]
        return None

    def _cache_advice(self, key: str, advice: List[Advice]):
        """Cache advice for reuse."""
        self._cache[key] = (advice, time.time())
        # Keep cache bounded
        if len(self._cache) > 100:
            oldest = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest]

    # ============= Retrieval Policy =============

    def _load_retrieval_policy(self) -> Dict[str, Any]:
        """Load retrieval routing policy from tuneables + env."""
        level = str(os.getenv("SPARK_RETRIEVAL_LEVEL", "1") or "1").strip()
        if level not in DEFAULT_RETRIEVAL_PROFILES:
            level = "1"
        policy = dict(DEFAULT_RETRIEVAL_PROFILES[level])
        policy["level"] = level

        # Optional overrides from tuneables.json -> retrieval section.
        advisor_policy: Optional[Dict[str, Any]] = None
        retrieval_keys_present: set = set()
        try:
            tuneables = Path.home() / ".spark" / "tuneables.json"
            if tuneables.exists():
                # Windows editors commonly write UTF-8 with BOM; accept both.
                data = json.loads(tuneables.read_text(encoding="utf-8-sig"))
                advisor = data.get("advisor") or {}
                if isinstance(advisor, dict):
                    ap = advisor.get("retrieval_policy")
                    if isinstance(ap, dict):
                        advisor_policy = ap
                retrieval = data.get("retrieval") or {}
                if isinstance(retrieval, dict):
                    lvl = str(retrieval.get("level") or level).strip()
                    if lvl in DEFAULT_RETRIEVAL_PROFILES:
                        level = lvl
                        policy = dict(DEFAULT_RETRIEVAL_PROFILES[level])
                        policy["level"] = level
                    profile_overrides = retrieval.get("profiles") or {}
                    if isinstance(profile_overrides, dict):
                        by_level = profile_overrides.get(level) or {}
                        if isinstance(by_level, dict):
                            policy.update(by_level)
                    overrides = retrieval.get("overrides") or {}
                    if isinstance(overrides, dict):
                        for key in (
                            "semantic_context_min",
                            "semantic_lexical_min",
                            "semantic_strong_override",
                            "lexical_weight",
                        ):
                            if key in overrides:
                                retrieval_keys_present.add(key)
                        policy.update(overrides)
                    # Flat top-level retrieval keys are also treated as overrides.
                    for key in (
                        "mode",
                        "gate_strategy",
                        "semantic_limit",
                        "semantic_context_min",
                        "semantic_lexical_min",
                        "semantic_strong_override",
                        "max_queries",
                        "agentic_query_limit",
                        "agentic_deadline_ms",
                        "agentic_rate_limit",
                        "agentic_rate_window",
                        "fast_path_budget_ms",
                        "deny_escalation_when_over_budget",
                        "prefilter_enabled",
                        "prefilter_max_insights",
                        "lexical_weight",
                        "bm25_k1",
                        "bm25_b",
                        "bm25_mix",
                        "complexity_threshold",
                        "min_results_no_escalation",
                        "min_top_score_no_escalation",
                        "escalate_on_weak_primary",
                        "escalate_on_high_risk",
                        "escalate_on_trigger",
                    ):
                        if key in retrieval:
                            policy[key] = retrieval.get(key)
                            if key in {
                                "semantic_context_min",
                                "semantic_lexical_min",
                                "semantic_strong_override",
                                "lexical_weight",
                            }:
                                retrieval_keys_present.add(key)
        except Exception:
            pass

        _maybe_warn_deprecated_advisor_retrieval_policy(
            advisor_policy=advisor_policy,
            retrieval_keys_present=retrieval_keys_present,
            effective_policy=policy,
        )

        env_mode = str(os.getenv("SPARK_RETRIEVAL_MODE", "") or "").strip().lower()
        if env_mode in {"auto", "embeddings_only", "hybrid_agentic"}:
            policy["mode"] = env_mode

        # Normalize types.
        policy["mode"] = str(policy.get("mode") or "auto").strip().lower()
        if policy["mode"] not in {"auto", "embeddings_only", "hybrid_agentic"}:
            policy["mode"] = "auto"
        policy["gate_strategy"] = str(policy.get("gate_strategy") or "minimal").strip().lower()
        if policy["gate_strategy"] not in {"minimal", "extended"}:
            policy["gate_strategy"] = "minimal"
        policy["semantic_limit"] = max(4, int(policy.get("semantic_limit", 8) or 8))
        policy["semantic_context_min"] = max(
            0.0, min(1.0, float(policy.get("semantic_context_min", 0.15) or 0.15))
        )
        policy["semantic_lexical_min"] = max(
            0.0, min(1.0, float(policy.get("semantic_lexical_min", 0.03) or 0.03))
        )
        policy["semantic_strong_override"] = max(
            0.0, min(1.0, float(policy.get("semantic_strong_override", 0.90) or 0.90))
        )
        policy["max_queries"] = max(1, int(policy.get("max_queries", 2) or 2))
        policy["agentic_query_limit"] = max(1, int(policy.get("agentic_query_limit", 2) or 2))
        deadline_raw = policy.get("agentic_deadline_ms", 700)
        if deadline_raw is None:
            deadline_raw = 700
        policy["agentic_deadline_ms"] = max(0, int(deadline_raw))

        rate_raw = policy.get("agentic_rate_limit", 0.2)
        if rate_raw is None:
            rate_raw = 0.2
        policy["agentic_rate_limit"] = max(0.0, min(1.0, float(rate_raw)))
        policy["agentic_rate_window"] = max(10, int(policy.get("agentic_rate_window", 80) or 80))
        policy["fast_path_budget_ms"] = max(50, int(policy.get("fast_path_budget_ms", 250) or 250))
        policy["deny_escalation_when_over_budget"] = bool(
            policy.get("deny_escalation_when_over_budget", True)
        )
        policy["prefilter_enabled"] = bool(policy.get("prefilter_enabled", True))
        prefilter_raw = policy.get("prefilter_max_insights", 500)
        if prefilter_raw is None:
            prefilter_raw = 500
        policy["prefilter_max_insights"] = max(20, int(prefilter_raw))
        policy["lexical_weight"] = max(0.0, min(1.0, float(policy.get("lexical_weight", 0.25) or 0.25)))
        policy["bm25_k1"] = max(0.1, float(policy.get("bm25_k1", 1.2) or 1.2))
        policy["bm25_b"] = max(0.0, min(1.0, float(policy.get("bm25_b", 0.75) or 0.75)))
        policy["bm25_mix"] = max(0.0, min(1.0, float(policy.get("bm25_mix", 0.75) or 0.75)))
        policy["complexity_threshold"] = max(1, int(policy.get("complexity_threshold", 2) or 2))
        policy["min_results_no_escalation"] = max(1, int(policy.get("min_results_no_escalation", 3) or 3))
        policy["min_top_score_no_escalation"] = max(
            0.0, min(1.0, float(policy.get("min_top_score_no_escalation", 0.7) or 0.7))
        )
        policy["escalate_on_weak_primary"] = bool(policy.get("escalate_on_weak_primary", True))
        policy["escalate_on_high_risk"] = bool(policy.get("escalate_on_high_risk", True))
        policy["escalate_on_trigger"] = bool(policy.get("escalate_on_trigger", True))
        policy["complexity_hints"] = list(DEFAULT_COMPLEXITY_HINTS)
        policy["high_risk_hints"] = list(DEFAULT_HIGH_RISK_HINTS)
        return policy

    def _analyze_query_complexity(self, tool_name: str, context: str) -> Dict[str, Any]:
        """Estimate when agentic retrieval is worth the added latency/cost."""
        text = str(context or "").strip().lower()
        tokens = [t for t in re.findall(r"[a-z0-9_]+", text) if t]
        score = 0
        reasons: List[str] = []

        if len(tokens) >= 18:
            score += 1
            reasons.append("long_query")
        if "?" in context:
            score += 1
            reasons.append("question_form")

        complexity_hits = [k for k in self.retrieval_policy.get("complexity_hints", []) if k in text]
        if complexity_hits:
            score += min(2, len(complexity_hits))
            reasons.append("complexity_terms")

        high_risk_hits = [k for k in self.retrieval_policy.get("high_risk_hints", []) if k in text]
        if high_risk_hits:
            score += 1
            reasons.append("risk_terms")

        tool = str(tool_name or "").strip().lower()
        if tool in {"bash", "edit", "write", "task"}:
            score += 1
            reasons.append("high_impact_tool")

        threshold = int(self.retrieval_policy.get("complexity_threshold", 2) or 2)
        return {
            "score": score,
            "threshold": threshold,
            "requires_agentic": score >= threshold,
            "complexity_hits": complexity_hits[:4],
            "high_risk_hits": high_risk_hits[:4],
            "reasons": reasons,
        }

    def _log_retrieval_route(self, entry: Dict[str, Any]) -> None:
        payload = dict(entry or {})
        payload["ts"] = time.time()
        _append_jsonl_capped(RETRIEVAL_ROUTE_LOG, payload, RETRIEVAL_ROUTE_LOG_MAX)

    def _record_agentic_route(self, used_agentic: bool, window: int) -> None:
        self._agentic_route_history.append(bool(used_agentic))
        max_window = max(10, int(window or 80))
        if len(self._agentic_route_history) > max_window:
            self._agentic_route_history = self._agentic_route_history[-max_window:]

    def _agentic_recent_rate(self, window: int) -> float:
        max_window = max(10, int(window or 80))
        if not self._agentic_route_history:
            return 0.0
        sample = self._agentic_route_history[-max_window:]
        return sum(1 for x in sample if x) / max(1, len(sample))

    def _allow_agentic_escalation(self, rate_limit: float, window: int) -> bool:
        if rate_limit >= 1.0:
            return True
        return self._agentic_recent_rate(window) < max(0.0, float(rate_limit))

    def _insight_blob(self, key: str, insight: Any) -> str:
        parts = [str(key or "")]
        for attr in ("insight", "context", "category", "project", "tool", "source", "scope"):
            val = getattr(insight, attr, None)
            if val:
                parts.append(str(val))
        if isinstance(insight, dict):
            for field in ("insight", "context", "category", "project", "tool", "source", "scope"):
                val = insight.get(field)
                if val:
                    parts.append(str(val))
        return " ".join(parts).lower()

    def _prefilter_cached_blob_tokens(self, key: str, insight: Any) -> Tuple[set, str]:
        """Return (tokens, blob_lower) for an insight, cached by blob hash."""
        blob = self._insight_blob(key, insight)
        blob_hash = hashlib.sha1(blob.encode("utf-8", errors="replace")).hexdigest()[:16]
        cached = self._prefilter_cache.get(key)
        if cached and cached[0] == blob_hash:
            return cached[1], cached[2]
        tokens = {t for t in re.findall(r"[a-z0-9_]+", blob) if len(t) >= 3}
        self._prefilter_cache[key] = (blob_hash, tokens, blob)
        # Keep cache bounded (avoid unbounded growth if keys churn).
        if len(self._prefilter_cache) > 5000:
            # Drop an arbitrary 20% slice.
            for k in list(self._prefilter_cache.keys())[:1000]:
                self._prefilter_cache.pop(k, None)
        return tokens, blob

    def _prefilter_insights_for_retrieval(
        self,
        insights: Dict[str, Any],
        tool_name: str,
        context: str,
        max_items: int,
    ) -> Dict[str, Any]:
        if not insights:
            return insights
        limit = max(20, int(max_items or 500))
        if len(insights) <= limit:
            return insights

        query_tokens = {t for t in re.findall(r"[a-z0-9_]+", (context or "").lower()) if len(t) >= 3}
        tool = str(tool_name or "").strip().lower()
        scored: List[Tuple[float, str, Any]] = []
        fallback: List[Tuple[float, str, Any]] = []
        for key, insight in insights.items():
            blob_tokens, blob = self._prefilter_cached_blob_tokens(str(key), insight)
            overlap = len(query_tokens & blob_tokens) if query_tokens else 0
            metadata_boost = 2.0 if tool and tool in blob else 0.0
            reliability = float(getattr(insight, "reliability", 0.5) or 0.5)
            score = (overlap * 3.0) + metadata_boost + reliability
            if overlap > 0 or metadata_boost > 0:
                scored.append((score, key, insight))
            else:
                fallback.append((reliability, key, insight))

        ranked: List[Tuple[float, str, Any]] = sorted(scored, key=lambda row: row[0], reverse=True)
        if len(ranked) < limit:
            ranked.extend(sorted(fallback, key=lambda row: row[0], reverse=True)[: max(0, limit - len(ranked))])

        selected = ranked[:limit]
        if not selected:
            return insights
        return {key: insight for _, key, insight in selected}

    def _mind_retrieval_allowed(self, include_mind: bool, pre_mind_count: int) -> bool:
        """Gate Mind retrieval for freshness while preserving empty-result fallback."""
        if not include_mind or not HAS_REQUESTS or self.mind is None:
            return False
        if MIND_MAX_STALE_SECONDS <= 0:
            return True

        stats = {}
        try:
            if hasattr(self.mind, "get_stats"):
                stats = self.mind.get_stats() or {}
        except Exception:
            # Don't block retrieval if stats are temporarily unavailable.
            return True

        last_sync_ts = _parse_iso_ts(stats.get("last_sync"))
        if last_sync_ts is None:
            return bool(MIND_STALE_ALLOW_IF_EMPTY and pre_mind_count <= 0)

        age_s = max(0.0, time.time() - last_sync_ts)
        if age_s <= MIND_MAX_STALE_SECONDS:
            return True
        return bool(MIND_STALE_ALLOW_IF_EMPTY and pre_mind_count <= 0)

    # ============= Core Advice Generation =============

    def advise(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        task_context: str = "",
        include_mind: bool = True,
        track_retrieval: bool = True,
        log_recent: bool = True,
        trace_id: Optional[str] = None,
    ) -> List[Advice]:
        """
        Get relevant advice before executing an action.

        This is the KEY function that closes the learning gap.

        Args:
            tool_name: The tool about to be used (e.g., "Edit", "Bash")
            tool_input: The input to the tool
            task_context: Optional description of what we're trying to do
            include_mind: Whether to query Mind for additional context
            track_retrieval: Whether to track this retrieval for outcome measurement.
                Set to False for sampling/analysis to avoid polluting metrics.
            log_recent: Whether to write to recent_advice.jsonl for outcome linkage.
                For advisory_engine paths, prefer recording only *delivered* advice via
                record_recent_delivery().
            trace_id: Optional trace_id for linking advice retrievals to traces.

        Returns:
            List of Advice objects, sorted by relevance
        """
        # Build context string for matching
        context_parts = [tool_name]
        if tool_input:
            context_parts.append(str(tool_input)[:200])
        if task_context:
            context_parts.append(task_context)
        context_raw = " ".join(context_parts).strip()
        context = context_raw.lower()

        # Build semantic context: include key tool_input values so trigger
        # rules can match against actual commands/paths, not just task_context.
        _input_hint = ""
        if tool_input:
            for _k in ("command", "file_path", "url", "pattern", "query"):
                if _k in tool_input:
                    _input_hint = str(tool_input[_k])[:200]
                    break
        semantic_parts = [tool_name]
        if _input_hint:
            semantic_parts.append(_input_hint)
        if task_context:
            semantic_parts.append(task_context)
        semantic_context = " ".join(semantic_parts).strip() if (task_context or _input_hint) else context_raw

        # Check cache
        cache_key = self._cache_key(
            tool_name,
            context_raw,
            tool_input=tool_input,
            task_context=task_context,
            include_mind=include_mind,
        )
        cached = self._get_cached_advice(cache_key)
        if cached:
            # Even on cache hits, emit observability/attribution when requested.
            # Otherwise outcome tracking can mismatch traces (same advice_id reused
            # across tool calls but Meta-Ralph sees only the first retrieval).
            if track_retrieval:
                try:
                    self._record_cognitive_surface(cached)
                except Exception:
                    pass
                try:
                    self._log_advice(cached, tool_name, context, trace_id=trace_id, log_recent=log_recent)
                except Exception:
                    pass
                try:
                    from .meta_ralph import get_meta_ralph

                    ralph = get_meta_ralph()
                    for adv in cached:
                        ralph.track_retrieval(
                            adv.advice_id,
                            adv.text,
                            insight_key=adv.insight_key,
                            source=adv.source,
                            trace_id=trace_id,
                        )
                except Exception:
                    pass
            return cached

        advice_list: List[Advice] = []

        # 1. Query memory banks (fast local)
        advice_list.extend(self._get_bank_advice(context))

        # 2. Query cognitive insights (semantic + keyword fallback)
        advice_list.extend(self._get_cognitive_advice(tool_name, context, semantic_context))

        # 2.5. Query chip insights (domain-specific intelligence).
        advice_list.extend(self._get_chip_advice(context))

        # 3. Query Mind if available
        if self._mind_retrieval_allowed(include_mind=include_mind, pre_mind_count=len(advice_list)):
            advice_list.extend(self._get_mind_advice(context))

        # 4. Get tool-specific learnings
        advice_list.extend(self._get_tool_specific_advice(tool_name))

        # 5. Get opportunity-scanner prompts (Socratic opportunity lens)
        advice_list.extend(
            self._get_opportunity_advice(
                tool_name=tool_name,
                context_raw=context_raw,
                task_context=task_context,
            )
        )

        # 6. Get surprise-based cautions
        advice_list.extend(self._get_surprise_advice(tool_name, context))

        # 7. Get skill-based hints
        advice_list.extend(self._get_skill_advice(context))

        # 8. Get EIDOS distillations (extracted rules from patterns)
        if HAS_EIDOS:
            advice_list.extend(self._get_eidos_advice(tool_name, context))

        # 9. Get conversation intelligence advice (ConvoIQ)
        advice_list.extend(self._get_convo_advice(tool_name, context))

        # 10. Get engagement pulse advice
        advice_list.extend(self._get_engagement_advice(tool_name, context))

        # 11. Get niche intelligence advice
        advice_list.extend(self._get_niche_advice(tool_name, context))

        # Global domain guard: do not let X-social specific learnings leak
        # into non-social tasks from non-semantic sources (chip/mind/cognitive/etc.).
        advice_list = self._filter_cross_domain_advice(advice_list, context)

        # Sort by relevance (confidence * context_match * effectiveness_boost)
        advice_list = self._rank_advice(advice_list)

        # Drop low-quality items — prefer fewer, higher-quality results
        advice_list = [a for a in advice_list if self._rank_score(a) >= MIN_RANK_SCORE]

        # Limit to top N
        advice_list = advice_list[:MAX_ADVICE_ITEMS]

        # Log advice given (only for operational use, not sampling)
        if track_retrieval:
            self._record_cognitive_surface(advice_list)
            self._log_advice(advice_list, tool_name, context, trace_id=trace_id, log_recent=log_recent)

            # Track retrievals in Meta-Ralph for outcome tracking
            try:
                from .meta_ralph import get_meta_ralph
                ralph = get_meta_ralph()
                for adv in advice_list:
                    ralph.track_retrieval(
                        adv.advice_id,
                        adv.text,
                        insight_key=adv.insight_key,
                        source=adv.source,
                        trace_id=trace_id,
                    )
            except Exception:
                pass  # Don't break advice flow if tracking fails

        # Cache for reuse
        self._cache_advice(cache_key, advice_list)

        return advice_list

    def _get_cognitive_advice(self, tool_name: str, context: str, semantic_context: Optional[str] = None) -> List[Advice]:
        """Get advice from cognitive insights (semantic-first with keyword fallback)."""
        semantic = self._get_semantic_cognitive_advice(tool_name=tool_name, context=semantic_context or context)
        keyword = self._get_cognitive_advice_keyword(tool_name, context)

        if not semantic:
            return keyword

        # Merge, preferring semantic results
        seen = {a.insight_key for a in semantic if a.insight_key}
        merged = list(semantic)
        for a in keyword:
            if a.insight_key and a.insight_key in seen:
                continue
            merged.append(a)
        return merged

    def _get_semantic_cognitive_advice(self, tool_name: str, context: str) -> List[Advice]:
        """Retrieve cognitive advice with policy-driven semantic/agentic routing."""
        try:
            from .semantic_retriever import get_semantic_retriever
        except Exception:
            return []

        retriever = get_semantic_retriever()
        if not retriever:
            return []
        insights = dict(getattr(self.cognitive, "insights", {}) or {})
        if not insights:
            return []

        route_start = time.perf_counter()
        policy = dict(self.retrieval_policy or {})
        mode = str(policy.get("mode") or "auto").strip().lower()
        gate_strategy = str(policy.get("gate_strategy") or "minimal").strip().lower()
        semantic_limit = int(policy.get("semantic_limit", 8) or 8)
        max_queries = int(policy.get("max_queries", 2) or 2)
        agentic_query_limit = int(policy.get("agentic_query_limit", 2) or 2)
        agentic_deadline_ms = int(policy.get("agentic_deadline_ms", 700))
        agentic_rate_limit = float(policy.get("agentic_rate_limit", 0.2))
        agentic_rate_window = int(policy.get("agentic_rate_window", 80) or 80)
        fast_path_budget_ms = int(policy.get("fast_path_budget_ms", 250) or 250)
        prefilter_enabled = bool(policy.get("prefilter_enabled", True))
        prefilter_max_insights = int(policy.get("prefilter_max_insights", 500))
        lexical_weight = float(policy.get("lexical_weight", 0.25) or 0.25)
        semantic_context_min = float(policy.get("semantic_context_min", 0.15) or 0.15)
        semantic_lexical_min = float(policy.get("semantic_lexical_min", 0.03) or 0.03)
        semantic_strong_override = float(policy.get("semantic_strong_override", 0.90) or 0.90)
        bm25_k1 = float(policy.get("bm25_k1", 1.2) or 1.2)
        bm25_b = float(policy.get("bm25_b", 0.75) or 0.75)
        bm25_mix = float(policy.get("bm25_mix", 0.75) or 0.75)

        analysis = self._analyze_query_complexity(tool_name, context)
        high_risk_hits = list(analysis.get("high_risk_hits") or [])
        high_risk = bool(high_risk_hits)
        active_insights = insights
        if prefilter_enabled:
            active_insights = self._prefilter_insights_for_retrieval(
                insights,
                tool_name=tool_name,
                context=context,
                max_items=prefilter_max_insights,
            )

        should_escalate = False
        escalate_reasons: List[str] = []
        primary_results: List[Any] = []
        primary_start = time.perf_counter()
        try:
            primary_results = list(retriever.retrieve(context, active_insights, limit=semantic_limit))
        except Exception:
            primary_results = []
        primary_elapsed_ms = int((time.perf_counter() - primary_start) * 1000)
        primary_over_budget = primary_elapsed_ms > fast_path_budget_ms
        if primary_over_budget:
            escalate_reasons.append("fast_path_budget_exceeded")

        primary_count = len(primary_results)
        primary_top_score = max((float(getattr(r, "fusion_score", 0.0) or 0.0) for r in primary_results), default=0.0)
        primary_trigger_hit = any(str(getattr(r, "source_type", "") or "") == "trigger" for r in primary_results)

        if mode == "hybrid_agentic":
            should_escalate = True
            escalate_reasons.append("forced_hybrid_agentic_mode")
        elif mode == "embeddings_only":
            should_escalate = False
            escalate_reasons.append("forced_embeddings_only_mode")
        else:
            if bool(policy.get("escalate_on_high_risk", True)) and high_risk:
                should_escalate = True
                escalate_reasons.append("high_risk_terms")
            if bool(policy.get("escalate_on_weak_primary", True)):
                if primary_count < int(policy.get("min_results_no_escalation", 3) or 3):
                    should_escalate = True
                    escalate_reasons.append("weak_primary_count")
                if primary_top_score < float(policy.get("min_top_score_no_escalation", 0.7) or 0.7):
                    should_escalate = True
                    escalate_reasons.append("weak_primary_score")
            if not primary_results:
                should_escalate = True
                escalate_reasons.append("empty_primary")
            if gate_strategy == "extended":
                if analysis.get("requires_agentic"):
                    should_escalate = True
                    escalate_reasons.append("query_complexity")
                if bool(policy.get("escalate_on_trigger", True)) and primary_trigger_hit:
                    should_escalate = True
                    escalate_reasons.append("trigger_signal")

        if should_escalate and mode == "auto":
            if not self._allow_agentic_escalation(rate_limit=agentic_rate_limit, window=agentic_rate_window):
                should_escalate = False
                escalate_reasons.append("agentic_rate_cap")

        # Latency-tail guard: if the primary semantic retrieval already exceeded the fast-path budget,
        # do not add agentic facet queries unless this is a high-risk query.
        if (
            should_escalate
            and mode == "auto"
            and primary_over_budget
            and bool(policy.get("deny_escalation_when_over_budget", True))
            and not high_risk
        ):
            should_escalate = False
            escalate_reasons.append("deny_over_budget")

        facet_queries: List[str] = []
        facet_queries_executed: List[str] = []
        agentic_timed_out = False
        if should_escalate and mode != "embeddings_only":
            facet_queries = self._extract_agentic_queries(context, limit=agentic_query_limit)
            facet_queries = facet_queries[: max(0, max_queries - 1)]
        deadline_ts = (time.perf_counter() + (agentic_deadline_ms / 1000.0)) if should_escalate and agentic_deadline_ms > 0 else None

        merged: Dict[str, Any] = {}
        for r in primary_results:
            key = r.insight_key or self._generate_advice_id(r.insight_text)
            prev = merged.get(key)
            if prev is None or float(getattr(r, "fusion_score", 0.0) or 0.0) > float(getattr(prev, "fusion_score", 0.0) or 0.0):
                merged[key] = r

        for q in facet_queries:
            if deadline_ts is not None and time.perf_counter() >= deadline_ts:
                agentic_timed_out = True
                escalate_reasons.append("agentic_deadline")
                break
            try:
                query_results = retriever.retrieve(q, active_insights, limit=semantic_limit)
                facet_queries_executed.append(q)
            except Exception:
                continue
            for r in query_results:
                key = r.insight_key or self._generate_advice_id(r.insight_text)
                prev = merged.get(key)
                if prev is None or float(getattr(r, "fusion_score", 0.0) or 0.0) > float(getattr(prev, "fusion_score", 0.0) or 0.0):
                    merged[key] = r

        if not merged:
            self._log_retrieval_route(
                {
                    "tool": tool_name,
                    "profile_level": policy.get("level"),
                    "profile_name": policy.get("profile"),
                    "mode": mode,
                    "route": "empty",
                    "escalated": should_escalate,
                    "primary_count": primary_count,
                    "primary_top_score": round(primary_top_score, 4),
                    "facets_used": len(facet_queries_executed),
                    "facets_planned": len(facet_queries),
                    "agentic_timed_out": agentic_timed_out,
                    "active_insights": len(active_insights),
                    "fast_path_budget_ms": fast_path_budget_ms,
                    "fast_path_elapsed_ms": primary_elapsed_ms,
                    "fast_path_over_budget": primary_over_budget,
                    "complexity_score": analysis.get("score"),
                    "complexity_threshold": analysis.get("threshold"),
                    "reasons": escalate_reasons[:6],
                    "route_elapsed_ms": int((time.perf_counter() - route_start) * 1000),
                }
            )
            self._record_agentic_route(False, agentic_rate_window)
            return []

        used_agentic = bool(facet_queries_executed)
        semantic_source = "semantic-agentic" if used_agentic else "semantic"
        merged_values = list(merged.values())
        lexical_scores = self._hybrid_lexical_scores(
            query=context,
            docs=[str(getattr(r, "insight_text", "") or "") for r in merged_values],
            bm25_mix=bm25_mix,
            k1=bm25_k1,
            b=bm25_b,
        )
        scored: List[Tuple[Any, float]] = []
        for idx, row in enumerate(merged_values):
            base = float(getattr(row, "fusion_score", 0.0) or 0.0)
            lex = lexical_scores[idx] if idx < len(lexical_scores) else 0.0
            scored.append((row, base + (lexical_weight * lex)))
        ranked = sorted(
            scored,
            key=lambda pair: pair[1],
            reverse=True,
        )
        ranked_rows = [row for row, _ in ranked]

        route_reason = " + ".join(escalate_reasons[:3]) if used_agentic else "primary_semantic_only"
        advice: List[Advice] = []
        filtered_low_match = 0
        filtered_domain_mismatch = 0
        social_query = self._is_x_social_query(context)
        for r in ranked_rows[:semantic_limit]:
            if hasattr(self.cognitive, "is_noise_insight") and self.cognitive.is_noise_insight(r.insight_text):
                continue
            confidence = max(0.6, float(getattr(r, "fusion_score", 0.0) or 0.0))
            if str(getattr(r, "source_type", "") or "") == "trigger":
                confidence = max(0.8, confidence)
            source = "trigger" if str(getattr(r, "source_type", "") or "") == "trigger" else semantic_source
            if (not social_query) and self._is_x_social_insight(str(getattr(r, "insight_text", "") or "")):
                filtered_domain_mismatch += 1
                continue
            semantic_sim = float(getattr(r, "semantic_sim", 0.0) or 0.0)
            trigger_conf = float(getattr(r, "trigger_conf", 0.0) or 0.0)
            lexical_match = self._lexical_overlap_score(context, str(getattr(r, "insight_text", "") or ""))
            if source != "trigger":
                has_context_match = semantic_sim >= semantic_context_min
                has_lexical_match = lexical_match >= semantic_lexical_min
                strong_override = semantic_sim >= semantic_strong_override
                if not (has_context_match or has_lexical_match or strong_override):
                    filtered_low_match += 1
                    continue
            context_match = max(semantic_sim, lexical_match, trigger_conf)
            if source == "trigger":
                context_match = max(0.7, context_match)
            base_reason = str(getattr(r, "why", "") or "").strip()
            if source == "trigger":
                reason = base_reason or "Trigger match"
            elif used_agentic:
                reason = base_reason or f"Hybrid-agentic route: {route_reason}"
            else:
                reason = base_reason or "Semantic route (embeddings primary)"

            advice.append(
                Advice(
                    advice_id=self._generate_advice_id(
                        r.insight_text, insight_key=r.insight_key, source=source
                    ),
                    insight_key=r.insight_key,
                    text=r.insight_text,
                    confidence=confidence,
                    source=source,
                    context_match=context_match,
                    reason=reason,
                )
            )

        self._log_retrieval_route(
            {
                "tool": tool_name,
                "profile_level": policy.get("level"),
                "profile_name": policy.get("profile"),
                "mode": mode,
                "gate_strategy": gate_strategy,
                "route": semantic_source,
                "escalated": used_agentic,
                "primary_count": primary_count,
                "primary_top_score": round(primary_top_score, 4),
                "returned_count": len(advice),
                "facets_used": len(facet_queries_executed),
                "facets_planned": len(facet_queries),
                "agentic_timed_out": agentic_timed_out,
                "agentic_rate_limit": agentic_rate_limit,
                "agentic_recent_rate": round(self._agentic_recent_rate(agentic_rate_window), 4),
                "active_insights": len(active_insights),
                "lexical_weight": lexical_weight,
                "semantic_context_min": semantic_context_min,
                "semantic_lexical_min": semantic_lexical_min,
                "semantic_strong_override": semantic_strong_override,
                "filtered_low_match": filtered_low_match,
                "filtered_domain_mismatch": filtered_domain_mismatch,
                "bm25_k1": bm25_k1,
                "bm25_b": bm25_b,
                "bm25_mix": bm25_mix,
                "fast_path_budget_ms": fast_path_budget_ms,
                "fast_path_elapsed_ms": primary_elapsed_ms,
                "fast_path_over_budget": primary_over_budget,
                "complexity_score": analysis.get("score"),
                "complexity_threshold": analysis.get("threshold"),
                "complexity_hits": analysis.get("complexity_hits") or [],
                "high_risk_hits": analysis.get("high_risk_hits") or [],
                "reasons": escalate_reasons[:6],
                "route_elapsed_ms": int((time.perf_counter() - route_start) * 1000),
            }
        )
        self._record_agentic_route(used_agentic, agentic_rate_window)
        return advice

    def _extract_agentic_queries(self, context: str, limit: int = 3) -> List[str]:
        """Extract compact facet queries from context for lightweight agentic retrieval."""
        tokens = []
        for raw in context.lower().replace("/", " ").replace("_", " ").split():
            t = raw.strip(".,:;()[]{}'\"`")
            if len(t) < 4:
                continue
            if t in {"with", "from", "that", "this", "into", "have", "should", "would", "could", "where", "when", "while"}:
                continue
            if not any(ch.isalnum() for ch in t):
                continue
            tokens.append(t)

        seen = set()
        facets: List[str] = []
        for t in tokens:
            if t in seen:
                continue
            seen.add(t)
            facets.append(t)
            if len(facets) >= limit:
                break

        return [f"{t} failure pattern and fix" for t in facets]

    def _is_x_social_query(self, text: str) -> bool:
        body = str(text or "").strip().lower()
        if not body:
            return False
        return any(marker in body for marker in X_SOCIAL_MARKERS)

    def _is_x_social_insight(self, text: str) -> bool:
        body = str(text or "").strip().lower()
        if not body:
            return False
        return any(marker in body for marker in X_SOCIAL_MARKERS)

    def _filter_cross_domain_advice(self, advice_list: List[Advice], context: str) -> List[Advice]:
        """Drop cross-domain social advice when the current query is not social."""
        if self._is_x_social_query(context):
            return list(advice_list)
        out: List[Advice] = []
        for item in advice_list:
            if self._is_x_social_insight(getattr(item, "text", "")):
                continue
            out.append(item)
        return out

    def _lexical_overlap_score(self, query: str, text: str) -> float:
        """Simple lexical overlap score [0..1] for hybrid rerank."""
        q = {t for t in re.findall(r"[a-z0-9_]+", query.lower()) if len(t) >= 3}
        d = {t for t in re.findall(r"[a-z0-9_]+", text.lower()) if len(t) >= 3}
        if not q or not d:
            return 0.0
        inter = len(q & d)
        union = max(len(q | d), 1)
        return inter / union

    def _bm25_normalized_scores(self, query: str, docs: List[str], k1: float = 1.2, b: float = 0.75) -> List[float]:
        """Compute normalized BM25 scores [0..1] for a query over docs."""
        if not docs:
            return []
        query_tokens = [t for t in re.findall(r"[a-z0-9_]+", query.lower()) if len(t) >= 3]
        if not query_tokens:
            return [0.0 for _ in docs]

        doc_tokens = [[t for t in re.findall(r"[a-z0-9_]+", str(doc).lower()) if len(t) >= 3] for doc in docs]
        n_docs = len(doc_tokens)
        avgdl = sum(len(toks) for toks in doc_tokens) / max(n_docs, 1)
        if avgdl <= 0:
            return [0.0 for _ in docs]

        df: Dict[str, int] = {}
        for toks in doc_tokens:
            for tok in set(toks):
                df[tok] = df.get(tok, 0) + 1

        qtf: Dict[str, int] = {}
        for tok in query_tokens:
            qtf[tok] = qtf.get(tok, 0) + 1

        raw_scores: List[float] = []
        for toks in doc_tokens:
            dl = max(len(toks), 1)
            tf: Dict[str, int] = {}
            for tok in toks:
                tf[tok] = tf.get(tok, 0) + 1
            score = 0.0
            for tok, q_count in qtf.items():
                term_df = df.get(tok, 0)
                if term_df <= 0:
                    continue
                idf = math.log(1.0 + ((n_docs - term_df + 0.5) / (term_df + 0.5)))
                term_tf = tf.get(tok, 0)
                if term_tf <= 0:
                    continue
                denom = term_tf + k1 * (1.0 - b + (b * (dl / avgdl)))
                if denom <= 0:
                    continue
                bm25_term = idf * ((term_tf * (k1 + 1.0)) / denom)
                score += bm25_term * float(q_count)
            raw_scores.append(score)

        max_score = max(raw_scores) if raw_scores else 0.0
        if max_score <= 0:
            return [0.0 for _ in docs]
        return [float(s / max_score) for s in raw_scores]

    def _hybrid_lexical_scores(
        self,
        query: str,
        docs: List[str],
        bm25_mix: float = 0.75,
        k1: float = 1.2,
        b: float = 0.75,
    ) -> List[float]:
        """Blend normalized BM25 and overlap into one lexical signal."""
        if not docs:
            return []
        bm25 = self._bm25_normalized_scores(query=query, docs=docs, k1=k1, b=b)
        overlap = [self._lexical_overlap_score(query, doc) for doc in docs]
        blend = max(0.0, min(1.0, float(bm25_mix)))
        return [(blend * bm) + ((1.0 - blend) * ov) for bm, ov in zip(bm25, overlap)]

    def _get_cognitive_advice_keyword(self, tool_name: str, context: str) -> List[Advice]:
        """Get advice from cognitive insights using keyword matching."""
        advice = []

        # Query insights relevant to this context
        insights = self.cognitive.get_insights_for_context(context, limit=10, with_keys=True)

        # Also get tool-specific insights
        tool_insights = self.cognitive.get_insights_for_context(tool_name, limit=5, with_keys=True)

        # Combine and dedupe
        seen = set()
        for insight_key, insight in insights + tool_insights:
            key = insight_key or insight.insight[:50]
            if key in seen:
                continue
            seen.add(key)

            if insight.reliability < MIN_RELIABILITY_FOR_ADVICE:
                continue
            if hasattr(self.cognitive, "is_noise_insight") and self.cognitive.is_noise_insight(insight.insight):
                continue

            # Calculate context match
            context_match = self._calculate_context_match(insight.context, context)

            # Task #13: Extract reason from evidence
            reason = ""
            if hasattr(insight, 'evidence') and insight.evidence:
                reason = insight.evidence[0][:100] if insight.evidence[0] else ""
            elif hasattr(insight, 'context') and insight.context:
                reason = f"From context: {insight.context[:80]}"

            advice.append(Advice(
                advice_id=self._generate_advice_id(
                    insight.insight, insight_key=insight_key, source="cognitive"
                ),
                insight_key=insight_key,
                text=insight.insight,
                confidence=insight.reliability,
                source="cognitive",
                context_match=context_match,
                reason=reason,
            ))

        return advice

    def _get_bank_advice(self, context: str) -> List[Advice]:
        """Get advice from memory banks (project/global)."""
        advice: List[Advice] = []
        try:
            project_key = infer_project_key()
            memories = bank_retrieve(context, project_key=project_key, limit=5)
        except Exception:
            return advice

        for mem in memories:
            text = (mem.get("text") or "").strip()
            if not text:
                continue
            if hasattr(self.cognitive, "is_noise_insight") and self.cognitive.is_noise_insight(text):
                continue
            # Filter metadata patterns like "X: Y = Z" (Task #16)
            if self._is_metadata_pattern(text):
                continue
            context_match = self._calculate_context_match(text, context)

            # Add reason from memory metadata (always provide a reason)
            reason = "From memory bank"  # Default fallback
            if mem.get("project_key"):
                reason = f"From project: {mem.get('project_key')}"
            elif mem.get("created_at"):
                created = mem.get('created_at', '')
                if isinstance(created, str):
                    reason = f"Stored: {created[:10]}"

            advice.append(Advice(
                advice_id=self._generate_advice_id(
                    text, insight_key=f"bank:{mem.get('entry_id', '')}", source="bank"
                ),
                insight_key=f"bank:{mem.get('entry_id', '')}",
                text=text[:200],
                confidence=0.65,
                source="bank",
                context_match=context_match,
                reason=reason,
            ))

        return advice

    def _get_mind_advice(self, context: str) -> List[Advice]:
        """Get advice from Mind persistent memory."""
        advice = []

        try:
            if hasattr(self.mind, "_check_mind_health") and not self.mind._check_mind_health():
                return advice
            memories = self.mind.retrieve_relevant(context, limit=5)

            seen_texts: set = set()
            for mem in memories:
                content = mem.get("content", "")
                salience = mem.get("salience", 0.5)

                if salience < MIND_MIN_SALIENCE:
                    continue
                if hasattr(self.cognitive, "is_noise_insight") and self.cognitive.is_noise_insight(content):
                    continue
                # Deduplicate identical or near-identical Mind memories
                dedup_key = content[:150].strip().lower()
                if dedup_key in seen_texts:
                    continue
                seen_texts.add(dedup_key)

                # Task #13: Add reason from Mind metadata
                reason = f"Salience: {salience:.1f}"
                if mem.get("temporal_level"):
                    levels = {1: "immediate", 2: "situational", 3: "seasonal", 4: "identity"}
                    reason = f"{levels.get(mem['temporal_level'], 'memory')} level memory"

                advice.append(Advice(
                    advice_id=self._generate_advice_id(
                        content, insight_key=f"mind:{mem.get('memory_id', 'unknown')[:12]}", source="mind"
                    ),
                    insight_key=f"mind:{mem.get('memory_id', 'unknown')[:12]}",
                    text=content[:200],
                    confidence=salience,
                    source="mind",
                    context_match=0.7,  # Mind already does semantic matching
                    reason=reason,
                ))
        except Exception:
            pass  # Mind unavailable, gracefully skip

        return advice

    def _insight_mentions_tool(self, tool_name: str, *texts: Any) -> bool:
        """Return True when text mentions the tool as a token, not a substring."""
        tool = str(tool_name or "").strip().lower()
        if not tool:
            return False

        token_pattern = re.compile(rf"(?<![a-z0-9]){re.escape(tool)}(?![a-z0-9])")
        normalized_tool = re.sub(r"[_\-\s]+", " ", tool).strip()
        normalized_pattern = None
        if normalized_tool and normalized_tool != tool:
            normalized_pattern = re.compile(
                rf"(?<![a-z0-9]){re.escape(normalized_tool)}(?![a-z0-9])"
            )

        for raw in texts:
            text = str(raw or "").strip().lower()
            if not text:
                continue
            if token_pattern.search(text):
                return True
            if normalized_pattern is not None:
                normalized_text = re.sub(r"[_\-\s]+", " ", text)
                if normalized_pattern.search(normalized_text):
                    return True
        return False

    def _get_tool_specific_advice(self, tool_name: str) -> List[Advice]:
        """Get advice specific to a tool based on past failures."""
        advice = []
        seen_texts = set()

        # Get self-awareness insights about this tool
        for insight in self.cognitive.get_self_awareness_insights():
            insight_text = str(getattr(insight, "insight", "") or "").strip()
            if not insight_text:
                continue
            if hasattr(self.cognitive, "is_noise_insight") and self.cognitive.is_noise_insight(insight_text):
                continue
            reliability = float(getattr(insight, "reliability", 0.0) or 0.0)
            if reliability < MIN_RELIABILITY_FOR_ADVICE:
                continue
            if not self._insight_mentions_tool(
                tool_name,
                insight_text,
                getattr(insight, "context", ""),
            ):
                continue

            dedupe_key = re.sub(r"\s+", " ", insight_text.lower())
            if dedupe_key in seen_texts:
                continue
            seen_texts.add(dedupe_key)

            # Task #13: Add validation count as reason
            reason = (
                f"Validated {insight.times_validated}x"
                if hasattr(insight, "times_validated")
                else ""
            )

            advice.append(Advice(
                advice_id=self._generate_advice_id(
                    f"[Caution] {insight_text}",
                    insight_key=f"tool:{tool_name}",
                    source="self_awareness",
                ),
                insight_key=f"tool:{tool_name}",
                text=f"[Caution] {insight_text}",
                confidence=reliability,
                source="self_awareness",
                context_match=1.0,  # Direct tool match
                reason=reason,
            ))

        return advice

    def _get_opportunity_advice(
        self,
        *,
        tool_name: str,
        context_raw: str,
        task_context: str = "",
    ) -> List[Advice]:
        """Generate Socratic opportunity prompts for user-facing guidance."""
        try:
            from .opportunity_scanner import generate_user_opportunities
        except Exception:
            return []

        try:
            rows = generate_user_opportunities(
                tool_name=tool_name,
                context=context_raw,
                task_context=task_context,
                session_id="default",
                persist=False,
            )
        except Exception:
            return []
        if not rows:
            return []

        out: List[Advice] = []
        for row in rows:
            question = str(row.get("question") or "").strip()
            next_step = str(row.get("next_step") or "").strip()
            if not question:
                continue
            text = f"[Opportunity] Ask: {question}"
            if next_step:
                text = f"{text} Next: {next_step}"
            out.append(
                Advice(
                    advice_id=self._generate_advice_id(
                        f"opportunity:{tool_name}:{question}",
                        insight_key=f"opportunity:{str(row.get('category') or 'general')}",
                        source="opportunity",
                    ),
                    insight_key=f"opportunity:{str(row.get('category') or 'general')}",
                    text=text,
                    confidence=float(row.get("confidence") or 0.65),
                    source="opportunity",
                    context_match=max(
                        0.55,
                        float(
                            row.get("context_match")
                            or self._calculate_context_match(question, context_raw)
                        ),
                    ),
                    reason=str(
                        row.get("rationale")
                        or "Opportunity scanner: Socratic improvement prompt"
                    ),
                )
            )
        return out

    def _get_chip_advice(self, context: str) -> List[Advice]:
        """Get advice from recent high-quality chip insights."""
        advice: List[Advice] = []
        if _chips_disabled():
            return advice
        if not CHIP_INSIGHTS_DIR.exists():
            return advice

        candidates: List[Dict[str, Any]] = []
        files = sorted(
            CHIP_INSIGHTS_DIR.glob("*.jsonl"),
            key=lambda p: p.stat().st_mtime if p.exists() else 0,
            reverse=True,
        )[:CHIP_ADVICE_MAX_FILES]

        for file_path in files:
            for raw in _tail_jsonl(file_path, CHIP_ADVICE_FILE_TAIL):
                try:
                    row = json.loads(raw)
                except Exception:
                    continue
                quality = (row.get("captured_data") or {}).get("quality_score") or {}
                score = float(quality.get("total", 0.0) or 0.0)
                conf = float(row.get("confidence") or score or 0.0)
                if score < CHIP_ADVICE_MIN_SCORE and conf < MIN_RELIABILITY_FOR_ADVICE:
                    continue
                text = str(
                    row.get("content")
                    or row.get("insight")
                    or row.get("text")
                    or row.get("summary")
                    or ""
                ).strip()
                if not text:
                    continue
                chip_id = str(row.get("chip_id") or file_path.stem).strip()
                if self._is_telemetry_chip_row(chip_id, text):
                    continue
                if hasattr(self.cognitive, "is_noise_insight") and self.cognitive.is_noise_insight(text):
                    continue
                if self._is_metadata_pattern(text):
                    continue
                context_match = self._calculate_context_match(text, context)
                domain_bonus = self._chip_domain_bonus(chip_id, context)
                if context_match < 0.08 and domain_bonus < 0.05:
                    continue
                if context_match < 0.05 and score < (CHIP_ADVICE_MIN_SCORE + 0.1):
                    continue
                candidates.append(
                    {
                        "chip_id": chip_id,
                        "observer": row.get("observer_name") or "observer",
                        "text": text,
                        "score": score,
                        "confidence": conf,
                        "context_match": context_match,
                        "rank": (0.45 * score) + (0.35 * conf) + (0.20 * context_match) + domain_bonus,
                    }
                )

        # Rank and dedupe.
        seen = set()
        candidates.sort(key=lambda x: (x["rank"], x["score"], x["confidence"]), reverse=True)
        for item in candidates:
            key = item["text"][:180].strip().lower()
            if key in seen:
                continue
            seen.add(key)
            context_match = float(item.get("context_match") or 0.0)
            reason = f"{item['chip_id']}/{item['observer']} quality={item['score']:.2f}"
            advice.append(
                Advice(
                    advice_id=self._generate_advice_id(
                        f"[Chip:{item['chip_id']}] {item['text'][:220]}",
                        insight_key=f"chip:{item['chip_id']}:{item['observer']}",
                        source="chip",
                    ),
                    insight_key=f"chip:{item['chip_id']}:{item['observer']}",
                    text=f"[Chip:{item['chip_id']}] {item['text'][:220]}",
                    confidence=min(1.0, max(item["confidence"], item["score"])),
                    source="chip",
                    context_match=context_match,
                    reason=reason,
                )
            )
            if len(advice) >= CHIP_ADVICE_LIMIT:
                break

        return advice

    def _is_telemetry_chip_row(self, chip_id: str, text: str) -> bool:
        chip = str(chip_id or "").strip().lower()
        if chip in CHIP_TELEMETRY_BLOCKLIST:
            return True
        payload = str(text or "").strip().lower()
        if not payload:
            return True
        if any(marker in payload for marker in CHIP_TELEMETRY_MARKERS):
            return True
        return False

    def _chip_domain_bonus(self, chip_id: str, context: str) -> float:
        chip = str(chip_id or "").strip().lower()
        text = str(context or "").strip().lower()
        if not chip or not text:
            return 0.0

        social_query = self._is_x_social_query(text)
        coding_query = any(t in text for t in ("code", "refactor", "test", "debug", "python", "module"))
        marketing_query = any(t in text for t in ("marketing", "campaign", "conversion", "audience", "brand"))
        memory_query = any(t in text for t in ("memory", "retrieval", "cross-session", "stale", "distillation"))

        social_chip = any(t in chip for t in ("social", "x_", "x-", "engagement"))
        coding_chip = any(t in chip for t in ("vibecoding", "api-design", "game_dev"))
        marketing_chip = any(t in chip for t in ("marketing", "market-intel", "biz-ops"))

        bonus = 0.0
        if social_query and social_chip:
            bonus += 0.15
        if coding_query and coding_chip:
            bonus += 0.12
        if marketing_query and marketing_chip:
            bonus += 0.12
        if memory_query and coding_chip:
            bonus += 0.06

        if not social_query and social_chip:
            bonus -= 0.08
        return bonus

    def _get_surprise_advice(self, tool_name: str, context: str) -> List[Advice]:
        """Get advice from past surprises (unexpected failures)."""
        advice = []

        try:
            from .aha_tracker import get_aha_tracker
            aha = get_aha_tracker()

            # Get recent surprises related to this tool/context
            for surprise in aha.get_recent_surprises(30):
                if surprise.surprise_type != "unexpected_failure":
                    continue
                if tool_name.lower() not in str(surprise.context).lower():
                    continue
                lesson = surprise.lesson_extracted or "Be careful - this failed unexpectedly before"

                # Add reason with timestamp and context
                reason = f"Failed on {surprise.timestamp[:10] if hasattr(surprise, 'timestamp') else 'recently'}"
                if hasattr(surprise, 'context') and surprise.context:
                    reason += f" in {str(surprise.context)[:30]}"

                advice.append(Advice(
                    advice_id=self._generate_advice_id(
                        f"[Past Failure] {lesson}",
                        insight_key=f"surprise:{surprise.surprise_type}",
                        source="surprise",
                    ),
                    insight_key=f"surprise:{surprise.surprise_type}",
                    text=f"[Past Failure] {lesson}",
                    confidence=0.8,
                    source="surprise",
                    context_match=0.9,
                    reason=reason,
                ))
        except Exception:
            pass  # aha_tracker might not be available

        return advice

    def _get_skill_advice(self, context: str) -> List[Advice]:
        """Get hints from relevant skills."""
        advice: List[Advice] = []
        try:
            from .skills_router import recommend_skills
            skills = recommend_skills(context, limit=3)
        except Exception:
            return advice

        for s in skills:
            sid = s.get("skill_id") or s.get("name") or "unknown-skill"
            desc = (s.get("description") or "").strip()
            if desc:
                text = f"Consider skill [{sid}]: {desc[:120]}"
            else:
                text = f"Consider skill [{sid}]"

            # Add reason from skill relevance
            reason = f"Matched: {s.get('match_reason', 'context keywords')}" if s.get('match_reason') else "Relevant to context"

            advice.append(Advice(
                advice_id=self._generate_advice_id(text, insight_key=f"skill:{sid}", source="skill"),
                insight_key=f"skill:{sid}",
                text=text,
                confidence=0.6,
                source="skill",
                context_match=0.7,
                reason=reason,
            ))

        return advice

    def _get_eidos_advice(self, tool_name: str, context: str) -> List[Advice]:
        """Get advice from EIDOS distillations (extracted rules from patterns)."""
        advice = []

        if not HAS_EIDOS:
            return advice

        try:
            retriever = get_retriever()

            # Build intent from tool and context
            intent = f"{tool_name} {context[:80]}"

            # Get distillations for this intent (includes policies, heuristics, anti-patterns)
            distillations = retriever.retrieve_for_intent(intent)

            for d in distillations[:5]:
                # Determine advice type label based on distillation type
                type_label = d.type.value.upper() if hasattr(d.type, 'value') else str(d.type)

                # Add reason from distillation confidence and usage
                reason = f"Confidence: {d.confidence:.0%}"
                if hasattr(d, 'usage_count') and d.usage_count:
                    reason += f", used {d.usage_count}x"

                # Compute real context match instead of hardcoding 0.85
                eidos_match = self._calculate_context_match(d.statement, context)

                advice.append(Advice(
                    advice_id=self._generate_advice_id(
                        f"[EIDOS {type_label}] {d.statement}",
                        insight_key=f"eidos:{d.type.value}:{d.distillation_id[:8]}",
                        source="eidos",
                    ),
                    insight_key=f"eidos:{d.type.value}:{d.distillation_id[:8]}",
                    text=f"[EIDOS {type_label}] {d.statement}",
                    confidence=d.confidence,
                    source="eidos",
                    context_match=eidos_match,
                    reason=reason,
                ))
                # Record usage (will mark helped=True on positive outcome)
                retriever.record_usage(d.distillation_id, helped=False)

        except Exception:
            pass  # Don't break advice flow if EIDOS retrieval fails

        return advice

    def _get_niche_advice(self, tool_name: str, context: str) -> List[Advice]:
        """Get niche intelligence advice.

        Activates for X user profile tools or engagement contexts.
        Surfaces active opportunities and relationship context.
        """
        advice: List[Advice] = []

        niche_signals = [
            "profile", "user", "follower", "following", "engage",
            "x-twitter", "community", "niche", "network", "relationship",
        ]
        if not any(s in context for s in niche_signals):
            return advice

        try:
            from lib.niche_mapper import get_niche_mapper

            mapper = get_niche_mapper()

            # Surface active high-urgency opportunities
            opps = mapper.get_active_opportunities(min_urgency=4)
            for opp in opps[:2]:
                text = (
                    f"[NicheNet] Opportunity: engage @{opp.target} - "
                    f"{opp.reason} (urgency {opp.urgency}/5, "
                    f"tone: {opp.suggested_tone})"
                )
                advice.append(Advice(
                    advice_id=self._generate_advice_id(
                        text, insight_key=f"niche:opp:{opp.target}", source="niche"
                    ),
                    insight_key=f"niche:opp:{opp.target}",
                    text=text,
                    confidence=min(0.8, opp.urgency * 0.15),
                    source="niche",
                    context_match=0.7,
                    reason=opp.reason,
                ))

            # Surface warm relationship context for relevant handles
            for handle in list(mapper.accounts.keys())[:100]:
                if handle in context:
                    acct = mapper.accounts[handle]
                    if acct.warmth in ("warm", "hot", "ally"):
                        text = (
                            f"[NicheNet] @{handle} is {acct.warmth} "
                            f"({acct.interaction_count} interactions, "
                            f"topics: {', '.join(acct.topics[:3])})"
                        )
                        advice.append(Advice(
                            advice_id=self._generate_advice_id(
                                text, insight_key=f"niche:warmth:{handle}", source="niche"
                            ),
                            insight_key=f"niche:warmth:{handle}",
                            text=text,
                            confidence=0.75,
                            source="niche",
                            context_match=0.9,
                            reason=f"Relationship: {acct.warmth}",
                        ))
                        break  # Only one relationship hint per call

        except Exception:
            pass

        return advice

    def _get_engagement_advice(self, tool_name: str, context: str) -> List[Advice]:
        """Get engagement pulse advice.

        Activates when posting tweets or checking engagement.
        Surfaces prediction accuracy and recent surprises.
        """
        advice: List[Advice] = []

        engagement_signals = [
            "tweet", "post", "engagement", "likes", "performance",
            "x-twitter", "viral", "thread",
        ]
        if not any(s in context for s in engagement_signals):
            return advice

        try:
            from lib.engagement_tracker import get_engagement_tracker

            tracker = get_engagement_tracker()
            stats = tracker.get_stats()

            # Surface prediction accuracy if we have data
            accuracy = stats.get("prediction_accuracy", {})
            if accuracy.get("total_predictions", 0) >= 5:
                acc_pct = accuracy.get("accuracy", 0)
                text = (
                    f"[Pulse] Engagement prediction accuracy: {acc_pct}% "
                    f"(avg ratio: {accuracy.get('avg_ratio', 0)}x)"
                )
                advice.append(Advice(
                    advice_id=self._generate_advice_id(
                        text, insight_key="engagement:accuracy", source="engagement"
                    ),
                    insight_key="engagement:accuracy",
                    text=text,
                    confidence=0.7,
                    source="engagement",
                    context_match=0.7,
                    reason=f"Based on {accuracy.get('total_predictions', 0)} predictions",
                ))

            # Surface recent surprises
            surprises = [
                t for t in tracker.tracked.values() if t.surprise_detected
            ]
            for s in surprises[-2:]:
                text = (
                    f"[Pulse] Recent {s.surprise_type}: "
                    f"'{s.content_preview[:60]}' ({s.surprise_ratio}x prediction)"
                )
                advice.append(Advice(
                    advice_id=self._generate_advice_id(
                        text,
                        insight_key=f"engagement:surprise:{s.tweet_id[:8]}",
                        source="engagement",
                    ),
                    insight_key=f"engagement:surprise:{s.tweet_id[:8]}",
                    text=text,
                    confidence=0.65,
                    source="engagement",
                    context_match=0.6,
                    reason=f"Surprise ratio: {s.surprise_ratio}x",
                ))

        except Exception:
            pass

        return advice

    def _get_convo_advice(self, tool_name: str, context: str) -> List[Advice]:
        """Get conversation intelligence advice from ConvoIQ.

        Only activates for X/Twitter reply tools or when context mentions
        replies, conversations, or engagement.
        """
        advice: List[Advice] = []

        # Only trigger for relevant contexts
        convo_signals = [
            "reply", "respond", "tweet", "thread", "engagement",
            "x-twitter", "conversation", "quote", "mention",
        ]
        if not any(s in context for s in convo_signals):
            return advice

        try:
            from lib.convo_analyzer import get_convo_analyzer

            analyzer = get_convo_analyzer()
            stats = analyzer.get_stats()

            # Surface top DNA patterns as advice
            for dna_key, dna in list(analyzer.dna_patterns.items())[:3]:
                if dna.engagement_score >= 5.0 and dna.times_seen >= 2:
                    text = (
                        f"[ConvoIQ] {dna.hook_type} hooks with {dna.tone} tone "
                        f"work well (engagement {dna.engagement_score:.0f}/10, "
                        f"seen {dna.times_seen}x)"
                    )
                    ctx_match = self._calculate_context_match(
                        f"{dna.hook_type} {dna.tone} {dna.pattern_type}",
                        context,
                    )
                    advice.append(Advice(
                        advice_id=self._generate_advice_id(
                            text, insight_key=f"convo:dna:{dna_key}", source="convo"
                        ),
                        insight_key=f"convo:dna:{dna_key}",
                        text=text,
                        confidence=min(0.9, 0.5 + dna.times_seen * 0.1),
                        source="convo",
                        context_match=ctx_match,
                        reason=f"DNA pattern validated {dna.times_seen}x",
                    ))

            # If replying to someone, recommend best hook
            if "reply" in context or "respond" in context:
                # Extract parent text hint from context if available
                rec = analyzer.get_best_hook(context[:200])
                text = (
                    f"[ConvoIQ] Try {rec.hook_type} hook with {rec.tone} tone: "
                    f"{rec.reasoning}"
                )
                advice.append(Advice(
                    advice_id=self._generate_advice_id(
                        text, insight_key=f"convo:hook:{rec.hook_type}", source="convo"
                    ),
                    insight_key=f"convo:hook:{rec.hook_type}",
                    text=text,
                    confidence=rec.confidence,
                    source="convo",
                    context_match=0.8,
                    reason=rec.reasoning,
                ))

        except Exception:
            pass  # Don't break advice flow if ConvoIQ isn't available

        return advice

    def _calculate_context_match(self, insight_context: str, current_context: str) -> float:
        """Calculate how well an insight's context matches current context."""
        if not insight_context or not current_context:
            return 0.5

        insight_words = set(insight_context.lower().split())
        current_words = set(current_context.lower().split())

        if not insight_words:
            return 0.5

        overlap = len(insight_words & current_words)
        return min(1.0, overlap / max(len(insight_words), 1) + 0.3)

    def _is_metadata_pattern(self, text: str) -> bool:
        """Detect metadata patterns that aren't actionable advice.

        Filters patterns like:
        - "User communication style: detail_level = concise"
        - "X: Y = Z" key-value metadata
        - Incomplete sentence fragments
        """
        import re

        text_stripped = text.strip()

        # Pattern 1: Key-value metadata "X: Y = Z" or "X: Y"
        # e.g., "User communication style: detail_level = concise"
        if re.match(r'^[A-Za-z\s]+:\s*[a-z_]+\s*=\s*.+$', text_stripped):
            return True

        # Pattern 2: Simple "Label: value" metadata without actionable content
        # e.g., "Principle: it is according to..."
        if re.match(r'^(Principle|Style|Setting|Config|Meta|Mode|Level|Type):\s*', text_stripped, re.I):
            # Only filter if it doesn't contain action verbs
            action_verbs = ['use', 'avoid', 'check', 'verify', 'ensure', 'always',
                           'never', 'remember', "don't", 'prefer', 'try', 'run']
            if not any(v in text_stripped.lower() for v in action_verbs):
                return True

        # Pattern 3: Underscore-style metadata keys
        # e.g., "detail_level", "code_style", "response_format"
        if re.match(r'^[a-z_]+\s*[:=]\s*.+$', text_stripped):
            return True

        # Pattern 4: Very short fragments (likely metadata, not advice)
        if len(text_stripped) < 15 and ':' in text_stripped:
            return True

        # Pattern 5: Incomplete sentences ending with conjunctions/prepositions
        incomplete_endings = [' that', ' the', ' a', ' an', ' of', ' to', ' for',
                             ' with', ' and', ' or', ' but', ' in', ' on', ' we']
        if any(text_stripped.lower().endswith(e) for e in incomplete_endings):
            return True

        return False

    def _score_actionability(self, text: str) -> float:
        """Score how actionable advice is (0.0 to 1.0).

        Actionable advice tells you WHAT TO DO, not just observations.
        """
        text_lower = text.lower()
        score = 0.5  # Base score

        # Strong action verbs = highly actionable (+0.3)
        action_verbs = ['use ', 'avoid ', 'check ', 'verify ', 'ensure ', 'always ',
                        'never ', 'remember ', "don't ", 'prefer ', 'try ', 'run ']
        if any(v in text_lower for v in action_verbs):
            score += 0.3

        # When-then patterns = conditional guidance (+0.2)
        conditional_patterns = ['when ', 'if ', 'before ', 'after ', 'instead of']
        if any(p in text_lower for p in conditional_patterns):
            score += 0.2

        # Vague/observational = less actionable (-0.2)
        vague_patterns = ['user prefers', 'user likes', 'seems to', 'might be', 'probably']
        if any(p in text_lower for p in vague_patterns):
            score -= 0.2

        # EIDOS/Caution tags = already validated (+0.1)
        if text.startswith('[EIDOS') or text.startswith('[Caution]'):
            score += 0.1

        return max(0.1, min(1.0, score))

    # Source quality tiers (Task #10: boost validated sources)
    _SOURCE_BOOST = {
        "eidos": 1.4,           # EIDOS distillations are validated patterns
        "self_awareness": 1.3,  # Tool-specific cautions from past failures
        "convo": 1.2,           # Conversation intelligence (ConvoIQ)
        "engagement": 1.15,     # Engagement pulse predictions
        "niche": 1.1,           # Niche intelligence network
        "cognitive": 1.0,       # Standard cognitive insights
        "mind": 1.0,            # Mind memories
        "bank": 0.9,            # Memory banks (less curated)
        "chip": 1.15,           # Domain-specific chip intelligence
        "semantic": 1.05,       # Semantic retrieval of cognitive insights
        "semantic-hybrid": 1.08,  # Backward-compatible label for hybrid retrieval
        "semantic-agentic": 1.12,  # Agentic retrieval over semantic shortlist
        "trigger": 1.2,         # Explicit trigger rules
        "opportunity": 1.18,    # Socratic opportunity prompts
    }

    def _rank_score(self, a: Advice) -> float:
        """Compute a relevance score for a single advice item."""
        base_score = a.confidence * a.context_match

        # Source quality boost (Task #10)
        base_score *= self._SOURCE_BOOST.get(a.source, 1.0)

        # Actionability boost (Task #9)
        actionability = self._score_actionability(a.text)
        base_score *= (0.5 + actionability)  # 0.5x to 1.5x based on actionability

        # Insight-level outcome boost (Task #11)
        try:
            from .meta_ralph import get_meta_ralph
            ralph = get_meta_ralph()
        except Exception:
            ralph = None
        if ralph and a.insight_key:
            insight_effectiveness = ralph.get_insight_effectiveness(a.insight_key)
            base_score *= (0.5 + insight_effectiveness)

        # Boost based on source-level past effectiveness (fallback)
        source_stats = self.effectiveness.get("by_source", {}).get(a.source, {})
        if source_stats.get("total", 0) > 0:
            helpful_rate = source_stats.get("helpful", 0) / source_stats["total"]
            base_score *= (0.8 + helpful_rate * 0.4)  # 0.8x to 1.2x

        return base_score

    def _rank_advice(self, advice_list: List[Advice]) -> List[Advice]:
        """Rank advice by relevance, actionability, and effectiveness."""
        return sorted(advice_list, key=self._rank_score, reverse=True)

    def _log_advice(
        self,
        advice_list: List[Advice],
        tool: str,
        context: str,
        trace_id: Optional[str] = None,
        log_recent: bool = True,
    ):
        """Log advice given for later analysis."""
        if not advice_list:
            return

        entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool,
            "context": context[:100],
            "trace_id": trace_id,
            "advice_ids": [a.advice_id for a in advice_list],
            "advice_texts": [a.text[:100] for a in advice_list],
            "insight_keys": [a.insight_key for a in advice_list],
            "sources": [a.source for a in advice_list],
        }

        _append_jsonl_capped(ADVICE_LOG, entry, max_lines=4000)

        self.effectiveness["total_advice_given"] += len(advice_list)
        self._save_effectiveness()

        if log_recent:
            # Default direct-advisor semantics: advice retrieved is assumed delivered.
            record_recent_delivery(
                tool=tool,
                advice_list=advice_list,
                trace_id=trace_id,
                route="advisor",
                delivered=True,
            )

    def _get_recent_advice_entry(
        self,
        tool_name: str,
        trace_id: Optional[str] = None,
        allow_task_fallback: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Return the most recent advice entry for a tool within TTL.

        Uses fuzzy matching to handle tool name variations:
        - "Bash" matches "Bash command"
        - "Edit" matches "Edit file"
        - "Read" matches "Read code"
        """
        if not RECENT_ADVICE_LOG.exists():
            return None
        try:
            lines = _tail_jsonl(RECENT_ADVICE_LOG, RECENT_ADVICE_MAX_LINES)
        except Exception:
            return None

        now = time.time()
        tool_lower = (tool_name or "").strip().lower()  # Case-insensitive matching
        if not tool_lower:
            return None
        task_fallback = None  # Track most recent task advice as fallback
        prefix_match = None  # Track prefix matches (e.g., "Bash" in "Bash command")
        trace_match = None

        for line in reversed(lines[-RECENT_ADVICE_MAX_LINES:]):
            try:
                entry = json.loads(line)
            except Exception:
                continue

            ts = float(entry.get("ts") or 0.0)
            if now - ts > RECENT_ADVICE_MAX_AGE_S:
                continue  # Too old

            entry_trace = (entry.get("trace_id") or "").strip()
            if trace_id and entry_trace and entry_trace == str(trace_id).strip():
                trace_match = entry
                break

            entry_tool = entry.get("tool", "").lower()

            # Exact tool match - return immediately
            if entry_tool == tool_lower:
                return entry

            # Prefix match: "Bash" matches "bash command", "Edit" matches "edit file"
            if prefix_match is None:
                if entry_tool.startswith(tool_lower + " ") or entry_tool.startswith(tool_lower + "_"):
                    prefix_match = entry
                elif tool_lower.startswith(entry_tool + " ") or tool_lower.startswith(entry_tool + "_"):
                    prefix_match = entry

            # Optional fallback for explicit Task-tool flows.
            if entry_tool == "task" and task_fallback is None:
                task_fallback = entry

        # Prefer exact trace match; otherwise use tool/prefix fallback.
        if trace_match:
            return trace_match
        if prefix_match:
            return prefix_match
        if allow_task_fallback or tool_lower == "task":
            return task_fallback
        return None

    def _find_recent_advice_by_id(self, advice_id: str) -> Optional[Dict[str, Any]]:
        """Find recent advice entry containing a specific advice_id."""
        if not RECENT_ADVICE_LOG.exists() or not advice_id:
            return None
        try:
            lines = _tail_jsonl(RECENT_ADVICE_LOG, RECENT_ADVICE_MAX_LINES)
        except Exception:
            return None
        for line in reversed(lines[-RECENT_ADVICE_MAX_LINES:]):
            try:
                entry = json.loads(line)
            except Exception:
                continue
            ids = entry.get("advice_ids") or []
            if advice_id in ids:
                return entry
        return None

    # ============= Outcome Tracking =============

    def report_outcome(
        self,
        advice_id: str,
        was_followed: bool,
        was_helpful: Optional[bool] = None,
        notes: str = "",
        trace_id: Optional[str] = None,
    ):
        """
        Report whether advice was followed and if it helped.

        This closes the feedback loop - we learn which advice actually works.

        Args:
            advice_id: ID of the advice
            was_followed: Did the user/agent follow this advice?
            was_helpful: If followed, did it help? (None if unclear)
            notes: Optional notes about the outcome
        """
        outcome = AdviceOutcome(
            advice_id=advice_id,
            was_followed=was_followed,
            was_helpful=was_helpful,
            outcome_notes=notes,
        )

        # Update effectiveness stats
        inc_followed, inc_helpful = self._mark_outcome_counted(
            advice_id=advice_id,
            was_followed=was_followed,
            was_helpful=was_helpful,
        )
        if inc_followed:
            self.effectiveness["total_followed"] += 1
        if inc_helpful:
            self.effectiveness["total_helpful"] += 1

        self._save_effectiveness()
        self._record_cognitive_helpful(advice_id, was_helpful)

        # Track outcome in Meta-Ralph
        try:
            from .meta_ralph import get_meta_ralph
            ralph = get_meta_ralph()
            outcome_str = (
                "good" if was_helpful is True
                else ("bad" if was_helpful is False else None)
            )
            # Avoid overwriting an existing explicit outcome with "unknown".
            if outcome_str:
                # Best-effort: enrich with insight_key/source and trace binding so outcomes
                # can flow back to the correct learning and be strictly attributable.
                ik = None
                src = None
                derived_trace = None
                try:
                    entry = self._find_recent_advice_by_id(advice_id)
                    if entry:
                        ids = entry.get("advice_ids") or []
                        idx = ids.index(advice_id) if advice_id in ids else -1
                        if idx >= 0:
                            iks = entry.get("insight_keys") or []
                            srcs = entry.get("sources") or []
                            if idx < len(iks):
                                ik = iks[idx]
                            if idx < len(srcs):
                                src = srcs[idx]
                        derived_trace = entry.get("trace_id")
                except Exception:
                    pass

                ralph.track_outcome(
                    advice_id,
                    outcome_str,
                    notes,
                    # Prefer the retrieval trace (from recent advice log) when available,
                    # so strict attribution remains trace-bound even if callers report
                    # the outcome under a follow-on trace.
                    trace_id=derived_trace or trace_id,
                    insight_key=ik,
                    source=src,
                )
        except Exception:
            pass  # Don't break outcome flow if tracking fails

        # Log outcome
        with open(ADVICE_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({"outcome": asdict(outcome)}) + "\n")

    def report_action_outcome(
        self,
        tool_name: str,
        success: bool,
        advice_was_relevant: bool = False,
        trace_id: Optional[str] = None,
    ):
        """
        Simplified outcome reporting after any action.

        Call this after each tool execution to build the feedback loop.
        """
        # Update source effectiveness based on whether advice helped
        entry = self._get_recent_advice_entry(tool_name, trace_id=trace_id)

        # Use actual source from recent advice (not hardcoded "cognitive")
        source = "cognitive"  # Default fallback
        if entry:
            sources = entry.get("sources") or []
            if sources:
                source = sources[0]  # Primary source

        if source not in self.effectiveness.get("by_source", {}):
            self.effectiveness.setdefault("by_source", {})[source] = {
                "total": 0, "helpful": 0
            }

        self.effectiveness["by_source"][source]["total"] += 1
        if success and advice_was_relevant:
            self.effectiveness["by_source"][source]["helpful"] += 1

        self._save_effectiveness()

        # Report outcome to Meta-Ralph for feedback loop.
        # Track ALL outcomes, not just ones with prior advice.
        outcome_str = "good" if success else "bad"
        evidence = f"tool={tool_name} success={success}"

        try:
            from .meta_ralph import get_meta_ralph
            ralph = get_meta_ralph()

            # If there was prior advice, link outcomes to those advice IDs
            # CRITICAL: propagate insight_keys so outcomes link to actual insights
            if entry:
                advice_ids = entry.get("advice_ids") or []
                insight_keys = entry.get("insight_keys") or []
                entry_sources = entry.get("sources") or []
                for i, aid in enumerate(advice_ids):
                    # Propagate insight_key to Meta-Ralph so outcome records
                    # can flow back to cognitive insight reliability scoring
                    ik = insight_keys[i] if i < len(insight_keys) else None
                    src = entry_sources[i] if i < len(entry_sources) else None
                    ralph.track_outcome(
                        aid, outcome_str, evidence,
                        trace_id=trace_id,
                        insight_key=ik,
                        source=src,
                    )
                    # Record that advice was seen, but do NOT auto-mark as
                    # helpful just because the tool succeeded.  Only explicit
                    # feedback (advice_was_relevant=True) or failure-after-advice
                    # (False) should count.  None = unknown.
                    was_followed = bool(advice_was_relevant)
                    was_helpful = (
                        True if (advice_was_relevant and success)
                        else (False if (advice_was_relevant and not success) else None)
                    )
                    self.report_outcome(
                        aid,
                        was_followed=was_followed,
                        was_helpful=was_helpful,
                        notes=f"Auto-linked from {tool_name}",
                        trace_id=trace_id,
                    )

            # Also track tool-level outcome (even without specific advice)
            tool_outcome_id = f"tool:{tool_name}"
            ralph.track_outcome(tool_outcome_id, outcome_str, evidence, trace_id=trace_id)
        except Exception:
            pass

    def record_advice_feedback(
        self,
        helpful: Optional[bool],
        notes: str = "",
        tool: Optional[str] = None,
        advice_id: Optional[str] = None,
        followed: bool = True,
    ) -> Dict[str, Any]:
        """Record explicit feedback on advice helpfulness.

        If advice_id is provided, records outcome for that advice.
        Else if tool is provided, uses the most recent advice entry for that tool.
        """
        if advice_id:
            self.report_outcome(advice_id, was_followed=followed, was_helpful=helpful, notes=notes or "")
            try:
                entry = self._find_recent_advice_by_id(advice_id)
                insight_keys = []
                sources = []
                tool_name = tool
                if entry:
                    tool_name = tool_name or entry.get("tool")
                    ids = entry.get("advice_ids") or []
                    idx = ids.index(advice_id) if advice_id in ids else -1
                    ik = entry.get("insight_keys") or []
                    src = entry.get("sources") or []
                    if 0 <= idx < len(ik):
                        insight_keys = [ik[idx]]
                    if 0 <= idx < len(src):
                        sources = [src[idx]]
                from .advice_feedback import record_feedback
                record_feedback(
                    advice_ids=[advice_id],
                    tool=tool_name,
                    helpful=helpful,
                    followed=followed,
                    notes=notes or "",
                    insight_keys=insight_keys,
                    sources=sources,
                )
            except Exception:
                pass
            return {"status": "ok", "advice_ids": [advice_id], "tool": tool}

        if tool:
            entry = self._get_recent_advice_entry(tool)
            if not entry:
                return {"status": "not_found", "message": "No recent advice found for tool", "tool": tool}
            advice_ids = entry.get("advice_ids") or []
            if not advice_ids:
                return {"status": "not_found", "message": "Recent advice had no advice_ids", "tool": tool}
            for aid in advice_ids:
                self.report_outcome(aid, was_followed=followed, was_helpful=helpful, notes=notes or "")
            try:
                insight_keys = entry.get("insight_keys") or []
                sources = entry.get("sources") or []
                from .advice_feedback import record_feedback
                record_feedback(
                    advice_ids=advice_ids,
                    tool=tool,
                    helpful=helpful,
                    followed=followed,
                    notes=notes or "",
                    insight_keys=insight_keys,
                    sources=sources,
                )
            except Exception:
                pass
            return {"status": "ok", "advice_ids": advice_ids, "tool": tool}

        return {"status": "error", "message": "Provide advice_id or tool"}

    # ============= Quick Access Methods =============

    def get_quick_advice(self, tool_name: str) -> Optional[str]:
        """
        Get single most relevant piece of advice for a tool.

        This is the simplest integration point - just call this before any action.
        """
        advice_list = self.advise(tool_name, {}, include_mind=False)
        if advice_list:
            return advice_list[0].text
        return None

    def should_be_careful(self, tool_name: str) -> Tuple[bool, str]:
        """
        Quick check: should we be extra careful with this tool?

        Returns (should_be_careful, reason)
        """
        # Check self-awareness for struggles with this tool
        for insight in self.cognitive.get_self_awareness_insights():
            insight_text = str(getattr(insight, "insight", "") or "").strip()
            if not insight_text:
                continue
            if not self._insight_mentions_tool(tool_name, insight_text, getattr(insight, "context", "")):
                continue
            lowered = insight_text.lower()
            if "struggle" in lowered or "fail" in lowered:
                return True, insight_text

        return False, ""

    def get_effectiveness_report(self) -> Dict:
        """Get report on how effective advice has been."""
        total = self.effectiveness.get("total_advice_given", 0)
        followed = self.effectiveness.get("total_followed", 0)
        helpful = self.effectiveness.get("total_helpful", 0)

        return {
            "total_advice_given": total,
            "follow_rate": followed / max(total, 1),
            "helpfulness_rate": helpful / max(followed, 1) if followed > 0 else 0,
            "by_source": self.effectiveness.get("by_source", {}),
        }

    def compute_contrast_effectiveness(self) -> Dict[str, Any]:
        """
        Compute advice effectiveness by contrasting tool outcomes WITH vs WITHOUT advice.

        This is a background analysis that provides a true measure of advice value
        by comparing success rates when advice was present vs absent.

        Returns:
            Dict with per-tool contrast ratios and overall effectiveness estimate.
        """
        try:
            from .meta_ralph import get_meta_ralph
            ralph = get_meta_ralph()
        except Exception:
            return {"error": "Meta-Ralph unavailable"}

        # Collect outcome records that have insight_keys (advice was present)
        with_advice = {"good": 0, "bad": 0}
        without_advice = {"good": 0, "bad": 0}
        by_tool: Dict[str, Dict[str, Dict[str, int]]] = {}

        for rec in ralph.outcome_records.values():
            outcome = ralph._normalize_outcome(rec.outcome)
            if outcome not in ("good", "bad"):
                continue

            # Determine if this was a tool-level record or advice-linked
            lid = rec.learning_id or ""
            tool_name = ""
            has_advice = bool(rec.insight_key)

            if lid.startswith("tool:"):
                tool_name = lid[5:]
            elif rec.outcome_evidence:
                # Extract tool from evidence "tool=X success=Y"
                for part in rec.outcome_evidence.split():
                    if part.startswith("tool="):
                        tool_name = part[5:]
                        break

            if not tool_name:
                continue

            if tool_name not in by_tool:
                by_tool[tool_name] = {
                    "with_advice": {"good": 0, "bad": 0},
                    "without_advice": {"good": 0, "bad": 0},
                }

            if has_advice:
                with_advice[outcome] += 1
                by_tool[tool_name]["with_advice"][outcome] += 1
            else:
                without_advice[outcome] += 1
                by_tool[tool_name]["without_advice"][outcome] += 1

        # Compute contrast ratios
        wa_total = with_advice["good"] + with_advice["bad"]
        wo_total = without_advice["good"] + without_advice["bad"]

        wa_rate = with_advice["good"] / max(wa_total, 1)
        wo_rate = without_advice["good"] / max(wo_total, 1)

        # Contrast ratio: how much better is success WITH advice vs WITHOUT
        contrast = wa_rate - wo_rate if (wa_total >= 5 and wo_total >= 5) else None

        per_tool = {}
        for tool, data in by_tool.items():
            wt = data["with_advice"]["good"] + data["with_advice"]["bad"]
            wot = data["without_advice"]["good"] + data["without_advice"]["bad"]
            if wt >= 3 and wot >= 3:
                wr = data["with_advice"]["good"] / max(wt, 1)
                wor = data["without_advice"]["good"] / max(wot, 1)
                per_tool[tool] = {
                    "with_advice_rate": round(wr, 3),
                    "without_advice_rate": round(wor, 3),
                    "contrast": round(wr - wor, 3),
                    "samples": wt + wot,
                }

        return {
            "overall_contrast": round(contrast, 3) if contrast is not None else None,
            "with_advice": with_advice,
            "without_advice": without_advice,
            "per_tool": per_tool,
            "sufficient_data": wa_total >= 5 and wo_total >= 5,
        }

    def repair_effectiveness_counters(self) -> Dict[str, Any]:
        """Normalize persisted effectiveness counters and return before/after."""
        before = {
            "total_advice_given": int(self.effectiveness.get("total_advice_given", 0) or 0),
            "total_followed": int(self.effectiveness.get("total_followed", 0) or 0),
            "total_helpful": int(self.effectiveness.get("total_helpful", 0) or 0),
        }
        self.effectiveness = self._normalize_effectiveness(self.effectiveness)
        self._save_effectiveness()
        after = {
            "total_advice_given": int(self.effectiveness.get("total_advice_given", 0) or 0),
            "total_followed": int(self.effectiveness.get("total_followed", 0) or 0),
            "total_helpful": int(self.effectiveness.get("total_helpful", 0) or 0),
        }
        return {"before": before, "after": after}

    # ============= Context Generation =============

    def generate_context_block(self, tool_name: str, task_context: str = "", include_mind: bool = False) -> str:
        """
        Generate a context block that can be injected into prompts.

        This is how learnings become actionable in the LLM context.
        """
        advice_list = self.advise(tool_name, {}, task_context, include_mind=include_mind)

        if not advice_list:
            return ""

        lines = ["## Spark Advisor Notes"]

        # Add cautions first
        cautions = [a for a in advice_list if "[Caution]" in a.text or "[Past Failure]" in a.text]
        if cautions:
            lines.append("### Cautions")
            for a in cautions[:2]:
                lines.append(f"- {a.text}")

        # Add recommendations
        recs = [a for a in advice_list if a not in cautions]
        if recs:
            lines.append("### Relevant Learnings")
            for a in recs[:3]:
                conf_str = f"({a.confidence:.0%} confident)" if a.confidence >= 0.7 else ""
                lines.append(f"- {a.text} {conf_str}")

        return "\n".join(lines)


# ============= Singleton =============
_advisor: Optional[SparkAdvisor] = None

def get_advisor() -> SparkAdvisor:
    """Get the global advisor instance."""
    global _advisor
    if _advisor is None:
        _advisor = SparkAdvisor()
    return _advisor


# ============= Convenience Functions =============
def advise_on_tool(
    tool_name: str,
    tool_input: Dict = None,
    context: str = "",
    include_mind: bool = True,
    track_retrieval: bool = True,
    log_recent: bool = True,
    trace_id: Optional[str] = None,
) -> List[Advice]:
    """Get advice before using a tool."""
    return get_advisor().advise(
        tool_name,
        tool_input or {},
        context,
        include_mind=include_mind,
        track_retrieval=track_retrieval,
        log_recent=log_recent,
        trace_id=trace_id,
    )


def get_quick_advice(tool_name: str) -> Optional[str]:
    """Get single most relevant advice for a tool."""
    return get_advisor().get_quick_advice(tool_name)


def should_be_careful(tool_name: str) -> Tuple[bool, str]:
    """Check if we should be careful with this tool."""
    return get_advisor().should_be_careful(tool_name)


def report_outcome(
    tool_name: str,
    success: bool,
    advice_helped: bool = False,
    trace_id: Optional[str] = None,
):
    """Report action outcome to close the feedback loop."""
    get_advisor().report_action_outcome(tool_name, success, advice_helped, trace_id=trace_id)


def record_advice_feedback(
    helpful: Optional[bool],
    notes: str = "",
    tool: Optional[str] = None,
    advice_id: Optional[str] = None,
    followed: bool = True,
):
    """Record explicit feedback on advice helpfulness."""
    return get_advisor().record_advice_feedback(
        helpful=helpful,
        notes=notes,
        tool=tool,
        advice_id=advice_id,
        followed=followed,
    )


def generate_context(tool_name: str, task: str = "") -> str:
    """Generate injectable context block."""
    return get_advisor().generate_context_block(tool_name, task)


def repair_effectiveness_counters() -> Dict[str, Any]:
    """Repair advisor effectiveness counters on disk."""
    return get_advisor().repair_effectiveness_counters()
