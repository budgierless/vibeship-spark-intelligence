#!/usr/bin/env sh
set -e

CMD="${SPARK_CLAWDBOT_CMD:-${CLAWDBOT_CMD:-clawdbot}}"
python -m spark.cli sync-context
exec "$CMD" "$@"
