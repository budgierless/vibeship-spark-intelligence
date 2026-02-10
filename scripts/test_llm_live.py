#!/usr/bin/env python3
"""Test LLM advisory generation live."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 1. Check cognitive insights
print("=== Cognitive Insights ===")
from lib.cognitive_learner import get_cognitive_learner, CognitiveCategory
cog = get_cognitive_learner()
all_insights = []
ranked = cog.get_ranked_insights(min_reliability=0.3, min_validations=0, limit=10)
print(f"  Ranked insights: {len(ranked)}")
for ins in ranked[:5]:
    text = ins.insight if hasattr(ins, "insight") else str(ins)
    all_insights.append(text)
    print(f"    -> {text[:100]}")
sa = cog.get_self_awareness_insights()
print(f"  Self-awareness: {len(sa)}")
for ins in sa[:3]:
    text = ins.insight if hasattr(ins, "insight") else str(ins)
    all_insights.append(text)
    print(f"    -> {text[:100]}")

# 2. Test advisory synthesis
print(f"\n=== Advisory Synthesis ({len(all_insights)} insights) ===")
from lib.llm import synthesize_advisory
patterns = ["7 patterns detected", "12 chip insights captured", "context synced to 6 targets"]
advisory = synthesize_advisory(patterns=patterns, insights=all_insights[:10])
if advisory:
    print(f"SUCCESS! Advisory ({len(advisory)} chars):")
    print(advisory)
else:
    print("FAILED - no advisory generated")

# 3. Check if SPARK_ADVISORY.md was written
from pathlib import Path
adv_file = Path.home() / ".openclaw" / "workspace" / "SPARK_ADVISORY.md"
if adv_file.exists():
    print(f"\n=== SPARK_ADVISORY.md ===")
    print(adv_file.read_text(encoding="utf-8")[:500])
