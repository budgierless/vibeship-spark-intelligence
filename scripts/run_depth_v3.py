#!/usr/bin/env python3
"""
DEPTH v3 — Autonomous Evolution Runner

Orchestrates the full evolution cycle:
1. Baseline benchmark (zero injection) per domain
2. Training cycles with domain-scoped knowledge injection
3. Post-training benchmark to measure if knowledge helped
4. Gap analysis and regression detection
5. Evolution report generation
6. Git commit artifacts at intervals

Usage:
    python scripts/run_depth_v3.py --domains ui_ux,debugging,api_data_flow --cycles 5
    python scripts/run_depth_v3.py --domain ui_ux --cycles 10 --skip-baseline
    python scripts/run_depth_v3.py --report-only
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.depth_trainer import (
    run_benchmark,
    run_autonomous_loop,
    check_regression,
    benchmark_report,
    get_weakest_gaps,
    get_golden_stats,
    get_training_history,
    get_benchmark_history,
    _safe_print,
    SPARK_DIR,
    BENCHMARK_LOG,
    GAPS_FILE,
    GOLDEN_ANSWERS_FILE,
    TRAINING_LOG,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(message)s",
)
log = logging.getLogger("depth.v3.runner")

REPORT_DIR = PROJECT_ROOT / "docs" / "reports"
REPORT_FILE = REPORT_DIR / "DEPTH_V3_EVOLUTION_REPORT.md"

AVAILABLE_DOMAINS = ["ui_ux", "debugging", "api_data_flow"]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _check_depth_server() -> bool:
    """Check if DEPTH server is running on localhost:5555."""
    try:
        import httpx
        resp = httpx.get("http://localhost:5555/api/health", timeout=5.0)
        return resp.status_code == 200
    except Exception:
        return False


def _check_ollama() -> bool:
    """Check if Ollama is running."""
    try:
        import httpx
        resp = httpx.get("http://localhost:11434/api/tags", timeout=5.0)
        return resp.status_code == 200
    except Exception:
        return False


def _git_commit(message: str):
    """Commit training artifacts to git."""
    try:
        # Stage training artifacts
        files_to_stage = []
        for f in [TRAINING_LOG, BENCHMARK_LOG, GAPS_FILE, GOLDEN_ANSWERS_FILE]:
            if f.exists():
                files_to_stage.append(str(f))

        # Stage report if exists
        if REPORT_FILE.exists():
            files_to_stage.append(str(REPORT_FILE))

        if not files_to_stage:
            return

        subprocess.run(
            ["git", "add"] + files_to_stage,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            timeout=30,
        )

        subprocess.run(
            ["git", "commit", "-m", message,
             "-m", "Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            timeout=30,
        )
        log.info("Git commit: %s", message)
    except Exception as e:
        log.warning("Git commit failed: %s", e)


def generate_evolution_report(
    baseline_results: Dict[str, List],
    post_results: Dict[str, List],
    training_cycles: int,
) -> str:
    """Generate comprehensive evolution report in Markdown."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# DEPTH v3 Evolution Report")
    lines.append(f"\nGenerated: {_now()}")
    lines.append(f"\nTraining cycles per domain: {training_cycles}")
    lines.append("")

    # Overview table
    lines.append("## Score Trajectory")
    lines.append("")
    lines.append("| Domain | Baseline | Post-Training | Delta | Trend |")
    lines.append("|--------|----------|---------------|-------|-------|")

    for domain in AVAILABLE_DOMAINS:
        base = baseline_results.get(domain, [])
        post = post_results.get(domain, [])

        if base:
            base_avg = sum(r.pct for r in base) / len(base)
        else:
            base_avg = 0

        if post:
            post_avg = sum(r.pct for r in post) / len(post)
        else:
            post_avg = 0

        delta = post_avg - base_avg
        trend = "improving" if delta > 2 else "declining" if delta < -2 else "stable"
        lines.append(f"| {domain} | {base_avg:.1f}% | {post_avg:.1f}% | {'+' if delta > 0 else ''}{delta:.1f}% | {trend} |")

    lines.append("")

    # Per-domain detailed analysis
    for domain in AVAILABLE_DOMAINS:
        base = baseline_results.get(domain, [])
        post = post_results.get(domain, [])

        if not base and not post:
            continue

        lines.append(f"## {domain}")
        lines.append("")

        # Per-topic comparison
        if base:
            lines.append("### Baseline Scores (Zero Injection)")
            lines.append("")
            for r in base:
                lines.append(f"- **{r.topic}**: {r.total_score}/{r.max_depth*10} ({r.pct:.0f}%, {r.grade}) | Profile: `{r.depth_profile}`")
            lines.append("")

        if post:
            lines.append("### Post-Training Scores")
            lines.append("")
            for r in post:
                lines.append(f"- **{r.topic}**: {r.total_score}/{r.max_depth*10} ({r.pct:.0f}%, {r.grade}) | Profile: `{r.depth_profile}`")
            lines.append("")

        # Per-depth analysis
        if base and post:
            lines.append("### Per-Depth Comparison")
            lines.append("")
            lines.append("| Depth | Baseline Avg | Post Avg | Delta |")
            lines.append("|-------|-------------|----------|-------|")

            for depth in range(1, 16):
                base_scores = [
                    s["score"] for r in base for s in r.steps if s["depth"] == depth
                ]
                post_scores = [
                    s["score"] for r in post for s in r.steps if s["depth"] == depth
                ]

                if base_scores and post_scores:
                    b_avg = sum(base_scores) / len(base_scores)
                    p_avg = sum(post_scores) / len(post_scores)
                    d = p_avg - b_avg
                    lines.append(f"| D{depth} | {b_avg:.1f} | {p_avg:.1f} | {'+' if d > 0 else ''}{d:.1f} |")

            lines.append("")

        # Regressions
        regs = check_regression(domain, verbose=False)
        if regs:
            lines.append("### Regressions Detected")
            lines.append("")
            for r in regs:
                lines.append(f"- **{r['topic']}** D{r['depth']}: {r['old_score']} -> {r['new_score']} (drop: {r['drop']})")
            lines.append("")

    # Gap analysis
    all_gaps = get_weakest_gaps(count=20)
    if all_gaps:
        lines.append("## Learning Gaps (Weakest Areas)")
        lines.append("")
        lines.append("| Domain | Topic | Depth | Score | Gap Type |")
        lines.append("|--------|-------|-------|-------|----------|")
        for g in all_gaps[:15]:
            lines.append(f"| {g.get('domain', '?')} | {g['topic'][:30]} | D{g['depth']} | {g['score']}/10 | {g.get('gap_type', '?')} |")
        lines.append("")

    # Golden answers
    golden = get_golden_stats()
    if golden["total"] > 0:
        lines.append("## Golden Answers (Verified Exemplars)")
        lines.append("")
        lines.append(f"Total: {golden['total']} verified high-quality answers")
        lines.append("")
        for d, count in golden.get("by_domain", {}).items():
            lines.append(f"- **{d}**: {count} golden answers")
        lines.append("")

    # Knowledge effectiveness
    lines.append("## Knowledge Effectiveness")
    lines.append("")
    training_history = get_training_history(limit=50)
    if training_history:
        with_kb = [h for h in training_history if h.get("knowledge_used", 0) > 0]
        without_kb = [h for h in training_history if h.get("knowledge_used", 0) == 0]

        if with_kb and without_kb:
            avg_with = sum(h.get("pct", 0) for h in with_kb) / len(with_kb)
            avg_without = sum(h.get("pct", 0) for h in without_kb) / len(without_kb)
            delta = avg_with - avg_without
            lines.append(f"- Sessions WITH knowledge injection: avg {avg_with:.1f}% ({len(with_kb)} sessions)")
            lines.append(f"- Sessions WITHOUT knowledge injection: avg {avg_without:.1f}% ({len(without_kb)} sessions)")
            lines.append(f"- KB Delta: {'+' if delta > 0 else ''}{delta:.1f}%")
            lines.append(f"- KB Effective: {'YES' if delta > 0 else 'NO'}")
        else:
            lines.append("- Not enough data to compare KB effectiveness yet")
    else:
        lines.append("- No training history yet")

    lines.append("")

    # System stats
    lines.append("## System Stats")
    lines.append("")
    bench_data = get_benchmark_history()
    lines.append(f"- Total benchmark runs: {len(bench_data)}")
    lines.append(f"- Total training sessions: {len(training_history)}")
    lines.append(f"- Golden answers: {golden['total']}")
    lines.append(f"- Learning gaps tracked: {len(all_gaps)}")
    lines.append(f"- Report generated: {_now()}")
    lines.append("")

    report_text = "\n".join(lines)

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report_text)

    log.info("Evolution report written to %s", REPORT_FILE)
    return report_text


async def run_evolution_cycle(
    domains: List[str],
    training_cycles: int = 5,
    skip_baseline: bool = False,
    verbose: bool = True,
):
    """Run a full evolution cycle: baseline -> train -> post-train -> report."""

    _safe_print("\n" + "=" * 70)
    _safe_print("  DEPTH v3 AUTONOMOUS EVOLUTION ENGINE")
    _safe_print(f"  Domains: {', '.join(domains)}")
    _safe_print(f"  Training cycles per domain: {training_cycles}")
    _safe_print(f"  Started: {_now()}")
    _safe_print("=" * 70 + "\n")

    baseline_results = {}
    post_results = {}

    for domain in domains:
        _safe_print(f"\n{'#' * 70}")
        _safe_print(f"  DOMAIN: {domain}")
        _safe_print(f"{'#' * 70}")

        # Step 1: Baseline benchmark (zero injection)
        if not skip_baseline:
            _safe_print(f"\n  [STEP 1] Running BASELINE benchmark for {domain}...")
            try:
                base = await run_benchmark(
                    domain=domain,
                    verbose=verbose,
                    label=f"baseline-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M')}",
                )
                baseline_results[domain] = base
                _safe_print(f"  Baseline complete: {len(base)} topics benchmarked")
            except Exception as e:
                log.error("Baseline benchmark failed for %s: %s", domain, e)
                _safe_print(f"  Baseline failed: {e}")
                baseline_results[domain] = []
        else:
            _safe_print(f"  [STEP 1] Skipping baseline (--skip-baseline)")
            baseline_results[domain] = []

        # Step 2: Training cycles
        _safe_print(f"\n  [STEP 2] Running {training_cycles} training cycles for {domain}...")
        try:
            await run_autonomous_loop(
                max_cycles=training_cycles,
                verbose=verbose,
                domain=domain,
                mode="vibe",
            )
        except Exception as e:
            log.error("Training loop failed for %s: %s", domain, e)
            _safe_print(f"  Training failed: {e}")

        # Step 3: Post-training benchmark
        _safe_print(f"\n  [STEP 3] Running POST-TRAINING benchmark for {domain}...")
        try:
            post = await run_benchmark(
                domain=domain,
                verbose=verbose,
                label=f"post-training-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M')}",
            )
            post_results[domain] = post
            _safe_print(f"  Post-training complete: {len(post)} topics benchmarked")
        except Exception as e:
            log.error("Post-training benchmark failed for %s: %s", domain, e)
            _safe_print(f"  Post-training failed: {e}")
            post_results[domain] = []

        # Step 4: Regression check
        _safe_print(f"\n  [STEP 4] Checking for regressions in {domain}...")
        regs = check_regression(domain, verbose=verbose)
        if regs:
            _safe_print(f"  WARNING: {len(regs)} regressions detected!")
        else:
            _safe_print(f"  No regressions detected")

        # Step 5: Generate report after each domain
        _safe_print(f"\n  [STEP 5] Generating evolution report...")
        generate_evolution_report(baseline_results, post_results, training_cycles)

    # Final comprehensive report
    _safe_print(f"\n\n{'=' * 70}")
    _safe_print("  EVOLUTION CYCLE COMPLETE")
    _safe_print(f"{'=' * 70}")

    report = generate_evolution_report(baseline_results, post_results, training_cycles)

    # Print summary
    _safe_print(f"\n  Report: {REPORT_FILE}")
    _safe_print(f"  Benchmark log: {BENCHMARK_LOG}")
    _safe_print(f"  Gaps file: {GAPS_FILE}")
    _safe_print(f"  Golden answers: {GOLDEN_ANSWERS_FILE}")
    _safe_print(f"  Completed: {_now()}")

    # Benchmark report
    _safe_print("\n")
    benchmark_report(verbose=True)

    return baseline_results, post_results


async def run_continuous_evolution(
    domains: List[str],
    cycles_per_round: int = 5,
    total_rounds: int = 3,
    verbose: bool = True,
):
    """Run multiple evolution rounds continuously.

    Each round: baseline -> N training cycles -> post-benchmark -> report -> git commit.
    """
    for round_num in range(1, total_rounds + 1):
        _safe_print(f"\n{'*' * 70}")
        _safe_print(f"  EVOLUTION ROUND {round_num}/{total_rounds}")
        _safe_print(f"{'*' * 70}")

        skip_base = round_num > 1  # Only baseline on first round
        await run_evolution_cycle(
            domains=domains,
            training_cycles=cycles_per_round,
            skip_baseline=skip_base,
            verbose=verbose,
        )

        # Git commit after each round
        _git_commit(
            f"DEPTH v3: Evolution round {round_num}/{total_rounds} "
            f"({', '.join(domains)}, {cycles_per_round} cycles)"
        )

        if round_num < total_rounds:
            _safe_print(f"\n  Pausing 10s before next round...")
            await asyncio.sleep(10)

    _safe_print(f"\n{'=' * 70}")
    _safe_print(f"  ALL {total_rounds} EVOLUTION ROUNDS COMPLETE")
    _safe_print(f"  Report: {REPORT_FILE}")
    _safe_print(f"{'=' * 70}\n")


async def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="DEPTH v3 Autonomous Evolution Runner"
    )
    parser.add_argument("--domains", type=str, default="ui_ux,debugging,api_data_flow",
                        help="Comma-separated domain list")
    parser.add_argument("--domain", type=str, help="Single domain (shortcut)")
    parser.add_argument("--cycles", type=int, default=5,
                        help="Training cycles per domain per round")
    parser.add_argument("--rounds", type=int, default=1,
                        help="Number of evolution rounds")
    parser.add_argument("--skip-baseline", action="store_true",
                        help="Skip initial baseline benchmark")
    parser.add_argument("--report-only", action="store_true",
                        help="Just generate report from existing data")
    parser.add_argument("--quiet", action="store_true", help="Minimal output")
    args = parser.parse_args()

    # Pre-flight checks
    if not _check_depth_server():
        _safe_print("ERROR: DEPTH server not running on localhost:5555")
        _safe_print("Start it: cd vibeship-depth-game && python server.py")
        sys.exit(1)

    if not _check_ollama():
        _safe_print("ERROR: Ollama not running on localhost:11434")
        _safe_print("Start it: ollama serve")
        sys.exit(1)

    if args.report_only:
        generate_evolution_report({}, {}, 0)
        benchmark_report(verbose=True)
        return

    domains = [args.domain] if args.domain else args.domains.split(",")
    domains = [d.strip() for d in domains if d.strip()]

    if args.rounds > 1:
        await run_continuous_evolution(
            domains=domains,
            cycles_per_round=args.cycles,
            total_rounds=args.rounds,
            verbose=not args.quiet,
        )
    else:
        await run_evolution_cycle(
            domains=domains,
            training_cycles=args.cycles,
            skip_baseline=args.skip_baseline,
            verbose=not args.quiet,
        )


if __name__ == "__main__":
    asyncio.run(main())
