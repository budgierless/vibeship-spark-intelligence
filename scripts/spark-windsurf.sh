#!/usr/bin/env sh
set -e

CMD="${SPARK_WINDSURF_CMD:-${WINDSURF_CMD:-windsurf}}"
python -m spark.cli sync-context
exec "$CMD" "$@"
