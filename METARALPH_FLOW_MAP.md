# Meta-Ralph Flow Map

Generated: 2026-02-03
Status: **ALL SYSTEMS OPERATIONAL** (8/8 tests pass)

## Where Meta-Ralph Fits in the Intelligence Flow

```
SOURCES (observe.py, sparkd.py, adapters)
    |
    v
QUEUE (~/.spark/queue/events.jsonl)
    |
    v
BRIDGE_WORKER (every 60s)
    |
    +---> memory_capture
    |
    +---> pattern_detection --------+
    |         |                     |
    |         v                     |
    |     aggregator                |
    |         |                     |
    |         v                     |
    +---> chips_runtime             |
    |         |                     |
    |         v                     |
    |     (758k insights)           |
    |                               |
    +============================================+
    |                                            |
    |            *** META-RALPH ***              |
    |          Quality Gate & Feedback           |
    |                                            |
    |   +------------+  +------------+           |
    |   | roast()    |  | track_     |           |
    |   | Score 0-10 |  | outcome()  |           |
    |   +-----+------+  +-----+------+           |
    |         |               |                  |
    |         v               v                  |
    |   +-----------+   +-----------+            |
    |   | QUALITY   |   | FEEDBACK  |            |
    |   | >= 4/10   |   | good/bad  |            |
    |   +-----------+   +-----------+            |
    |         |               |                  |
    |         v               v                  |
    |   +-----------+   +-----------+            |
    |   | REFINE    |   | ADJUST    |            |
    |   | needs_work|   | scoring   |            |
    |   +-----------+   +-----------+            |
    |                                            |
    +============================================+
                    |
                    v
    +----------------------------------+
    |       PERSISTENCE LAYER          |
    |                                  |
    | cognitive_insights.json (1,564)  |
    | eidos.db (17 ep, 7 distill)      |
    | chip_insights/*.jsonl (765,997)  |
    +----------------------------------+
                    |
                    v
    +----------------------------------+
    |         MIND BRIDGE              |
    |      Sync to Mind API            |
    +----------------------------------+
                    |
                    v
    +----------------------------------+
    |          MIND API                |
    |      32,335 memories             |
    |      (lite+ tier)                |
    +----------------------------------+
```

## Meta-Ralph Integration Points

| Location | Function | What Happens |
|----------|----------|--------------|
| `observe.py:702` | `extract_cognitive_signals()` | User prompts roasted |
| `observe.py:583` | `extract_cognitive_signals()` | Write/Edit content roasted |
| `advisor.py:570` | `track_outcome()` | Tool outcomes recorded |
| `bridge_cycle` | pattern detection | Events -> distillations |

## Current Metrics (From Real Storage)

| Metric | Value | Source |
|--------|-------|--------|
| Quality Rate | 47.1% | meta_ralph/roast_history.json |
| Total Roasted | 399 | meta_ralph state |
| Quality Passed | 188 | meta_ralph state |
| Primitive Rejected | 76 | meta_ralph state |
| Outcomes Tracked | 355 | meta_ralph/outcome_tracking.json |
| Outcomes Acted On | 5 | outcome_records |
| Refinements Made | 1+ | live test verified |
| Cognitive Insights | 1,564 | cognitive_insights.json |
| Chip Insights | 765,997 | chip_insights/*.jsonl |
| EIDOS Distillations | 7 | eidos.db |
| Mind Memories | 32,335 | Mind API |

## Test Verification

Run the integration test to verify everything is working:

```bash
python tests/test_metaralph_integration.py
```

Expected output: `8/8 tests passed`

## What Each Test Verifies

| Test | Verifies |
|------|----------|
| storage | All data files exist with content |
| meta_ralph | State is healthy (not over/under filtering) |
| eidos | Distillations are being created |
| mind | Mind API is accessible |
| bridge | Bridge worker is running (<120s heartbeat) |
| roast | Live scoring works correctly |
| outcomes | Outcome tracking increments |
| refinement | needs_work items get refined |

## Tuning Meta-Ralph

### When to Lower Quality Threshold (currently 4)
- Pass rate < 10% AND blocked items score 3+
- Valuable insights are being blocked

### When to Raise Quality Threshold
- Pass rate > 80% AND stored items aren't useful
- Too much noise in retrieval

### Current Tuneables

| Parameter | Value | Location |
|-----------|-------|----------|
| quality_threshold | 4 | meta_ralph.py |
| needs_work_threshold | 2 | meta_ralph.py |
| QUALITY_SIGNALS | 15 patterns | meta_ralph.py |
| PRIMITIVE_PATTERNS | 17 patterns | meta_ralph.py |

## Flow Verification Checklist

Before any tuning session:

- [ ] `python tests/test_metaralph_integration.py` passes 8/8
- [ ] Bridge worker heartbeat < 120s old
- [ ] Mind API responds to /health
- [ ] Queue is being processed (events decreasing or stable)
- [ ] Cognitive insights count is growing over sessions

## Anti-Hallucination Rules

1. **Never trust terminal output** - Query storage directly
2. **Verify changes in storage** - Not just "code looks right"
3. **Check the flow** - Is bridge_worker running? Is Mind up?
4. **Run integration test** - Before claiming improvements work
