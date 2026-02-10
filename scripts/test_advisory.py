#!/usr/bin/env python3
"""Test full LLM advisory synthesis."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.llm import ask_claude, synthesize_advisory

# Quick sanity check
print("=== Quick test ===")
r = ask_claude("Say just OK")
print(f"ask_claude: [{r}]")

# Real advisory test
print("\n=== Advisory synthesis ===")
patterns = [
    "7 coding patterns detected in bridge cycle",
    "12 chip insights captured across 7 domains",
    "Memory leak found: fastembed ONNX model consuming 8GB RAM",
    "Chip JSONL files grew to 44MB before rotation fix",
]
insights = [
    "bridge_worker must run with SPARK_EMBEDDINGS=0 or RAM explodes",
    "PowerShell Invoke-WebRequest chokes on 483KB responses, use curl.exe",
    "Spark Pulse must start via -m uvicorn to skip blocking startup_services()",
    "Chip JSONL rotation threshold of 2MB per chip prevents file bloat",
    "Python subprocess cannot provide TTY for Claude CLI on Windows",
]

advisory = synthesize_advisory(patterns=patterns, insights=insights)
if advisory:
    print(f"SUCCESS ({len(advisory)} chars):")
    print(advisory)
else:
    print("FAILED - no advisory returned")
