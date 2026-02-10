#!/usr/bin/env python3
"""Test LLM with direct file-based approach."""
import sys, os, json, time, subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path

# 1. Get insights
print("=== Getting insights ===")
from lib.cognitive_learner import get_cognitive_learner
cog = get_cognitive_learner()
ranked = cog.get_ranked_insights(min_reliability=0.3, min_validations=0, limit=10)
print(f"Ranked: {len(ranked)}")
insights = [ins.insight for ins in ranked[:5] if hasattr(ins, 'insight')]
sa = cog.get_self_awareness_insights()
print(f"Self-awareness: {len(sa)}")
for ins in sa[:3]:
    insights.append(ins.insight if hasattr(ins, 'insight') else str(ins))

print(f"Total insights for advisory: {len(insights)}")
for i, text in enumerate(insights[:5]):
    print(f"  {i+1}. {text[:80]}")

# 2. Build prompt and test via file I/O
prompt = """You are Spark Intelligence, an AI learning system that observes coding sessions.
Given these patterns and insights, synthesize 2-4 actionable recommendations.

PATTERNS:
- 7 patterns detected in bridge cycle
- 12 chip insights captured across 7 domains
- Context synced to 6 targets (claude_code, cursor, windsurf, clawdbot, openclaw, exports)

INSIGHTS:
"""
for text in insights[:10]:
    prompt += f"- {text[:150]}\n"

prompt += "\nOutput a numbered list of 2-4 specific recommendations."

# Write prompt
spark_dir = Path.home() / ".spark"
prompt_file = spark_dir / "llm_prompt.txt"
response_file = spark_dir / "llm_response.txt"
prompt_file.write_text(prompt, encoding="utf-8")
if response_file.exists():
    response_file.unlink()

print(f"\n=== Calling Claude CLI ===")
print(f"Prompt: {len(prompt)} chars")

# Use the approach that worked: powershell with file redirect
ps_cmd = f"""$p = Get-Content '{prompt_file}' -Raw; claude -p --output-format text $p > '{response_file}' 2>$null"""

result = subprocess.run(
    ["powershell", "-NoProfile", "-Command", ps_cmd],
    timeout=60,
    capture_output=True,
    creationflags=subprocess.CREATE_NEW_CONSOLE,
)
print(f"Exit code: {result.returncode}")

time.sleep(2)
if response_file.exists():
    response = response_file.read_text(encoding="utf-8").strip()
    print(f"\n=== ADVISORY ({len(response)} chars) ===")
    print(response)
else:
    print("NO RESPONSE FILE - Claude CLI failed")
    print(f"Stderr: {result.stderr.decode('utf-8', errors='replace')[:300]}")
