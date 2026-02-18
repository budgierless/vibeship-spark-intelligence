# Memory Actionability Framework (v1)

## Goal
Improve downstream distillation and transformation quality by storing memories in type-specific actionable form.

## Core Idea
Not every memory should be captured the same way. We classify each memory into a type and attach a lightweight actionability profile.

## Memory types
- failure
- success
- improvement
- frustration
- breakthrough
- general

## Required profile behavior
Each memory stores:
- `memory_type`
- `outcome_quality`
- `actionability_profile` with fields tuned to type

Examples:
- Failure -> trigger signal, root cause hint, next fix step, reuse conditions
- Success -> situation, approach, why it worked, reuse conditions
- Improvement -> current gap, candidate upgrade, expected impact
- Frustration -> pain signal, blocker type, stabilizer
- Breakthrough -> unlock signal, transferable principle

## Why this helps
- Distillation gets richer context before transformation.
- Transformation outputs become more advisory-usable.
- Retrieval can rank by both emotional salience and practical reusability.

## Next upgrades
1. Add memory completeness scoring before distillation.
2. Add per-type validation checks in transformation stage.
3. Add recursive quality loop: memory -> distillation -> transformation -> quality feedback -> template tuning.
