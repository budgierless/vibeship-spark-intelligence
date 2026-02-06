# Spark Scheduler - Quick Guide

## What It Does

Runs your X/Twitter intelligence automatically in the background. Four tasks:

| Task | Every | What happens |
|------|-------|-------------|
| Mention poll | 10 min | Fetches @mentions, scores them, queues draft replies |
| Engagement snapshots | 30 min | Checks how your tweets are performing |
| Daily research | 24 hours | Searches X for trends in your topics |
| Niche scan | 6 hours | Discovers new accounts in your space |

**It never posts anything.** Draft replies go to a review queue.

## How to Use

### Start everything (scheduler included)
```
python -m spark.cli up
```

### Run scheduler alone
```
python spark_scheduler.py
```

### Run one task right now
```
python spark_scheduler.py --task mention_poll --force
python spark_scheduler.py --task engagement_snapshots --force
python spark_scheduler.py --task daily_research --force
python spark_scheduler.py --task niche_scan --force
```

### Run all due tasks once and exit
```
python spark_scheduler.py --once
```

### Check status
```
python -m spark.cli status
```
Look for the `scheduler: RUNNING` line.

## Review Draft Replies

The scheduler scores mentions but never auto-posts. Drafts are saved here:

```
~/.spark/multiplier/draft_replies.json
```

Each draft has:
- `tweet_id` -- the mention
- `author` -- who mentioned you
- `action` -- "reward" or "engage"
- `reply_text` -- suggested reply
- `multiplier_tier` -- bronze/silver/gold/diamond (if reward)
- `posted` -- false until you approve it

To review in Claude: "Show me pending Multiplier replies"

## Change Settings

Edit `~/.spark/tuneables.json`, add a `"scheduler"` section:

```json
{
  "scheduler": {
    "enabled": true,
    "mention_poll_interval": 600,
    "engagement_snapshot_interval": 1800,
    "daily_research_interval": 86400,
    "niche_scan_interval": 21600,
    "mention_poll_enabled": true,
    "engagement_snapshot_enabled": true,
    "daily_research_enabled": true,
    "niche_scan_enabled": true
  }
}
```

All intervals are in seconds. Changes apply on next cycle (no restart needed).

To disable a specific task, set its `_enabled` to `false`.

## Files

| File | What |
|------|------|
| `spark_scheduler.py` | The daemon |
| `lib/x_client.py` | Talks to X API via tweepy |
| `~/.spark/scheduler/state.json` | Task timestamps |
| `~/.spark/scheduler/heartbeat.json` | Health signal |
| `~/.spark/multiplier/draft_replies.json` | Reply queue |
| `~/.spark/multiplier/scored_mentions.db` | Scored mentions DB |

## Requirements

These environment variables must be set (they already are on this machine):

```
TWITTER_BEARER_TOKEN
TWITTER_API_KEY
TWITTER_API_SECRET
TWITTER_ACCESS_TOKEN
TWITTER_ACCESS_TOKEN_SECRET
```

## Troubleshooting

**Scheduler won't start:** Check `TWITTER_BEARER_TOKEN` is set. Run `python spark_scheduler.py --once` to see errors.

**No mentions showing up:** The X API only returns mentions from the last 7 days. Run `python spark_scheduler.py --task mention_poll --force` to test.

**Watchdog keeps restarting it:** Check `~/.spark/logs/scheduler.log` for errors.

**Want to stop it:** `python -m spark.cli down` stops everything, or kill the scheduler PID from `~/.spark/pids/scheduler.pid`.
