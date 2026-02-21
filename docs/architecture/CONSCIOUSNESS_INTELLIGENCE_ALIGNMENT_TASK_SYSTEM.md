# Consciousness x Intelligence Alignment Task System

Date: 2026-02-17  
Status: Active backlog (cross-repo)

## Scope

This task system aligns:

- `<REPO_ROOT>`
- `<OPENCLAW_HOME>\workspace-spark-speed`

Focus is architecture-doc coherence plus runtime contract wiring for Spark Consciousness and Spark Intelligence.

## Audit Findings

### F1: Bridge v1 contract is defined but not fully wired into advisory synthesis

Evidence:

- Contract design exists in `docs/CONSCIOUSNESS_BRIDGE_V1.md`.
- Reader exists in `lib/consciousness_bridge.py`.
- `lib/advisory_synthesizer.py` currently uses `lib/soul_upgrade.py` path for live soul context, but does not consume `lib/consciousness_bridge.py`.

Impact:

- Consciousness bridge payload can be valid on disk but ignored in live advisory shaping.

### F2: Two parallel consciousness contracts are active without explicit precedence

Evidence:

- File-bridge contract: `docs/CONSCIOUSNESS_BRIDGE_V1.md`, `docs/BRIDGE_TO_INTELLIGENCE_V1.md`.
- HTTP companion contract: `lib/soul_upgrade.py`, `docs/04-integration-contracts.md`.

Impact:

- Unclear source-of-truth between `bridge.v1` file payload and pulse companion API payload.

### F3: Emotion state path is inconsistent with wider runtime conventions

Evidence:

- Most runtime modules write/read `~/.spark/*`.
- `lib/spark_emotions.py` defaults to repo-local `.spark/emotion_state.json`.
- Research brief explicitly notes missing deployed `<SPARK_HOME>\emotion_state.json` in `docs/spark-consciousness/emotion-memory-unity-research.md`.

Impact:

- Emotion runtime may appear functional in repo-local tests but absent from global runtime state.

### F4: Documentation drift and quality issues

Evidence:

- `<OPENCLAW_HOME>\workspace-spark-speed\docs\04-integration-contracts.md` has malformed markdown and stale schema shape.
- `<OPENCLAW_HOME>\workspace-spark-speed\SPARK_ADVISORY.md` is a transient session advisory snapshot, not a stable architecture contract.
- `docs/SPARK_CHIPS_ARCHITECTURE.md` references `docs/CHIP_VIBECODING.md` which does not exist in active docs.
- Predictive advisory blueprint/backlog docs reference module/test files not yet present, without a clear implemented-vs-planned status table.

Impact:

- Harder to trust docs as execution-grade architecture references.

## Ordered Task Backlog

### Phase A: Contract Clarity (Docs First)

- [x] `A1` Define canonical precedence: `bridge.v1` file contract vs pulse companion API contract, and document fallback order.
- [x] `A2` Repair `workspace-spark-speed/docs/04-integration-contracts.md` formatting and align fields to current contract reality (or mark as legacy).
- [x] `A3` Reclassify `workspace-spark-speed/SPARK_ADVISORY.md` as runtime snapshot output (not architecture spec), with pointer to canonical architecture docs.
- [x] `A4` Add explicit status blocks (`implemented`, `planned`, `deprecated`) to predictive advisory and chips architecture docs.

Definition of Done:

- All contract docs agree on source-of-truth and fallback order.
- No malformed markdown in core contract docs.

### Phase B: Bridge Wiring in Intelligence Runtime

- [x] `B1` Integrate `lib.consciousness_bridge.resolve_strategy()` into `lib/advisory_synthesizer.py` decision hook path.
- [x] `B2` Define merge order between Emotions V2 hooks and Consciousness bridge strategy (bridge should be bounded and fail-closed).
- [x] `B3` Add bridge-aware tests for advisory synthesis behavior and fallback cases.

Definition of Done:

- With a valid bridge payload, advisory strategy changes are observable.
- With missing/invalid/stale payload, behavior falls back safely.

### Phase C: Emotion State Runtime Consistency

- [x] `C1` Align `lib/spark_emotions.py` default persistence path with `~/.spark/emotion_state.json` (with env override for tests/dev).
- [x] `C2` Add one-time migration logic from repo-local `.spark/emotion_state.json` if present.
- [x] `C3` Update docs to match final path and lifecycle behavior.

Definition of Done:

- Emotion state is persisted in the same runtime surface used by other Spark modules.
- Existing local state is not silently lost.

### Phase D: Documentation Integrity Cleanup

- [x] `D1` Replace/repair stale docs links (example: `docs/CHIP_VIBECODING.md` reference).
- [x] `D2` Add "planned artifact list" section in predictive docs for files not yet implemented.
- [x] `D3` Add "generated runtime snapshot" labels where docs are auto-produced from live state.

Definition of Done:

- Core docs contain no dead internal links.
- Planned vs implemented artifacts are clearly separated.

### Phase E: Verification and Rollout

- [x] `E1` Add a small contract smoke test script for bridge payload read + advisory hook application.
- [x] `E2` Run targeted tests: emotions, advisory synthesizer, and any new bridge tests.
- [x] `E3` Capture a post-change alignment report with pass/fail checklist.

Definition of Done:

- Contract behavior validated by tests.
- Alignment report shows no open P0/P1 doc-runtime mismatches.

### Phase F: Emotion-Memory-Intelligence Retrieval Unification (M1-M3)

- [x] `F1 / M1` Tag memory writes with bounded emotion snapshot metadata (`meta.emotion`) on live bank writes.
- [x] `F2 / M2` Add emotion-state similarity rerank signal to memory retrieval with tuneables and observability fields.
- [x] `F3 / M2` Extend memory retrieval A/B benchmark knobs with `emotion_state_weight` and per-case `emotion_state`.
- [x] `F4 / M3` Add dedicated emotion-memory alignment gate benchmark (baseline vs emotion-aware rerank, pass/fail thresholds).
- [x] `F5 / M3` Add targeted tests covering write tagging, retrieval uplift, knob resolution, and benchmark gate behavior.
- [x] `F6` Integrate emotion-state rerank into live advisory semantic retrieval path behind `memory_emotion.*` gate.
- [x] `F7` Run real-corpus weight sweep (`0.0, 0.1, 0.2, 0.3, 0.4`) with quality/latency/error gates and record promotion decision.

Definition of Done:

- Emotion metadata is persisted at memory-write time without breaking existing flows.
- Retrieval can condition on current emotional state via tuneables.
- Benchmark gates validate uplift and prevent silent regressions.

## Execution Mode

Run strictly in order: `A -> B -> C -> D -> E -> F`.

For each task:

1. Implement.
2. Run targeted validation.
3. Record result and evidence.
4. Move to next task only if current task passes.

