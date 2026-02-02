#!/usr/bin/env python3
"""
Spark Pulse - Neural visualization + control rail.

Run with: python spark_pulse.py
Open: http://localhost:8765
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

import sys
sys.path.insert(0, str(Path(__file__).parent))

from lib.chips.registry import ChipRegistry
from lib.metalearning.strategist import LearningStrategist

try:
    from lib.eidos import get_store
    HAS_EIDOS = True
except ImportError:
    HAS_EIDOS = False

PORT = 8765
SPARK_DIR = Path.home() / ".spark"
CHIP_INSIGHTS_DIR = SPARK_DIR / "chip_insights"
LOGO_FILE = Path(__file__).parent / "logo.png"


def _read_last_json_line(path: Path) -> dict:
    """Read last JSON line from a jsonl file (best effort)."""
    if not path.exists():
        return {}
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            seek = min(size, 8192)
            f.seek(-seek, 2)
            chunk = f.read().decode("utf-8", errors="ignore")
        lines = [line for line in chunk.splitlines() if line.strip()]
        if not lines:
            return {}
        return json.loads(lines[-1])
    except Exception:
        return {}


def get_episode_summary() -> dict:
    if not HAS_EIDOS:
        return {"available": False, "reason": "EIDOS not installed"}
    try:
        store = get_store()
        episodes = store.get_recent_episodes(limit=1)
        if not episodes:
            return {"available": True, "empty": True}
        ep = episodes[0]
        return {
            "available": True,
            "episode_id": ep.episode_id,
            "phase": ep.phase.value,
            "outcome": ep.outcome.value if ep.outcome else "in_progress",
            "steps": ep.step_count,
            "start_ts": ep.start_ts,
            "end_ts": ep.end_ts,
            "success_rate": store.get_stats().get("success_rate", 0),
        }
    except Exception as e:
        return {"available": False, "reason": str(e)}


def get_chip_stats() -> dict:
    registry = ChipRegistry()
    installed = registry.get_installed()
    active = registry.get_active_chips()
    active_ids = {c.id for c in active}

    chips = []
    for chip in sorted(installed, key=lambda c: c.id):
        insight_file = CHIP_INSIGHTS_DIR / f"{chip.id}.jsonl"
        last = _read_last_json_line(insight_file)
        chips.append({
            "id": chip.id,
            "name": chip.name,
            "activation": getattr(chip, "activation", "auto"),
            "active": chip.id in active_ids,
            "insights": sum(1 for _ in insight_file.open("r", encoding="utf-8")) if insight_file.exists() else 0,
            "last_seen": last.get("timestamp") if isinstance(last, dict) else None,
        })

    return {
        "installed": len(installed),
        "active": len(active),
        "auto": sum(1 for c in installed if getattr(c, "activation", "auto") == "auto"),
        "opt_in": sum(1 for c in installed if getattr(c, "activation", "auto") != "auto"),
        "chips": chips[:10],
    }


def get_tuneables() -> dict:
    strategist = LearningStrategist()
    strategy = strategist.strategy
    validation_mode = os.getenv("SPARK_CHIP_SCHEMA_VALIDATION", "warn").strip().lower()
    return {
        "auto_activate_threshold": strategy.auto_activate_threshold,
        "trigger_deprecation_threshold": strategy.trigger_deprecation_threshold,
        "provisional_chip_confidence": strategy.provisional_chip_confidence,
        "schema_validation_mode": validation_mode or "warn",
    }


def get_pulse_data() -> dict:
    return {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "episode": get_episode_summary(),
        "tuneables": get_tuneables(),
        "chips": get_chip_stats(),
    }


def generate_pulse_html() -> str:
    data = get_pulse_data()
    ep = data["episode"]
    tune = data["tuneables"]
    chips = data["chips"]

    if not ep.get("available"):
        ep_html = f'<div class="empty">EIDOS unavailable: {ep.get("reason","")}</div>'
    elif ep.get("empty"):
        ep_html = '<div class="empty">No episodes yet.</div>'
    else:
        ep_html = f'''
        <div class="rail-row">
            <span class="rail-label">Episode</span>
            <span class="rail-value">{ep.get("episode_id","")[:8]}</span>
        </div>
        <div class="rail-row">
            <span class="rail-label">Phase</span>
            <span class="rail-value">{ep.get("phase","")}</span>
        </div>
        <div class="rail-row">
            <span class="rail-label">Outcome</span>
            <span class="rail-value">{ep.get("outcome","")}</span>
        </div>
        <div class="rail-row">
            <span class="rail-label">Steps</span>
            <span class="rail-value">{ep.get("steps",0)}</span>
        </div>
        <div class="rail-row">
            <span class="rail-label">Success</span>
            <span class="rail-value">{int(ep.get("success_rate",0)*100)}%</span>
        </div>
        '''

    chip_rows = []
    for c in chips["chips"]:
        last = c.get("last_seen") or "—"
        chip_rows.append(f'''
        <div class="chip-row">
            <div>
                <div class="chip-name">{c["id"]}</div>
                <div class="chip-meta">{c["activation"]} · {c["insights"]} insights</div>
            </div>
            <div class="chip-last">{last[:19]}</div>
        </div>''')
    chips_html = "\n".join(chip_rows) if chip_rows else '<div class="empty">No chips installed.</div>'

    css = """
    :root {
        --bg-primary: #0b0e16;
        --bg-secondary: #111625;
        --bg-tertiary: #151c2e;
        --text-primary: #eef1f6;
        --text-secondary: #9aa3b5;
        --text-tertiary: #6c7489;
        --accent: #4de3b3;
        --accent-2: #4d8dff;
        --border: #232a3b;
        --font-ui: "Space Grotesk", system-ui, sans-serif;
        --font-mono: "JetBrains Mono", monospace;
    }

    * { margin: 0; padding: 0; box-sizing: border-box; }

    body {
        font-family: var(--font-ui);
        background: radial-gradient(1200px 800px at 10% -20%, #16233a 0%, var(--bg-primary) 55%);
        color: var(--text-primary);
        min-height: 100vh;
    }

    .navbar {
        height: 54px;
        display: flex;
        align-items: center;
        padding: 0 1.5rem;
        border-bottom: 1px solid var(--border);
        backdrop-filter: blur(8px);
        background: rgba(11, 14, 22, 0.6);
    }

    .navbar-logo { display: flex; align-items: center; gap: 0.5rem; }
    .navbar-icon { width: 22px; height: 22px; }
    .navbar-text { font-size: 1.1rem; letter-spacing: 0.04em; }
    .navbar-product { color: var(--accent); font-weight: 600; }

    .pulse-layout {
        display: grid;
        grid-template-columns: 1fr 320px;
        gap: 1.5rem;
        padding: 2rem 2.5rem 2.5rem;
    }

    .canvas {
        background: linear-gradient(135deg, rgba(77,141,255,0.12), rgba(77,227,179,0.05));
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 2rem;
        min-height: 520px;
        position: relative;
        overflow: hidden;
    }

    .canvas::after {
        content: "";
        position: absolute;
        width: 420px;
        height: 420px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(77,227,179,0.12), transparent 60%);
        top: -140px;
        right: -140px;
        animation: drift 16s ease-in-out infinite;
    }

    @keyframes drift {
        0% { transform: translate(0,0); }
        50% { transform: translate(-30px, 40px); }
        100% { transform: translate(0,0); }
    }

    .canvas-title { font-size: 1.6rem; margin-bottom: 0.4rem; }
    .canvas-sub { color: var(--text-secondary); font-size: 0.95rem; margin-bottom: 2rem; }

    .pulse-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1rem;
    }

    .pulse-card {
        background: rgba(9, 12, 20, 0.7);
        border: 1px solid var(--border);
        padding: 1rem;
        border-radius: 12px;
    }

    .pulse-card h4 { font-size: 0.8rem; letter-spacing: 0.12em; text-transform: uppercase; color: var(--text-tertiary); }
    .pulse-card .value { font-family: var(--font-mono); font-size: 1.4rem; margin-top: 0.5rem; color: var(--accent); }

    .right-rail { display: flex; flex-direction: column; gap: 1rem; }
    .rail-card {
        background: var(--bg-secondary);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1rem;
    }
    .rail-title {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.15em;
        color: var(--text-tertiary);
        margin-bottom: 0.75rem;
    }
    .rail-row { display: flex; justify-content: space-between; font-size: 0.8rem; padding: 0.25rem 0; }
    .rail-label { color: var(--text-secondary); }
    .rail-value { font-family: var(--font-mono); color: var(--text-primary); }
    .chip-row { display: flex; justify-content: space-between; gap: 0.75rem; padding: 0.5rem 0; border-bottom: 1px solid var(--border); }
    .chip-row:last-child { border-bottom: none; }
    .chip-name { font-size: 0.85rem; }
    .chip-meta { font-size: 0.7rem; color: var(--text-tertiary); }
    .chip-last { font-size: 0.7rem; color: var(--text-tertiary); font-family: var(--font-mono); }
    .list { margin-top: 0.5rem; font-size: 0.78rem; color: var(--text-secondary); }
    .list li { margin-left: 1rem; margin-top: 0.35rem; }
    .empty { color: var(--text-tertiary); font-size: 0.8rem; }

    @media (max-width: 980px) {
        .pulse-layout { grid-template-columns: 1fr; }
        .right-rail { order: -1; }
    }
    """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Spark Pulse</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Space+Grotesk:wght@400;500;600&display=swap" rel="stylesheet">
  <style>{css}</style>
</head>
<body>
  <nav class="navbar">
    <div class="navbar-logo">
      <img src="/logo.png" alt="vibeship" class="navbar-icon" />
      <span class="navbar-text">vibeship</span>
      <span class="navbar-product">spark pulse</span>
    </div>
  </nav>

  <div class="pulse-layout">
    <section class="canvas">
      <div class="canvas-title">Pulse Field</div>
      <div class="canvas-sub">Neural activity map with live chip signals.</div>

      <div class="pulse-grid">
        <div class="pulse-card">
          <h4>Installed Chips</h4>
          <div class="value">{chips["installed"]}</div>
        </div>
        <div class="pulse-card">
          <h4>Active Chips</h4>
          <div class="value">{chips["active"]}</div>
        </div>
        <div class="pulse-card">
          <h4>Auto / Opt-In</h4>
          <div class="value">{chips["auto"]} / {chips["opt_in"]}</div>
        </div>
      </div>
    </section>

    <aside class="right-rail">
      <div class="rail-card">
        <div class="rail-title">Episode</div>
        {ep_html}
      </div>

      <div class="rail-card">
        <div class="rail-title">Tuneables · Chips</div>
        <div class="rail-row"><span class="rail-label">Auto-activate</span><span class="rail-value">{tune["auto_activate_threshold"]:.2f}</span></div>
        <div class="rail-row"><span class="rail-label">Deprecation</span><span class="rail-value">{tune["trigger_deprecation_threshold"]:.2f}</span></div>
        <div class="rail-row"><span class="rail-label">Provisional</span><span class="rail-value">{tune["provisional_chip_confidence"]:.2f}</span></div>
        <div class="rail-row"><span class="rail-label">Schema</span><span class="rail-value">{tune["schema_validation_mode"]}</span></div>
        <ul class="list">
          <li>Watch trigger precision after tune changes.</li>
          <li>Keep opt-in chips manual until signal is clean.</li>
          <li>Use `SPARK_CHIP_SCHEMA_VALIDATION=block` in CI.</li>
        </ul>
      </div>

      <div class="rail-card">
        <div class="rail-title">Chips</div>
        {chips_html}
        <ul class="list">
          <li>Integrate: `spark chips install path/to/chip.yaml`</li>
          <li>Activate: `spark chips activate chip-id`</li>
          <li>Edit: `chips/chip-id.chip.yaml`</li>
          <li>Update: `spark chips test chip-id --test-text "..."`</li>
          <li>Evaluate: `python benchmarks/run_benchmarks.py --chips chip-id`</li>
        </ul>
      </div>
    </aside>
  </div>
</body>
</html>"""
    return html


class PulseHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(generate_pulse_html().encode())
        elif self.path == '/api/pulse':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(get_pulse_data(), indent=2).encode())
        elif self.path == '/logo.png':
            if not LOGO_FILE.exists():
                self.send_response(404)
                self.end_headers()
                return
            logo_bytes = LOGO_FILE.read_bytes()
            self.send_response(200)
            self.send_header('Content-type', 'image/png')
            self.send_header('Content-Length', str(len(logo_bytes)))
            self.end_headers()
            self.wfile.write(logo_bytes)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def main():
    print()
    print("  vibeship spark")
    print("  -----------------------------")
    print(f"  Spark Pulse: http://localhost:{PORT}")
    print("  Press Ctrl+C to stop")
    print()
    server = ThreadingHTTPServer(('localhost', PORT), PulseHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
