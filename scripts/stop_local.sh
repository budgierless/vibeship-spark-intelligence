#!/bin/bash
# Stop Spark local services started by run_local.sh

set -e

PID_DIR="$HOME/.spark/pids"

stop() {
  local name="$1"
  local pid_file="$PID_DIR/${name}.pid"
  if [ ! -f "$pid_file" ]; then
    echo "[spark] ${name} not running (no pid)"
    return
  fi
  local pid
  pid="$(cat "$pid_file" || true)"
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    echo "[spark] stopping ${name} (pid $pid)"
    kill "$pid" || true
  fi
  rm -f "$pid_file"
}

stop watchdog
stop dashboard
stop bridge_worker
stop sparkd
