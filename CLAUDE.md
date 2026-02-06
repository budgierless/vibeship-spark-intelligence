

## Spark Learnings

*Auto-promoted insights from Spark*


<!-- SPARK_LEARNINGS_START -->
## Spark Bootstrap
Auto-loaded high-confidence learnings from ~/.spark/cognitive_insights.json
Last updated: 2026-02-06T04:55:09

- [self_awareness] I struggle with Bash fails with permission_denied -> Fix: Check file permissions or run with ele tasks (48% reliable, 3684 validations)
- [self_awareness] I struggle with Bash fails with windows_path -> Fix: Use forward slashes (/) instead of backslas tasks (30% reliable, 1825 validations)
- [self_awareness] I struggle with Bash fails with file_not_found -> Fix: Verify path exists with Read or ls first tasks (28% reliable, 2857 validations)
- [self_awareness] I struggle with Bash fails with syntax_error -> Fix: Check syntax, look for missing quotes or br tasks (25% reliable, 1405 validations)
- [self_awareness] I struggle with Bash fails with json_error -> Fix: Verify JSON format is valid (recovered 100%) tasks (12% reliable, 475 validations)
- [self_awareness] I struggle with Bash fails with command_not_found -> Fix: Check command spelling or install requ tasks (12% reliable, 541 validations)
- [self_awareness] I struggle with Bash fails with connection_error -> Fix: Check if service is running on expected tasks (10% reliable, 473 validations)
- [self_awareness] I struggle with Bash fails with windows_encoding -> Fix: Use ASCII characters or set UTF-8 encod tasks (10% reliable, 472 validations)
- [self_awareness] I struggle with Bash fails with timeout -> Fix: Reduce scope or increase timeout tasks (23% reliable, 1375 validations)
- [context] **Always verify:** Is bridge_worker running? Is the queue being processed?

### Rule 3: Pipeline Health Before Tuning

**CRITICAL:** Before ANY tuning or iteration session:

> **Run `python tests/test_pipeline_health.py` FIRST. Scoring metrics are meaningless if the pipeline isn't operational.**

Session 2 lesson: Meta-Ralph showed 39.4% quality rate, but `learnings_stored=0`. Perfect scoring, broken pipeline = zero learning.

### Rule 4: Anti-Hallucination

**CRITICAL:** Never claim improvement... (94% reliable, 59 validations)
- [user_understanding] Now, can we actually do this in this way? After we do these upgrades too for the next iteration, can you actually give me a project prompt so that I can run that using Spark and we can see in real-time what is really happening - what is being saved into the memory and what are the gaps? Instead of trying to just do these through these tests, because in real-time, we may be able to achieve even more understanding - not maybe, but even more understanding - about what is working and what is not. If... (96% reliable, 222 validations)
- [user_understanding] User prefers 'I think we gotta do it better over here for things to look more serious' over 'gonna lie. And we can bring maybe a GLB format, or maybe we can do this through steps. I don't know, just recommend me something' (77% reliable, 116 validations)

## Project Focus
- Phase: discovery

## Project Questions
- What is the project goal in one sentence?
- How will we know it's complete?
- What could make this fail later?
<!-- SPARK_LEARNINGS_END -->