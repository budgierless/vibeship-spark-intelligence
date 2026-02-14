#!/usr/bin/env python3
"""x_trends_brief

Generate a concise trends + content advisory brief from Spark's stored X research
insights (JSONL under ~/.spark/chip_insights).

This does *not* call the X API. It's safe/cheap to run frequently.

Outputs:
- top "new" / "surging" topics observed recently
- top high-performing tweets captured recently (by likes)
- 3-7 content angles derived from replicable lessons / triggers

Usage:
  python scripts/x_trends_brief.py --hours 4
  python scripts/x_trends_brief.py --hours 24 --save docs/reports
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path


SPARK_DIR = Path.home() / ".spark"
CHIP_INSIGHTS_DIR = SPARK_DIR / "chip_insights"


def _parse_ts(s: str) -> datetime | None:
    try:
        # store_insight uses ISO with timezone (UTC). Be defensive if tz is missing.
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _read_jsonl(path: Path):
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=4.0, help="Lookback window in hours")
    ap.add_argument("--save", default=None, help="Optional directory to save a markdown report")
    ap.add_argument("--limit", type=int, default=8, help="Max tweets to show")
    args = ap.parse_args()

    since = datetime.now(timezone.utc) - timedelta(hours=args.hours)

    engagement_path = CHIP_INSIGHTS_DIR / "engagement-pulse.jsonl"
    social_path = CHIP_INSIGHTS_DIR / "x_social.jsonl"

    # Trends
    trends: list[dict] = []
    for row in _read_jsonl(social_path):
        ts = _parse_ts(row.get("timestamp", ""))
        if not ts or ts < since:
            continue
        if row.get("observer") != "trend_observed":
            continue
        fields = (row.get("captured_data") or {}).get("fields") or {}
        if fields.get("direction") in ("surging", "new"):
            trends.append({
                "topic": fields.get("topic"),
                "direction": fields.get("direction"),
                "volume": fields.get("volume"),
                "previous_avg": fields.get("previous_avg"),
                "ts": ts,
            })

    # High performers
    tweets: list[dict] = []
    for row in _read_jsonl(engagement_path):
        ts = _parse_ts(row.get("timestamp", ""))
        if not ts or ts < since:
            continue
        if row.get("observer") != "high_performer_detected":
            continue
        fields = (row.get("captured_data") or {}).get("fields") or {}
        likes = fields.get("likes", 0) or 0
        tweets.append({
            "topic": fields.get("topic"),
            "likes": int(likes),
            "user": fields.get("user_handle"),
            "followers": fields.get("user_followers"),
            "text": fields.get("content") or fields.get("tweet_text") or "",
            "url": fields.get("tweet_url"),
            "lesson": fields.get("replicable_lesson") or fields.get("why_it_works") or "",
            "triggers": fields.get("emotional_triggers") or [],
            "ts": ts,
        })

    tweets.sort(key=lambda t: (t.get("likes", 0), t.get("followers", 0) or 0), reverse=True)
    tweets = tweets[: max(1, args.limit)]

    # Content angles
    angles: list[str] = []
    for t in tweets:
        if t.get("lesson"):
            angles.append(t["lesson"].strip())
        elif t.get("triggers"):
            trig = ", ".join(list(t["triggers"])[:2])
            angles.append(f"Lean into triggers: {trig}")

    # Deduplicate angles
    seen = set()
    angles_dedup = []
    for a in angles:
        key = a.lower()
        if key in seen:
            continue
        seen.add(key)
        angles_dedup.append(a)
    angles = angles_dedup[:7]

    # Format
    window_label = f"last {args.hours:g}h"
    lines: list[str] = []
    lines.append(f"# X Trends Brief ({window_label})")
    lines.append("")

    if trends:
        trends.sort(key=lambda x: x["ts"], reverse=True)
        lines.append("## Hot signals (new/surging)")
        for tr in trends[:10]:
            topic = tr.get("topic") or "?"
            direction = tr.get("direction")
            vol = tr.get("volume")
            prev = tr.get("previous_avg")
            lines.append(f"- **{topic}** — {direction} (vol={vol}, prev_avg={prev})")
        lines.append("")

    if tweets:
        lines.append("## Top viral posts captured")
        for t in tweets:
            topic = t.get("topic") or "?"
            likes = t.get("likes")
            user = t.get("user") or "?"
            txt = (t.get("text") or "").replace("\n", " ").strip()
            if len(txt) > 220:
                txt = txt[:217] + "..."
            url = t.get("url")
            url_part = f" ({url})" if url else ""
            lines.append(f"- **{likes}** likes · {user} · _{topic}_ — {txt}{url_part}")
        lines.append("")

    if angles:
        lines.append("## Content angles to write")
        for a in angles:
            lines.append(f"- {a}")
        lines.append("")

    if not (trends or tweets):
        lines.append("No recent trends/high-performers found in the lookback window.")
        lines.append("")

    out = "\n".join(lines)
    print(out)

    if args.save:
        out_dir = Path(args.save)
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
        path = out_dir / f"x_trends_brief_{stamp}Z.md"
        path.write_text(out, encoding="utf-8")
        print(f"\nSaved: {path}")


if __name__ == "__main__":
    main()
