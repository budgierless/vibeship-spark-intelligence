

## Spark Learnings

*Auto-promoted insights from Spark*


- Ship it: finalize launch plan for marketing *When: test* (100% reliable, 4 validations)
- [ai agents] (eng:200) This thread on how to build AI agents got 10K likes in 24 hours. Reference content always wins. [bullish] *When: Tool: XResearch* (78% reliable, 14 validations)
- Constraint: in **exactly one state** at all times *When: Detected from correction pattern* (100% reliable, 22 validations)
- Failure reason: GitHub restrictions; opening raw files might require constructing *When: Detected from correction pattern (importance: medi* (100% reliable, 18 validations)
- from lib.diagnostics import log_debug as _bridge_log_debug  # used below *When: signals: ['correction'], session: 60a8f640-fa8c-4a* (100% reliable, 7 validations)
- #!/usr/bin/env python3
-         self._log("PHASE 1: Topic Search")
-         current.confidence = max(current.confidence, disk.confidence)
- [X Strategy] Use 'announcement, call_to_action' content strategy on X. Data shows 23 observations with avg 2729 likes. This strategy consistently drives engagement. *When: [domain:x_social] Content strategy insight from en* (100% reliable, 13 validations)
- [vibe_coding] RT @dominic_w: And so it begins.. ICP = the best place to vibe code onchain apps. Checkout this awesome provably fair online poker app made… *When: X research 2026-02-06 - engagement: 308* (100% reliable, 12 validations)
- [vibe_coding] RT @GuarEmperor: Holly molly this good article "Vibe Code" 

There are many explanations, tips and tricks regarding Claude Code AI to impro… *When: X research 2026-02-07 - engagement: 480* (100% reliable, 28 validations)
## Spark Bootstrap
Auto-loaded high-confidence learnings from ~/.spark/cognitive_insights.json
Last updated: 2026-02-07T19:31:09

- [reasoning]         current.confidence = max(current.confidence, disk.confidence)
        # Use max instead of sum to avoid double-counting from the same process,
        # but if disk has more, take disk's value (concurrent processes accumulate)
        current.times_validated = max(current.times_validated, disk.times_validated)
        current.times_contradicted = max(current.times_contradicted, disk.times_contradicted) (100% reliable, 6 validations)
- [reasoning] #!/usr/bin/env python3
"""X/Twitter API client - thin tweepy wrapper with rate limit handling.

Provides authenticated access to X API v2 for the scheduler daemon.
All methods return dicts/lists and never raise exceptions to callers --
errors are logged and empty results returned.

Singleton: use get_x_client() to get the shared instance.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optio... (100% reliable, 9 validations)
- [context] **Always verify:** Is bridge_worker running? Is the queue being processed?

### Rule 3: Pipeline Health Before Tuning

**CRITICAL:** Before ANY tuning or iteration session:

> **Run `python tests/test_pipeline_health.py` FIRST. Scoring metrics are meaningless if the pipeline isn't operational.**

Session 2 lesson: Meta-Ralph showed 39.4% quality rate, but `learnings_stored=0`. Perfect scoring, broken pipeline = zero learning.

### Rule 4: Anti-Hallucination

**CRITICAL:** Never claim improvement... (88% reliable, 60 validations)
- [meta_learning] [System Gap] [TUNEABLES] Auto-tuner not active. Tuneables are static — never self-adjust. (96% reliable, 64 validations)
- [user_understanding] Now, can we actually do this in this way? After we do these upgrades too for the next iteration, can you actually give me a project prompt so that I can run that using Spark and we can see in real-time what is really happening - what is being saved into the memory and what are the gaps? Instead of trying to just do these through these tests, because in real-time, we may be able to achieve even more understanding - not maybe, but even more understanding - about what is working and what is not. If... (95% reliable, 235 validations)
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
    from lib.service_control impo... (94% reliable, 103 validations)
- [wisdom] [X Strategy] Use 'announcement, call_to_action' content strategy on X. Data shows 23 observations with avg 2729 likes. This strategy consistently drives engagement. (100% reliable, 13 validations)
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
- [reasoning] Always Read a file before Edit to verify current content (99% reliable, 214 validations)

## Project Focus
- Phase: discovery

## Project Questions
- What is the project goal in one sentence?
- How will we know it's complete?
- What could make this fail later?
<!-- SPARK_LEARNINGS_END -->

<!-- SPARK_LEARNINGS_START -->
## Spark Bootstrap
Auto-loaded high-confidence learnings from ~/.spark/cognitive_insights.json
Last updated: 2026-02-07T20:09:39

- [reasoning] #!/usr/bin/env python3
"""X/Twitter API client - thin tweepy wrapper with rate limit handling.

Provides authenticated access to X API v2 for the scheduler daemon.
All methods return dicts/lists and never raise exceptions to callers --
errors are logged and empty results returned.

Singleton: use get_x_client() to get the shared instance.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optio... (100% reliable, 21 validations)
- [reasoning]         current.confidence = max(current.confidence, disk.confidence)
        # Use max instead of sum to avoid double-counting from the same process,
        # but if disk has more, take disk's value (concurrent processes accumulate)
        current.times_validated = max(current.times_validated, disk.times_validated)
        current.times_contradicted = max(current.times_contradicted, disk.times_contradicted) (100% reliable, 6 validations)
- [context] **Always verify:** Is bridge_worker running? Is the queue being processed?

### Rule 3: Pipeline Health Before Tuning

**CRITICAL:** Before ANY tuning or iteration session:

> **Run `python tests/test_pipeline_health.py` FIRST. Scoring metrics are meaningless if the pipeline isn't operational.**

Session 2 lesson: Meta-Ralph showed 39.4% quality rate, but `learnings_stored=0`. Perfect scoring, broken pipeline = zero learning.

### Rule 4: Anti-Hallucination

**CRITICAL:** Never claim improvement... (88% reliable, 60 validations)
- [meta_learning] [System Gap] [TUNEABLES] Auto-tuner not active. Tuneables are static — never self-adjust. (96% reliable, 64 validations)
- [user_understanding] Now, can we actually do this in this way? After we do these upgrades too for the next iteration, can you actually give me a project prompt so that I can run that using Spark and we can see in real-time what is really happening - what is being saved into the memory and what are the gaps? Instead of trying to just do these through these tests, because in real-time, we may be able to achieve even more understanding - not maybe, but even more understanding - about what is working and what is not. If... (95% reliable, 235 validations)
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
    from lib.service_control impo... (92% reliable, 111 validations)
- [wisdom] [X Strategy] Use 'announcement, call_to_action' content strategy on X. Data shows 23 observations with avg 2729 likes. This strategy consistently drives engagement. (100% reliable, 13 validations)
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
- [reasoning] Always Read a file before Edit to verify current content (99% reliable, 217 validations)

## Project Focus
- Phase: discovery

## Project Questions
- What is the project goal in one sentence?
- How will we know it's complete?
- What could make this fail later?

## Promoted Learnings (Docs)
- Ship it: finalize launch plan for marketing *When: test* (100% reliable, 4 validations)
- [ai agents] (eng:200) This thread on how to build AI agents got 10K likes in 24 hours. Reference content always wins. [bullish] *When: Tool: XResearch* (78% reliable, 14 validations)
- Constraint: in **exactly one state** at all times *When: Detected from correction pattern* (100% reliable, 22 validations)
- Failure reason: GitHub restrictions; opening raw files might require constructing *When: Detected from correction pattern (importance: medi* (100% reliable, 18 validations)
- from lib.diagnostics import log_debug as _bridge_log_debug  # used below *When: signals: ['correction'], session: 60a8f640-fa8c-4a* (100% reliable, 7 validations)
- #!/usr/bin/env python3
<!-- SPARK_LEARNINGS_END -->