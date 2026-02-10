#!/usr/bin/env python3
"""Profile bridge_worker memory usage across cycles."""
import sys, os, gc
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psutil
proc = psutil.Process()
print(f"Start: {proc.memory_info().rss/1024/1024:.0f}MB")

from lib.bridge_cycle import run_bridge_cycle
print(f"After import: {proc.memory_info().rss/1024/1024:.0f}MB")

for i in range(5):
    stats = run_bridge_cycle(memory_limit=10, pattern_limit=50)
    gc.collect()
    mem = proc.memory_info().rss/1024/1024
    print(f"After cycle {i+1}: {mem:.0f}MB | patterns={stats.get('pattern_processed',0)} errors={stats.get('errors',[])}")
    if mem > 2000:
        print("LEAK DETECTED - stopping")
        break

print("Done")
