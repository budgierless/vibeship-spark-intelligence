# Future Config System Plan (Reverted)

Status:
- The experimental config-wiring attempt was reverted on 2026-02-03.
- This document explains how to implement the system later, safely, and in phases.

Goal:
- Centralize Spark tuneables in one YAML file with profiles.
- Keep env vars for quick overrides and temporary testing.
- Provide agent- and terminal-friendly settings for context injection.

Why we paused:
- Too many control surfaces at once (code defaults + YAML + env + adapters) can cause drift.
- We want stability and clarity before reintroducing a config control plane.

---

## Recommended approach (phased)

Phase 1 (high impact):
- memory_capture, pattern_detection, distiller, memory_gate
- eidos budgets + watchers
- context_sync + promoter
- advisor + mind_bridge
- bridge_worker / bridge_cycle limits

Phase 2 (medium impact):
- outcomes + prediction + validation
- chips scoring + evolution
- resonance / spark_voice / growth

Phase 3 (low impact):
- dashboards, diagnostics, adapters, research

---

## Architecture (when you restart)

1) YAML source of truth
- File: config/spark_runtime.yaml
- Contains defaults and profiles (default, exploratory, strict, fast, memory_heavy).
- Sections should mirror subsystems to avoid confusion.

2) Config loader
- File: lib/config.py
- Responsibilities:
  - Load YAML and merge defaults + selected profile.
  - Allow env overrides (env > YAML > code defaults).
  - Provide get_setting(key, default, env_var=...).

3) Env apply (optional)
- Command: spark config apply
- Writes ~/.spark/spark_runtime.env for services to consume.
- service_control.py and spark_watchdog.py load that env file before spawning workers.
- This allows "big changes" in YAML to propagate by applying once.

4) LLM terminal adapters (outputs)
- Outputs should read from config:
  - outputs.adapters.claude_code
  - outputs.adapters.cursor
  - outputs.adapters.windsurf
  - outputs.adapters.clawdbot
  - outputs.adapters.exports
- Per-adapter control:
  - enabled
  - path
  - markers
  - max_chars
  - headers

---

## Profiles (example intent)

- default: balanced, current behavior
- exploratory: lower thresholds, more capture, faster learning
- strict: higher thresholds, less noise
- fast: fewer items, lower overhead
- memory_heavy: more retention and larger context sync

---

## Precedence rules (recommended)

env > YAML > code defaults

Why:
- YAML defines stable baseline.
- Env lets you do quick, temporary overrides without editing YAML.
- Code defaults are the final fallback if neither is set.

---

## Risk controls (to avoid chaos)

1) Explicit allowlist
- Only expose a curated list of tuneables in YAML.
- Avoid "all knobs" too early.

2) Schema validation
- Add a simple validation check in lib/config.py for missing/invalid keys.

3) Drift detection
- Add a unit test or CI check:
  - Every YAML key must map to a known code setting.
  - Every configurable code setting must be present in YAML (or explicitly excluded).

4) Safe defaults
- No profile should disable safety checks by default.

---

## Files to change (later)

Core:
- lib/config.py (new)
- config/spark_runtime.yaml (new)

Wire-ins:
- bridge_worker.py
- lib/bridge_cycle.py
- lib/queue.py
- hooks/observe.py
- lib/memory_capture.py
- lib/pattern_detection/*
- lib/pattern_detection/distiller.py
- lib/pattern_detection/memory_gate.py
- lib/eidos/* (budgets + watchers)
- lib/context_sync.py
- lib/promoter.py
- lib/advisor.py
- lib/mind_bridge.py
- lib/output_adapters/*
- sparkd.py
- mind_server.py
- lib/service_control.py
- spark_watchdog.py

CLI:
- spark/cli.py (add: spark config show/apply/export)

Dependencies:
- pyproject.toml (add PyYAML)

---

## Minimal "restart" plan

1) Add lib/config.py + config/spark_runtime.yaml.
2) Wire high-impact modules only.
3) Add spark config show/apply to CLI.
4) Add tests for config key coverage.
5) Expand to medium/low impact later.

---

## Why this is still valuable

Pros:
- Single source of truth for tuning.
- Easy switching between behavior modes.
- LLMs and tools can parse one config file to understand the system.
- Makes experiments reproducible.

Cons:
- Risk of configuration drift if not maintained.
- More moving parts to understand.
- Potential for conflicting control planes if env/YAML/code are all used loosely.

Recommendation:
- Keep it phased and strict. Do not expose every knob at once.

