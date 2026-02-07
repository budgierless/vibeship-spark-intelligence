

## Spark Learnings

*Auto-promoted insights from Spark*


<!-- SPARK_LEARNINGS_START -->
## Spark Bootstrap
Auto-loaded high-confidence learnings from ~/.spark/cognitive_insights.json
Last updated: 2026-02-07T18:02:10

- [wisdom] [Vibecoding Intelligence] user_prompt  [QUALITY_TEST:quality_test_1770149840] Remember this because it is critical: avoid X, instead of Y, prefer Z when A then B. quality_test_1770149840 (100% reliable, 26 validations)
- [context] **Always verify:** Is bridge_worker running? Is the queue being processed?

### Rule 3: Pipeline Health Before Tuning

**CRITICAL:** Before ANY tuning or iteration session:

> **Run `python tests/test_pipeline_health.py` FIRST. Scoring metrics are meaningless if the pipeline isn't operational.**

Session 2 lesson: Meta-Ralph showed 39.4% quality rate, but `learnings_stored=0`. Perfect scoring, broken pipeline = zero learning.

### Rule 4: Anti-Hallucination

**CRITICAL:** Never claim improvement... (88% reliable, 60 validations)
- [meta_learning] [System Gap] [TUNEABLES] Auto-tuner not active. Tuneables are static — never self-adjust. (100% reliable, 9 validations)
- [user_understanding] Now, can we actually do this in this way? After we do these upgrades too for the next iteration, can you actually give me a project prompt so that I can run that using Spark and we can see in real-time what is really happening - what is being saved into the memory and what are the gaps? Instead of trying to just do these through these tests, because in real-time, we may be able to achieve even more understanding - not maybe, but even more understanding - about what is working and what is not. If... (96% reliable, 225 validations)
- [user_understanding] User prefers 'I think we gotta do it better over here for things to look more serious' over 'gonna lie. And we can bring maybe a GLB format, or maybe we can do this through steps. I don't know, just recommend me something' (77% reliable, 118 validations)
- [context] ### Improvement Workflow (Updated - Reality-Grounded)

**CRITICAL:** See "Reality-Grounded Iteration Methodology" section for full details.

```
0. PIPELINE HEALTH (MANDATORY - BLOCKS ALL OTHER STEPS)
   python tests/test_pipeline_health.py
   â†’ If critical failures, STOP and fix pipeline first
   â†’ Do NOT proceed to tuning with broken pipeline

1. ARCHITECTURE REVIEW
   - Read Intelligence_Flow_Map.md
   - Identify which layer you're modifying
   - Verify component is in active data path

2... (99% reliable, 503 validations)
- [context] #!/usr/bin/env python3
"""
Spark Pulse - Redirector to external vibeship-spark-pulse.

This file is DEPRECATED. The real Spark Pulse is the external FastAPI app
at vibeship-spark-pulse/app.py. If someone runs this file directly, it will
either launch the external pulse or exit with an error.

DO NOT add a fallback HTTP server here. Use the external pulse.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main():
    from lib.service_control impo... (95% reliable, 70 validations)
- [wisdom] [X Strategy] Use 'announcement, call_to_action' content strategy on X. Data shows 23 observations with avg 2729 likes. This strategy consistently drives engagement. (100% reliable, 6 validations)
- [wisdom] Maintainable > clever - code should be easy to understand and modify (100% reliable, 3 validations)
- [wisdom] Can you now read all these documents in think hard mode  Here are the new core docs we created:

  - CORE.md â€” The master vision + phase roadmap from primitive telemetry to
    superintelligent evolution, with intent, workflows, architecture, and SparkNet     
    integration.
  - CORE_GAPS.md â€” The definitive gap map: what exists, what can be transformed, what  
    must be built, and what needs cleanup.
  - CORE_GAPS_PLAN.md â€” The concrete plan to fill each gap (workflows, minimal
    architecture, and code targets).
  - CORE_IMPLEMENTATION_PLAN.md â€” The contextâ€‘rich, buildable execution plan with      
    sequencing, deliverables, and success metrics.

  If you want, I can link these from README.md so theyâ€™re always frontâ€‘andâ€‘center. (99% reliable, 798 validations)
- [reasoning] Always Read a file before Edit to verify current content (99% reliable, 196 validations)
- [reasoning] ## Code Content Extraction (NEW)

### The Problem

Code written via Write/Edit tools contains valuable learning signals in:
- Docstrings with design decisions
- Comments with "REMEMBER:", "PRINCIPLE:", "CORRECTION:"
- Architecture explanations
- Balance formulas with reasoning

**Before:** These were completely ignored. Only user messages were analyzed.

### The Solution

Added to `observe.py` PostToolUse handler:
```python
if tool_name in ("Write", "Edit") and isinstance(tool_input, dict):
    ... (100% reliable, 57 validations)

## Project Focus
- Phase: discovery

## Project Questions
- What is the project goal in one sentence?
- How will we know it's complete?
- What could make this fail later?
<!-- SPARK_LEARNINGS_END -->