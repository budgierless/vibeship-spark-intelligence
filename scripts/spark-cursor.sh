#!/usr/bin/env sh
set -e

CMD="${SPARK_CURSOR_CMD:-${CURSOR_CMD:-cursor}}"
python -m spark.cli sync-context
exec "$CMD" "$@"
