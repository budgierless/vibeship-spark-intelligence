#!/bin/bash
# Run Spark local services (lightweight, compatible)
# Starts: sparkd (8787), bridge_worker, dashboard (8585), pulse (8765), meta-ralph (8586), watchdog

set -e

SPARK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SPARK_DIR"

python3 -m spark.cli up
python3 -m spark.cli services
