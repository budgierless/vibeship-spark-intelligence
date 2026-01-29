"""Track which insights were surfaced to the user."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional


EXPOSURES_FILE = Path.home() / ".spark" / "exposures.jsonl"


def record_exposures(source: str, items: Iterable[Dict]) -> int:
    """Append exposure entries. Returns count written."""
    rows: List[Dict] = []
    now = time.time()
    for item in items:
        if not item:
            continue
        rows.append({
            "ts": now,
            "source": source,
            "insight_key": item.get("insight_key"),
            "category": item.get("category"),
            "text": item.get("text"),
        })

    if not rows:
        return 0

    EXPOSURES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with EXPOSURES_FILE.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
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
