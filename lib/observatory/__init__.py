"""Spark Intelligence Observatory — full pipeline visualization for Obsidian.

Public API:
    generate_observatory(force=False) — generate all observatory pages
    maybe_sync_observatory(stats=None) — cooldown-gated auto-sync (call from bridge_cycle)
"""

from __future__ import annotations

import time
import traceback
from pathlib import Path

from .config import load_config

_last_sync_ts: float = 0.0


def generate_observatory(*, force: bool = False, verbose: bool = False) -> dict:
    """Generate the full observatory (flow dashboard + 12 stage pages + canvas).

    Returns a summary dict with file counts and timing.
    """
    from .readers import read_all_stages
    from .flow_dashboard import generate_flow_dashboard
    from .stage_pages import generate_all_stage_pages
    from .canvas_generator import generate_canvas
    from .explorer import generate_explorer

    t0 = time.time()
    cfg = load_config()

    if not cfg.enabled and not force:
        return {"skipped": True, "reason": "disabled"}

    vault = Path(cfg.vault_dir).expanduser()
    obs_dir = vault / "_observatory"
    stages_dir = obs_dir / "stages"
    stages_dir.mkdir(parents=True, exist_ok=True)

    # Read all stage data
    data = read_all_stages(max_recent=cfg.max_recent_items)
    if verbose:
        print(f"  [observatory] read {len(data)} stages in {(time.time()-t0)*1000:.0f}ms")

    # Generate flow dashboard
    flow_path = obs_dir / "flow.md"
    flow_content = generate_flow_dashboard(data)
    flow_path.write_text(flow_content, encoding="utf-8")

    # Generate stage pages
    files_written = 1  # flow.md
    for filename, content in generate_all_stage_pages(data):
        (stages_dir / filename).write_text(content, encoding="utf-8")
        files_written += 1

    # Generate canvas
    if cfg.generate_canvas:
        canvas_path = obs_dir / "flow.canvas"
        canvas_content = generate_canvas()
        canvas_path.write_text(canvas_content, encoding="utf-8")
        files_written += 1

    # Generate explorer (individual item detail pages)
    t_explore = time.time()
    explorer_counts = generate_explorer(cfg)
    explorer_total = sum(explorer_counts.values()) + 1  # +1 for master index
    files_written += explorer_total
    if verbose:
        print(f"  [observatory] explorer: {explorer_total} files in {(time.time()-t_explore)*1000:.0f}ms")
        for section, count in explorer_counts.items():
            print(f"    {section}: {count} pages")

    elapsed_ms = (time.time() - t0) * 1000
    if verbose:
        print(f"  [observatory] total: {files_written} files in {elapsed_ms:.0f}ms to {obs_dir}")

    return {
        "files_written": files_written,
        "elapsed_ms": round(elapsed_ms, 1),
        "vault_dir": str(vault),
        "explorer": explorer_counts,
    }


def maybe_sync_observatory(stats: dict | None = None) -> None:
    """Cooldown-gated sync — safe to call every bridge cycle."""
    global _last_sync_ts

    try:
        cfg = load_config()
        if not cfg.enabled or not cfg.auto_sync:
            return

        now = time.time()
        if (now - _last_sync_ts) < cfg.sync_cooldown_s:
            return

        _last_sync_ts = now
        generate_observatory()
    except Exception:
        # Non-critical — never crash the pipeline
        traceback.print_exc()
