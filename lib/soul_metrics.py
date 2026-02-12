from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

SOUL_METRICS_FILE = Path.home() / '.spark' / 'soul_metrics.jsonl'


def record_metric(kind: str, payload: Dict[str, Any]) -> None:
    try:
        SOUL_METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
        row = {
            'ts': time.time(),
            'kind': kind,
            **(payload or {}),
        }
        with SOUL_METRICS_FILE.open('a', encoding='utf-8') as f:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    except Exception:
        return
