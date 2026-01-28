#!/usr/bin/env sh
set -e

CMD="${SPARK_CLAUDE_CMD:-${CLAUDE_CMD:-claude}}"
python -m spark.cli sync-context
exec "$CMD" "$@"
