#!/usr/bin/env python3
"""
EIDOS Dashboard - Quick health check for the intelligence system.

Run: python scripts/eidos_dashboard.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lib.eidos import (
    get_store, get_elevated_control_plane,
    get_truth_ledger, get_policy_patch_engine,
    get_minimal_mode_controller, WatcherType
)


def print_header(title):
    print(f"\n{'-' * 60}")
    print(f"  {title}")
    print(f"{'-' * 60}")


def main():
    store = get_store()
    ecp = get_elevated_control_plane()
    ledger = get_truth_ledger()
    patches = get_policy_patch_engine()
    minimal = get_minimal_mode_controller()

    stats = store.get_stats()

    print("\n" + "=" * 60)
    print("             EIDOS INTELLIGENCE DASHBOARD")
    print("=" * 60)

    # Database Stats
    print_header("DATABASE STATS")
    print(f"  Episodes:        {stats['episodes']}")
    print(f"  Steps:           {stats['steps']}")
    print(f"  Distillations:   {stats['distillations']}")
    print(f"  Policies:        {stats['policies']}")
    print(f"  Success Rate:    {stats['success_rate']:.1%}")
    print(f"  High Conf Dist:  {stats['high_confidence_distillations']}")

    # Recent Episodes
    print_header("RECENT EPISODES")
    episodes = store.get_recent_episodes(limit=5)
    if episodes:
        for ep in episodes:
            status = "OK" if ep.outcome.value == "success" else ep.outcome.value[:4].upper()
            print(f"  [{status:4}] {ep.phase.value:12} | {ep.step_count:2} steps | {ep.goal[:35]}")
    else:
        print("  No episodes yet")

    # Watchers
    print_header("WATCHER STATUS")
    alert_count = len(ecp.watcher_engine.alert_history)
    print(f"  Total Alerts:    {alert_count}")

    # Count by type
    watcher_counts = {}
    for alert in ecp.watcher_engine.alert_history:
        watcher_counts[alert.watcher.value] = watcher_counts.get(alert.watcher.value, 0) + 1

    if watcher_counts:
        print("  By Type:")
        for watcher, count in sorted(watcher_counts.items(), key=lambda x: -x[1]):
            print(f"    {watcher:25} {count}")
    else:
        print("  No alerts fired")

    # Recent Alerts
    if ecp.watcher_engine.alert_history:
        print("  Recent:")
        for alert in ecp.watcher_engine.alert_history[-3:]:
            print(f"    - {alert.watcher.value}: {alert.message[:40]}")

    # Truth Ledger
    print_header("TRUTH LEDGER")
    tl_stats = ledger.get_stats()
    print(f"  Total Entries:   {tl_stats['total']}")
    print(f"  Claims:          {tl_stats['claims']} (unverified)")
    print(f"  Facts:           {tl_stats['facts']} (validated)")
    print(f"  Rules:           {tl_stats['rules']} (generalized)")
    print(f"  High Confidence: {tl_stats['high_confidence']}")
    print(f"  Needs Revalid:   {tl_stats['needs_revalidation']}")
    print(f"  Stale:           {tl_stats['stale']}")

    # Policy Patches
    print_header("POLICY PATCHES")
    patch_stats = patches.get_stats()
    print(f"  Active Patches:  {patch_stats['enabled']}")
    print(f"  Times Triggered: {patch_stats['total_triggers']}")
    print(f"  Times Helped:    {patch_stats['total_helped']}")
    print(f"  Effectiveness:   {patch_stats['effectiveness']:.1%}")

    # List active patches
    print("  Active:")
    for patch in patches.patches.values():
        if patch.enabled:
            print(f"    - {patch.name}")

    # Minimal Mode
    print_header("MINIMAL MODE")
    mm_stats = minimal.get_stats()
    status = "ACTIVE" if mm_stats['currently_active'] else "Inactive"
    print(f"  Current Status:  {status}")
    if mm_stats['currently_active']:
        print(f"  Reason:          {mm_stats['reason']}")
    print(f"  Times Entered:   {mm_stats['times_entered']}")
    print(f"  Avg Duration:    {mm_stats['avg_duration_steps']:.1f} steps")

    # Health Assessment
    print_header("HEALTH ASSESSMENT")

    issues = []

    # Check success rate
    if stats['success_rate'] < 0.5:
        issues.append(f"Low success rate: {stats['success_rate']:.1%}")
    elif stats['success_rate'] < 0.7:
        issues.append(f"Success rate could improve: {stats['success_rate']:.1%}")

    # Check watcher alerts
    if alert_count > 10:
        issues.append(f"High watcher alerts: {alert_count}")

    # Check stale truths
    if tl_stats['stale'] > 0:
        issues.append(f"Stale truths need revalidation: {tl_stats['stale']}")

    # Check minimal mode
    if mm_stats['currently_active']:
        issues.append("Currently in MINIMAL MODE")

    if issues:
        print("  ISSUES DETECTED:")
        for issue in issues:
            print(f"    ! {issue}")
    else:
        print("  All systems healthy")

    print("\n" + "=" * 60)
    print("  Database: ~/.spark/eidos.db")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
