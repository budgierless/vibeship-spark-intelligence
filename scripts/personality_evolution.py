#!/usr/bin/env python3
"""Inspect/apply/reset Spark personality evolution V1 state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lib.personality_evolver import load_personality_evolver


def _load_signals(args: argparse.Namespace) -> dict:
    if args.signals:
        return json.loads(args.signals)
    if args.signals_file:
        return json.loads(Path(args.signals_file).read_text(encoding="utf-8"))
    return {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Spark personality evolution V1 utility")
    parser.add_argument("--state-path", help="Optional custom state path")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("inspect", help="Print evolution state and style profile")

    apply_parser = sub.add_parser("apply", help="Apply user-guided interaction signals")
    apply_parser.add_argument("--signals", help="Signals JSON string")
    apply_parser.add_argument("--signals-file", help="Path to signals JSON file")

    reset_parser = sub.add_parser("reset", help="Reset evolution state to defaults")
    reset_parser.add_argument("--yes", action="store_true", help="Confirm reset")

    args = parser.parse_args()
    evolver = load_personality_evolver(state_path=Path(args.state_path) if args.state_path else None)

    if args.command == "inspect":
        print(
            json.dumps(
                {
                    "enabled": evolver.enabled,
                    "observer_mode": evolver.observer_mode,
                    "state_path": str(evolver.state_path),
                    "state": evolver.state,
                    "style_profile": evolver.emit_style_profile(),
                },
                indent=2,
            )
        )
        return

    if args.command == "apply":
        signals = _load_signals(args)
        result = evolver.ingest_signals(signals, persist=True)
        print(json.dumps(result, indent=2))
        return

    if args.command == "reset":
        if not args.yes:
            raise SystemExit("Refusing reset without --yes")
        state = evolver.reset_state(persist=True)
        print(json.dumps({"reset": True, "state": state}, indent=2))
        return


if __name__ == "__main__":
    main()
