#!/usr/bin/env sh
set -e

CMD="${SPARK_CODEX_CMD:-${CODEX_CMD:-codex}}"
python -m spark.cli sync-context
exec "$CMD" "$@"
