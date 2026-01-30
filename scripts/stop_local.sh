#!/bin/bash
# Stop Spark local services

set -e

SPARK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SPARK_DIR"

python3 -m spark.cli down
