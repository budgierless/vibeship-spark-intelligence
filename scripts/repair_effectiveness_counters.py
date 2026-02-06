#!/usr/bin/env python3
"""Repair advisor effectiveness counters to satisfy invariants."""

import json

from lib.advisor import repair_effectiveness_counters


def main() -> int:
    result = repair_effectiveness_counters()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

