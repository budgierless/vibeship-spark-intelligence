# Getting Started (5 Minutes)

If you are new: follow this page first. For the full map, see `docs/DOCS_INDEX.md`.

## 0) Prereqs

- Python 3.10+
- `pip`

## 1) Install

### Option A: Installer (Recommended)

- Windows: clone `spark-openclaw-installer` and run `install.ps1`
- Mac/Linux: clone `spark-openclaw-installer` and run `install.sh`

See `README.md` for the exact commands.

### Option B: Manual (Repo)

```bash
cd /path/to/vibeship-spark-intelligence
pip install -e .[services]
```

## 2) Start Services

### Windows (repo)

```bat
start_spark.bat
```

### Mac/Linux (repo)

```bash
python3 -m spark.cli up
# or: spark up
```

## 3) Verify Health

CLI:
```bash
python3 -m spark.cli health
```

HTTP:
- sparkd liveness: `http://127.0.0.1:8787/health` (plain `ok`)
- sparkd status: `http://127.0.0.1:8787/status` (JSON)
- Mind (if enabled): `http://127.0.0.1:8080/health`

## 4) Open Dashboards

- Spark Pulse (primary): `http://localhost:8765`

See `DASHBOARD_PLAYBOOK.md` for all ports and endpoints.

## 5) Connect Your Coding Agent

If you use Claude Code or Cursor:
- Claude Code: `docs/claude_code.md`
- Cursor/VS Code: `docs/cursor.md`

The goal is simple:
- Spark writes learnings to context files.
- Your agent reads them and adapts.

## Troubleshooting (Fast)

- Port already in use: change ports via env (see `lib/ports.py` and `docs/QUICKSTART.md`).
- Health is red: start via `start_spark.bat` / `spark up` (not manual scripts) so watchdog + workers come up correctly.
- Queue shows 0 events: you may simply not have run any tool interactions yet in this session.
