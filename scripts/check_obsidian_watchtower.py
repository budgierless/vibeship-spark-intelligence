#!/usr/bin/env python3
"""Quick sanity check for Obsidian watchtower export health."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _read_file_count(path: Path) -> int:
    if not path.exists():
        return 0
    return len([p for p in path.glob("*.md") if p.is_file()])


def _latest_mtime(path: Path) -> str:
    if not path.exists():
        return "missing"
    try:
        ts = path.stat().st_mtime
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "unknown"


def main() -> int:
    print("\n[obsidian-watchtower] running")
    root = _repo_root()
    sys.path.insert(0, str(root))

    try:
        from lib.advisory_packet_store import (
            _sync_obsidian_catalog,
            _get_obsidian_status,
            get_packet_store_config,
        )
    except Exception as e:
        print(f"[obsidian-watchtower] import error: {e}")
        return 1

    cfg = get_packet_store_config()
    enabled = bool(cfg.get("obsidian_enabled", False))
    auto = bool(cfg.get("obsidian_auto_export", False))
    export_dir = Path(str(cfg.get("obsidian_export_dir") or "")).expanduser()
    index_path = Path(str(cfg.get("obsidian_export_dir") or "")).expanduser() / "packets" / "index.md"
    watchtower_path = Path(str(cfg.get("obsidian_export_dir") or "")).expanduser() / "watchtower.md"
    packets_dir = export_dir / "packets"

    print("[obsidian-watchtower] config")
    print(f"  - enabled: {enabled}")
    print(f"  - auto_export: {auto}")
    print(f"  - export_dir: {export_dir}")
    print(f"  - export_dir_exists: {export_dir.exists()}")
    print(f"  - obsidian_index_file: {index_path}")
    print(f"  - obsidian_watchtower_file: {watchtower_path}")

    if not enabled:
        print(f"  - obsidian_sync_status: {_get_obsidian_status()}")
        print("[obsidian-watchtower] skip sync: obsidian_enabled is false")
        return 0

    try:
        sync_out = _sync_obsidian_catalog()
        print(f"[obsidian-watchtower] catalog sync: {sync_out or 'no-op'}")
    except Exception as e:
        print(f"[obsidian-watchtower] sync error: {e}")
        print(f"  - obsidian_sync_status: {_get_obsidian_status()}")
        return 1

    print(f"  - obsidian_sync_status: {_get_obsidian_status()}")
    print("[obsidian-watchtower] artifacts")
    print(f"  - packet_notes: {packets_dir} ({_read_file_count(packets_dir)} md files)")
    print(f"  - index.md exists: {index_path.exists()} ({_latest_mtime(index_path)})")
    print(f"  - watchtower.md exists: {watchtower_path.exists()} ({_latest_mtime(watchtower_path)})")

    if index_path.exists() and watchtower_path.exists():
        print("[obsidian-watchtower] healthy: both dashboard files present")
    elif index_path.exists() or watchtower_path.exists():
        print("[obsidian-watchtower] partial: one dashboard file missing")
    else:
        print("[obsidian-watchtower] warning: dashboard files missing (check permissions/path)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
