#!/bin/bash
# Show status of local Spark services started by run_local.sh

set -e
PID_DIR="$HOME/.spark/pids"

check() {
  local name="$1" port="$2"
  local pid_file="$PID_DIR/${name}.pid"
  if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "[spark] ${name}: RUNNING (pid $(cat "$pid_file"))"
  else
    echo "[spark] ${name}: STOPPED"
  fi
  if [ -n "$port" ]; then
    if curl -s "http://127.0.0.1:${port}/health" >/dev/null 2>&1; then
      echo "        health: OK (:${port})"
    else
      echo "        health: (no response) (:${port})"
    fi
  fi
}

echo ""
check sparkd 8787
check bridge_worker ""
check dashboard ""
check watchdog ""

echo ""
echo "Dashboard: http://127.0.0.1:8585"
