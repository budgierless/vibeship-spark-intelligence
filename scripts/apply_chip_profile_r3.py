#!/usr/bin/env python3
"""Apply the promoted R3 chip profile to user tuneables.

Writes chip_merge quality limits into ~/.spark/tuneables.json so merge/distillation
matches the benchmarked profile.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict


R3_CHIP_MERGE: Dict[str, Any] = {
    "min_cognitive_value": 0.25,
    "min_actionability": 0.15,
    "min_transferability": 0.15,
    "min_statement_len": 20,
}


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(raw, dict):
        return {}
    return raw


def apply_r3(path: Path) -> Dict[str, Any]:
    data = _load_json(path)
    current = dict(data.get("chip_merge") or {})
    current.update(R3_CHIP_MERGE)
    data["chip_merge"] = current
    data["updated_at"] = datetime.now(UTC).isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply R3 chip profile to ~/.spark/tuneables.json")
    ap.add_argument(
        "--path",
        default=str(Path.home() / ".spark" / "tuneables.json"),
        help="Tuneables file path (default: ~/.spark/tuneables.json)",
    )
    args = ap.parse_args()

    path = Path(args.path)
    apply_r3(path)
    print(f"Applied R3 chip_merge profile: {path}")
    print(json.dumps(R3_CHIP_MERGE, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
