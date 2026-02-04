#!/bin/bash
# Run Spark local services (lightweight, compatible)
# Starts: sparkd (8787), bridge_worker, dashboard (8585), pulse (8765), meta-ralph (8586), watchdog

set -e

SPARK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SPARK_DIR"

SPARK_ARGS=()
if [[ "${SPARK_LITE}" == "1" || "${SPARK_LITE}" == "true" || "${SPARK_LITE}" == "yes" ]]; then
  SPARK_ARGS+=("--lite")
fi
if [[ "${SPARK_NO_DASHBOARD}" == "1" ]]; then
  SPARK_ARGS+=("--no-dashboard")
fi
if [[ "${SPARK_NO_PULSE}" == "1" ]]; then
  SPARK_ARGS+=("--no-pulse")
fi
if [[ "${SPARK_NO_META_RALPH}" == "1" ]]; then
  SPARK_ARGS+=("--no-meta-ralph")
fi
if [[ "${SPARK_NO_WATCHDOG}" == "1" ]]; then
  SPARK_ARGS+=("--no-watchdog")
fi

python3 -m spark.cli up "${SPARK_ARGS[@]}"
python3 -m spark.cli services
