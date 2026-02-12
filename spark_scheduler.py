#!/usr/bin/env python3
"""spark_scheduler -- periodic X intelligence tasks.

Runs mention polling, engagement snapshots, daily research, and niche scans
on configurable intervals. No HTTP server; communicates health via heartbeat.

Design:
- Task-based scheduler with configurable intervals per task
- Sequential execution to respect X API rate limits
- Fail-safe: task failures logged and skipped
- Draft reply queue for human review (NO auto-posting)

Usage:
  python spark_scheduler.py
  python spark_scheduler.py --once
  python spark_scheduler.py --task mention_poll --force
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))

from lib.diagnostics import setup_component_logging, log_exception

logger = logging.getLogger("spark.scheduler")

SPARK_DIR = Path.home() / ".spark"
SCHEDULER_DIR = SPARK_DIR / "scheduler"
HEARTBEAT_FILE = SCHEDULER_DIR / "heartbeat.json"
STATE_FILE = SCHEDULER_DIR / "state.json"
DRAFT_REPLIES_FILE = SPARK_DIR / "multiplier" / "draft_replies.json"
MULTIPLIER_DB_PATH = SPARK_DIR / "multiplier" / "scored_mentions.db"
TUNEABLES_FILE = SPARK_DIR / "tuneables.json"

CHECK_INTERVAL = 60  # Main loop checks every 60s which tasks are due


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = {
    "enabled": True,
    "mention_poll_interval": 600,
    "engagement_snapshot_interval": 1800,
    "daily_research_interval": 86400,
    "niche_scan_interval": 21600,
    "advisory_review_interval": 43200,
    "mention_poll_enabled": True,
    "engagement_snapshot_enabled": True,
    "daily_research_enabled": True,
    "niche_scan_enabled": True,
    "advisory_review_enabled": True,
    "advisory_review_window_hours": 12,
}


def load_scheduler_config() -> Dict[str, Any]:
    """Load scheduler config from tuneables.json -> 'scheduler' section."""
    config = dict(DEFAULT_CONFIG)
    try:
        if TUNEABLES_FILE.exists():
            data = json.loads(TUNEABLES_FILE.read_text(encoding="utf-8"))
            cfg = data.get("scheduler")
            if isinstance(cfg, dict):
                config.update(cfg)
    except Exception:
        pass
    return config


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def _load_state() -> Dict[str, Any]:
    """Load scheduler state from disk."""
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_state(state: Dict[str, Any]) -> None:
    """Persist scheduler state."""
    try:
        SCHEDULER_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception as e:
        logger.debug("Failed to save state: %s", e)


def write_scheduler_heartbeat(task_stats: Dict[str, Any]) -> None:
    """Write heartbeat file for watchdog monitoring."""
    try:
        SCHEDULER_DIR.mkdir(parents=True, exist_ok=True)
        HEARTBEAT_FILE.write_text(
            json.dumps({"ts": time.time(), "stats": task_stats}, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def scheduler_heartbeat_age_s() -> Optional[float]:
    """Return heartbeat age in seconds, or None if missing."""
    try:
        if not HEARTBEAT_FILE.exists():
            return None
        data = json.loads(HEARTBEAT_FILE.read_text(encoding="utf-8"))
        ts = float(data.get("ts", 0))
        if ts <= 0:
            return None
        return max(0.0, time.time() - ts)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Draft reply queue
# ---------------------------------------------------------------------------

def _save_draft_reply(decision: Dict[str, Any]) -> None:
    """Append a draft reply to the queue for human review."""
    try:
        DRAFT_REPLIES_FILE.parent.mkdir(parents=True, exist_ok=True)
        drafts = []
        if DRAFT_REPLIES_FILE.exists():
            try:
                drafts = json.loads(DRAFT_REPLIES_FILE.read_text(encoding="utf-8"))
            except Exception:
                drafts = []

        drafts.append({
            "tweet_id": decision.get("tweet_id", ""),
            "author": decision.get("author", ""),
            "action": decision.get("action", ""),
            "reply_text": decision.get("reply_text", ""),
            "reasoning": decision.get("reasoning", ""),
            "multiplier_tier": decision.get("multiplier_tier", ""),
            "queued_at": time.time(),
            "posted": False,
        })
        # Keep max 200 entries
        drafts = drafts[-200:]
        DRAFT_REPLIES_FILE.write_text(json.dumps(drafts, indent=2), encoding="utf-8")
    except Exception as e:
        logger.debug("Failed to save draft reply: %s", e)


def get_pending_drafts() -> List[Dict]:
    """Get unposted draft replies for human review."""
    try:
        if not DRAFT_REPLIES_FILE.exists():
            return []
        drafts = json.loads(DRAFT_REPLIES_FILE.read_text(encoding="utf-8"))
        return [d for d in drafts if not d.get("posted", False)]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Task: Mention Poll
# ---------------------------------------------------------------------------

def task_mention_poll(state: Dict[str, Any]) -> Dict[str, Any]:
    """Poll @mentions, score through Multiplier, queue draft replies."""
    from lib.x_client import get_x_client

    # Resolve spark-multiplier path
    multiplier_candidates = [
        Path(__file__).resolve().parent.parent / "spark-multiplier",
        Path.home() / "Desktop" / "spark-multiplier",
    ]
    multiplier_path = None
    for candidate in multiplier_candidates:
        if (candidate / "src" / "mention_monitor.py").exists():
            multiplier_path = candidate
            break

    if not multiplier_path:
        return {"error": "spark-multiplier not found"}

    if str(multiplier_path) not in sys.path:
        sys.path.insert(0, str(multiplier_path))

    from src.mention_monitor import MentionMonitor
    from src.models import MentionEvent
    from src.storage import Storage

    client = get_x_client()
    since_id = state.get("last_mention_id")
    raw_mentions = client.get_mentions(since_id=since_id, max_results=50)

    if not raw_mentions:
        return {"mentions_found": 0, "decisions": 0, "drafts_queued": 0}

    # Convert to MentionEvent objects
    mention_events = []
    for m in raw_mentions:
        mention_events.append(MentionEvent(
            tweet_id=m["tweet_id"],
            author=m.get("author", ""),
            text=m.get("text", ""),
            likes=m.get("likes", 0),
            retweets=m.get("retweets", 0),
            replies=m.get("replies", 0),
            author_followers=m.get("author_followers", 0),
            author_account_age_days=m.get("author_account_age_days", 0),
            created_at=m.get("created_at", ""),
            is_reply=m.get("is_reply", False),
            parent_tweet_id=m.get("parent_tweet_id", ""),
        ))

    # Process through Multiplier pipeline
    storage = Storage(db_path=MULTIPLIER_DB_PATH)
    monitor = MentionMonitor(storage=storage)
    decisions = monitor.process_mentions(mention_events)

    # Queue draft replies for human review
    drafts_queued = 0
    for d in decisions:
        if d.action in ("reward", "engage"):
            draft = {
                "tweet_id": d.tweet_id,
                "author": d.author,
                "action": d.action,
                "reply_text": d.reply_text,
                "reasoning": d.reasoning,
            }
            if d.multiplier:
                draft["multiplier_tier"] = d.multiplier.multiplier_tier
            _save_draft_reply(draft)
            drafts_queued += 1

    # Update since_id to newest mention
    if raw_mentions:
        newest_id = max(raw_mentions, key=lambda m: int(m["tweet_id"]))["tweet_id"]
        state["last_mention_id"] = newest_id

    logger.info(
        "mention_poll: %d mentions, %d decisions, %d drafts",
        len(raw_mentions), len(decisions), drafts_queued,
    )
    return {
        "mentions_found": len(raw_mentions),
        "decisions": len(decisions),
        "drafts_queued": drafts_queued,
    }


# ---------------------------------------------------------------------------
# Task: Engagement Snapshots
# ---------------------------------------------------------------------------

def task_engagement_snapshots(state: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch actual metrics for pending Pulse snapshots."""
    from lib.x_client import get_x_client
    from lib.engagement_tracker import get_engagement_tracker

    client = get_x_client()
    tracker = get_engagement_tracker()
    pending = tracker.get_pending_snapshots()

    if not pending:
        return {"pending": 0, "taken": 0}

    taken = 0
    for tweet_id, label in pending:
        metrics = client.get_tweet_by_id(tweet_id)
        if metrics:
            tracker.take_snapshot(
                tweet_id,
                likes=metrics.get("likes", 0),
                replies=metrics.get("replies", 0),
                retweets=metrics.get("retweets", 0),
                impressions=metrics.get("impressions", 0),
            )
            taken += 1

    tracker.cleanup_old(max_age_days=7)
    logger.info("engagement_snapshots: %d pending, %d taken", len(pending), taken)
    return {"pending": len(pending), "taken": taken}


# ---------------------------------------------------------------------------
# Task: Daily Research
# ---------------------------------------------------------------------------

def task_daily_research(state: Dict[str, Any]) -> Dict[str, Any]:
    """Run X searches for configured topics, feed through chip system."""
    from lib.x_client import get_x_client
    from scripts.daily_trend_research import (
        RESEARCH_TOPICS,
        extract_insights_from_search,
        generate_content_recommendations,
        store_daily_report,
        inject_to_spark,
        scan_niche_accounts,
        study_reply_patterns,
    )

    client = get_x_client()
    all_insights = []
    all_search_results = []

    for topic_name, topic_config in RESEARCH_TOPICS.items():
        for query in topic_config["queries"]:
            results = client.search_tweets(query, max_results=30)
            if results:
                # Convert to format expected by extract_insights_from_search
                formatted = [
                    {
                        "text": r.get("text", ""),
                        "likes": r.get("likes", 0),
                        "retweets": r.get("retweets", 0),
                        "created_at": r.get("created_at", ""),
                        "author": r.get("author", ""),
                    }
                    for r in results
                ]
                insights = extract_insights_from_search(formatted, topic_name)
                all_insights.extend(insights)
                all_search_results.extend(formatted)

    # Generate recommendations and store report
    recommendations = generate_content_recommendations(all_insights) if all_insights else []
    if all_insights:
        store_daily_report(all_insights, recommendations)
        injected = inject_to_spark(all_insights)
    else:
        injected = 0

    # Feed through NicheNet and ConvoIQ
    niche_discovered = scan_niche_accounts(all_search_results) if all_search_results else 0
    patterns_found = study_reply_patterns(all_search_results) if all_search_results else 0

    logger.info(
        "daily_research: %d insights, %d injected, %d niche accounts, %d patterns",
        len(all_insights), injected, niche_discovered, patterns_found,
    )
    return {
        "insights": len(all_insights),
        "recommendations": len(recommendations),
        "injected": injected,
        "niche_discovered": niche_discovered,
        "patterns_found": patterns_found,
    }


# ---------------------------------------------------------------------------
# Task: Niche Scan
# ---------------------------------------------------------------------------

def task_niche_scan(state: Dict[str, Any]) -> Dict[str, Any]:
    """Update NicheNet with accounts from recent research."""
    from lib.niche_mapper import get_niche_mapper

    mapper = get_niche_mapper()
    report_file = SPARK_DIR / "research_reports" / "latest.json"

    if not report_file.exists():
        return {"accounts_updated": 0}

    try:
        report = json.loads(report_file.read_text(encoding="utf-8"))
    except Exception:
        return {"accounts_updated": 0}

    # Extract unique authors from insights
    updated = 0
    seen = set()
    for insight in report.get("all_insights", []):
        # Insights don't always have author info, but scan for mentions
        topic = insight.get("topic", "")
        text = insight.get("text", "")
        engagement = insight.get("engagement", 0)

        if engagement < 10:
            continue

        # Look for @mentions in the text
        import re
        mentions = re.findall(r"@(\w+)", text)
        for handle in mentions:
            if handle.lower() in seen:
                continue
            seen.add(handle.lower())
            relevance = min(0.8, 0.3 + engagement / 200)
            mapper.discover_account(
                handle=handle,
                topics=[topic],
                relevance=relevance,
                discovered_via="scheduler_niche_scan",
            )
            updated += 1

    stats = mapper.get_network_stats()
    logger.info("niche_scan: %d accounts updated, %d total tracked",
                updated, stats.get("tracked_accounts", 0))
    return {"accounts_updated": updated, "total_tracked": stats.get("tracked_accounts", 0)}


def task_advisory_review(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a trace-backed advisory self-review report."""
    del state  # State not required for this task.
    script = Path(__file__).resolve().parent / "scripts" / "advisory_self_review.py"
    if not script.exists():
        return {"error": f"missing script: {script}"}

    cfg = load_scheduler_config()
    window_h = int(cfg.get("advisory_review_window_hours", 12) or 12)
    cmd = [
        sys.executable,
        str(script),
        "--window-hours",
        str(max(1, window_h)),
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(Path(__file__).resolve().parent),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        return {"error": f"self_review_failed: {stderr[:300]}"}

    line = (proc.stdout or "").strip().splitlines()
    msg = line[-1] if line else ""
    logger.info("advisory_review: %s", msg or "ok")
    return {"status": "ok", "message": msg}


# ---------------------------------------------------------------------------
# Task registry
# ---------------------------------------------------------------------------

TASKS = {
    "mention_poll": {
        "fn": task_mention_poll,
        "config_key_interval": "mention_poll_interval",
        "config_key_enabled": "mention_poll_enabled",
    },
    "engagement_snapshots": {
        "fn": task_engagement_snapshots,
        "config_key_interval": "engagement_snapshot_interval",
        "config_key_enabled": "engagement_snapshot_enabled",
    },
    "daily_research": {
        "fn": task_daily_research,
        "config_key_interval": "daily_research_interval",
        "config_key_enabled": "daily_research_enabled",
    },
    "niche_scan": {
        "fn": task_niche_scan,
        "config_key_interval": "niche_scan_interval",
        "config_key_enabled": "niche_scan_enabled",
    },
    "advisory_review": {
        "fn": task_advisory_review,
        "config_key_interval": "advisory_review_interval",
        "config_key_enabled": "advisory_review_enabled",
    },
}


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run_due_tasks(
    config: Dict[str, Any],
    state: Dict[str, Any],
    only_task: Optional[str] = None,
    force: bool = False,
) -> Dict[str, Any]:
    """Check which tasks are due, run them sequentially, update state."""
    now = time.time()
    combined_stats: Dict[str, Any] = {}

    for task_name, task_info in TASKS.items():
        if only_task and task_name != only_task:
            continue

        enabled = config.get(task_info["config_key_enabled"], True)
        if not enabled and not force:
            continue

        interval = config.get(task_info["config_key_interval"], 600)
        last_run = state.get(f"last_run_{task_name}", 0.0)

        if not force and (now - last_run) < interval:
            continue

        logger.info("Running task: %s", task_name)
        try:
            stats = task_info["fn"](state)
            state[f"last_run_{task_name}"] = time.time()
            state[f"last_result_{task_name}"] = "ok"
            combined_stats[task_name] = stats
        except Exception as e:
            state[f"last_result_{task_name}"] = f"error: {str(e)[:200]}"
            log_exception("scheduler", f"task {task_name} failed", e)
            combined_stats[task_name] = {"error": str(e)[:200]}

    _save_state(state)
    return combined_stats


def main():
    ap = argparse.ArgumentParser(description="Spark X Intelligence Scheduler")
    ap.add_argument("--once", action="store_true", help="Run all due tasks once then exit")
    ap.add_argument("--task", type=str, default=None, help="Run a specific task")
    ap.add_argument("--force", action="store_true", help="Run even if not due")
    args = ap.parse_args()

    setup_component_logging("scheduler")
    logger.info("Spark scheduler starting")

    config = load_scheduler_config()
    if not config.get("enabled", True):
        logger.info("Scheduler disabled in tuneables.json")
        return

    state = _load_state()
    stop_event = threading.Event()

    def _shutdown(signum=None, frame=None):
        logger.info("Scheduler shutting down")
        stop_event.set()

    try:
        signal.signal(signal.SIGINT, _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)
    except Exception:
        pass

    # Single run mode
    if args.once or args.task:
        stats = run_due_tasks(
            config, state,
            only_task=args.task,
            force=args.force or bool(args.task),
        )
        write_scheduler_heartbeat(stats)
        logger.info("Single run complete: %s", json.dumps(stats, default=str))
        return

    # Daemon loop
    logger.info("Scheduler daemon started (check interval: %ds)", CHECK_INTERVAL)
    while not stop_event.is_set():
        try:
            config = load_scheduler_config()  # Hot reload
            stats = run_due_tasks(config, state)
            write_scheduler_heartbeat(stats)
            if stats:
                logger.info("Tasks completed: %s", list(stats.keys()))
        except Exception as e:
            log_exception("scheduler", "scheduler cycle failed", e)

        stop_event.wait(CHECK_INTERVAL)

    logger.info("Scheduler stopped")


if __name__ == "__main__":
    main()
