#!/usr/bin/env python3
"""Prune chip insight rows for disabled/noisy observers.

Reads observer policy from ~/.spark/chip_observer_policy.json and removes rows
whose observer names/keys are disabled. This is useful to clean historical
telemetry-heavy backlog so diagnostics reflect higher-signal observers.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


def _normalize_chip_id(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", "-")


def _normalize_observer(value: Any) -> str:
    return str(value or "").strip().lower()


def _load_registry_active(project_path: str) -> List[str]:
    registry = Path.home() / ".spark" / "chip_registry.json"
    if not registry.exists():
        return []
    try:
        raw = json.loads(registry.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(raw, dict):
        return []
    active = raw.get("active") or {}
    if not isinstance(active, dict):
        return []
    rows = active.get(project_path) or []
    if not isinstance(rows, list):
        return []
    return sorted({str(r).strip() for r in rows if str(r).strip()})


def _load_policy(path: Path) -> Tuple[Set[str], Set[str]]:
    if not path.exists():
        return set(), set()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return set(), set()
    if not isinstance(raw, dict):
        return set(), set()

    disabled_keys: Set[str] = set()
    for value in raw.get("disabled_observers") or []:
        text = str(value or "").strip().lower()
        if not text:
            continue
        if "/" in text:
            chip_id, observer = text.split("/", 1)
            chip_id = _normalize_chip_id(chip_id)
            observer = _normalize_observer(observer)
            if chip_id and observer:
                disabled_keys.add(f"{chip_id}/{observer}")

    disabled_names: Set[str] = set()
    for value in raw.get("disabled_observer_names") or []:
        text = _normalize_observer(value)
        if text:
            disabled_names.add(text)

    return disabled_keys, disabled_names


def _is_schema_row(row: Dict[str, Any]) -> bool:
    captured = row.get("captured_data") or {}
    if not isinstance(captured, dict):
        return False
    payload = captured.get("learning_payload")
    return isinstance(payload, dict) and bool(payload)


def _read_jsonl_rows(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _write_jsonl(path: Path, rows: List[Dict[str, Any]]):
    payload = "".join(json.dumps(row, ensure_ascii=True) + "\n" for row in rows)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)


def _row_observer_key(row: Dict[str, Any]) -> Tuple[str, str, str]:
    chip_id = _normalize_chip_id(row.get("chip_id"))
    observer = _normalize_observer(row.get("observer_name") or row.get("observer"))
    key = f"{chip_id}/{observer}" if chip_id and observer else ""
    return chip_id, observer, key


def main() -> int:
    ap = argparse.ArgumentParser(description="Prune chip insight rows from disabled observers")
    ap.add_argument("--policy-file", default=str(Path.home() / ".spark" / "chip_observer_policy.json"))
    ap.add_argument("--chip-dir", default=str(Path.home() / ".spark" / "chip_insights"))
    ap.add_argument("--active-only", action="store_true", help="Only process active chips for a project")
    ap.add_argument(
        "--project-path",
        default=".",
        help="Project path key used in ~/.spark/chip_registry.json when --active-only is set",
    )
    ap.add_argument(
        "--extra-observer-names",
        default="",
        help="Comma-separated extra observer names to prune (in addition to policy)",
    )
    ap.add_argument(
        "--drop-schema-from-disabled",
        action="store_true",
        help="Also drop schema rows from disabled observers (default keeps schema rows)",
    )
    ap.add_argument("--archive", action="store_true", help="Backup original files before writing")
    ap.add_argument("--apply", action="store_true", help="Write changes (default dry-run)")
    args = ap.parse_args()

    chip_dir = Path(args.chip_dir)
    files = sorted(chip_dir.glob("*.jsonl"))
    active_ids = _load_registry_active(str(args.project_path)) if bool(args.active_only) else []
    if active_ids:
        wanted = {f"{chip_id}.jsonl" for chip_id in active_ids}
        files = [fp for fp in files if fp.name in wanted]

    disabled_keys, disabled_names = _load_policy(Path(args.policy_file))
    extra_names = {
        _normalize_observer(token)
        for token in str(args.extra_observer_names or "").split(",")
        if _normalize_observer(token)
    }
    disabled_names |= extra_names

    archive_dir: Path | None = None
    if bool(args.archive):
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        archive_dir = Path.home() / ".spark" / "archive" / "chip_insights_prune" / stamp
        archive_dir.mkdir(parents=True, exist_ok=True)

    print(f"chip_dir={chip_dir}")
    print(f"files={len(files)} active_only={bool(args.active_only)} apply={bool(args.apply)}")
    if active_ids:
        print(f"active_ids={','.join(active_ids)}")
    print(f"disabled_keys={len(disabled_keys)} disabled_names={len(disabled_names)}")
    if archive_dir is not None:
        print(f"archive_dir={archive_dir}")

    total_before = 0
    total_after = 0
    total_pruned = 0
    total_schema_kept = 0

    for path in files:
        rows = _read_jsonl_rows(path)
        before = len(rows)
        kept: List[Dict[str, Any]] = []
        pruned = 0
        schema_kept = 0

        for row in rows:
            _, observer, key = _row_observer_key(row)
            schema_row = _is_schema_row(row)
            should_prune = bool(observer) and (observer in disabled_names or (key and key in disabled_keys))
            if should_prune and schema_row and not bool(args.drop_schema_from_disabled):
                kept.append(row)
                schema_kept += 1
                continue
            if should_prune:
                pruned += 1
                continue
            kept.append(row)

        after = len(kept)
        total_before += before
        total_after += after
        total_pruned += pruned
        total_schema_kept += schema_kept

        if bool(args.apply) and before != after:
            if archive_dir is not None:
                shutil.copy2(path, archive_dir / path.name)
            _write_jsonl(path, kept)

        print(
            f"{path.name}: {before} -> {after} "
            f"(pruned={pruned}, schema_kept_from_disabled={schema_kept})"
        )

    print(
        f"TOTAL: {total_before} -> {total_after} "
        f"(pruned={total_pruned}, schema_kept_from_disabled={total_schema_kept})"
    )
    if not bool(args.apply):
        print("Dry-run only. Re-run with --apply to write changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

