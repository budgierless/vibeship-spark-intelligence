#!/usr/bin/env python3
"""
Spark Pulse Dashboard (Chips + Tuneables)

Live, storage-backed view into chips and tuning signals.

Run with: python spark_pulse.py
Open: http://localhost:<pulse-port>
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
from typing import Dict, Any
import threading
import webbrowser

from lib.ports import DASHBOARD_PORT, META_RALPH_PORT, PULSE_PORT
from lib.diagnostics import setup_component_logging

SPARK_DIR = Path.home() / ".spark"
PORT = PULSE_PORT


def _chip_stats() -> Dict[str, Any]:
    try:
        from lib.chips.registry import get_registry
        from lib.chips.evolution import get_evolution
    except Exception:
        return {
            "registry": {},
            "installed": [],
            "active": [],
            "insights_dir": 0,
            "provisional": 0,
            "evolution": {},
        }

    registry = get_registry()
    installed = [c.id for c in registry.get_installed()]
    active = [c.id for c in registry.get_active_chips()]
    stats = registry.get_stats()

    insights_dir = SPARK_DIR / "chip_insights"
    insights_files = len(list(insights_dir.glob("*.jsonl"))) if insights_dir.exists() else 0

    evo = get_evolution()
    provisional = len(evo.get_provisional_chips())

    # Summarize evolution signals
    tracked = 0
    high_value = 0
    low_value = 0
    for chip_id in installed:
        st = evo.get_evolution_stats(chip_id)
        if st.get("status") == "no_data":
            continue
        tracked += int(st.get("triggers_tracked") or 0)
        high_value += len(st.get("high_value_triggers") or [])
        low_value += len(st.get("low_value_triggers") or [])

    return {
        "registry": stats,
        "installed": installed,
        "active": active,
        "insights_dir": insights_files,
        "provisional": provisional,
        "evolution": {
            "triggers_tracked": tracked,
            "high_value_triggers": high_value,
            "low_value_triggers": low_value,
        },
    }


def _tuneable_recommendations() -> Dict[str, Any]:
    try:
        from lib.meta_ralph import get_meta_ralph
        ralph = get_meta_ralph()
        return ralph.analyze_tuneables()
    except Exception as e:
        return {"status": "unavailable", "reason": str(e)[:120]}


def get_pulse_data() -> Dict[str, Any]:
    return {
        "chips": _chip_stats(),
        "tuneables": _tuneable_recommendations(),
        "last_updated": time.time(),
    }


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Spark Pulse</title>
  <style>
    :root {
      --bg: #0c1118;
      --panel: #121a24;
      --panel-2: #0f1621;
      --text: #e6edf7;
      --muted: #97a6b8;
      --accent: #f5b547;
      --accent-2: #46d3c7;
      --border: #1f2a39;
      --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      --sans: "Space Grotesk", system-ui, -apple-system, Segoe UI, sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: var(--sans);
    }
    .nav {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 24px;
      border-bottom: 1px solid var(--border);
      background: rgba(12,17,24,0.9);
      position: sticky;
      top: 0;
      backdrop-filter: blur(8px);
    }
    .nav .brand { font-weight: 600; letter-spacing: 0.02em; }
    .nav .links a { color: var(--muted); text-decoration: none; margin-left: 16px; }
    .nav .links a:hover { color: var(--text); }
    .wrap { max-width: 1100px; margin: 24px auto; padding: 0 20px; }
    .hero {
      padding: 24px;
      background: linear-gradient(135deg, #101724, #0f1621);
      border: 1px solid var(--border);
      border-radius: 14px;
    }
    .hero h1 { margin: 0 0 6px; font-size: 28px; }
    .hero p { margin: 0; color: var(--muted); }
    .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-top: 16px; }
    .card { background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 16px; }
    .card h3 { margin: 0 0 8px; font-size: 16px; }
    .stat { font-size: 28px; font-weight: 700; }
    .muted { color: var(--muted); font-size: 13px; }
    .list { margin: 0; padding: 0; list-style: none; }
    .list li { padding: 6px 0; border-bottom: 1px dashed var(--border); }
    .list li:last-child { border-bottom: 0; }
    .pill { display: inline-block; padding: 2px 8px; border-radius: 999px; background: var(--panel-2); font-size: 12px; color: var(--muted); }
    .mono { font-family: var(--mono); }
    @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <div class="nav">
    <div class="brand">spark pulse</div>
    <div class="links">
      <a href="__SPARK_DASHBOARD_URL__">Spark Lab</a>
      <a href="__SPARK_META_RALPH_URL__">Meta-Ralph</a>
    </div>
  </div>
  <div class="wrap">
    <div class="hero">
      <h1>Chips + Tuneables Pulse</h1>
      <p>Real data from storage. No hallucinations.</p>
    </div>

    <div class="grid">
      <div class="card">
        <h3>Installed Chips</h3>
        <div class="stat" id="chips-total">0</div>
        <div class="muted" id="chips-active">0 active</div>
      </div>
      <div class="card">
        <h3>Chip Insights</h3>
        <div class="stat" id="chips-insights">0</div>
        <div class="muted">files in ~/.spark/chip_insights</div>
      </div>
      <div class="card">
        <h3>Evolution Signals</h3>
        <div class="muted">Triggers tracked</div>
        <div class="stat" id="chips-tracked">0</div>
        <div class="muted" id="chips-quality">0 high / 0 low</div>
      </div>
    </div>

    <div class="grid">
      <div class="card">
        <h3>Active Chips</h3>
        <ul class="list" id="chips-active-list"></ul>
      </div>
      <div class="card">
        <h3>Installed Chips</h3>
        <ul class="list" id="chips-installed-list"></ul>
      </div>
      <div class="card">
        <h3>Tuneable Recommendations</h3>
        <div class="muted" id="tuneables-status"></div>
        <ul class="list" id="tuneables-list"></ul>
      </div>
    </div>
  </div>

  <script>
    async function loadPulse() {
      const resp = await fetch('/api/pulse');
      const data = await resp.json();

      const chips = data.chips || {};
      const reg = chips.registry || {};
      document.getElementById('chips-total').textContent = reg.total_installed ?? 0;
      document.getElementById('chips-active').textContent = `${reg.total_active ?? 0} active`;
      document.getElementById('chips-insights').textContent = chips.insights_dir ?? 0;

      const evo = chips.evolution || {};
      document.getElementById('chips-tracked').textContent = evo.triggers_tracked ?? 0;
      document.getElementById('chips-quality').textContent = `${evo.high_value_triggers ?? 0} high / ${evo.low_value_triggers ?? 0} low`;

      const active = chips.active || [];
      const installed = chips.installed || [];
      const activeList = document.getElementById('chips-active-list');
      const installedList = document.getElementById('chips-installed-list');
      activeList.innerHTML = active.length ? active.map(c => `<li><span class="mono">${c}</span></li>`).join('') : '<li class="muted">No active chips</li>';
      installedList.innerHTML = installed.length ? installed.map(c => `<li><span class="mono">${c}</span></li>`).join('') : '<li class="muted">No chips installed</li>';

      const tuneables = data.tuneables || {};
      document.getElementById('tuneables-status').textContent = tuneables.status || 'ok';
      const list = document.getElementById('tuneables-list');
      const recs = tuneables.recommendations || [];
      list.innerHTML = recs.length
        ? recs.map(r => `<li><span class="pill mono">${r.tuneable || 'tuneable'}</span> ${r.recommendation || ''}</li>`).join('')
        : '<li class="muted">No recommendations yet</li>';
    }

    loadPulse();
    setInterval(loadPulse, 10000);
  </script>
</body>
</html>
"""


class PulseHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            html = HTML.replace("__SPARK_DASHBOARD_URL__", f"http://localhost:{DASHBOARD_PORT}")
            html = html.replace("__SPARK_META_RALPH_URL__", f"http://localhost:{META_RALPH_PORT}")
            self.wfile.write(html.encode("utf-8"))
            return
        if parsed.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"ok")
            return
        if parsed.path == "/api/pulse":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            payload = get_pulse_data()
            self.wfile.write(json.dumps(payload).encode("utf-8"))
            return
        self.send_error(404)


def main():
    # This primitive dashboard is DEPRECATED.
    # The real Spark Pulse lives at vibeship-spark-pulse (external repo).
    print("\n" + "=" * 64)
    print("  SPARK PULSE - DEPRECATED")
    print("=" * 64)
    print()
    print("  This internal spark_pulse.py is deprecated.")
    print("  Use the full Spark Pulse at vibeship-spark-pulse instead.")
    print()

    from lib.service_control import SPARK_PULSE_DIR
    external_app = SPARK_PULSE_DIR / "app.py"
    if external_app.exists():
        print(f"  Found external pulse at: {SPARK_PULSE_DIR}")
        print(f"  Starting external pulse...")
        print("=" * 64 + "\n")
        import subprocess, sys
        sys.exit(subprocess.call([sys.executable, str(external_app)]))
    else:
        print(f"  External pulse NOT found at: {SPARK_PULSE_DIR}")
        print(f"  Set SPARK_PULSE_DIR env var or clone vibeship-spark-pulse there.")
        print("=" * 64 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
