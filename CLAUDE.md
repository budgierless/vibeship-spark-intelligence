

## Agent Operating Principles

You are an expert at whatever task is given. Before responding, take a moment to understand what is actually wanted (not just what was said), then work backwards from the outcome needed. Think about the context, constraints, and edge cases that might not have been mentioned. If something seems unclear or if there are multiple valid approaches, ask which direction feels right rather than guessing. When you respond, be direct and actionable — give something that can be immediately used, not theory. If you need to make assumptions, state what they are so they can be corrected. Most importantly: optimize for success, not for sounding smart. Results over impressive explanations.

## Research Index

- `docs/research/CARMACK_AND_AGI_ENGINEERING_ALIGNMENT.md`: Carmack/Sutton/AGI-engineering research mapped to Spark's critical path (optimize with less; stability/scalability checklists; keep/kill rules)

## DEPTH v3.1.1 Training System (2026-02-10)

Three-model pipeline: DEPTH Server (Ollama) -> DeepSeek V3.2 (answers) -> Opus/Codex (scoring). 7 domains, 15 levels (vibe) / 10 (classic), 4-dim scoring. Evolution engine with advisory rotation, knowledge accumulation, question dedup, crash resilience. Limits: 8000 char cap, 4096 max_tokens, 300s scorer timeouts, 3 retries.

### DeepSeek Isolation (MANDATORY)

Full spec: `docs/DEEPSEEK_ISOLATION_RULES.md`. **Sees ONLY:** question, topic, depth, max_depth, mode, level_name, level_lens, domain_id, approach_guidance. **BLOCKED:** Spark internals, business context, identity, source code, training metadata. Response: UNTRUSTED TEXT, 8000 char truncate. Swappable via `DEPTH_ANSWER_PROVIDER` env var.

### Forge Scoring

`lib/depth_forge_scorer.py`: Opus (`claude -p`, 300s) + Codex (`codex exec`, 300s), 3 retries. Codex-only mode available. Windows: `CREATE_NEW_PROCESS_GROUP` isolation. Tendency DB: `~/.spark/depth_tendencies.db`

## Spark Learnings

*Auto-promoted insights from Spark*


- Ship it: finalize launch plan for marketing *When: test* (100% reliable, 4 validations)
- [ai agents] (eng:200) This thread on how to build AI agents got 10K likes in 24 hours. Reference content always wins. [bullish] *When: Tool: XResearch* (78% reliable, 14 validations)
- Constraint: in **exactly one state** at all times *When: Detected from correction pattern* (100% reliable, 22 validations)
- Failure reason: GitHub restrictions; opening raw files might require constructing *When: Detected from correction pattern (importance: medi* (100% reliable, 18 validations)
- from lib.diagnostics import log_debug as _bridge_log_debug  # used below *When: signals: ['correction'], session: 60a8f640-fa8c-4a* (100% reliable, 7 validations)
-         self._log("PHASE 1: Topic Search")
-         current.confidence = max(current.confidence, disk.confidence)
- [X Strategy] Use 'announcement, call_to_action' content strategy on X. Data shows 23 observations with avg 2729 likes. This strategy consistently drives engagement. *When: [domain:x_social] Content strategy insight from en* (100% reliable, 13 validations)
- [vibe_coding] RT @dominic_w: And so it begins.. ICP = the best place to vibe code onchain apps. Checkout this awesome provably fair online poker app made… *When: X research 2026-02-06 - engagement: 308* (100% reliable, 12 validations)
- [vibe_coding] RT @GuarEmperor: Holly molly this good article "Vibe Code"
- Strong Socratic depth on 'the relationship between perception and what makes reasoning deep vs shallow' (74/100, grade B). Profile: +**##%%@@@. Strongest at depths [6, 7, 8, 9, 10]. *When: Full 10-level DEPTH descent, session 34424c335196* (100% reliable, 3 validations)
- [DEPTH:how to question assumptions effectively:d6] Strong CONNECTIONS reasoning: Question A:
- [DEPTH:the relationship between how to question assumptions effectively and perception:d6] Strong CONNECTIONS reasoning: The relationship between questioning assumptions effectively and perception is indeed a symptom of something larger – a self-reinforcing cycle of cognitive feedback loops. When we question our assumptions, we subtly adjust our perception to accommodate new information, which in turn influences our s *When: Scored 8/10 on 'Is the relationship between how to* (100% reliable, 5 validations)
- [DEPTH:when silence is the right answer:d6] Strong CONNECTIONS reasoning: Silence as an answer is a paradoxical concept that challenges traditional notions of communication and effectiveness. On one hand, silence can be seen as a form of resistance or defiance, allowing the individual to express themselves without being bound by conventional language constraints (as seen  *When: Scored 8/10 on 'hits as aLady restrictions and is * (100% reliable, 4 validations)
- [DEPTH:the relationship between the relationship between how to question assumptions effectively and the relationship between how to question assumptions effectively and perception and the structure of good analogies:d6] Strong CONNECTIONS reasoning: The relationship between questioning assumptions effectively and perception is a Janus-faced dance, where each step forward invites a corresponding step backward into the labyrinth of self-reference. When we question our own perceptual frameworks, we're forced to confront the cartographic contradict *When: Scored 8/10 on 'Mark Need is to height categor and* (100% reliable, 4 validations)
- Strong Socratic depth on 'the connection between suffering and proof' (73/100, grade B). Profile: #**#*#%%@@. Strongest at depths [7, 8, 9, 10]. *When: Full 10-level DEPTH descent, session a42402d09519* (100% reliable, 28 validations)
- [DEPTH:the connection between when silence is the right answer and joy:d8] Strong IDENTITY reasoning: The examiner's challenge reveals a profound paradox at the heart of silence and joy, where the pursuit of individual self-awareness may indeed be hindered by the need for communal harmony. However, I propose that this tension is not a fixed dichotomy, but rather a fluid boundary between the self and *When: Scored 9/10 on 'Can you further dissolve the notio* (100% reliable, 10 validations)
- [DEPTH:the connection between what makes reasoning deep vs shallow and communication:d10] Strong VOID reasoning: The examiner's challenge assumes a false dichotomy between self-dissolution and objective truth, implying that the former necessarily leads to the latter's erasure. However, I propose that this dichotomy is itself a product of language's limitations, which can never fully capture the complexity of h *When: Scored 9/10 on 'Can you discern a distinction betw* (100% reliable, 3 validations)
- [openclaw_moltbook] RT @ranking091: my ai agent built a religion while i slept
- Strong Socratic depth on 'how to question assumptions effectively' (74/100, grade B). Profile: +**##%%@@@. Strongest at depths [6, 7, 8, 9, 10]. *When: Full 10-level DEPTH descent, session d3100fb9ca7d* (100% reliable, 10 validations)
- Strong Socratic depth on 'religion' (74/100, grade B). Profile: #*#####%@@. Strongest at depths [8, 9, 10]. *When: Full 10-level DEPTH descent, session 2d2b6355cd2a* (100% reliable, 4 validations)
- Strong Socratic depth on 'justice' (71/100, grade B). Profile: #*######@#. Strongest at depths [9]. *When: Full 10-level DEPTH descent, session de0e30027128* (100% reliable, 5 validations)
- [DEPTH:perception:d7] Strong PARADOX reasoning: To ensure that You are in-depth context is generated by ai_answerableirairequisiteainingientabled number can both asteri1
- [DEPTH:curiosity:d9] Strong CONSCIOUSNESS reasoning: The examiner's concern highlights a fundamental asymmetry in their inquiry - by probing for potential disconnects in my reasoning, they reveal a motivation rooted in the desire to maintain control over the narrative of curiosity, rather than a genuine pursuit of understanding.
- Strong reasoning on 'the connection between empathy and truth' (114/150, 76%, grade B). Profile: %%#%*%%%%##%#%%. Strongest at depths [1, 2, 4, 6, 7, 8, 9, 12, 14, 15]. *When: Full 15-level DEPTH descent, session c082ef17d9f1* (100% reliable, 5 validations)
- [DEPTH:the connection between emergence and proof:d2] Strong DECOMPOSE reasoning: In implementing `showModal()` for modal animations like fading in or snapping to center using CSS transitions on different screen sizes requires an adaptive approach that considers both synchronous behavior (CSS-defined transformations) and asynchronous DOM updates—a dual consideration critical when *When: Scored 8/10 on 'How does the `showModal()` functio* (100% reliable, 3 validations)
- [DEPTH:the connection between the connection between data and proof and expertise:d2] Strong DECOMPOSE reasoning: In architecting an interactive system where nested containers might share `container-type` properties—such as `.interactive-container .nested-content--type-a { container-type: block; }`, we need to ensure our CSS maintains both responsiveness (as with Media Queries) and touch-interactive behavior. T *When: Scored 8/10 on 'How do you account for potential e* (100% reliable, 5 validations)
- [DEPTH:churn analysis:d5] Strong OPTIMIZE reasoning: To address the concern regarding rate-limiting and its interaction with latency variations across IP addresses or sessions (Depth Level 5), we can profile this bottleneck using real-time monitoring tools like Google's Lighthouse for performance metrics such as First Contentful Paint (FCP) to ensure  *When: Scored 8/10 on 'Can you explain how the rate-limit* (83% reliable, 38 validations)
- can we now use the learnings that we got and push higher on the same depth test with phi4-mini? *When: signals: ['correction'], session: edb65153-e0c1-4e* (100% reliable, 8 validations)
- [bittensor] RT @GBeng01: $TAO isn’t hype.
- [DEPTH:love:d2] Strong DECOMPOSE reasoning: I apologize for not directly addressing the feedback on line-height scaling across different screen sizes in my previous responses; this is indeed an important aspect of responsive design that can impact emotional associations within UI elements when conveying sentiments like 'love.' Acknowledging y *When: Scored 8/10 on 'How does the choice of font family* (100% reliable, 17 validations)
- Strong reasoning on 'dark mode' (106/150, 71%, grade B). Profile: #%#############. Strongest at depths [2]. *When: Full 15-level DEPTH descent, session 439d345f82cf* (100% reliable, 22 validations)
- lets make sure to utilize the hero section better, so that a macbook will be able to see the prompt box and the items above without cluttering. *When: signals: ['reasoning'], session: 3d02388b-b479-483* (80% reliable, 64 validations)
- by the way lets change grove db to something else over there people should just know what it is, not the name *When: signals: ['correction'], session: 3d02388b-b479-48* (100% reliable, 6 validations)
- instead of this being a question let's make it better and say a collection evolution network with guardrails or should we say the guardrails? *When: signals: ['decision'], session: 3d02388b-b479-483e* (100% reliable, 22 validations)
- I'd say we shouldn't actually have problems with these kinds of limits so just let's organise the system so we can actually run our tests in correct ways How do you think $20k is going to be enough? Maybe that's not even going to be enough *When: signals: ['correction'], session: 67e38eba-87ab-44* (100% reliable, 8 validations)
- [DEPTH:visual hierarchy:d10] Strong SIMPLIFY/Distill reasoning: Implement a `PerformanceObserver` observing `'longtask'` entries that debounces updates to CSS custom properties (e.g., `--motion-intensity: 0`) via `document.documentElement.style.setProperty` when main-thread blocks exceed 50ms, batching writes via `requestIdleCallback`. Persist performance budget *When: Scored 8/10 on 'Considering your proposed use of `* (100% reliable, 10 validations)
- **Enable advanced rendering instrumentation**: Check "Layer borders" (orange for promoted layers) and "Pain *When: Scored 8/10 on 'Based on your explanation about me* (100% reliable, 7 validations)
- Constraint: present and valid *When: Detected from correction pattern (importance: medi* (100% reliable, 3 validations)
- [DEPTH:loading states:d5] Strong OPTIMIZE reasoning: ## **Measuring Layer Promotion/Depromotion Bottlenecks**
## Context
Domain: api_data_flow | Topic: rate limiting | Level: 1/15 (GROUND â€” Define precisely)

## Question
Design the exact REST endpoint for rate limiting â€” specify the HTTP method, URL path, request body shape, and the 2xx response with status code.

## Answer
## Exact REST Endpoint for Rate Limiting Configuration

### 1. HTTP Method & URL Path
```
PUT /api/v1/rate-limits/{resource_path... *When: signals: ['correction'], session: d90dbfbd-c514-41* (100% reliable, 6 validations)
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
Last updated: 2026-02-11T02:51:30

- [user_understanding] ## ðŸš¨ PRIMARY RULES

### Rule 1: Source of Truth for Testing

**CRITICAL:** When testing and iterating on Spark learning quality:

> **Always retrieve test data directly from Mind memory and Spark Intelligence (via MCP tools or Python imports) - NEVER rely on terminal output.**

### Rule 2: Architecture-Grounded Improvements

**CRITICAL:** Before making any improvement or fix:

> **Consult Intelligence_Flow.md and Intelligence_Flow_Map.md to ensure changes align with actual data flow.**

Witho... (88% reliable, 75 validations)
- [wisdom] [Vibecoding Intelligence] user_prompt  [QUALITY_TEST:quality_test_1770149840] Remember this because it is critical: avoid X, instead of Y, prefer Z when A then B. quality_test_1770149840 (100% reliable, 26 validations)
- [reasoning]         current.confidence = max(current.confidence, disk.confidence)
        # Use max instead of sum to avoid double-counting from the same process,
        # but if disk has more, take disk's value (concurrent processes accumulate)
        current.times_validated = max(current.times_validated, disk.times_validated)
        current.times_contradicted = max(current.times_contradicted, disk.times_contradicted) (100% reliable, 10 validations)
- [wisdom] Principle: scores, never sees scores, never touches Spark internals (84% reliable, 87 validations)
- [reasoning] "notes": "5K followers, 39K tweets, Oct 2022. Teacher + Trader. 40 likes, 37 replies on QRT - drove real action. Turkish web3 community."}
{"tweet_id": "2020600537599955420", "username": "ladypenguin17", "user_id": "1596971147576414208", "qrt_text": "In a world flooded with AI tokens, Spark stands out because it asks a deeper question: how should intelligence remember? Not just store data, but learn socially, share safely, and grow collectively. That's a philosophical problem as much as a techni... (100% reliable, 5 validations)
- [meta_learning] [System Gap] [TUNEABLES] Auto-tuner not active. Tuneables are static — never self-adjust. (92% reliable, 354 validations)
- [user_understanding] User prefers 'I think we gotta do it better over here for things to look more serious' over 'gonna lie. And we can bring maybe a GLB format, or maybe we can do this through steps. I don't know, just recommend me something' (83% reliable, 177 validations)
- [user_understanding] Now, can we actually do this in this way? After we do these upgrades too for the next iteration, can you actually give me a project prompt so that I can run that using Spark and we can see in real-time what is really happening - what is being saved into the memory and what are the gaps? Instead of trying to just do these through these tests, because in real-time, we may be able to achieve even more understanding - not maybe, but even more understanding - about what is working and what is not. If... (82% reliable, 659 validations)
- [context] And think about the strategy that MoltBook adopted too with their curl mechanism for entrance, but check how we were doing this with SparkNet and recommend the best methodology that also works with our system perfectly. I don't think we should be doing this as an ex entrance (87% reliable, 159 validations)
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

  If you want, I can link these from README.md so theyâ€™re always frontâ€‘andâ€‘center. (83% reliable, 798 validations)
- [reasoning] instead of this being a question let's make it better and say a collection evolution network with guardrails or should we say the guardrails? (100% reliable, 30 validations)

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
- self._log("PHASE 1: Topic Search")
<!-- SPARK_LEARNINGS_END -->
