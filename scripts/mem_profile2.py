#!/usr/bin/env python3
"""Pinpoint which bridge_cycle step causes the memory leak."""
import sys, os, gc
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psutil
proc = psutil.Process()

def mem():
    return f"{proc.memory_info().rss/1024/1024:.0f}MB"

print(f"Start: {mem()}")

# Import individually
from lib.bridge import update_spark_context
print(f"After import bridge: {mem()}")

from lib.memory_capture import process_recent_memory_events
print(f"After import memory: {mem()}")

from lib.pipeline import run_processing_cycle
print(f"After import pipeline: {mem()}")

from lib.context_sync import sync_context
print(f"After import sync: {mem()}")

# Step 1: Context update
print(f"\n--- Step 1: update_spark_context ---")
try:
    update_spark_context()
except Exception as e:
    print(f"  error: {e}")
gc.collect()
print(f"After: {mem()}")

# Step 2: Memory capture
print(f"\n--- Step 2: memory capture ---")
try:
    process_recent_memory_events(limit=10)
except Exception as e:
    print(f"  error: {e}")
gc.collect()
print(f"After: {mem()}")

# Step 3: Pipeline (pattern detection + extraction)
print(f"\n--- Step 3: run_processing_cycle ---")
try:
    metrics = run_processing_cycle()
    print(f"  events_read={metrics.events_read} patterns={metrics.patterns_detected}")
    # Release
    metrics.processed_events = []
    del metrics
except Exception as e:
    print(f"  error: {e}")
gc.collect()
print(f"After: {mem()}")

# Step 4: Sync
print(f"\n--- Step 4: sync_context ---")
try:
    sync_context()
except Exception as e:
    print(f"  error: {e}")
gc.collect()
print(f"After: {mem()}")

print(f"\nFinal: {mem()}")
