#!/usr/bin/env python3
"""Pinpoint which bridge_cycle substep causes the 8GB leak."""
import sys, os, gc, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psutil
proc = psutil.Process()
def mem(): return proc.memory_info().rss/1024/1024

print(f"Start: {mem():.0f}MB")

from lib.queue import read_recent_events, EventType
from lib.bridge import update_spark_context
from lib.chips import process_chip_events
from lib.chip_merger import merge_chip_insights
from lib.validation_loop import process_validation_events, process_outcome_validation
from lib.prediction_loop import process_prediction_cycle
from lib.content_learner import learn_from_edit_event
from lib.context_sync import sync_context
from lib.cognitive_learner import get_cognitive_learner
from lib.tastebank import parse_like_message, add_item

print(f"After imports: {mem():.0f}MB")

# Get events
events = read_recent_events(40)
print(f"After read events ({len(events)}): {mem():.0f}MB")

# Context
update_spark_context()
gc.collect()
print(f"After context: {mem():.0f}MB")

# Validation
try:
    process_validation_events(limit=200)
except Exception as e:
    print(f"  validation error: {e}")
gc.collect()
print(f"After validation: {mem():.0f}MB")

# Outcome validation
try:
    process_outcome_validation(limit=50)
except Exception as e:
    print(f"  outcome_validation error: {e}")
gc.collect()
print(f"After outcome_validation: {mem():.0f}MB")

# Prediction
try:
    process_prediction_cycle()
except Exception as e:
    print(f"  prediction error: {e}")
gc.collect()
print(f"After prediction: {mem():.0f}MB")

# Chips
try:
    chip_stats = process_chip_events(events)
    print(f"  chips: {chip_stats}")
except Exception as e:
    print(f"  chip error: {e}")
gc.collect()
print(f"After chips: {mem():.0f}MB")

# Chip merger
try:
    merge_chip_insights()
except Exception as e:
    print(f"  merge error: {e}")
gc.collect()
print(f"After chip_merger: {mem():.0f}MB")

# Cognitive signals
cognitive = get_cognitive_learner()
for ev in events:
    if ev.event_type == EventType.USER_PROMPT:
        text = (ev.data or {}).get("payload", {}).get("text", "")
        if text:
            cognitive.learn_user_preference(text[:200], "general")
gc.collect()
print(f"After cognitive: {mem():.0f}MB")

# Sync
try:
    sync_context()
except Exception as e:
    print(f"  sync error: {e}")
gc.collect()
print(f"After sync: {mem():.0f}MB")

print(f"\nFinal: {mem():.0f}MB")
m = mem()
if m > 1000:
    print(f"LEAK: {m:.0f}MB")
else:
    print("No major leak in individual steps - leak is in run_bridge_cycle orchestration")
