#!/usr/bin/env python3
"""
Spark Pulse - Redirector to external vibeship-spark-pulse.

This file is DEPRECATED. The real Spark Pulse is the external FastAPI app
at vibeship-spark-pulse/app.py. If someone runs this file directly, it will
either launch the external pulse or exit with an error.

DO NOT add a fallback HTTP server here. Use the external pulse.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main():
    from lib.service_control import SPARK_PULSE_DIR
    external_app = SPARK_PULSE_DIR / "app.py"

    print("\n" + "=" * 64)
    print("  SPARK PULSE - REDIRECTOR")
    print("=" * 64)

    if external_app.exists():
        print(f"  Launching external pulse: {SPARK_PULSE_DIR}")
        print("=" * 64 + "\n")
        sys.exit(subprocess.call([sys.executable, str(external_app)], cwd=str(SPARK_PULSE_DIR)))
    else:
        print()
        print("  ERROR: External Spark Pulse not found.")
        print(f"  Expected at: {external_app}")
        print()
        print("  Fix: Clone vibeship-spark-pulse to that path,")
        print("  or set SPARK_PULSE_DIR env var to its location.")
        print("=" * 64 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
