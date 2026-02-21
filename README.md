<p align="center">
  <img src="logo.png" alt="Spark Intelligence" width="120">
  <h1 align="center">Spark Intelligence</h1>
  <p align="center">
    <em>a local self-evolving intelligence.</em>
  </p>
  <p align="center">
    <a href="https://github.com/vibeship/spark-intelligence/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-blue?style=flat-square" alt="License"></a>
    <img src="https://img.shields.io/badge/python-3.10+-blue?style=flat-square" alt="Python">
    <img src="https://img.shields.io/badge/runs-100%25_local-green?style=flat-square" alt="Local">
    <img src="https://img.shields.io/badge/platform-Win%20%7C%20Mac%20%7C%20Linux-lightgrey?style=flat-square" alt="Platform">
  </p>
</p>

---

Learns constantly. Resonates and evolves with you.
Runs 100% on your machine as a local AI companion. Brings a spark to everything.

```
You code → Spark learns → Agent adapts → You code better → Spark learns more
```

## What is Spark?

Spark Intelligence is a self-evolution layer for AI coding agents. It captures interaction signals, distills them into learnings, and feeds those learnings back into your agent to improve behavior over time.

Not a chatbot. Not a wrapper. A learning engine.

## Install

```bash
git clone https://github.com/vibeship/spark-intelligence
cd spark-intelligence
pip install -e .[services]
```

## Quick Start

```bash
# Start services
spark up

# Check health
spark health

# View what Spark has learned
spark learnings
```

Windows: run `start_spark.bat` from the repo root.

Lightweight mode (core only, no dashboards): `spark up --lite`

## Connect Your Agent

Spark works with any coding agent that supports hooks or event capture.

| Agent | Integration | Guide |
|-------|------------|-------|
| **Claude Code** | Hooks (PreToolUse, PostToolUse, UserPromptSubmit) | `docs/claude_code.md` |
| **Cursor / VS Code** | tasks.json + emit_event | `docs/cursor.md` |
| **OpenClaw** | Session JSONL tailer | `docs/openclaw/` |

## What You Get

- **Learning engine** — captures signals, distills insights, promotes high-value learnings to your agent context
- **Quality gates** — Meta-Ralph scores every insight before it enters the knowledge base
- **Advisory system** — pre-tool advice ranked by fusion scoring across 7 sources
- **Episodic intelligence (EIDOS)** — prediction → outcome → evaluation loop
- **Domain chips** — pluggable YAML modules for domain-specific learning
- **Dashboards** — Spark Pulse (primary), Meta-Ralph analyzer
- **CLI** — `spark status`, `spark learnings`, `spark promote`, `spark up/down`, and more
- **Hot-reloadable config** — tuneables system with schema validation and drift tracking

## Architecture

```
Your Agent (Claude Code / Cursor / OpenClaw)
  → hooks capture events
  → queue → bridge worker → pipeline
  → quality gate (Meta-Ralph) → cognitive learner
  → advisory system delivers insights pre-tool
  → context files updated → agent reads and adapts
```

## Documentation

- **5-minute start**: `docs/GETTING_STARTED_5_MIN.md`
- **Full setup**: `docs/QUICKSTART.md`
- **Docs index**: `docs/DOCS_INDEX.md`
- **Website**: [spark.vibeship.com](https://spark.vibeship.com)

## Responsible Use

This is a self-evolving system. If you are planning a public release or high-autonomy deployment:
- `docs/RESPONSIBLE_PUBLIC_RELEASE.md`
- `docs/security/THREAT_MODEL.md`
- `SECURITY.md` for vulnerability reporting

## License

[AGPL-3.0](LICENSE) — free to use, modify, and distribute. Network use requires source disclosure.

---

<p align="center">
  <sub>Built by <a href="https://vibeship.com">Vibeship</a></sub>
</p>
