# Glossary and Navigation Hub

Updated: 2026-02-06

This is the central documentation hub.
Use this file to find terms, systems, and the correct source-of-truth doc.

## How To Use

1. Find a term in the glossary section.
2. Open the linked source-of-truth doc.
3. Use `docs/DOCS_INDEX.md` for full active-doc inventory.

## Fast Routing

- Setup and daily ops: `docs/QUICKSTART.md`
- Runtime architecture and stores: `Intelligence_Flow.md`
- Runtime component map: `Intelligence_Flow_Map.md`
- Tuneables and thresholds: `TUNEABLES.md`
- EIDOS loop and control plane: `EIDOS_GUIDE.md`
- Quality gate and outcomes feedback: `META_RALPH.md`
- Semantic retrieval behavior: `SEMANTIC_ADVISOR_DESIGN.md`
- Chips usage and authoring: `docs/CHIPS.md`
- Program execution status: `docs/PROGRAM_STATUS.md`
- Long-range architecture direction: `docs/VISION.md`

## Glossary

- Advisor: Decision-time guidance layer that surfaces learnings before actions. Docs: `SEMANTIC_ADVISOR_DESIGN.md`, `Intelligence_Flow.md`.
- Bridge cycle: Main periodic orchestration pass that processes events and updates learning systems. Docs: `Intelligence_Flow.md`.
- Chips: Domain-specific intelligence modules with triggers, observers, learners, and outcomes. Docs: `docs/CHIPS.md`, `docs/CHIP_WORKFLOW.md`.
- Cognitive insight: Human-useful learning artifact stored with reliability and validation signals. Docs: `Intelligence_Flow.md`, `TUNEABLES.md`.
- Context sync: Selection and publication of high-signal learnings into runtime context files. Docs: `Intelligence_Flow.md`.
- Distillation: Extraction of reusable rules from steps/outcomes. Docs: `EIDOS_GUIDE.md`, `Intelligence_Flow.md`.
- EIDOS: Enforcement loop for action, prediction, outcome, evaluation, distillation, and reuse. Docs: `EIDOS_GUIDE.md`, `EIDOS_QUICKSTART.md`.
- Memory gate: Scoring filter deciding what persists to durable memory. Docs: `TUNEABLES.md`, `EIDOS_GUIDE.md`.
- Meta-Ralph: Quality gate and feedback-adjustment system for learnings. Docs: `META_RALPH.md`.
- Mind bridge: Optional bridge to Mind service with retrieval and sync behavior. Docs: `Intelligence_Flow.md`, `docs/QUICKSTART.md`.
- Outcome loop: Validation path that links actions/advice to measured usefulness and reliability updates. Docs: `META_RALPH.md`, `Intelligence_Flow.md`.
- Pattern detection: Detector stack that identifies corrections, sentiment, repetition, semantics, and why-signals. Docs: `Intelligence_Flow.md`.
- Promotion: Durable publication of proven learnings into persistent context files. Docs: `Intelligence_Flow.md`, `docs/QUICKSTART.md`.
- Queue: Event ingest buffer with overflow handling and logical consume head. Docs: `Intelligence_Flow.md`.
- Semantic retrieval: Meaning-based retrieval and ranking with trigger and outcome-aware fusion. Docs: `SEMANTIC_ADVISOR_DESIGN.md`.
- SPARK_CONTEXT: Runtime context artifact produced from selected learnings. Docs: `Intelligence_Flow.md`.
- Trace ID: Cross-stage linking key for ingest, steps, outcomes, and dashboards. Docs: `Intelligence_Flow.md`.
- Tuneables: Configurable thresholds and weights across the runtime. Docs: `TUNEABLES.md`.

## Active Documentation Tree

Canonical and active docs:
- `README.md`
- `docs/DOCS_INDEX.md`
- `docs/GLOSSARY.md`
- `docs/QUICKSTART.md`
- `Intelligence_Flow.md`
- `Intelligence_Flow_Map.md`
- `TUNEABLES.md`
- `EIDOS_GUIDE.md`
- `EIDOS_QUICKSTART.md`
- `META_RALPH.md`
- `SEMANTIC_ADVISOR_DESIGN.md`
- `docs/CHIPS.md`
- `docs/CHIP_WORKFLOW.md`
- `docs/adapters.md`
- `docs/claude_code.md`
- `docs/cursor.md`
- `docs/PROJECT_INTELLIGENCE.md`
- `docs/PROGRAM_STATUS.md`
- `docs/VISION.md`
- `SPARK_LEARNING_GUIDE.md`
- `STUCK_STATE_PLAYBOOK.md`

Strategic docs intentionally kept active:
- `MoE_Plan.md`
- `Path to AGI.md`
- `EVOLUTION_CHIPS_RESEARCH.md`

Historical docs:
- `docs/archive/`
- `docs/reports/`
