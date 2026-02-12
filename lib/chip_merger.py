"""
Chip Insight Merger - Bridge chip insights into the cognitive learning pipeline.

Chips capture domain-specific insights that are stored separately.
This module merges high-value chip insights into the main cognitive system
so they can be validated, promoted, and injected into context.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

from lib.cognitive_learner import get_cognitive_learner, CognitiveCategory
from lib.exposure_tracker import record_exposures
from lib.queue import _tail_lines
from lib.chips.registry import get_registry


CHIP_INSIGHTS_DIR = Path.home() / ".spark" / "chip_insights"
MERGE_STATE_FILE = Path.home() / ".spark" / "chip_merge_state.json"
LOW_QUALITY_COOLDOWN_S = 4 * 3600
MAX_REJECTED_TRACKING = 2000


# Map chip domains to cognitive categories
CHIP_TO_CATEGORY = {
    "market-intel": CognitiveCategory.CONTEXT,
    "game_dev": CognitiveCategory.REASONING,
    "game-dev": CognitiveCategory.REASONING,
    "marketing": CognitiveCategory.CONTEXT,
    "vibecoding": CognitiveCategory.WISDOM,
    "moltbook": CognitiveCategory.REASONING,
    "biz-ops": CognitiveCategory.CONTEXT,
    "bench-core": CognitiveCategory.SELF_AWARENESS,
    "bench_core": CognitiveCategory.SELF_AWARENESS,
    "spark-core": CognitiveCategory.META_LEARNING,
}

DOMAIN_TO_CATEGORY = {
    "coding": CognitiveCategory.REASONING,
    "development": CognitiveCategory.REASONING,
    "debugging": CognitiveCategory.REASONING,
    "tools": CognitiveCategory.META_LEARNING,
    "engineering": CognitiveCategory.REASONING,
    "delivery": CognitiveCategory.WISDOM,
    "reliability": CognitiveCategory.WISDOM,
    "game_dev": CognitiveCategory.REASONING,
    "game": CognitiveCategory.REASONING,
    "marketing": CognitiveCategory.CONTEXT,
    "growth": CognitiveCategory.CONTEXT,
    "strategy": CognitiveCategory.CONTEXT,
    "pricing": CognitiveCategory.CONTEXT,
    "benchmarking": CognitiveCategory.SELF_AWARENESS,
}


def _load_merge_state() -> Dict[str, Any]:
    """Load the merge state tracking which insights have been merged."""
    if not MERGE_STATE_FILE.exists():
        return {"merged_hashes": [], "last_merge": None, "rejected_low_quality": {}}
    try:
        state = json.loads(MERGE_STATE_FILE.read_text(encoding="utf-8"))
        if not isinstance(state, dict):
            return {"merged_hashes": [], "last_merge": None, "rejected_low_quality": {}}
        if not isinstance(state.get("merged_hashes"), list):
            state["merged_hashes"] = []
        if not isinstance(state.get("rejected_low_quality"), dict):
            state["rejected_low_quality"] = {}
        return state
    except Exception:
        return {"merged_hashes": [], "last_merge": None, "rejected_low_quality": {}}


def _save_merge_state(state: Dict[str, Any]):
    """Save the merge state."""
    MERGE_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    MERGE_STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _hash_insight(chip_id: str, content: str) -> str:
    """Create a stable dedupe hash for chip insight content."""
    import hashlib
    normalized = " ".join((content or "").strip().lower().split())
    raw = f"{chip_id.strip().lower()}|{normalized[:180]}".encode("utf-8", errors="ignore")
    return hashlib.sha1(raw).hexdigest()[:12]


def _prune_rejected_state(entries: Dict[str, Any], now_ts: float) -> Dict[str, float]:
    """Keep recent low-quality rejections only."""
    kept: Dict[str, float] = {}
    for key, value in entries.items():
        try:
            ts = float(value)
        except Exception:
            continue
        if ts <= 0:
            continue
        if (now_ts - ts) <= LOW_QUALITY_COOLDOWN_S:
            kept[key] = ts
    if len(kept) > MAX_REJECTED_TRACKING:
        # Keep most recent signatures only.
        ordered = sorted(kept.items(), key=lambda kv: kv[1], reverse=True)[:MAX_REJECTED_TRACKING]
        kept = {k: v for k, v in ordered}
    return kept


def _infer_category(chip_id: str, captured_data: Dict[str, Any], content: str) -> CognitiveCategory:
    """Infer cognitive category for chips with robust fallback."""
    if chip_id in CHIP_TO_CATEGORY:
        return CHIP_TO_CATEGORY[chip_id]
    canonical = chip_id.replace("_", "-")
    if canonical in CHIP_TO_CATEGORY:
        return CHIP_TO_CATEGORY[canonical]

    # Try installed chip metadata (domains).
    try:
        chip = get_registry().get_chip(chip_id)
    except Exception:
        chip = None
    if chip and getattr(chip, "domains", None):
        for domain in chip.domains:
            key = str(domain).strip().lower().replace("-", "_")
            if key in DOMAIN_TO_CATEGORY:
                return DOMAIN_TO_CATEGORY[key]

    # Heuristic fallback from content.
    text = f"{chip_id} {content or ''}".lower()
    if any(k in text for k in ("prefer", "should", "avoid", "never", "always", "lesson")):
        return CognitiveCategory.WISDOM
    if any(k in text for k in ("error", "failed", "fix", "issue", "debug")):
        return CognitiveCategory.REASONING
    if any(k in text for k in ("user", "audience", "market", "customer", "campaign")):
        return CognitiveCategory.CONTEXT
    if any(k in text for k in ("confidence", "benchmark", "method", "self")):
        return CognitiveCategory.SELF_AWARENESS
    return CognitiveCategory.CONTEXT


def _tail_jsonl(path: Path, limit: int) -> List[Dict[str, Any]]:
    """Read the last N JSONL rows without loading the whole file."""
    if limit <= 0 or not path.exists():
        return []

    out: List[Dict[str, Any]] = []
    for raw in _tail_lines(path, limit):
        if not raw:
            continue
        try:
            out.append(json.loads(raw))
        except Exception:
            continue
    return out


def _count_jsonl_lines(path: Path) -> int:
    """Count non-empty JSONL rows with streaming IO."""
    if not path.exists():
        return 0
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return 0


def load_chip_insights(chip_id: str = None, limit: int = 100) -> List[Dict]:
    """Load chip insights from disk."""
    insights = []

    if chip_id:
        files = [CHIP_INSIGHTS_DIR / f"{chip_id}.jsonl"]
    else:
        files = list(CHIP_INSIGHTS_DIR.glob("*.jsonl")) if CHIP_INSIGHTS_DIR.exists() else []

    for file_path in files:
        if not file_path.exists():
            continue
        try:
            # Tail-read avoids loading very large chip files into memory each cycle.
            insights.extend(_tail_jsonl(file_path, limit=limit))
        except Exception:
            continue

    # Sort by timestamp descending
    insights.sort(key=lambda i: i.get("timestamp", ""), reverse=True)
    return insights[:limit]


def merge_chip_insights(
    min_confidence: float = 0.7,
    min_quality_score: float = 0.7,
    limit: int = 50,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Merge high-confidence chip insights into the cognitive learning system.

    This is the key function that bridges domain-specific chip observations
    into the main learning pipeline where they can be validated and promoted.

    Args:
        min_confidence: Minimum confidence to consider for merging
        limit: Max insights to process per run
        dry_run: If True, don't actually merge, just report what would happen

    Returns:
        Stats about the merge operation
    """
    state = _load_merge_state()
    merged_hashes = set(state.get("merged_hashes", []))
    now_ts = time.time()
    rejected_low_quality = _prune_rejected_state(state.get("rejected_low_quality", {}), now_ts)

    stats = {
        "processed": 0,
        "merged": 0,
        "skipped_low_confidence": 0,
        "skipped_low_quality": 0,
        "skipped_low_quality_cooldown": 0,
        "skipped_duplicate": 0,
        "by_chip": {},
    }

    cog = get_cognitive_learner()
    chip_insights = load_chip_insights(limit=limit)
    exposures_to_record = []

    for chip_insight in chip_insights:
        stats["processed"] += 1

        chip_id = chip_insight.get("chip_id", "unknown")
        content = chip_insight.get("content", "")
        confidence = chip_insight.get("confidence", 0.5)
        captured_data = chip_insight.get("captured_data", {})
        insight_hash = _hash_insight(chip_id, content)

        # Skip low confidence
        if confidence < min_confidence:
            stats["skipped_low_confidence"] += 1
            continue

        # Skip already merged (stable hash ignores timestamp churn)
        if insight_hash in merged_hashes:
            stats["skipped_duplicate"] += 1
            continue

        quality = (captured_data.get("quality_score") or {})
        quality_total = float(quality.get("total", confidence) or confidence)
        if quality_total < min_quality_score:
            previous = float(rejected_low_quality.get(insight_hash, 0.0) or 0.0)
            if previous > 0 and (now_ts - previous) < LOW_QUALITY_COOLDOWN_S:
                stats["skipped_low_quality_cooldown"] += 1
            else:
                stats["skipped_low_quality"] += 1
                rejected_low_quality[insight_hash] = now_ts
            continue
        rejected_low_quality.pop(insight_hash, None)

        # Determine category with fallback inference.
        category = _infer_category(chip_id, captured_data, content)

        # Build context from captured data
        context_parts = []
        if captured_data.get("file_path"):
            context_parts.append(f"File: {captured_data['file_path']}")
        if captured_data.get("tool"):
            context_parts.append(f"Tool: {captured_data['tool']}")
        if captured_data.get("change_summary"):
            context_parts.append(captured_data["change_summary"])
        context = " | ".join(context_parts) if context_parts else f"From {chip_id} chip"

        if not dry_run:
            # Add to cognitive system (but don't double-record exposure)
            cog.add_insight(
                category=category,
                insight=content,
                context=context,
                confidence=confidence,
                record_exposure=False  # We'll batch record below
            )

            # Track for exposure recording
            key = cog._generate_key(category, content[:40].replace(" ", "_").lower())
            exposures_to_record.append({
                "insight_key": key,
                "category": category.value,
                "text": content,
            })

            merged_hashes.add(insight_hash)

        stats["merged"] += 1
        stats["by_chip"][chip_id] = stats["by_chip"].get(chip_id, 0) + 1

    # Batch record exposures
    if exposures_to_record and not dry_run:
        try:
            from lib.exposure_tracker import infer_latest_trace_id, infer_latest_session_id
            session_id = infer_latest_session_id()
            trace_id = infer_latest_trace_id(session_id)
        except Exception:
            session_id = None
            trace_id = None
        record_exposures(source="chip_merge", items=exposures_to_record, session_id=session_id, trace_id=trace_id)

    # Save state
    if not dry_run:
        state["merged_hashes"] = list(merged_hashes)[-1000:]  # Keep last 1000
        state["rejected_low_quality"] = _prune_rejected_state(rejected_low_quality, now_ts)
        state["last_merge"] = datetime.now().isoformat()
        state["last_stats"] = stats
        _save_merge_state(state)

    return stats


def get_merge_stats() -> Dict[str, Any]:
    """Get statistics about chip merging."""
    state = _load_merge_state()

    # Count insights per chip
    chip_counts = {}
    if CHIP_INSIGHTS_DIR.exists():
        for f in CHIP_INSIGHTS_DIR.glob("*.jsonl"):
            try:
                chip_counts[f.stem] = _count_jsonl_lines(f)
            except Exception:
                continue

    return {
        "total_merged": len(state.get("merged_hashes", [])),
        "last_merge": state.get("last_merge"),
        "last_stats": state.get("last_stats"),
        "chip_insight_counts": chip_counts,
    }
