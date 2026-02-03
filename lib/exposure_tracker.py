"""Track which insights were surfaced to the user."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .primitive_filter import is_primitive_text


EXPOSURES_FILE = Path.home() / ".spark" / "exposures.jsonl"
LAST_EXPOSURE_FILE = Path.home() / ".spark" / "last_exposure.json"


def record_exposures(
    source: str,
    items: Iterable[Dict],
    *,
    session_id: Optional[str] = None,
    trace_id: Optional[str] = None
) -> int:
    """Append exposure entries. Returns count written."""
    rows: List[Dict] = []
    now = time.time()
    for item in items:
        if not item:
            continue
        text = item.get("text")
        if isinstance(text, str) and is_primitive_text(text):
            continue
        rows.append({
            "ts": now,
            "source": source,
            "insight_key": item.get("insight_key"),
            "category": item.get("category"),
            "text": text,
            "session_id": session_id,
            "trace_id": trace_id,
        })

    if not rows:
        return 0

    EXPOSURES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with EXPOSURES_FILE.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    try:
        # Persist the most recent exposure for quick linking.
        LAST_EXPOSURE_FILE.parent.mkdir(parents=True, exist_ok=True)
        LAST_EXPOSURE_FILE.write_text(json.dumps(rows[-1], ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    return len(rows)


def read_recent_exposures(limit: int = 200, max_age_s: float = 6 * 3600) -> List[Dict]:
    if not EXPOSURES_FILE.exists():
        return []
    try:
        lines = EXPOSURES_FILE.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []

    now = time.time()
    out: List[Dict] = []
    for line in reversed(lines[-limit:]):
        try:
            row = json.loads(line)
        except Exception:
            continue
        ts = float(row.get("ts") or 0.0)
        if max_age_s and ts and (now - ts) > max_age_s:
            continue
        out.append(row)
    return out


def read_exposures_within(*, max_age_s: float, now: Optional[float] = None, limit: int = 200) -> List[Dict]:
    """Read exposures within max_age_s relative to now."""
    if not EXPOSURES_FILE.exists():
        return []
    try:
        lines = EXPOSURES_FILE.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []
    now_ts = float(now or time.time())
    out: List[Dict] = []
    for line in reversed(lines[-limit:]):
        try:
            row = json.loads(line)
        except Exception:
            continue
        ts = float(row.get("ts") or 0.0)
        if max_age_s and ts and (now_ts - ts) > max_age_s:
            continue
        out.append(row)
    return out


def read_last_exposure() -> Optional[Dict]:
    """Return the most recent exposure record if available."""
    if not LAST_EXPOSURE_FILE.exists():
        return None
    try:
        return json.loads(LAST_EXPOSURE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def infer_latest_session_id() -> Optional[str]:
    """Best-effort latest session id from last exposure or recent queue events."""
    last = read_last_exposure()
    if last:
        sid = last.get("session_id")
        if isinstance(sid, str) and sid.strip():
            return sid
    try:
        from lib.queue import read_recent_events
        events = read_recent_events(1)
        if events:
            return events[-1].session_id
    except Exception:
        return None
    return None
