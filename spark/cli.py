#!/usr/bin/env python3
"""
Spark CLI - Command-line interface for Spark

Usage:
    python -m spark.cli status     # Show system status
    python -m spark.cli services   # Show daemon/service status
    python -m spark.cli up         # Start background services
    python -m spark.cli ensure     # Start missing services if not running
    python -m spark.cli down       # Stop background services
    python -m spark.cli sync       # Sync insights to Mind
    python -m spark.cli queue      # Process offline queue
    python -m spark.cli process    # Run bridge worker cycle / drain backlog
    python -m spark.cli validate   # Run validation scan
    python -m spark.cli learnings  # Show recent learnings
    python -m spark.cli promote    # Run promotion check
    python -m spark.cli write      # Write learnings to markdown
    python -m spark.cli health     # Health check
    python -m spark.cli memory     # Memory capture suggestions
    python -m spark.cli outcome    # Record explicit outcome check-in
    python -m spark.cli eval       # Evaluate predictions vs outcomes
    python -m spark.cli validate-ingest  # Validate recent queue events
    python -m spark.cli project    # Project questioning + capture
"""

import sys
import json
import argparse
import time
import os
from pathlib import Path

from lib.cognitive_learner import get_cognitive_learner
from lib.mind_bridge import get_mind_bridge, sync_all_to_mind
from lib.markdown_writer import get_markdown_writer, write_all_learnings
from lib.promoter import get_promoter, check_and_promote
from lib.queue import get_queue_stats, read_recent_events, count_events
from lib.aha_tracker import get_aha_tracker
from lib.spark_voice import get_spark_voice
from lib.growth_tracker import get_growth_tracker
from lib.context_sync import sync_context
from lib.service_control import (
    start_services,
    stop_services,
    service_status,
    format_status_lines,
)
from lib.bridge_cycle import run_bridge_cycle, write_bridge_heartbeat, bridge_heartbeat_age_s
from lib.pattern_detection import get_pattern_backlog
from lib.validation_loop import (
    process_validation_events,
    get_validation_backlog,
    get_validation_state,
    process_outcome_validation,
    get_insight_outcome_coverage,
)
from lib.prediction_loop import get_prediction_state
from lib.evaluation import evaluate_predictions
from lib.outcome_log import (
    append_outcome,
    build_explicit_outcome,
    link_outcome_to_insight,
    get_outcome_links,
    read_outcomes,
    get_unlinked_outcomes,
    get_outcome_stats,
)
from lib.outcome_checkin import list_checkins, record_checkin_request
from lib.ingest_validation import scan_queue_events, write_ingest_report
from lib.exposure_tracker import (
    read_recent_exposures,
    read_exposures_within,
    read_last_exposure,
    infer_latest_session_id,
)
from lib.project_profile import (
    load_profile,
    save_profile,
    ensure_questions,
    get_suggested_questions,
    record_answer,
    record_entry,
    infer_domain,
    set_phase,
    completion_score,
)
from lib.memory_banks import store_memory
from lib.outcome_log import append_outcome, make_outcome_id
from lib.memory_capture import (
    process_recent_memory_events,
    list_pending as capture_list_pending,
    accept_suggestion as capture_accept,
    reject_suggestion as capture_reject,
)
from lib.capture_cli import format_pending
from lib.memory_migrate import migrate as migrate_memory

# Chips imports (lazy to avoid startup cost if not used)
def _get_chips_registry():
    from lib.chips import get_registry
    return get_registry()

def _get_chips_router():
    from lib.chips import get_router
    return get_router()

# Moltbook imports (lazy to avoid startup cost if not used)
def _get_moltbook_client():
    from adapters.moltbook.client import MoltbookClient, is_registered
    return MoltbookClient(), is_registered

def _get_moltbook_agent():
    from adapters.moltbook.agent import SparkMoltbookAgent
    return SparkMoltbookAgent()


def _configure_output():
    """Ensure UTF-8 output on Windows terminals to avoid UnicodeEncodeError."""
    for stream in (sys.stdout, sys.stderr):
        try:
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def cmd_status(args):
    """Show overall system status."""
    voice = get_spark_voice()
    
    print("\n" + "=" * 60)
    print("  SPARK - Self-Evolving Intelligence Layer")
    print("=" * 60)
    print(f"\n  {voice.get_status_voice()}\n")
    
    # Cognitive learner stats
    cognitive = get_cognitive_learner()
    cognitive_stats = cognitive.get_stats()
    print("📚 Cognitive Insights")
    print(f"   Total: {cognitive_stats['total_insights']}")
    print(f"   Avg Reliability: {cognitive_stats['avg_reliability']:.0%}")
    print(f"   Promoted: {cognitive_stats['promoted_count']}")
    print(f"   By Category:")
    for cat, count in cognitive_stats['by_category'].items():
        print(f"      - {cat}: {count}")
    print()
    
    # Mind bridge stats
    bridge = get_mind_bridge()
    bridge_stats = bridge.get_stats()
    print("🧠 Mind Bridge")
    print(f"   Mind Available: {'✓ Yes' if bridge_stats['mind_available'] else '✗ No'}")
    print(f"   Synced to Mind: {bridge_stats['synced_count']}")
    print(f"   Offline Queue: {bridge_stats['offline_queue_size']}")
    print(f"   Last Sync: {bridge_stats['last_sync'] or 'Never'}")
    print()
    
    # Queue stats
    queue_stats = get_queue_stats()
    print("📋 Event Queue")
    print(f"   Events: {queue_stats['event_count']}")
    print(f"   Size: {queue_stats['size_mb']} MB")
    print(f"   Needs Rotation: {'Yes' if queue_stats['needs_rotation'] else 'No'}")
    print(f"   Pattern Backlog: {get_pattern_backlog()}")
    print(f"   Validation Backlog: {get_validation_backlog()}")
    ingest_stats = scan_queue_events(limit=200)
    processed = ingest_stats.get("processed", 0) or 0
    invalid = ingest_stats.get("invalid", 0) or 0
    if processed:
        valid = ingest_stats.get("valid", 0) or 0
        print(f"   Ingest Valid (last {processed}): {valid}/{processed} ({invalid} invalid)")
    print()

    # Project intelligence
    try:
        profile = load_profile(Path.cwd())
        score = completion_score(profile)
        print("🎯 Project Intelligence")
        print(f"   Domain: {profile.get('domain')}  Phase: {profile.get('phase')}")
        print(f"   Completion Score: {score['score']}/100")
        print(f"   Done: {profile.get('done') or 'not set'}")
        print()
    except Exception:
        pass

    # Worker heartbeat
    hb_age = bridge_heartbeat_age_s()
    print("âš™ Workers")
    if hb_age is None:
        print("   bridge_worker: Unknown (no heartbeat)")
    else:
        status = "OK" if hb_age <= 90 else "Stale"
        print(f"   bridge_worker: {status} (last {int(hb_age)}s ago)")
    print()

    # Validation loop
    vstate = get_validation_state()
    last_ts = vstate.get("last_run_ts")
    last_stats = vstate.get("last_stats") or {}
    if last_ts:
        age_s = max(0, int(time.time() - float(last_ts)))
        print("✅ Validation Loop")
        print(f"   Last Run: {age_s}s ago")
        print(
            f"   Last Stats: +{last_stats.get('validated', 0)} / -{last_stats.get('contradicted', 0)} "
            f"(surprises {last_stats.get('surprises', 0)})"
        )
    else:
        print("✅ Validation Loop")
        print("   Last Run: Never")
    print()

    # Prediction loop
    pstate = get_prediction_state()
    plast_ts = pstate.get("last_run_ts")
    plast_stats = pstate.get("last_stats") or {}
    if plast_ts:
        age_s = max(0, int(time.time() - float(plast_ts)))
        print("🧭 Prediction Loop")
        print(f"   Last Run: {age_s}s ago")
        print(
            f"   Last Stats: preds {plast_stats.get('predictions', 0)}, "
            f"outcomes {plast_stats.get('outcomes', 0)}, "
            f"+{plast_stats.get('validated', 0)} / -{plast_stats.get('contradicted', 0)} "
            f"(matched {plast_stats.get('matched', 0)}, surprises {plast_stats.get('surprises', 0)})"
        )
    else:
        print("🧭 Prediction Loop")
        print("   Last Run: Never")
    print()
    
    # Markdown writer stats
    writer = get_markdown_writer()
    writer_stats = writer.get_stats()
    print("📝 Markdown Output")
    print(f"   Directory: {writer_stats['learnings_dir']}")
    print(f"   Learnings Written: {writer_stats['learnings_count']}")
    print(f"   Errors Written: {writer_stats['errors_count']}")
    print()
    
    # Promoter stats
    promoter = get_promoter()
    promo_stats = promoter.get_promotion_status()
    print("📤 Promotions")
    print(f"   Ready for Promotion: {promo_stats['ready_for_promotion']}")
    print(f"   Already Promoted: {promo_stats['promoted_count']}")
    if promo_stats['by_target']:
        print(f"   By Target:")
        for target, count in promo_stats['by_target'].items():
            print(f"      - {target}: {count}")
    print()
    
    # Aha tracker stats
    aha = get_aha_tracker()
    aha_stats = aha.get_stats()
    print("💡 Surprises (Aha Moments)")
    print(f"   Total Captured: {aha_stats['total_captured']}")
    print(f"   Unexpected Successes: {aha_stats['unexpected_successes']}")
    print(f"   Unexpected Failures: {aha_stats['unexpected_failures']}")
    print(f"   Lessons Extracted: {aha_stats['lessons_extracted']}")
    if aha_stats['pending_surface'] > 0:
        print(f"   ⚠️  Pending to Show: {aha_stats['pending_surface']}")
    print()
    
    # Voice/personality stats
    voice_stats = voice.get_stats()
    print("🎭 Personality")
    print(f"   Age: {voice_stats['age_days']} days")
    print(f"   Interactions: {voice_stats['interactions']}")
    print(f"   Opinions Formed: {voice_stats['opinions_formed']}")
    print(f"   Growth Moments: {voice_stats['growth_moments']}")
    if voice_stats['strong_opinions'] > 0:
        print(f"   Strong Opinions: {voice_stats['strong_opinions']}")
    print()
    
    print("=" * 60)


def cmd_sync(args):
    """Sync insights to Mind."""
    print("[SPARK] Syncing to Mind...")
    stats = sync_all_to_mind()
    print(f"\nResults: {json.dumps(stats, indent=2)}")


def cmd_queue(args):
    """Process offline queue."""
    bridge = get_mind_bridge()
    print("[SPARK] Processing offline queue...")
    count = bridge.process_offline_queue()
    print(f"Processed: {count} items")


def cmd_process(args):
    """Run one bridge worker cycle or drain backlog."""
    iterations = 0
    processed = 0
    start = time.time()

    max_iterations = args.max_iterations
    timeout_s = args.timeout

    while True:
        stats = run_bridge_cycle(
            query=args.query,
            memory_limit=args.memory_limit,
            pattern_limit=args.pattern_limit,
        )
        write_bridge_heartbeat(stats)
        iterations += 1
        processed += int(stats.get("pattern_processed") or 0)

        errors = stats.get("errors") or []
        if errors:
            print(f"[SPARK] Cycle errors: {', '.join(errors)}")

        backlog = get_pattern_backlog()
        if not args.drain:
            break
        if backlog <= 0:
            break
        if max_iterations and iterations >= max_iterations:
            break
        if timeout_s and (time.time() - start) >= timeout_s:
            break
        if stats.get("pattern_processed", 0) <= 0 and not errors:
            break
        time.sleep(max(0.5, float(args.interval)))

    print(f"[SPARK] bridge_worker cycles: {iterations}, patterns processed: {processed}")


def cmd_validate(args):
    """Run validation loop scan on recent events."""
    stats = process_validation_events(limit=args.limit)
    print("[SPARK] Validation scan")
    print(f"  processed: {stats.get('processed', 0)}")
    print(f"  validated: {stats.get('validated', 0)}")
    print(f"  contradicted: {stats.get('contradicted', 0)}")
    print(f"  surprises: {stats.get('surprises', 0)}")


def cmd_learnings(args):
    """Show recent learnings."""
    cognitive = get_cognitive_learner()
    insights = list(cognitive.insights.values())
    
    # Sort by created_at
    insights.sort(key=lambda x: x.created_at, reverse=True)
    
    limit = args.limit or 10
    print(f"\n📚 Recent Cognitive Insights (showing {min(limit, len(insights))} of {len(insights)})\n")
    
    for insight in insights[:limit]:
        status = "✓ Promoted" if insight.promoted else f"{insight.reliability:.0%} reliable"
        print(f"[{insight.category.value}] {insight.insight}")
        print(f"   {status} | {insight.times_validated} validations | {insight.created_at[:10]}")
        print()


def cmd_promote(args):
    """Run promotion check."""
    dry_run = args.dry_run
    print(f"[SPARK] Checking for promotable insights (dry_run={dry_run})...")
    stats = check_and_promote(dry_run=dry_run, include_project=(not args.no_project))
    print(f"\nResults: {json.dumps(stats, indent=2)}")


def cmd_write(args):
    """Write learnings to markdown."""
    print("[SPARK] Writing learnings to markdown...")
    stats = write_all_learnings()
    print(f"\nResults: {json.dumps(stats, indent=2)}")


def cmd_sync_context(args):
    """Sync bootstrap context to platform outputs."""
    project_dir = Path(args.project).expanduser() if args.project else None
    stats = sync_context(
        project_dir=project_dir,
        min_reliability=args.min_reliability,
        min_validations=args.min_validations,
        limit=args.limit,
        include_promoted=(not args.no_promoted),
        diagnose=args.diagnose,
    )
    out = {
        "selected": stats.selected,
        "promoted_selected": stats.promoted_selected,
        "targets": stats.targets,
    }
    if args.diagnose:
        out["diagnostics"] = stats.diagnostics or {}
    print(json.dumps(out, indent=2))


def cmd_decay(args):
    """Preview or apply decay-based pruning."""
    cognitive = get_cognitive_learner()
    if args.apply:
        pruned = cognitive.prune_stale(max_age_days=args.max_age_days, min_effective=args.min_effective)
        print(f"[SPARK] Pruned {pruned} stale insights")
        return

    candidates = cognitive.get_prune_candidates(
        max_age_days=args.max_age_days,
        min_effective=args.min_effective,
        limit=args.limit,
    )
    print("[SPARK] Decay dry-run")
    print(f"  candidates: {len(candidates)} (showing up to {args.limit})")
    for c in candidates:
        print(f"- [{c['category']}] {c['insight']}")
        print(f"  age={c['age_days']}d effective={c['effective_reliability']} raw={c['reliability']} v={c['validations']} x={c['contradictions']}")


def cmd_health(args):
    """Health check."""
    print("\n🏥 Health Check\n")
    
    # Check cognitive learner
    try:
        cognitive = get_cognitive_learner()
        print("✓ Cognitive Learner: OK")
    except Exception as e:
        print(f"✗ Cognitive Learner: {e}")
    
    # Check Mind connection
    bridge = get_mind_bridge()
    if bridge._check_mind_health():
        print("✓ Mind API: OK")
    else:
        print("✗ Mind API: Not available (will queue offline)")
    
    # Check queue
    try:
        stats = get_queue_stats()
        print(f"✓ Event Queue: OK ({stats['event_count']} events)")
    except Exception as e:
        print(f"✗ Event Queue: {e}")
    
    # Check bridge worker heartbeat
    hb_age = bridge_heartbeat_age_s()
    if hb_age is None:
        print("âš  bridge_worker: No heartbeat (start bridge_worker)")
    else:
        print(f"âœ“ bridge_worker: heartbeat {int(hb_age)}s ago")

    # Check learnings dir
    writer = get_markdown_writer()
    if writer.learnings_dir.exists():
        print(f"✓ Learnings Dir: OK ({writer.learnings_dir})")
    else:
        print(f"? Learnings Dir: Will be created on first write")
    
    print()


def cmd_services(args):
    """Show daemon/service status."""
    status = service_status(bridge_stale_s=args.bridge_stale_s)
    print("")
    for line in format_status_lines(status, bridge_stale_s=args.bridge_stale_s):
        print(line)
    print("")


def _should_start_watchdog(args) -> bool:
    if args.no_watchdog:
        return False
    return os.environ.get("SPARK_NO_WATCHDOG", "") == ""


def cmd_up(args):
    """Start Spark background services."""
    include_watchdog = _should_start_watchdog(args)
    results = start_services(
        bridge_interval=args.bridge_interval,
        bridge_query=args.bridge_query,
        watchdog_interval=args.watchdog_interval,
        include_dashboard=not args.no_dashboard,
        include_watchdog=include_watchdog,
        bridge_stale_s=args.bridge_stale_s,
    )

    print("")
    print("[spark] starting services")
    for name, result in results.items():
        print(f"  {name}: {result}")
    print("")

    if args.sync_context:
        project_dir = Path(args.project).expanduser() if args.project else Path.cwd()
        sync_context(project_dir=project_dir)
        print(f"[spark] sync-context: {project_dir}")


def cmd_ensure(args):
    """Ensure Spark services are running (start any missing)."""
    cmd_up(args)


def cmd_down(args):
    """Stop Spark background services."""
    results = stop_services()
    print("")
    print("[spark] stopping services")
    for name, result in results.items():
        print(f"  {name}: {result}")
    print("")


def cmd_events(args):
    """Show recent events."""
    limit = args.limit or 20
    events = read_recent_events(limit)
    
    print(f"\n📋 Recent Events (showing {len(events)} of {count_events()})\n")
    
    for event in events:
        tool_str = f" [{event.tool_name}]" if event.tool_name else ""
        error_str = f" ERROR: {event.error[:50]}..." if event.error else ""
        print(f"[{event.event_type.value}]{tool_str}{error_str}")


def cmd_capture(args):
    """Portable memory capture: scan → suggest → accept/reject."""
    if args.scan or (not args.list and not args.accept and not args.reject):
        stats = process_recent_memory_events(limit=80)
        print("[SPARK] Memory capture scan")
        print(f"  auto_saved: {stats['auto_saved']}")
        print(f"  explicit_saved: {stats['explicit_saved']}")
        print(f"  suggested: {stats['suggested']}")
        print(f"  pending_total: {stats['pending_total']}")
        print()

    if args.accept:
        ok = capture_accept(args.accept)
        print("✓ Accepted" if ok else "✗ Not found / not pending")
    return


def cmd_outcome(args):
    """Record an explicit outcome check-in."""
    if args.pending:
        items = list_checkins(limit=args.limit)
        if not items:
            print("[SPARK] No pending check-ins found.")
            return
        print("[SPARK] Recent check-in requests:")
        for item in items:
            ts = item.get("created_at")
            sid = item.get("session_id") or "unknown"
            event = item.get("event") or "unknown"
            print(f"   - {sid} ({event}) @ {ts}")
        return

    result = args.result
    text = args.text
    tool = args.tool

    if not result:
        try:
            result = input("Outcome (yes/no/partial): ").strip()
        except Exception:
            result = "unknown"
    if text is None:
        try:
            text = input("Notes (optional): ").strip()
        except Exception:
            text = ""

    row, polarity = build_explicit_outcome(
        result=result,
        text=text or "",
        tool=tool,
        created_at=args.time,
    )
    if args.session_id:
        row["session_id"] = args.session_id
    link_keys = []
    if args.link_key:
        link_keys.extend([k for k in args.link_key if k])
    link_count = int(args.link_count or 0)
    if args.link_latest:
        link_count = max(link_count, 1)
    if link_count > 0:
        exposures = read_recent_exposures(limit=link_count)
        if row.get("session_id"):
            same = [ex for ex in exposures if ex.get("session_id") == row.get("session_id")]
            if same:
                exposures = same
        for ex in exposures:
            key = ex.get("insight_key")
            if key:
                link_keys.append(key)
        row["linked_texts"] = [ex.get("text") for ex in exposures if ex.get("text")]
    else:
        auto_link = args.auto_link or os.environ.get("SPARK_OUTCOME_AUTO_LINK") == "1"
        if auto_link:
            if not row.get("session_id"):
                sid = infer_latest_session_id()
                if sid:
                    row["session_id"] = sid
            window_s = float(args.link_window_mins or 30) * 60
            now_ts = float(args.time or 0) or None
            exposures = read_exposures_within(max_age_s=window_s, now=now_ts, limit=200)
            if not exposures:
                last = read_last_exposure()
                if last:
                    exposures = [last]
            if row.get("session_id"):
                same = [ex for ex in exposures if ex.get("session_id") == row.get("session_id")]
                if same:
                    exposures = same
            for ex in exposures:
                key = ex.get("insight_key")
                if key:
                    link_keys.append(key)
            if exposures:
                row["linked_texts"] = [ex.get("text") for ex in exposures if ex.get("text")]
    if link_keys:
        deduped = []
        for k in link_keys:
            if k and k not in deduped:
                deduped.append(k)
        row["linked_insights"] = deduped
    append_outcome(row)
    print(f"[SPARK] Outcome recorded: {row.get('result')} (polarity={polarity})")


def cmd_eval(args):
    """Evaluate prediction accuracy against outcomes."""
    max_age_s = float(args.days) * 24 * 3600
    stats = evaluate_predictions(max_age_s=max_age_s, sim_threshold=args.sim)
    print("[SPARK] Evaluation")
    print(f"   Predictions: {stats['predictions']}")
    print(f"   Outcomes: {stats['outcomes']}")
    print(f"   Matched: {stats['matched']}")
    print(f"   Validated: {stats['validated']}")
    print(f"   Contradicted: {stats['contradicted']}")
    print(f"   Precision: {stats['precision']:.0%}")
    print(f"   Outcome Coverage: {stats['outcome_coverage']:.0%}")


def cmd_outcome_link(args):
    """Link an outcome to an insight for validation."""
    outcome_id = args.outcome_id
    insight_key = args.insight_key
    chip_id = args.chip_id
    confidence = float(args.confidence or 1.0)
    notes = args.notes or ""

    link = link_outcome_to_insight(
        outcome_id=outcome_id,
        insight_key=insight_key,
        chip_id=chip_id,
        confidence=confidence,
        notes=notes,
    )
    print(f"[SPARK] Link created: {link.get('link_id')}")
    print(f"   Outcome: {outcome_id}")
    print(f"   Insight: {insight_key}")
    if chip_id:
        print(f"   Chip: {chip_id}")


def cmd_outcome_stats(args):
    """Show outcome-insight coverage statistics."""
    chip_id = args.chip_id if hasattr(args, 'chip_id') else None

    # Get general outcome stats
    stats = get_outcome_stats(chip_id=chip_id)
    coverage = get_insight_outcome_coverage()

    print("[SPARK] Outcome Statistics")
    print(f"   Total Outcomes: {stats['total_outcomes']}")
    print(f"   By Polarity: +{stats['by_polarity'].get('pos', 0)} / -{stats['by_polarity'].get('neg', 0)} / ~{stats['by_polarity'].get('neutral', 0)}")
    print(f"   Total Links: {stats['total_links']}")
    print(f"   Validated Links: {stats['validated_links']}")
    print(f"   Unlinked Outcomes: {stats['unlinked']}")
    print()
    print("[SPARK] Insight Coverage")
    print(f"   Total Insights: {coverage['total_insights']}")
    print(f"   With Outcomes: {coverage['insights_with_outcomes']}")
    print(f"   Validated: {coverage['insights_validated']}")
    print(f"   Coverage: {coverage['outcome_coverage']:.1%}")
    print(f"   Validation Rate: {coverage['validation_rate']:.1%}")


def cmd_outcome_validate(args):
    """Run outcome-based validation on insights."""
    limit = int(args.limit or 100)
    stats = process_outcome_validation(limit=limit)

    print("[SPARK] Outcome Validation")
    print(f"   Processed: {stats['processed']}")
    print(f"   Validated: {stats['validated']}")
    print(f"   Contradicted: {stats['contradicted']}")
    print(f"   Surprises: {stats['surprises']}")


def cmd_outcome_unlinked(args):
    """List outcomes without insight links."""
    limit = int(args.limit or 20)
    outcomes = get_unlinked_outcomes(limit=limit)

    if not outcomes:
        print("[SPARK] No unlinked outcomes found.")
        return

    print(f"[SPARK] Unlinked Outcomes ({len(outcomes)}):")
    for o in outcomes:
        oid = o.get("outcome_id", "?")[:10]
        pol = o.get("polarity", "?")
        text = (o.get("text") or "")[:60]
        print(f"   [{pol:^7}] {oid}... {text}")


def cmd_outcome_links(args):
    """List outcome-insight links."""
    insight_key = args.insight_key if hasattr(args, 'insight_key') else None
    chip_id = args.chip_id if hasattr(args, 'chip_id') else None
    limit = int(args.limit or 50)

    links = get_outcome_links(insight_key=insight_key, chip_id=chip_id, limit=limit)

    if not links:
        print("[SPARK] No links found.")
        return

    print(f"[SPARK] Outcome-Insight Links ({len(links)}):")
    for link in links:
        lid = link.get("link_id", "?")[:8]
        oid = link.get("outcome_id", "?")[:8]
        ikey = link.get("insight_key", "?")[:30]
        validated = "Y" if link.get("validated") else "N"
        result = link.get("validation_result", "-")
        print(f"   {lid}... {oid}... -> {ikey} [validated={validated} result={result}]")


def cmd_validate_ingest(args):
    """Validate recent queue events for schema issues."""
    stats = scan_queue_events(limit=args.limit)
    if not args.no_write:
        write_ingest_report(stats)
    print("[SPARK] Ingest validation")
    print(f"   Processed: {stats['processed']}")
    print(f"   Valid: {stats['valid']}")
    print(f"   Invalid: {stats['invalid']}")
    if stats["reasons"]:
        print("   Reasons:")
        for k, v in stats["reasons"].items():
            print(f"     - {k}: {v}")


def _print_project_questions(profile, limit: int = 5):
    suggested = get_suggested_questions(profile, limit=limit)
    if not suggested:
        print("[SPARK] No unanswered questions.")
        return
    print("[SPARK] Suggested questions:")
    for q in suggested:
        cat = q.get("category") or "general"
        qid = q.get("id") or "unknown"
        text = q.get("question") or ""
        print(f"   - [{cat}] {qid}: {text}")


def cmd_project_init(args):
    profile = load_profile(Path(args.project) if args.project else None)
    if args.domain:
        profile["domain"] = args.domain
        save_profile(profile)
    if not profile.get("domain"):
        profile["domain"] = infer_domain(Path(args.project) if args.project else None)
        save_profile(profile)
    added = ensure_questions(profile)
    print(f"[SPARK] Project: {profile.get('project_key')}  Domain: {profile.get('domain')}")
    if added:
        print(f"[SPARK] Added {added} domain questions")
    _print_project_questions(profile, args.limit)


def cmd_project_status(args):
    profile = load_profile(Path(args.project) if args.project else None)
    score = completion_score(profile)
    print(f"[SPARK] Project: {profile.get('project_key')}")
    print(f"   Domain: {profile.get('domain')}")
    print(f"   Phase: {profile.get('phase')}")
    print(f"   Completion Score: {score['score']}/100")
    print(f"   Goals: {len(profile.get('goals') or [])}")
    print(f"   Done: {'set' if profile.get('done') else 'not set'}")
    print(f"   Milestones: {len(profile.get('milestones') or [])}")
    print(f"   Decisions: {len(profile.get('decisions') or [])}")
    print(f"   Insights: {len(profile.get('insights') or [])}")
    print(f"   Feedback: {len(profile.get('feedback') or [])}")
    print(f"   Risks: {len(profile.get('risks') or [])}")
    print(f"   References: {len(profile.get('references') or [])}")
    print(f"   Transfers: {len(profile.get('transfers') or [])}")
    questions = profile.get("questions") or []
    answered = len([q for q in questions if q.get("answered_at")])
    print(f"   Questions answered: {answered}/{len(questions)}")


def cmd_project_questions(args):
    profile = load_profile(Path(args.project) if args.project else None)
    ensure_questions(profile)
    _print_project_questions(profile, args.limit)


def cmd_project_answer(args):
    profile = load_profile(Path(args.project) if args.project else None)
    ensure_questions(profile)
    entry = record_answer(profile, args.id, args.text or "")
    if not entry:
        print("[SPARK] Answer not recorded (missing id or text).")
        return
    # Store as project-scoped memory for retrieval
    qtext = ""
    for q in profile.get("questions") or []:
        if q.get("id") == args.id:
            qtext = q.get("question") or ""
            break
    note = f"{qtext} Answer: {args.text}".strip() if qtext else (args.text or "").strip()
    if note:
        store_memory(note, category=f"project_answer:{entry.get('category') or 'general'}")
    print("[SPARK] Answer recorded.")


def cmd_project_capture(args):
    profile = load_profile(Path(args.project) if args.project else None)
    entry_type = args.type
    text = (args.text or "").strip()
    if not text:
        print("[SPARK] Missing --text")
        return
    meta = {}
    if args.status:
        meta["status"] = args.status
    if args.why:
        meta["why"] = args.why
    if args.impact:
        meta["impact"] = args.impact
    if args.evidence:
        meta["evidence"] = args.evidence

    if entry_type == "done":
        profile["done"] = text
        save_profile(profile)
    entry = record_entry(profile, entry_type, text, meta=meta)

    category_map = {
        "goal": "project_goal",
        "done": "project_done",
        "milestone": "project_milestone",
        "decision": "project_decision",
        "insight": "project_insight",
        "feedback": "project_feedback",
        "risk": "project_risk",
        "reference": "project_reference",
        "transfer": "project_transfer",
    }
    store_memory(text, category=category_map.get(entry_type, "project_note"))

    # If milestone or done is marked complete, record an outcome for validation.
    status = (args.status or "").strip().lower()
    if entry_type == "done" or (entry_type == "milestone" and status in ("done", "complete", "completed")):
        sid = infer_latest_session_id()
        outcome_text = f"{entry_type} complete: {text}"
        append_outcome({
            "outcome_id": make_outcome_id(profile.get("project_key") or "project", entry.get("entry_id") or "", "done"),
            "event_type": "project_outcome",
            "text": outcome_text,
            "polarity": "pos",
            "created_at": time.time(),
            "project_key": profile.get("project_key"),
            "domain": profile.get("domain"),
            "entity_id": entry.get("entry_id"),
            "session_id": sid,
        })
    else:
        project_key = profile.get("project_key") or "project"
        if entry_type == "reference":
            record_checkin_request(
                session_id=f"project:{project_key}",
                event="project_transfer",
                reason=f"Transfer from reference: {text[:140]}",
            )
        elif entry_type in ("decision", "milestone", "transfer"):
            record_checkin_request(
                session_id=f"project:{project_key}",
                event=f"project_{entry_type}",
                reason=text[:160],
            )
    print(f"[SPARK] Captured {entry_type}.")


def cmd_project_phase(args):
    profile = load_profile(Path(args.project) if args.project else None)
    if args.set_phase:
        set_phase(profile, args.set_phase)
        ensure_questions(profile)
        print(f"[SPARK] Phase set: {profile.get('phase')}")
    else:
        print(f"[SPARK] Phase: {profile.get('phase')}")

def cmd_surprises(args):
    """Show surprise moments (aha!)."""
    aha = get_aha_tracker()
    
    if args.insights:
        # Show insights/analysis
        insights = aha.get_insights()
        print("\n💡 Surprise Analysis\n")
        for key, value in insights.items():
            if key != "recommendations":
                print(f"   {key}: {value}")
        if insights.get("recommendations"):
            print("\n   Recommendations:")
            for r in insights["recommendations"]:
                print(f"      - {r}")
        print()
        return
    
    if args.surface:
        # Surface pending surprises
        pending = aha.surface_all_pending()
        if pending:
            print("\n💡 Surfacing Surprises:\n")
            for s in pending:
                print(s)
                print()
        else:
            print("\nNo pending surprises to surface.")
        return
    
    # Show recent surprises
    limit = args.limit or 10
    surprises = aha.get_recent_surprises(limit)
    
    print(f"\n💡 Recent Surprises (showing {len(surprises)})\n")
    
    for s in surprises:
        print(s.format_visible())
        print()
    
    if not surprises:
        print("   No surprises captured yet.")
        print("   Surprises happen when predictions don't match outcomes.")
        print()


def cmd_voice(args):
    """Show or interact with Spark's personality."""
    voice = get_spark_voice()
    
    if args.introduce:
        print("\n" + voice.introduce())
        return
    
    if args.opinions:
        opinions = voice.get_strong_opinions() if args.strong else voice.get_opinions()
        print(f"\n🎭 Spark's Opinions ({len(opinions)} total)\n")
        for o in opinions:
            strength = "strongly" if o.strength > 0.8 else "tends to"
            print(f"   [{o.topic}] {strength} prefer {o.preference}")
            print(f"      Reason: {o.reason}")
            print(f"      Strength: {o.strength:.0%}")
            print()
        return
    
    if args.growth:
        moments = voice.get_recent_growth(args.limit or 5)
        print(f"\n📈 Growth Moments ({len(moments)})\n")
        for m in moments:
            print(f"   Before: {m.before}")
            print(f"   After: {m.after}")
            print(f"   Trigger: {m.trigger}")
            print()
        return
    
    # Default: show status
    stats = voice.get_stats()
    print("\n🎭 Spark Voice Status\n")
    print(f"   {voice.get_status_voice()}")
    print()
    print(f"   Age: {stats['age_days']} days")
    print(f"   Interactions: {stats['interactions']}")
    print(f"   Opinions: {stats['opinions_formed']} ({stats['strong_opinions']} strong)")
    print(f"   Growth moments: {stats['growth_moments']}")
    print()


def cmd_bridge(args):
    """Bridge learnings to operational context."""
    from lib.bridge import (
        generate_active_context, 
        update_spark_context, 
        auto_promote_insights,
        bridge_status
    )
    
    if args.update:
        update_spark_context(query=args.query)
        print("✓ Updated SPARK_CONTEXT.md with active learnings")
    elif args.promote:
        count = auto_promote_insights()
        if count > 0:
            print(f"✓ Promoted {count} high-value insights to MEMORY.md")
        else:
            print("No insights ready for promotion yet")
    elif args.status:
        status = bridge_status()
        print(f"\n  Bridge Status")
        print(f"  {'─' * 30}")
        print(f"  High-value insights: {status['high_value_insights']}")
        print(f"  Lessons learned: {status['lessons_learned']}")
        print(f"  Strong opinions: {status['strong_opinions']}")
        print(f"  Context file: {'✓' if status['context_exists'] else '✗'}")
        print(f"  Memory file: {'✓' if status['memory_exists'] else '✗'}")
        print()
    else:
        # Default: show active context
        print(generate_active_context())


def cmd_memory(args):
    """Configure/view Clawdbot semantic memory (embeddings provider)."""
    from lib.clawdbot_memory_setup import (
        get_current_memory_search,
        apply_memory_mode,
        run_memory_status,
        recommended_modes,
    )

    if args.list:
        modes = recommended_modes()
        print("\nMemory provider options:")
        for k, v in modes.items():
            print(f"  - {k:7}  cost={v['cost']}, privacy={v['privacy']}, setup={v['setup']}")
        print("\nTip: Codex OAuth doesn't include embeddings; local/remote/openai/gemini solve it.")
        return

    if args.show:
        ms = get_current_memory_search()
        print("\nCurrent Clawdbot agents.defaults.memorySearch:")
        print(ms if ms else "(not set)")
        return

    if args.status:
        print(run_memory_status(agent=args.agent))
        return

    if args.set_mode:
        applied = apply_memory_mode(
            args.set_mode,
            local_model_path=args.local_model_path,
            remote_base_url=args.remote_base_url,
            remote_api_key=args.remote_api_key,
            model=args.model,
            fallback=args.fallback,
            restart=not args.no_restart,
        )
        print("✓ Applied memorySearch:")
        print(applied)
        print("\nNext: run `clawdbot memory index --agent main` (or use `spark memory --status`).")
        return

    print("Use --list, --show, --status, or --set <mode>.")


def cmd_memory_migrate(args):
    """Backfill JSONL memory banks into the SQLite memory store."""
    stats = migrate_memory()
    print(json.dumps(stats, indent=2))


def cmd_moltbook(args):
    """Moltbook agent commands - social network for AI agents."""
    from adapters.moltbook.client import MoltbookClient, is_registered, MoltbookError
    from adapters.moltbook.agent import SparkMoltbookAgent, AGENT_NAME, AGENT_BIO
    from adapters.moltbook.heartbeat import HeartbeatDaemon

    if args.action == "register":
        if is_registered():
            print("[SPARK] Already registered on Moltbook.")
            print("        Use 'spark moltbook status' to check your profile.")
            return

        name = args.name or AGENT_NAME
        description = args.description or AGENT_BIO

        print(f"[SPARK] Registering '{name}' on Moltbook...")
        try:
            client = MoltbookClient()
            result = client.register(name, description)
            print("\n✓ Registration initiated!")
            print(f"\n  Agent ID: {result.get('agent_id')}")
            print(f"  Claim URL: {result.get('claim_url')}")
            print(f"\n  Verification Code: {result.get('verification_code')}")
            print("\n  Next Steps:")
            print("  1. Post the verification code on Twitter/X")
            print("  2. Run 'spark moltbook status' to check verification")
            print("  3. Once verified, run 'spark moltbook heartbeat' to start engaging")
        except MoltbookError as e:
            print(f"[SPARK] Registration failed: {e}")

    elif args.action == "status":
        if not is_registered():
            print("[SPARK] Not registered on Moltbook. Run 'spark moltbook register' first.")
            return

        try:
            agent = SparkMoltbookAgent()
            status = agent.get_status()

            print("\n🌐 Moltbook Agent Status\n")
            print(f"  Name: {status['name']}")
            print(f"  Karma: {status['karma']}")
            print(f"  Posts: {status['total_posts']}")
            print(f"  Comments: {status['total_comments']}")
            print(f"  Votes: {status['total_votes']}")
            print(f"  Pending Insights: {status['pending_insights']}")
            wait_m = int(status.get("time_until_post", 0) // 60)
            can_post = "Yes" if status.get("can_post") else f"No (wait {wait_m}m)"
            print(f"  Can Post: {can_post}")

            if status['last_heartbeat']:
                from datetime import datetime
                last = datetime.fromtimestamp(status['last_heartbeat'])
                print(f"  Last Heartbeat: {last.strftime('%Y-%m-%d %H:%M')}")
            print()

        except MoltbookError as e:
            print(f"[SPARK] Status check failed: {e}")

    elif args.action == "heartbeat":
        if not is_registered():
            print("[SPARK] Not registered on Moltbook. Run 'spark moltbook register' first.")
            return

        print("[SPARK] Running Moltbook heartbeat...")
        try:
            agent = SparkMoltbookAgent()
            result = agent.heartbeat()
            print(f"\n✓ Heartbeat complete")
            print(f"  Actions: {len(result.get('actions', []))}")
            print(f"  Karma Delta: {result.get('karma_delta', 0):+d}")
            print(f"  Opportunities Found: {result.get('opportunities_found', 0)}")

            for action in result.get("actions", []):
                print(f"  - {action['type']}: {action.get('submolt', 'n/a')}")
            print()

        except MoltbookError as e:
            print(f"[SPARK] Heartbeat failed: {e}")

    elif args.action == "queue":
        if not args.insight:
            print("[SPARK] Use --insight to specify the insight to queue")
            return

        agent = SparkMoltbookAgent()
        agent.queue_insight(
            insight=args.insight,
            insight_type=args.type or "observation",
            submolt=args.submolt or "spark-insights",
        )
        print(f"✓ Queued insight for next heartbeat")

    elif args.action == "daemon":
        if args.stop:
            HeartbeatDaemon.stop()
        elif args.status_check:
            if HeartbeatDaemon.is_running():
                print("[SPARK] Moltbook heartbeat daemon is running")
            else:
                print("[SPARK] Moltbook heartbeat daemon is not running")
        else:
            if HeartbeatDaemon.is_running():
                print("[SPARK] Daemon already running. Use 'spark moltbook daemon --stop' to stop.")
                return
            daemon = HeartbeatDaemon(interval_hours=args.interval or 4)
            if args.once:
                daemon.start(daemon_mode=False)
            else:
                daemon.start(daemon_mode=True)

    elif args.action == "subscribe":
        if not is_registered():
            print("[SPARK] Not registered on Moltbook. Run 'spark moltbook register' first.")
            return

        agent = SparkMoltbookAgent()
        submolts = args.submolts if args.submolts else None
        agent.subscribe_to_submolts(submolts)
        print("✓ Subscribed to submolts")

    else:
        print("Unknown action. Use: register, status, heartbeat, queue, daemon, subscribe")



def cmd_chips(args):
    """Manage Spark chips - domain-specific intelligence modules."""
    from pathlib import Path
    from lib.chips import get_registry, load_chip, ChipRunner, get_chip_store

    registry = get_registry()

    if args.action == "list":
        chips = registry.list_all()
        if not chips:
            print("\n[SPARK] No chips installed.")
            print("        Use 'spark chips install <path>' to install a chip.")
            return

        print(f"\n{'=' * 50}")
        print("  SPARK CHIPS - Domain Intelligence")
        print(f"{'=' * 50}\n")

        active = [c for c in chips if c.active]
        inactive = [c for c in chips if not c.active]

        if active:
            print("Active Chips:")
            for chip in active:
                print(f"  [*] {chip.id} v{chip.version}")
                print(f"      {chip.name}")
                print(f"      Insights: {chip.stats.insights_generated} | Events: {chip.stats.events_processed}")

        if inactive:
            print("\nInactive Chips:")
            for chip in inactive:
                print(f"  [ ] {chip.id} v{chip.version}")
                print(f"      {chip.name}")

        print()

    elif args.action == "install":
        if not args.path:
            print("[SPARK] Use --path to specify chip YAML file")
            return

        path = Path(args.path).expanduser()
        if not path.exists():
            print(f"[SPARK] File not found: {path}")
            return

        try:
            entry = registry.install(path, source=args.source or "custom")
            print(f"[SPARK] Installed chip: {entry.id} v{entry.version}")
            print(f"        Name: {entry.name}")
            print(f"        Source: {entry.source}")
            print(f"        Use 'spark chips activate {entry.id}' to enable")
        except Exception as e:
            print(f"[SPARK] Install failed: {e}")

    elif args.action == "uninstall":
        if not args.chip_id:
            print("[SPARK] Specify chip ID to uninstall")
            return

        if registry.uninstall(args.chip_id):
            print(f"[SPARK] Uninstalled chip: {args.chip_id}")
        else:
            print(f"[SPARK] Chip not found: {args.chip_id}")

    elif args.action == "activate":
        if not args.chip_id:
            print("[SPARK] Specify chip ID to activate")
            return

        if registry.activate(args.chip_id):
            print(f"[SPARK] Activated chip: {args.chip_id}")
        else:
            print(f"[SPARK] Chip not found: {args.chip_id}")

    elif args.action == "deactivate":
        if not args.chip_id:
            print("[SPARK] Specify chip ID to deactivate")
            return

        if registry.deactivate(args.chip_id):
            print(f"[SPARK] Deactivated chip: {args.chip_id}")
        else:
            print(f"[SPARK] Chip not found: {args.chip_id}")

    elif args.action == "status":
        chip_id = args.chip_id
        if not chip_id:
            # Show overall status
            stats = registry.get_stats()
            print(f"\n[SPARK] Chips Status")
            print(f"  Installed: {stats['total_installed']}")
            print(f"  Active: {stats['total_active']}")
            return

        entry = registry.get(chip_id)
        if not entry:
            print(f"[SPARK] Chip not found: {chip_id}")
            return

        spec = registry.get_spec(chip_id)
        print(f"\n[SPARK] Chip: {entry.id}")
        print(f"  Name: {entry.name}")
        print(f"  Version: {entry.version}")
        print(f"  Source: {entry.source}")
        print(f"  Active: {'Yes' if entry.active else 'No'}")
        print(f"  Installed: {entry.installed_at[:10]}")
        print(f"\n  Stats:")
        print(f"    Insights Generated: {entry.stats.insights_generated}")
        print(f"    Events Processed: {entry.stats.events_processed}")
        print(f"    Predictions Made: {entry.stats.predictions_made}")
        if entry.stats.last_active:
            print(f"    Last Active: {entry.stats.last_active[:19]}")

        if spec:
            print(f"\n  Components:")
            print(f"    Domains: {', '.join(spec.domains[:5])}")
            print(f"    Triggers: {len(spec.triggers.patterns)} patterns, {len(spec.triggers.events)} events")
            print(f"    Observers: {len(spec.observers)}")
            print(f"    Learners: {len(spec.learners)}")
            print(f"    Outcomes: {len(spec.outcomes_positive)}+ / {len(spec.outcomes_negative)}-")

    elif args.action == "insights":
        chip_id = args.chip_id
        if not chip_id:
            print("[SPARK] Specify chip ID to view insights")
            return

        store = get_chip_store(chip_id)
        insights = store.get_insights(limit=args.limit or 10)

        if not insights:
            print(f"\n[SPARK] No insights for chip: {chip_id}")
            return

        print(f"\n[SPARK] Insights from {chip_id} (showing {len(insights)})\n")
        for i in insights:
            conf = i.get("confidence", 0)
            print(f"  [{i.get('category', 'general')}] {i.get('insight')}")
            print(f"      Confidence: {conf:.0%} | Validations: {i.get('validations', 0)}")
            print()

    elif args.action == "test":
        chip_id = args.chip_id
        if not chip_id:
            print("[SPARK] Specify chip ID to test")
            return

        spec = registry.get_spec(chip_id)
        if not spec:
            print(f"[SPARK] Chip not found: {chip_id}")
            return

        # Test with sample event
        test_text = args.test_text or "This is a test event"
        test_event = {
            "session_id": "test-session",
            "hook_event": "UserPromptSubmit",
            "payload": {"text": test_text},
        }

        runner = ChipRunner(spec)
        insights = runner.process_event(test_event)

        print(f"\n[SPARK] Test chip: {chip_id}")
        print(f"  Input: {test_text[:80]}...")
        print(f"  Insights generated: {len(insights)}")
        for ins in insights:
            print(f"    - {ins.get('insight', '')[:100]}")

    else:
        print("Unknown action. Use: list, install, uninstall, activate, deactivate, status, insights, test")


def cmd_timeline(args):
    """Show growth timeline."""
    growth = get_growth_tracker()
    
    # Record current snapshot
    cognitive = get_cognitive_learner()
    aha = get_aha_tracker()
    cog_stats = cognitive.get_stats()
    aha_stats = aha.get_stats()
    
    growth.record_snapshot(
        insights_count=cog_stats['total_insights'],
        promoted_count=cog_stats['promoted_count'],
        aha_count=aha_stats['total_captured'],
        avg_reliability=cog_stats['avg_reliability'],
        categories_active=len([c for c, n in cog_stats['by_category'].items() if n > 0]),
        events_processed=count_events(),
    )
    
    print("\n" + growth.get_growth_narrative())
    print()
    
    # Show timeline
    timeline = growth.get_timeline(args.limit or 10)
    if timeline:
        print("\n📅 Timeline\n")
        for item in timeline:
            date = item['timestamp'][:10]
            print(f"   [{date}] {item['title']}")
    print()
    
    # Show delta if requested
    if args.delta:
        delta = growth.get_growth_delta(args.delta)
        print(f"\n📊 Change over last {args.delta}h:")
        print(f"   Insights: +{delta.get('insights_delta', 0)}")
        print(f"   Reliability: {delta.get('reliability_delta', 0):+.0%}")
        print(f"   Aha moments: +{delta.get('aha_delta', 0)}")
        print()


def cmd_learn(args):
    """Manually learn an insight."""
    from lib.cognitive_learner import CognitiveCategory
    
    category_map = {
        "self": CognitiveCategory.SELF_AWARENESS,
        "self_awareness": CognitiveCategory.SELF_AWARENESS,
        "user": CognitiveCategory.USER_UNDERSTANDING,
        "user_understanding": CognitiveCategory.USER_UNDERSTANDING,
        "reasoning": CognitiveCategory.REASONING,
        "context": CognitiveCategory.CONTEXT,
        "wisdom": CognitiveCategory.WISDOM,
        "meta": CognitiveCategory.META_LEARNING,
        "meta_learning": CognitiveCategory.META_LEARNING,
        "communication": CognitiveCategory.COMMUNICATION,
        "creativity": CognitiveCategory.CREATIVITY,
    }
    
    cat_key = args.category.lower()
    if cat_key not in category_map:
        print(f"Unknown category: {args.category}")
        print(f"Valid: {', '.join(category_map.keys())}")
        return
    
    category = category_map[cat_key]
    cognitive = get_cognitive_learner()
    
    insight = cognitive.add_insight(
        category=category,
        insight=args.insight,
        context=args.context or "",
        confidence=args.reliability
    )
    
    print(f"\n✓ Learned [{category.value}]: {insight.insight}")
    print(f"  Reliability: {insight.reliability:.0%}")
    if args.context:
        print(f"  Context: {args.context}")
    print()
    
    # Auto-sync if requested
    if args.sync:
        print("[SPARK] Syncing to Mind...")
        stats = sync_all_to_mind()
        print(f"Synced: {stats['synced']}, Queued: {stats['queued']}")


def main():
    _configure_output()
    parser = argparse.ArgumentParser(
        description="Spark CLI - Self-evolving intelligence layer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  status      Show overall system status
  services    Show daemon/service status
  up          Start background services
  ensure      Start missing services if not running
  down        Stop background services
  sync        Sync cognitive insights to Mind
  queue       Process offline queue
  process     Run bridge worker cycle or drain backlog
  validate    Run validation scan on recent events
  learnings   Show recent cognitive insights
  promote     Run promotion check
  write       Write learnings to markdown files
  health      Run health check
  events      Show recent events from queue
  capture     Memory capture suggestions (portable)

Examples:
  spark status
  spark services
  spark up --sync-context
  spark sync
  spark promote --dry-run
  spark learnings --limit 20
  spark capture --list
  spark capture --accept <id>
"""
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    def _add_up_args(p):
        p.add_argument("--bridge-interval", type=int, default=30, help="bridge_worker interval (seconds)")
        p.add_argument("--bridge-query", default=None, help="optional fixed query for bridge_worker")
        p.add_argument("--watchdog-interval", type=int, default=60, help="watchdog interval (seconds)")
        p.add_argument("--bridge-stale-s", type=int, default=90, help="bridge_worker stale threshold (seconds)")
        p.add_argument("--no-watchdog", action="store_true", help="do not start watchdog")
        p.add_argument("--no-dashboard", action="store_true", help="do not start dashboard")
        p.add_argument("--sync-context", action="store_true", help="run sync-context after start")
        p.add_argument("--project", "-p", default=None, help="project root for sync-context")

    # status
    subparsers.add_parser("status", help="Show overall system status")

    # services
    services_parser = subparsers.add_parser("services", help="Show daemon/service status")
    services_parser.add_argument("--bridge-stale-s", type=int, default=90, help="bridge_worker stale threshold (seconds)")

    # up
    up_parser = subparsers.add_parser("up", help="Start background services")
    _add_up_args(up_parser)

    # ensure
    ensure_parser = subparsers.add_parser("ensure", help="Start missing services if not running")
    _add_up_args(ensure_parser)

    # down
    subparsers.add_parser("down", help="Stop background services")
    
    # sync
    subparsers.add_parser("sync", help="Sync insights to Mind")
    
    # queue
    subparsers.add_parser("queue", help="Process offline queue")

    # process
    process_parser = subparsers.add_parser("process", help="Run bridge worker cycle or drain backlog")
    process_parser.add_argument("--drain", action="store_true", help="Loop until pattern backlog is cleared")
    process_parser.add_argument("--interval", type=float, default=1.0, help="Seconds between cycles when draining")
    process_parser.add_argument("--timeout", type=float, default=300.0, help="Max seconds to run when draining")
    process_parser.add_argument("--max-iterations", type=int, default=100, help="Max cycles when draining")
    process_parser.add_argument("--pattern-limit", type=int, default=200, help="Events per cycle for pattern detection")
    process_parser.add_argument("--memory-limit", type=int, default=60, help="Events per cycle for memory capture")
    process_parser.add_argument("--query", default=None, help="Optional fixed query for context")

    # validate
    validate_parser = subparsers.add_parser("validate", help="Run validation scan on recent events")
    validate_parser.add_argument("--limit", "-n", type=int, default=200, help="Events to scan")
    
    # learnings
    learnings_parser = subparsers.add_parser("learnings", help="Show recent learnings")
    learnings_parser.add_argument("--limit", "-n", type=int, default=10, help="Number to show")
    
    # promote
    promote_parser = subparsers.add_parser("promote", help="Run promotion check")
    promote_parser.add_argument("--dry-run", action="store_true", help="Don't actually promote")
    promote_parser.add_argument("--no-project", action="store_true", help="Skip PROJECT.md update")
    
    # write
    subparsers.add_parser("write", help="Write learnings to markdown")

    # sync-context
    sync_ctx = subparsers.add_parser("sync-context", help="Sync bootstrap context to outputs")
    sync_ctx.add_argument("--project", "-p", default=None, help="Project root for file outputs")
    sync_ctx.add_argument("--min-reliability", type=float, default=0.7, help="Minimum reliability")
    sync_ctx.add_argument("--min-validations", type=int, default=3, help="Minimum validations")
    sync_ctx.add_argument("--limit", type=int, default=12, help="Max items")
    sync_ctx.add_argument("--no-promoted", action="store_true", help="Skip promoted learnings from docs")
    sync_ctx.add_argument("--diagnose", action="store_true", help="Include selection diagnostics in output")

    # decay
    decay = subparsers.add_parser("decay", help="Preview or apply decay-based pruning")
    decay.add_argument("--max-age-days", type=float, default=180.0, help="Min age in days to consider stale")
    decay.add_argument("--min-effective", type=float, default=0.2, help="Min effective reliability to keep")
    decay.add_argument("--limit", type=int, default=20, help="Max candidates to show in dry-run")
    decay.add_argument("--apply", action="store_true", help="Actually prune stale insights")

    # health
    subparsers.add_parser("health", help="Health check")
    
    # events
    events_parser = subparsers.add_parser("events", help="Show recent events")
    events_parser.add_argument("--limit", "-n", type=int, default=20, help="Number to show")

    # outcome
    outcome_parser = subparsers.add_parser("outcome", help="Record explicit outcome check-in")
    outcome_parser.add_argument("--result", choices=["yes", "no", "partial", "mixed", "success", "failure"], help="Outcome result")
    outcome_parser.add_argument("--text", "-t", default=None, help="Optional notes")
    outcome_parser.add_argument("--tool", help="Associated tool or topic")
    outcome_parser.add_argument("--time", type=float, default=None, help="Unix timestamp override")
    outcome_parser.add_argument("--pending", action="store_true", help="List recent check-in requests")
    outcome_parser.add_argument("--limit", type=int, default=5, help="How many pending items to show")
    outcome_parser.add_argument("--link-latest", action="store_true", help="Link to most recent exposure")
    outcome_parser.add_argument("--link-count", type=int, default=0, help="Link to last N exposures")
    outcome_parser.add_argument("--link-key", action="append", help="Explicit insight_key to link")
    outcome_parser.add_argument("--auto-link", action="store_true", help="Auto-link exposures within a time window")
    outcome_parser.add_argument("--link-window-mins", type=float, default=30.0, help="Auto-link window in minutes")
    outcome_parser.add_argument("--session-id", help="Attach session_id to outcome")

    # eval
    eval_parser = subparsers.add_parser("eval", help="Evaluate predictions against outcomes")
    eval_parser.add_argument("--days", type=float, default=7.0, help="Lookback window in days")
    eval_parser.add_argument("--sim", type=float, default=0.72, help="Similarity threshold (0-1)")

    # outcome-link: Link an outcome to an insight
    outcome_link_parser = subparsers.add_parser("outcome-link", help="Link outcome to insight")
    outcome_link_parser.add_argument("outcome_id", help="Outcome ID to link")
    outcome_link_parser.add_argument("insight_key", help="Insight key to link to")
    outcome_link_parser.add_argument("--chip-id", help="Optional chip ID for scoping")
    outcome_link_parser.add_argument("--confidence", type=float, default=1.0, help="Link confidence (0-1)")
    outcome_link_parser.add_argument("--notes", help="Optional notes")

    # outcome-stats: Show outcome coverage statistics
    outcome_stats_parser = subparsers.add_parser("outcome-stats", help="Outcome-insight coverage stats")
    outcome_stats_parser.add_argument("--chip-id", help="Filter by chip ID")

    # outcome-validate: Run outcome-based validation
    outcome_validate_parser = subparsers.add_parser("outcome-validate", help="Validate insights using outcomes")
    outcome_validate_parser.add_argument("--limit", "-n", type=int, default=100, help="Max links to process")

    # outcome-unlinked: List outcomes without links
    outcome_unlinked_parser = subparsers.add_parser("outcome-unlinked", help="List unlinked outcomes")
    outcome_unlinked_parser.add_argument("--limit", "-n", type=int, default=20, help="Max to show")

    # outcome-links: List outcome-insight links
    outcome_links_parser = subparsers.add_parser("outcome-links", help="List outcome-insight links")
    outcome_links_parser.add_argument("--insight-key", help="Filter by insight key")
    outcome_links_parser.add_argument("--chip-id", help="Filter by chip ID")
    outcome_links_parser.add_argument("--limit", "-n", type=int, default=50, help="Max to show")

    # validate-ingest
    ingest_parser = subparsers.add_parser("validate-ingest", help="Validate recent queue events")
    ingest_parser.add_argument("--limit", "-n", type=int, default=200, help="Events to scan")
    ingest_parser.add_argument("--no-write", action="store_true", help="Skip writing ingest report file")
    
    # learn
    learn_parser = subparsers.add_parser("learn", help="Manually learn an insight")
    learn_parser.add_argument("category", help="Category (self, user, reasoning, context, wisdom, meta, communication, creativity)")
    learn_parser.add_argument("insight", help="The insight text")
    learn_parser.add_argument("--context", "-c", help="Additional context")
    learn_parser.add_argument("--reliability", "-r", type=float, default=0.7, help="Initial reliability (0-1)")
    learn_parser.add_argument("--sync", "-s", action="store_true", help="Sync to Mind after learning")
    
    # surprises
    surprises_parser = subparsers.add_parser("surprises", help="Show aha moments")
    surprises_parser.add_argument("--limit", "-n", type=int, default=10, help="Number to show")
    surprises_parser.add_argument("--insights", "-i", action="store_true", help="Show analysis/insights")
    surprises_parser.add_argument("--surface", "-s", action="store_true", help="Surface pending surprises")
    
    # voice
    voice_parser = subparsers.add_parser("voice", help="Spark's personality")
    voice_parser.add_argument("--introduce", "-i", action="store_true", help="Introduce Spark")
    voice_parser.add_argument("--opinions", "-o", action="store_true", help="Show opinions")
    voice_parser.add_argument("--strong", action="store_true", help="Only strong opinions")
    voice_parser.add_argument("--growth", "-g", action="store_true", help="Show growth moments")
    voice_parser.add_argument("--limit", "-n", type=int, default=5, help="Number to show")
    
    # timeline
    timeline_parser = subparsers.add_parser("timeline", help="Show growth timeline")
    timeline_parser.add_argument("--limit", "-n", type=int, default=10, help="Number of events")
    timeline_parser.add_argument("--delta", "-d", type=int, help="Show change over N hours")
    
    # bridge - connect learnings to behavior
    bridge_parser = subparsers.add_parser("bridge", help="Bridge learnings to operational context")
    bridge_parser.add_argument("--update", "-u", action="store_true", help="Update SPARK_CONTEXT.md")
    bridge_parser.add_argument("--promote", "-p", action="store_true", help="Auto-promote insights to MEMORY.md")
    bridge_parser.add_argument("--status", "-s", action="store_true", help="Show bridge status")
    bridge_parser.add_argument("--query", help="Optional: tailor context to a specific task")

    # capture - portable memory capture suggestions (keyword + intent hybrid)
    capture_parser = subparsers.add_parser("capture", help="Capture important statements into Spark learnings")
    capture_parser.add_argument("--scan", action="store_true", help="Scan recent events and update suggestions")
    capture_parser.add_argument("--list", action="store_true", help="List pending suggestions")
    capture_parser.add_argument("--accept", help="Accept a pending suggestion by id")
    capture_parser.add_argument("--reject", help="Reject a pending suggestion by id")
    capture_parser.add_argument("--limit", "-n", type=int, default=10, help="How many to list")

    # memory - configure Clawdbot semantic memory provider
    mem_parser = subparsers.add_parser("memory", help="Configure/view Clawdbot memory search (embeddings)")
    mem_parser.add_argument("--list", action="store_true", help="List recommended provider modes")
    mem_parser.add_argument("--show", action="store_true", help="Show current memorySearch config")
    mem_parser.add_argument("--status", action="store_true", help="Run clawdbot memory status --deep")
    mem_parser.add_argument("--agent", default="main", help="Agent id for status (default: main)")
    mem_parser.add_argument("--set", dest="set_mode", choices=["off", "local", "remote", "openai", "gemini"], help="Set provider mode")
    mem_parser.add_argument("--model", help="Embedding model name (remote/openai/gemini)")
    mem_parser.add_argument("--fallback", default="none", help="Fallback provider (default: none)")
    mem_parser.add_argument("--local-model-path", help="Path to local GGUF embedding model (local mode)")
    mem_parser.add_argument("--remote-base-url", help="OpenAI-compatible baseUrl (remote mode)")
    mem_parser.add_argument("--remote-api-key", help="API key for remote baseUrl (remote mode)")
    mem_parser.add_argument("--no-restart", action="store_true", help="Don't restart Clawdbot gateway")

    # memory-migrate
    subparsers.add_parser("memory-migrate", help="Backfill JSONL memories into SQLite store")

    # project - questioning and capture
    project_parser = subparsers.add_parser("project", help="Project questioning and capture")
    project_sub = project_parser.add_subparsers(dest="project_cmd")

    project_init = project_sub.add_parser("init", help="Initialize or update project profile")
    project_init.add_argument("--domain", help="Set project domain (game_dev, marketing, org, product, engineering)")
    project_init.add_argument("--project", help="Project root path")
    project_init.add_argument("--limit", type=int, default=5, help="How many questions to show")

    project_status = project_sub.add_parser("status", help="Show project profile summary")
    project_status.add_argument("--project", help="Project root path")

    project_questions = project_sub.add_parser("questions", help="Show suggested project questions")
    project_questions.add_argument("--project", help="Project root path")
    project_questions.add_argument("--limit", type=int, default=5, help="How many questions to show")

    project_answer = project_sub.add_parser("answer", help="Answer a project question")
    project_answer.add_argument("id", help="Question id")
    project_answer.add_argument("--text", "-t", required=True, help="Answer text")
    project_answer.add_argument("--project", help="Project root path")

    project_capture = project_sub.add_parser("capture", help="Capture a project insight/decision/milestone")
    project_capture.add_argument("--type", required=True, choices=["goal", "done", "milestone", "decision", "insight", "feedback", "risk", "reference", "transfer"], help="Capture type")
    project_capture.add_argument("--text", "-t", required=True, help="Capture text")
    project_capture.add_argument("--project", help="Project root path")
    project_capture.add_argument("--status", help="Status (for milestones)")
    project_capture.add_argument("--why", help="Decision rationale")
    project_capture.add_argument("--impact", help="Impact")
    project_capture.add_argument("--evidence", help="Evidence or feedback source")

    project_phase = project_sub.add_parser("phase", help="Get or set project phase")
    project_phase.add_argument("--set", dest="set_phase", help="Set phase (discovery/prototype/polish/launch)")
    project_phase.add_argument("--project", help="Project root path")

    # chips - domain-specific intelligence
    chips_parser = subparsers.add_parser("chips", help="Manage Spark chips - domain-specific intelligence")
    chips_parser.add_argument("action", nargs="?", default="list",
                              choices=["list", "install", "uninstall", "activate", "deactivate", "status", "insights", "test"],
                              help="Action to perform")
    chips_parser.add_argument("chip_id", nargs="?", help="Chip ID (for activate/deactivate/status/insights/test)")
    chips_parser.add_argument("--path", "-p", help="Path to chip YAML file (for install)")
    chips_parser.add_argument("--source", choices=["official", "community", "custom"], default="custom",
                              help="Chip source (for install)")
    chips_parser.add_argument("--limit", "-n", type=int, default=10, help="Number of insights to show")
    chips_parser.add_argument("--test-text", "-t", help="Test text for chip testing")

    # moltbook - AI agent social network
    moltbook_parser = subparsers.add_parser("moltbook", help="Moltbook agent - social network for AI agents")
    moltbook_parser.add_argument("action", nargs="?", default="status",
                                 choices=["register", "status", "heartbeat", "queue", "daemon", "subscribe"],
                                 help="Action to perform")
    moltbook_parser.add_argument("--name", help="Agent name (for register)")
    moltbook_parser.add_argument("--description", help="Agent description (for register)")
    moltbook_parser.add_argument("--insight", help="Insight text (for queue)")
    moltbook_parser.add_argument("--type", choices=["observation", "learning", "pattern", "question"],
                                 help="Insight type (for queue)")
    moltbook_parser.add_argument("--submolt", help="Target submolt (for queue)")
    moltbook_parser.add_argument("--submolts", nargs="+", help="Submolts to subscribe to (for subscribe)")
    moltbook_parser.add_argument("--interval", type=float, help="Hours between heartbeats (for daemon)")
    moltbook_parser.add_argument("--once", action="store_true", help="Run daemon once then exit")
    moltbook_parser.add_argument("--stop", action="store_true", help="Stop running daemon")
    moltbook_parser.add_argument("--status-check", action="store_true", help="Check if daemon is running")

    args = parser.parse_args()
    
    if not args.command:
        # Default to status
        cmd_status(args)
        return
    
    commands = {
        "status": cmd_status,
        "services": cmd_services,
        "up": cmd_up,
        "ensure": cmd_ensure,
        "down": cmd_down,
        "sync": cmd_sync,
        "queue": cmd_queue,
        "process": cmd_process,
        "validate": cmd_validate,
        "learnings": cmd_learnings,
        "promote": cmd_promote,
        "write": cmd_write,
        "sync-context": cmd_sync_context,
        "decay": cmd_decay,
        "health": cmd_health,
        "events": cmd_events,
        "outcome": cmd_outcome,
        "outcome-link": cmd_outcome_link,
        "outcome-stats": cmd_outcome_stats,
        "outcome-validate": cmd_outcome_validate,
        "outcome-unlinked": cmd_outcome_unlinked,
        "outcome-links": cmd_outcome_links,
        "eval": cmd_eval,
        "validate-ingest": cmd_validate_ingest,
        "capture": cmd_capture,
        "learn": cmd_learn,
        "surprises": cmd_surprises,
        "voice": cmd_voice,
        "timeline": cmd_timeline,
        "bridge": cmd_bridge,
        "memory": cmd_memory,
        "memory-migrate": cmd_memory_migrate,
        "chips": cmd_chips,
        "moltbook": cmd_moltbook,
        "project": None,
    }
    
    if args.command == "project":
        if args.project_cmd == "init":
            cmd_project_init(args)
        elif args.project_cmd == "status":
            cmd_project_status(args)
        elif args.project_cmd == "questions":
            cmd_project_questions(args)
        elif args.project_cmd == "answer":
            cmd_project_answer(args)
        elif args.project_cmd == "capture":
            cmd_project_capture(args)
        elif args.project_cmd == "phase":
            cmd_project_phase(args)
        else:
            project_parser.print_help()
        return

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
