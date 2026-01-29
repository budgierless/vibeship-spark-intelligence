#!/bin/bash
# Run Spark local services (lightweight, compatible)
# Starts: sparkd (8787), bridge_worker, dashboard (8585)

set -e

SPARK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$HOME/.spark/pids"
LOG_DIR="$HOME/.spark/logs"

mkdir -p "$PID_DIR" "$LOG_DIR"

start() {
  local name="$1"; shift
  local pid_file="$PID_DIR/${name}.pid"
  local log_file="$LOG_DIR/${name}.log"

  if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "[spark] ${name} already running (pid $(cat "$pid_file"))"
    return
  fi

  echo "[spark] starting ${name}…"
  nohup "$@" > "$log_file" 2>&1 &
  echo $! > "$pid_file"
  echo "[spark] ${name} pid $! (log $log_file)"
}

cd "$SPARK_DIR"

start sparkd python3 "$SPARK_DIR/sparkd.py"
start bridge_worker python3 "$SPARK_DIR/bridge_worker.py" --interval 30
start dashboard python3 "$SPARK_DIR/dashboard.py"
start watchdog python3 "$SPARK_DIR/scripts/watchdog.py" --interval 60

echo ""
echo "[spark] Dashboard: http://127.0.0.1:8585"
echo "[spark] sparkd:    http://127.0.0.1:8787/health"
