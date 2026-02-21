"""Generate browsable detail pages for individual items in each data store.

Generates:
  explore/
    cognitive/     _index.md + per-insight pages
    distillations/ _index.md + per-distillation pages
    episodes/      _index.md + per-episode pages (with steps)
    advisory/      _index.md (source breakdown + recent advice)
    promotions/    _index.md + per-batch pages
    verdicts/      _index.md + per-verdict pages
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Iterator

from .config import ObservatoryConfig, spark_dir
from .linker import fmt_ts, fmt_ago, fmt_num, fmt_size, flow_link
from .readers import _load_json, _tail_jsonl, _count_jsonl, _file_size


_SD = spark_dir()


def _slug(text: str, max_len: int = 60) -> str:
    """Convert text to a safe filename slug."""
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9_\-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:max_len] if s else "unnamed"


def _frontmatter(meta: dict) -> str:
    """Generate YAML frontmatter block."""
    lines = ["---"]
    for k, v in meta.items():
        if isinstance(v, str):
            # Escape quotes in strings
            v_safe = v.replace('"', '\\"')
            lines.append(f'{k}: "{v_safe}"')
        elif isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        elif isinstance(v, (int, float)):
            lines.append(f"{k}: {v}")
        elif isinstance(v, list):
            lines.append(f"{k}: {json.dumps(v)}")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---\n")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
#  COGNITIVE INSIGHTS
# ═══════════════════════════════════════════════════════════════════════

def _export_cognitive(explore_dir: Path, limit: int) -> int:
    """Export cognitive insights as individual pages + index."""
    out = explore_dir / "cognitive"
    out.mkdir(parents=True, exist_ok=True)
    ci = _load_json(_SD / "cognitive_insights.json") or {}
    if not isinstance(ci, dict):
        return 0

    # Sort by reliability * validations (descending)
    items = []
    for key, val in ci.items():
        if not isinstance(val, dict):
            continue
        items.append((key, val))
    items.sort(key=lambda x: (-x[1].get("reliability", 0), -x[1].get("times_validated", 0)))
    items = items[:limit]

    # Generate detail pages
    for key, val in items:
        slug = _slug(key)
        insight = val.get("insight", "")
        meta = {
            "type": "spark-cognitive-insight",
            "key": key,
            "category": val.get("category", "?"),
            "reliability": round(val.get("reliability", 0), 3),
            "validations": val.get("times_validated", 0),
            "contradictions": val.get("times_contradicted", 0),
            "confidence": round(val.get("confidence", 0), 3),
            "promoted": val.get("promoted", False),
            "promoted_to": val.get("promoted_to") or "none",
            "source": val.get("source", "?"),
            "created_at": val.get("created_at", "?"),
        }
        body = [_frontmatter(meta)]
        body.append(f"# {key[:80]}\n")
        body.append(f"> Back to [[_index|Cognitive Index]] | {flow_link()}\n")
        body.append(f"## Insight\n\n{insight}\n")
        body.append(f"## Metadata\n")
        body.append(f"| Field | Value |")
        body.append(f"|-------|-------|")
        body.append(f"| Category | {val.get('category', '?')} |")
        body.append(f"| Reliability | {val.get('reliability', 0):.0%} |")
        body.append(f"| Validations | {val.get('times_validated', 0)} |")
        body.append(f"| Contradictions | {val.get('times_contradicted', 0)} |")
        body.append(f"| Confidence | {val.get('confidence', 0):.3f} |")
        body.append(f"| Source | {val.get('source', '?')} |")
        body.append(f"| Promoted | {'yes' if val.get('promoted') else 'no'} |")
        if val.get("promoted_to"):
            body.append(f"| Promoted to | {val['promoted_to']} |")
        body.append(f"| Advisory readiness | {val.get('advisory_readiness', 0):.3f} |")
        body.append(f"| Created | {val.get('created_at', '?')} |")
        body.append(f"| Last validated | {val.get('last_validated_at', 'never')} |")
        body.append("")

        # Evidence
        evidence = val.get("evidence", [])
        if evidence:
            body.append(f"## Evidence ({len(evidence)} items)\n")
            for i, e in enumerate(evidence[:10], 1):
                e_text = str(e)[:200].replace("\n", " ").replace("\r", "")
                body.append(f"{i}. `{e_text}`")
            if len(evidence) > 10:
                body.append(f"\n*... and {len(evidence) - 10} more*")
            body.append("")

        # Counter-examples
        counters = val.get("counter_examples", [])
        if counters:
            body.append(f"## Counter-Examples ({len(counters)})\n")
            for i, c in enumerate(counters[:5], 1):
                body.append(f"{i}. `{str(c)[:200]}`")
            body.append("")

        (out / f"{slug}.md").write_text("\n".join(body), encoding="utf-8")

    # Generate index
    index = [_frontmatter({
        "type": "spark-cognitive-index",
        "total": len(ci),
        "exported": len(items),
        "limit": limit,
    })]
    index.append(f"# Cognitive Insights ({len(items)}/{len(ci)})\n")
    index.append(f"> {flow_link()} | [[../stages/06-cognitive-learner|Stage 6: Cognitive Learner]]\n")
    if len(items) < len(ci):
        index.append(f"*Showing top {len(items)} by reliability. Increase `explore_cognitive_max` in tuneables to see more.*\n")

    index.append("| Key | Category | Reliability | Validations | Promoted | Link |")
    index.append("|-----|----------|-------------|-------------|----------|------|")
    for key, val in items:
        slug = _slug(key)
        rel = f"{val.get('reliability', 0):.0%}"
        vld = val.get("times_validated", 0)
        promoted = "yes" if val.get("promoted") else "—"
        cat = val.get("category", "?")
        index.append(f"| `{key[:50]}` | {cat} | {rel} | {vld} | {promoted} | [[{slug}]] |")
    index.append("")
    (out / "_index.md").write_text("\n".join(index), encoding="utf-8")
    return len(items) + 1  # detail pages + index


# ═══════════════════════════════════════════════════════════════════════
#  EIDOS DISTILLATIONS
# ═══════════════════════════════════════════════════════════════════════

def _export_distillations(explore_dir: Path, limit: int) -> int:
    """Export EIDOS distillations as individual pages + index."""
    out = explore_dir / "distillations"
    out.mkdir(parents=True, exist_ok=True)
    db_path = _SD / "eidos.db"
    if not db_path.exists():
        (out / "_index.md").write_text(f"# Distillations\n\neidos.db not found.\n", encoding="utf-8")
        return 1

    try:
        conn = sqlite3.connect(str(db_path), timeout=2)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM distillations")
        total = cur.fetchone()[0]

        cur.execute("""
            SELECT * FROM distillations
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
    except Exception as e:
        (out / "_index.md").write_text(f"# Distillations\n\nError reading eidos.db: {e}\n", encoding="utf-8")
        return 1

    for row in rows:
        did = row["distillation_id"]
        slug = _slug(did)
        meta = {
            "type": "spark-eidos-distillation",
            "distillation_id": did,
            "distillation_type": row.get("type", "?"),
            "confidence": round(row.get("confidence", 0), 3),
            "validation_count": row.get("validation_count", 0),
            "contradiction_count": row.get("contradiction_count", 0),
            "times_retrieved": row.get("times_retrieved", 0),
            "times_used": row.get("times_used", 0),
            "times_helped": row.get("times_helped", 0),
            "created_at": fmt_ts(row.get("created_at")),
        }
        body = [_frontmatter(meta)]
        body.append(f"# Distillation: {did[:20]}\n")
        body.append(f"> Back to [[_index|Distillations Index]] | {flow_link()} | [[../stages/07-eidos|Stage 7: EIDOS]]\n")
        body.append(f"**Type:** {row.get('type', '?')} | **Confidence:** {row.get('confidence', 0):.2f}\n")
        body.append(f"## Statement\n\n{row.get('statement', '(empty)')}\n")
        body.append(f"## Metrics\n")
        body.append(f"| Field | Value |")
        body.append(f"|-------|-------|")
        body.append(f"| Validated | {row.get('validation_count', 0)} times |")
        body.append(f"| Contradicted | {row.get('contradiction_count', 0)} times |")
        body.append(f"| Retrieved | {row.get('times_retrieved', 0)} times |")
        body.append(f"| Used | {row.get('times_used', 0)} times |")
        body.append(f"| Helped | {row.get('times_helped', 0)} times |")
        body.append(f"| Created | {fmt_ts(row.get('created_at'))} |")
        revalidate = row.get("revalidate_by")
        if revalidate:
            body.append(f"| Revalidate by | {fmt_ts(revalidate)} |")
        body.append("")

        # Domains & triggers
        for field, label in [("domains", "Domains"), ("triggers", "Triggers"), ("anti_triggers", "Anti-Triggers")]:
            raw = row.get(field)
            if raw:
                try:
                    items = json.loads(raw) if isinstance(raw, str) else raw
                    if items:
                        body.append(f"## {label}\n")
                        for item in items:
                            body.append(f"- `{item}`")
                        body.append("")
                except Exception:
                    pass

        # Source steps
        raw_steps = row.get("source_steps")
        if raw_steps:
            try:
                step_ids = json.loads(raw_steps) if isinstance(raw_steps, str) else raw_steps
                if step_ids:
                    body.append(f"## Source Steps ({len(step_ids)})\n")
                    for sid in step_ids[:10]:
                        body.append(f"- `{sid}`")
                    body.append("")
            except Exception:
                pass

        (out / f"{slug}.md").write_text("\n".join(body), encoding="utf-8")

    # Index
    index = [_frontmatter({
        "type": "spark-distillations-index",
        "total": total,
        "exported": len(rows),
        "limit": limit,
    })]
    index.append(f"# EIDOS Distillations ({len(rows)}/{total})\n")
    index.append(f"> {flow_link()} | [[../stages/07-eidos|Stage 7: EIDOS]]\n")
    if len(rows) < total:
        index.append(f"*Showing most recent {len(rows)}. Increase `explore_distillations_max` in tuneables to see more.*\n")

    index.append("| ID | Type | Statement | Confidence | Validated | Retrieved | Link |")
    index.append("|----|------|-----------|------------|-----------|-----------|------|")
    for row in rows:
        did = row["distillation_id"]
        slug = _slug(did)
        stmt = (row.get("statement", "")[:80] + "...") if len(row.get("statement", "")) > 80 else row.get("statement", "")
        stmt = stmt.replace("|", "/").replace("\n", " ")
        index.append(f"| `{did[:12]}` | {row.get('type','?')} | {stmt} | {row.get('confidence',0):.2f} | {row.get('validation_count',0)} | {row.get('times_retrieved',0)} | [[{slug}]] |")
    index.append("")
    (out / "_index.md").write_text("\n".join(index), encoding="utf-8")
    return len(rows) + 1


# ═══════════════════════════════════════════════════════════════════════
#  EIDOS EPISODES
# ═══════════════════════════════════════════════════════════════════════

def _export_episodes(explore_dir: Path, limit: int) -> int:
    """Export EIDOS episodes with their steps as individual pages + index."""
    out = explore_dir / "episodes"
    out.mkdir(parents=True, exist_ok=True)
    db_path = _SD / "eidos.db"
    if not db_path.exists():
        (out / "_index.md").write_text(f"# Episodes\n\neidos.db not found.\n", encoding="utf-8")
        return 1

    try:
        conn = sqlite3.connect(str(db_path), timeout=2)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM episodes")
        total = cur.fetchone()[0]

        cur.execute("""
            SELECT * FROM episodes
            ORDER BY start_ts DESC
            LIMIT ?
        """, (limit,))
        episodes = [dict(r) for r in cur.fetchall()]

        # Prefetch steps for these episodes
        if episodes:
            eids = [e["episode_id"] for e in episodes]
            placeholders = ",".join("?" * len(eids))
            cur.execute(f"""
                SELECT * FROM steps
                WHERE episode_id IN ({placeholders})
                ORDER BY created_at ASC
            """, eids)
            all_steps = [dict(r) for r in cur.fetchall()]
        else:
            all_steps = []
        conn.close()
    except Exception as e:
        (out / "_index.md").write_text(f"# Episodes\n\nError reading eidos.db: {e}\n", encoding="utf-8")
        return 1

    # Group steps by episode
    steps_by_ep: dict[str, list[dict]] = {}
    for s in all_steps:
        eid = s.get("episode_id", "")
        steps_by_ep.setdefault(eid, []).append(s)

    for ep in episodes:
        eid = ep["episode_id"]
        slug = _slug(eid)
        goal = ep.get("goal", "")[:120]
        steps = steps_by_ep.get(eid, [])

        meta = {
            "type": "spark-eidos-episode",
            "episode_id": eid,
            "outcome": ep.get("outcome", "?"),
            "phase": ep.get("phase", "?"),
            "step_count": ep.get("step_count", 0),
            "started": fmt_ts(ep.get("start_ts")),
            "ended": fmt_ts(ep.get("end_ts")),
        }
        body = [_frontmatter(meta)]
        body.append(f"# Episode: {eid[:16]}\n")
        body.append(f"> Back to [[_index|Episodes Index]] | {flow_link()} | [[../stages/07-eidos|Stage 7: EIDOS]]\n")

        body.append(f"## Goal\n\n{goal}\n")
        body.append(f"## Summary\n")
        body.append(f"| Field | Value |")
        body.append(f"|-------|-------|")
        body.append(f"| Outcome | **{ep.get('outcome', '?')}** |")
        body.append(f"| Phase | {ep.get('phase', '?')} |")
        body.append(f"| Steps | {ep.get('step_count', 0)} |")
        body.append(f"| Started | {fmt_ts(ep.get('start_ts'))} |")
        body.append(f"| Ended | {fmt_ts(ep.get('end_ts'))} |")
        if ep.get("final_evaluation"):
            body.append(f"| Evaluation | {ep['final_evaluation'][:100]} |")
        body.append("")

        # Steps
        if steps:
            body.append(f"## Steps ({len(steps)})\n")
            for i, s in enumerate(steps, 1):
                eval_icon = {"success": "pass", "failure": "FAIL", "unknown": "?"}.get(s.get("evaluation", ""), "?")
                body.append(f"### Step {i}: {s.get('intent', '?')[:80]}\n")
                body.append(f"- **Decision:** {s.get('decision', '?')[:120]}")
                body.append(f"- **Action:** {s.get('action_type', '?')}")
                if s.get("prediction"):
                    body.append(f"- **Prediction:** {s['prediction'][:120]}")
                body.append(f"- **Evaluation:** {eval_icon}")
                if s.get("surprise_level", 0) > 0.1:
                    body.append(f"- **Surprise:** {s['surprise_level']:.2f}")
                if s.get("lesson"):
                    body.append(f"- **Lesson:** {s['lesson'][:150]}")
                body.append("")
        else:
            body.append("## Steps\n\nNo steps recorded for this episode.\n")

        (out / f"{slug}.md").write_text("\n".join(body), encoding="utf-8")

    # Index
    index = [_frontmatter({
        "type": "spark-episodes-index",
        "total": total,
        "exported": len(episodes),
        "limit": limit,
    })]
    index.append(f"# EIDOS Episodes ({len(episodes)}/{total})\n")
    index.append(f"> {flow_link()} | [[../stages/07-eidos|Stage 7: EIDOS]]\n")
    if len(episodes) < total:
        index.append(f"*Showing most recent {len(episodes)}. Increase `explore_episodes_max` in tuneables to see more.*\n")

    index.append("| ID | Goal | Outcome | Phase | Steps | Started | Link |")
    index.append("|----|------|---------|-------|-------|---------|------|")
    for ep in episodes:
        eid = ep["episode_id"]
        slug = _slug(eid)
        goal = ep.get("goal", "")[:60].replace("|", "/").replace("\n", " ")
        index.append(f"| `{eid[:12]}` | {goal} | **{ep.get('outcome','?')}** | {ep.get('phase','?')} | {ep.get('step_count',0)} | {fmt_ts(ep.get('start_ts'))} | [[{slug}]] |")
    index.append("")
    (out / "_index.md").write_text("\n".join(index), encoding="utf-8")
    return len(episodes) + 1


# ═══════════════════════════════════════════════════════════════════════
#  META-RALPH VERDICTS
# ═══════════════════════════════════════════════════════════════════════

def _export_verdicts(explore_dir: Path, limit: int) -> int:
    """Export recent Meta-Ralph roast verdicts as a browsable index."""
    out = explore_dir / "verdicts"
    out.mkdir(parents=True, exist_ok=True)

    rh = _load_json(_SD / "meta_ralph" / "roast_history.json") or {}
    history = rh.get("history", []) if isinstance(rh, dict) else []
    total = len(history)
    recent = history[-limit:] if history else []

    # Verdict distribution
    verdicts: dict[str, int] = {}
    for entry in history:
        v = entry.get("result", {}).get("verdict", "unknown")
        verdicts[v] = verdicts.get(v, 0) + 1

    # Generate per-verdict detail pages grouped by batch (same timestamp)
    pages_written = 0
    for i, entry in enumerate(recent):
        idx = total - limit + i if total > limit else i
        slug = f"verdict_{idx:05d}"
        result = entry.get("result", {})
        score = result.get("score", {})

        meta = {
            "type": "spark-metaralph-verdict",
            "verdict": result.get("verdict", "?"),
            "total_score": score.get("total", 0) if isinstance(score, dict) else 0,
            "source": entry.get("source", "?"),
            "timestamp": entry.get("timestamp", "?"),
        }
        body = [_frontmatter(meta)]
        body.append(f"# Verdict #{idx}: {result.get('verdict', '?')}\n")
        body.append(f"> Back to [[_index|Verdicts Index]] | {flow_link()} | [[../stages/05-meta-ralph|Stage 5: Meta-Ralph]]\n")

        # Original text (truncated for readability)
        original = result.get("original", "")
        if original:
            display = original[:500]
            if len(original) > 500:
                display += f"\n\n*... ({len(original)} chars total)*"
            body.append(f"## Input Text\n\n{display}\n")

        # Score breakdown
        if isinstance(score, dict):
            body.append(f"## Score Breakdown\n")
            body.append(f"| Dimension | Score |")
            body.append(f"|-----------|-------|")
            for dim in ["actionability", "novelty", "reasoning", "specificity", "outcome_linked", "ethics"]:
                body.append(f"| {dim} | {score.get(dim, 0)} |")
            body.append(f"| **Total** | **{score.get('total', 0)}** |")
            body.append(f"| Verdict | **{score.get('verdict', result.get('verdict', '?'))}** |")
            body.append("")

        # Issues
        issues = result.get("issues_found", [])
        if issues:
            body.append(f"## Issues Found\n")
            for issue in issues:
                body.append(f"- {issue}")
            body.append("")

        # Refinement
        refined = result.get("refined_version")
        if refined:
            body.append(f"## Refined Version\n\n{refined[:300]}\n")

        (out / f"{slug}.md").write_text("\n".join(body), encoding="utf-8")
        pages_written += 1

    # Index
    index = [_frontmatter({
        "type": "spark-verdicts-index",
        "total": total,
        "exported": len(recent),
        "limit": limit,
    })]
    index.append(f"# Meta-Ralph Verdicts ({len(recent)}/{total})\n")
    index.append(f"> {flow_link()} | [[../stages/05-meta-ralph|Stage 5: Meta-Ralph]]\n")
    if len(recent) < total:
        index.append(f"*Showing most recent {len(recent)}. Increase `explore_verdicts_max` in tuneables to see more.*\n")

    # Distribution
    if verdicts:
        index.append("## Verdict Distribution (all time)\n")
        index.append("| Verdict | Count | % |")
        index.append("|---------|-------|---|")
        for v, count in sorted(verdicts.items(), key=lambda x: -x[1]):
            pct = round(count / max(total, 1) * 100, 1)
            index.append(f"| {v} | {count} | {pct}% |")
        index.append("")

    # Recent table
    index.append("## Recent Verdicts\n")
    index.append("| # | Time | Source | Verdict | Score | Link |")
    index.append("|---|------|--------|---------|-------|------|")
    for i, entry in enumerate(recent):
        idx = total - limit + i if total > limit else i
        slug = f"verdict_{idx:05d}"
        result = entry.get("result", {})
        score = result.get("score", {})
        total_score = score.get("total", 0) if isinstance(score, dict) else 0
        ts = entry.get("timestamp", "?")[:19]
        index.append(f"| {idx} | {ts} | {entry.get('source','?')} | **{result.get('verdict','?')}** | {total_score} | [[{slug}]] |")
    index.append("")
    (out / "_index.md").write_text("\n".join(index), encoding="utf-8")
    return pages_written + 1


# ═══════════════════════════════════════════════════════════════════════
#  PROMOTIONS
# ═══════════════════════════════════════════════════════════════════════

def _export_promotions(explore_dir: Path, limit: int) -> int:
    """Export promotion log as a browsable index (no individual pages — log entries are small)."""
    out = explore_dir / "promotions"
    out.mkdir(parents=True, exist_ok=True)
    path = _SD / "promotion_log.jsonl"
    total = _count_jsonl(path)
    recent = _tail_jsonl(path, limit)

    # Target + result distribution from recent
    targets: dict[str, int] = {}
    results: dict[str, int] = {}
    for entry in recent:
        t = entry.get("target", "?")
        r = entry.get("result", "?")
        targets[t] = targets.get(t, 0) + 1
        results[r] = results.get(r, 0) + 1

    index = [_frontmatter({
        "type": "spark-promotions-index",
        "total": total,
        "exported": len(recent),
        "limit": limit,
    })]
    index.append(f"# Promotion Log ({len(recent)}/{total})\n")
    index.append(f"> {flow_link()} | [[../stages/09-promotion|Stage 9: Promotion]]\n")
    if len(recent) < total:
        index.append(f"*Showing most recent {len(recent)}. Increase `explore_promotions_max` in tuneables to see more.*\n")

    if targets:
        index.append("## Target Distribution (recent)\n")
        index.append("| Target | Count |")
        index.append("|--------|-------|")
        for t, c in sorted(targets.items(), key=lambda x: -x[1]):
            index.append(f"| {t} | {c} |")
        index.append("")

    if results:
        index.append("## Result Distribution (recent)\n")
        index.append("| Result | Count |")
        index.append("|--------|-------|")
        for r, c in sorted(results.items(), key=lambda x: -x[1]):
            index.append(f"| {r} | {c} |")
        index.append("")

    index.append("## Recent Activity\n")
    index.append("| Time | Key | Target | Result | Reason |")
    index.append("|------|-----|--------|--------|--------|")
    for entry in reversed(recent):  # Most recent first
        ts = entry.get("ts", "?")[:19]
        key = entry.get("key", "?")[:50]
        target = entry.get("target", "?")
        result = entry.get("result", "?")
        reason = entry.get("reason", "")[:40].replace("|", "/")
        index.append(f"| {ts} | `{key}` | {target} | {result} | {reason} |")
    index.append("")
    (out / "_index.md").write_text("\n".join(index), encoding="utf-8")
    return 1


# ═══════════════════════════════════════════════════════════════════════
#  ADVISORY SOURCE EFFECTIVENESS
# ═══════════════════════════════════════════════════════════════════════

def _export_advisory(explore_dir: Path, advice_limit: int) -> int:
    """Export advisory effectiveness breakdown + recent advice as a browsable index."""
    out = explore_dir / "advisory"
    out.mkdir(parents=True, exist_ok=True)

    eff = _load_json(_SD / "advisor" / "effectiveness.json") or {}
    metrics = _load_json(_SD / "advisor" / "metrics.json") or {}
    recent = _tail_jsonl(_SD / "advisor" / "advice_log.jsonl", advice_limit)

    total_given = eff.get("total_advice_given", 0)
    total_followed = eff.get("total_followed", 0)
    total_helpful = eff.get("total_helpful", 0)

    index = [_frontmatter({
        "type": "spark-advisory-index",
        "total_given": total_given,
        "total_followed": total_followed,
        "total_helpful": total_helpful,
        "followed_rate": round(total_followed / max(total_given, 1) * 100, 1),
    })]
    index.append(f"# Advisory Effectiveness\n")
    index.append(f"> {flow_link()} | [[../stages/08-advisory|Stage 8: Advisory]]\n")

    index.append("## Overall\n")
    index.append("| Metric | Value |")
    index.append("|--------|-------|")
    index.append(f"| Total advice given | {fmt_num(total_given)} |")
    index.append(f"| Followed | {fmt_num(total_followed)} ({total_followed/max(total_given,1)*100:.1f}%) |")
    index.append(f"| Helpful | {fmt_num(total_helpful)} |")
    index.append(f"| Cognitive helpful rate | {metrics.get('cognitive_helpful_rate', 0):.1%} |")
    index.append("")

    by_source = eff.get("by_source", {})
    if by_source:
        index.append("## Source Effectiveness\n")
        index.append("| Source | Total | Helpful | Rate |")
        index.append("|--------|-------|---------|------|")
        for src, stats in sorted(by_source.items(), key=lambda x: -x[1].get("total", 0)):
            t = stats.get("total", 0)
            h = stats.get("helpful", 0)
            rate = f"{h/max(t,1)*100:.1f}%" if t > 0 else "—"
            index.append(f"| **{src}** | {fmt_num(t)} | {fmt_num(h)} | {rate} |")
        index.append("")

    # Recent advice entries
    advice_entries = [r for r in recent if "advice_texts" in r]
    if advice_entries:
        index.append(f"## Recent Advice ({len(advice_entries)} entries)\n")
        for i, entry in enumerate(reversed(advice_entries[-50:]), 1):
            tool = entry.get("tool", "?")
            ts = entry.get("timestamp", "?")[:19]
            texts = entry.get("advice_texts", [])
            sources = entry.get("sources", [])
            index.append(f"### {i}. {tool} ({ts})\n")
            for j, txt in enumerate(texts[:5]):
                src = sources[j] if j < len(sources) else "?"
                index.append(f"- **[{src}]** {txt[:200]}")
            index.append("")

    (out / "_index.md").write_text("\n".join(index), encoding="utf-8")
    return 1


# ═══════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ═══════════════════════════════════════════════════════════════════════

def generate_explorer(cfg: ObservatoryConfig) -> dict[str, int]:
    """Generate all explorer pages. Returns {section: files_written}."""
    vault = Path(cfg.vault_dir).expanduser()
    explore_dir = vault / "_observatory" / "explore"
    explore_dir.mkdir(parents=True, exist_ok=True)

    counts = {}
    counts["cognitive"] = _export_cognitive(explore_dir, cfg.explore_cognitive_max)
    counts["distillations"] = _export_distillations(explore_dir, cfg.explore_distillations_max)
    counts["episodes"] = _export_episodes(explore_dir, cfg.explore_episodes_max)
    counts["verdicts"] = _export_verdicts(explore_dir, cfg.explore_verdicts_max)
    counts["promotions"] = _export_promotions(explore_dir, cfg.explore_promotions_max)
    counts["advisory"] = _export_advisory(explore_dir, cfg.explore_advice_max)

    # Generate master explore index
    _generate_explore_index(explore_dir, counts, cfg)
    return counts


def _generate_explore_index(explore_dir: Path, counts: dict[str, int], cfg: ObservatoryConfig) -> None:
    """Generate the master explore/_index.md that links to all sections."""
    index = [_frontmatter({"type": "spark-explorer-index"})]
    index.append(f"# Explore Spark Intelligence\n")
    index.append(f"> {flow_link()} | Browse individual items from every stage\n")
    index.append("## Data Stores\n")
    index.append("| Store | Items Exported | Max | Browse |")
    index.append("|-------|---------------|-----|--------|")
    sections = [
        ("cognitive", "Cognitive Insights", cfg.explore_cognitive_max, "explore_cognitive_max"),
        ("distillations", "EIDOS Distillations", cfg.explore_distillations_max, "explore_distillations_max"),
        ("episodes", "EIDOS Episodes", cfg.explore_episodes_max, "explore_episodes_max"),
        ("verdicts", "Meta-Ralph Verdicts", cfg.explore_verdicts_max, "explore_verdicts_max"),
        ("promotions", "Promotion Log", cfg.explore_promotions_max, "explore_promotions_max"),
        ("advisory", "Advisory Effectiveness", cfg.explore_advice_max, "explore_advice_max"),
    ]
    for key, label, max_val, tuneable in sections:
        n = counts.get(key, 0)
        index.append(f"| {label} | {n} pages | {max_val} | [[{key}/_index]] |")
    index.append("")
    index.append("## Adjusting Limits\n")
    index.append("All limits are configurable in `~/.spark/tuneables.json` under the `observatory` section:\n")
    index.append("```json")
    index.append('"observatory": {')
    index.append(f'    "explore_cognitive_max": {cfg.explore_cognitive_max},')
    index.append(f'    "explore_distillations_max": {cfg.explore_distillations_max},')
    index.append(f'    "explore_episodes_max": {cfg.explore_episodes_max},')
    index.append(f'    "explore_verdicts_max": {cfg.explore_verdicts_max},')
    index.append(f'    "explore_promotions_max": {cfg.explore_promotions_max},')
    index.append(f'    "explore_advice_max": {cfg.explore_advice_max}')
    index.append("}")
    index.append("```\n")
    index.append("Then regenerate: `python scripts/generate_observatory.py --force --verbose`\n")
    (explore_dir / "_index.md").write_text("\n".join(index), encoding="utf-8")
