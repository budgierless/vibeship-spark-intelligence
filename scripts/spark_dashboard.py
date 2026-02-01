#!/usr/bin/env python3
"""
Spark Intelligence Dashboard (CLI)

CLI dashboard showing:
1. What Spark is learning from X trends
2. Ecosystem intelligence (Moltbook, OpenClaw, BASE, Solana, Bittensor)
3. Cognitive insight stats

For full UI, use the xtrends Svelte dashboard.

Run:
    python scripts/spark_dashboard.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.cognitive_learner import get_cognitive_learner, CognitiveCategory


def load_research_reports():
    """Load all research reports."""
    report_dir = Path.home() / '.spark' / 'research_reports'
    reports = []

    if report_dir.exists():
        for f in sorted(report_dir.glob('report_*.json'), reverse=True)[:30]:
            try:
                reports.append(json.loads(f.read_text()))
            except:
                pass

    return reports


def load_collective_intelligence():
    """Load SparkNet collective intelligence."""
    collective_dir = Path.home() / '.spark' / 'sparknet' / 'collective'
    collective = {}

    if collective_dir.exists():
        for f in collective_dir.glob('*.json'):
            try:
                collective[f.stem] = json.loads(f.read_text())
            except:
                pass

    return collective


def get_ecosystem_insights():
    """Get ecosystem-specific insights from Spark."""
    learner = get_cognitive_learner()

    ecosystems = {
        'moltbook': [],
        'openclaw': [],
        'base': [],
        'solana': [],
        'bittensor': [],
        'vibe_coding': [],
    }

    for key, insight in learner.insights.items():
        text = (insight.insight + ' ' + insight.context).lower()

        for eco in ecosystems.keys():
            if eco in text or eco.replace('_', ' ') in text:
                ecosystems[eco].append({
                    'insight': insight.insight,
                    'confidence': insight.confidence,
                    'validations': insight.times_validated,
                    'created': insight.created_at[:10] if insight.created_at else 'unknown',
                })

    return ecosystems


def get_content_recommendations():
    """Get content recommendations."""
    try:
        from scripts.content_recommendations import generate_recommendations
        return generate_recommendations()
    except:
        return {'content_ideas': [], 'ready_to_post': []}


def run_cli_dashboard():
    """Run a CLI version of the dashboard."""
    print("\n" + "=" * 70)
    print("  SPARK INTELLIGENCE DASHBOARD (CLI Mode)")
    print("=" * 70)

    learner = get_cognitive_learner()
    stats = learner.get_stats()

    print(f"\n📊 COGNITIVE INSIGHTS: {stats['total_insights']}")
    print(f"   Average Reliability: {stats['avg_reliability']:.0%}")
    print(f"   Promoted: {stats['promoted_count']}")

    print("\n   By Category:")
    for cat, count in sorted(stats['by_category'].items(), key=lambda x: -x[1]):
        print(f"     - {cat}: {count}")

    # Ecosystem insights
    print("\n🌐 ECOSYSTEM INTELLIGENCE:")
    ecosystems = get_ecosystem_insights()
    for eco, insights in ecosystems.items():
        if insights:
            print(f"\n   {eco.upper()} ({len(insights)} insights)")
            for i in sorted(insights, key=lambda x: -x['confidence'])[:3]:
                print(f"     • {i['insight'][:60]}... ({i['confidence']:.0%})")

    # Collective intelligence
    print("\n🤖 SPARKNET COLLECTIVE:")
    collective = load_collective_intelligence()
    for name, data in collective.items():
        if isinstance(data, list):
            print(f"   {name}: {len(data)} items")

    # Recent research
    print("\n📰 RECENT RESEARCH REPORTS:")
    reports = load_research_reports()
    for r in reports[:3]:
        print(f"   - {r.get('date', 'unknown')}: {r.get('insights_count', 0)} insights")

    # Content recommendations
    print("\n✍️  CONTENT RECOMMENDATIONS:")
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from content_recommendations import generate_recommendations
        recs = generate_recommendations()
        for i, idea in enumerate(recs.get('content_ideas', [])[:5], 1):
            print(f"   {i}. [{idea['framework']}] {idea['angle'][:50]}...")
    except Exception as e:
        print(f"   (Error loading recommendations: {e})")

    print("\n" + "=" * 70)
    print("  For full UI dashboard, use xtrends Svelte app:")
    print("  cd xtrends/svelte-app && npm run dev")
    print("=" * 70)


if __name__ == '__main__':
    run_cli_dashboard()
