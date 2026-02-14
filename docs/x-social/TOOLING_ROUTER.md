# X Research Tooling Router (x-research-skill + XMCP + Spark learner)

Goal: **when we do X research manually, Spark should still learn/evolve**.

We run two layers in parallel:

1) **x-research-skill (Bun/TS CLI)** — fast, agent-friendly, ad-hoc research workflow.
2) **XMCP / x-twitter-mcp (MCP server + tweepy utilities)** — fallback + extra endpoints/features not covered by x-research-skill.

Then we bridge outputs into:

3) **SparkResearcher (lib/x_research.py)** — the internal learner that writes chip insights (engagement-pulse, x_social) so bridge_worker can distill patterns.

---

## What to use when (practical scenarios)

### Use **x-research-skill** when you want research outputs *now*
Best for:
- Quick pulse checks ("what’s CT saying about X today")
- Query search w/ sorting + noise filtering
- Pull a full thread by tweet id
- Pull recent tweets from a profile
- Maintain a watchlist + check it
- Save a markdown research doc

Commands (via wrapper):

```powershell
# help
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\USER\.openclaw\workspace\skills\x-research\x-search.ps1 --help

# search
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\USER\.openclaw\workspace\skills\x-research\x-search.ps1 search "AI agents" --quick --quality

# thread
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\USER\.openclaw\workspace\skills\x-research\x-search.ps1 thread 1234567890

# profile
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\USER\.openclaw\workspace\skills\x-research\x-search.ps1 profile frankdegods
```

Notes:
- x-research-skill uses **recent search** (last 7 days) by default.
- It expects `X_BEARER_TOKEN`; our wrapper sources it from `mcp-servers/x-twitter-mcp/.env`.

### Use **XMCP / x-twitter-mcp** when you need features x-research-skill doesn’t have
Typical reasons:
- Any custom MCP workflow you already built around XMCP
- Posting/liking/deleting (if desired)
- Special endpoints / custom fields / richer user objects
- Full-archive search (if you implement it there first)

Relevant local folder:
- `vibeship-spark-intelligence/mcp-servers/x-twitter-mcp/`

---

## Making Spark learn from ad-hoc research (required)

### The principle
If we do manual research, we should also **ingest** a structured version into Spark’s learner so:
- patterns can be extracted
- chips can distill learnings
- the research loop can evolve (topics, triggers, watchlist)

### Current bridge: `scripts/x_research_ingest.py`
This script:
1) Runs `x-search.ps1 search ... --json`
2) Maps results to `SparkResearcher.ingest_mcp_results()` shape
3) Stores insights into `~/.spark/chip_insights/engagement-pulse.jsonl`

Usage:

```powershell
cd C:\Users\USER\Desktop\vibeship-spark-intelligence
python scripts\x_research_ingest.py search "OpenClaw" --topic openclaw --quick --limit 25 --since 1d
```

### Scheduled-friendly pulse cycle: `scripts/x_pulse_cycle.py`
Runs a **single aggregated query** in x-research quick mode (cheap), ingests results, then prints a trends/content brief.

```powershell
cd C:\Users\USER\Desktop\vibeship-spark-intelligence
python scripts\x_pulse_cycle.py --since 4h --limit 25 --hours 4
```

Brief-only (no API calls):

```powershell
python scripts\x_trends_brief.py --hours 4
```

---

## Default routing policy (simple)

- If you want **answers + sourced brief** → x-research-skill
- If you want **Spark to learn from it** → run `scripts/x_research_ingest.py` (or we wire it as a follow-up step)
- If x-research-skill can’t do it (or needs MCP wiring) → XMCP

---

## Security notes

- Do **not** paste tokens into chat.
- Keep tokens only in local `.env` files (already gitignored):
  - `**/x-twitter-mcp/.env`
  - `.env`
- Prefer read-only tokens when possible.
