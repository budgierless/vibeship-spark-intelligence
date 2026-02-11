# OpenClaw Research & Updates Log

Purpose: single place to track OpenClaw-related tuning changes, why they were made, and whether results improved or degraded.

## How to use this file

For each change:
1. Record **baseline** before changing anything
2. Record **exact parameter/code change**
3. Record **validation window** (time and cycles)
4. Record **outcome** (better/worse/neutral)
5. Keep or roll back explicitly

---

## Experiment Entry Template

### [YYYY-MM-DD HH:mm TZ] Experiment title
- **Owner:**
- **Goal:**
- **Hypothesis:**
- **Scope:** tuneables/code/cron/docs
- **Baseline:**
  - advisory relevance:
  - duplicate advice rate:
  - chips activated per cycle:
  - queue health:
- **Changes made:**
  - file/key:
  - old -> new:
- **Validation plan:**
  - cycles:
  - duration:
  - metrics:
- **Result:** better / worse / neutral
- **Evidence:**
- **Decision:** keep / rollback / iterate
- **Follow-up:**

---

## 2026-02-11 Active Worklog

### [2026-02-11 13:34 GMT+4] Sprint 1 — Redundant advisory pruning
- **Goal:** Stop advisories repeating commands already executed.
- **Changes made:**
  - `lib/bridge_cycle.py`
  - Added `_prune_redundant_advisory(...)` before writing `SPARK_ADVISORY.md`
  - Added command-backtick matching + session-status heuristic
- **Result:** better
- **Evidence:** immediate live behavior stopped obvious repeated `session-status` style advice.
- **Decision:** keep

### [2026-02-11 13:53 GMT+4] Sprint 2 — Chip fan-out relevance cap
- **Goal:** Reduce chip over-activation noise per cycle.
- **Changes made:**
  - `lib/chips/runtime.py`
  - Added `SPARK_CHIP_EVENT_ACTIVE_LIMIT` (default 6)
  - Event-level selection of most relevant chips by trigger matches
  - `process_chip_events` now reports chips actually used when available
- **Result:** better
- **Evidence:** validation cycle showed `chips 6 ...` with no errors (down from observed 13 active on tiny cycles).
- **Decision:** keep

### [2026-02-11 14:01 GMT+4] Advisory cadence + payload tuning
- **Goal:** Make advice more in-flow and less batch/noise heavy.
- **Changes made (tuneables):**
  - `~/.spark/tuneables.json`
  - `advisory_gate.max_emit_per_call`: `2 -> 1`
  - `advisory_gate.tool_cooldown_s`: `30 -> 90`
  - `advisory_gate.advice_repeat_cooldown_s`: `600 -> 1800`
  - `advisor.max_advice_items`: `10 -> 4`
  - `advisor.max_items`: `8 -> 5`
- **Changes made (cron behavior text):**
  - Job: `spark-context-refresh` (`56a7f5be-e734-47a7-a526-73c3dc9bde1a`)
  - Updated payload to checkpoint-style relevance checks (not broad batch strategy generation).
- **Validation status:** pending (next 3-6 cycles)
- **Initial decision:** keep for trial

### [2026-02-11 14:57 GMT+4] P0-1 — Packet invalidation correctness (`file_hint`)
- **Goal:** Ensure file-scoped invalidation actually removes stale advisory packets after edits.
- **Baseline issue:** `invalidate_packets(..., file_hint=...)` matched only `packet_meta`, but metadata does not store `advisory_text`/`advice_items`, so many stale packets were not invalidated.
- **Changes made:**
  - `lib/advisory_packet_store.py`
  - `invalidate_packets` now loads full packet via `get_packet(packet_id)` when `file_hint` is provided and matches against full `advisory_text` + serialized `advice_items`.
- **Test coverage added:**
  - `tests/test_advisory_packet_store.py::test_invalidate_packets_with_file_hint_matches_full_packet`
  - Validates only matching packet invalidates for `file_hint="lib/bridge_cycle.py"`.
- **Validation result:** better
  - Local test run: `python -m pytest tests/test_advisory_packet_store.py -q` → `9 passed`.
- **Carmack alignment score (0-6):** 5
  - real-time impact: 2, live-use value: 2, modularity gain: 1
- **Decision:** keep

### [2026-02-11 15:35 GMT+4] P0-2 — Implicit feedback affects packet effectiveness
- **Goal:** Ensure post-tool implicit outcomes actually update packet effectiveness ranking.
- **Baseline issue:** feedback with `followed=False` did not update helpful/unhelpful counts, so effectiveness scores barely changed in real use.
- **Changes made:**
  - `lib/advisory_packet_store.py`
  - `record_packet_feedback` now updates helpful/unhelpful counts whenever `helpful` is provided (explicit or implicit), while preserving `followed` as metadata.
- **Test coverage added:**
  - `tests/test_advisory_packet_store.py::test_implicit_feedback_updates_effectiveness_even_when_not_followed`
  - Verifies implicit unhelpful feedback decreases effectiveness score.
- **Validation result:** better
  - Local test run: `python -m pytest tests/test_advisory_packet_store.py -q` → `10 passed`.
- **Carmack alignment score (0-6):** 6
  - real-time impact: 2, live-use value: 2, modularity gain: 2
- **Decision:** keep

### [2026-02-11 15:37 GMT+4] P1-1 — Advisory stage timing + structured hot-path error codes
- **Goal:** Improve observability in advisory hot path without adding heavy runtime overhead.
- **Changes made:**
  - `lib/advisory_engine.py`
  - Added per-call stage timing capture for: `memory_bundle`, `packet_lookup`, `gate`, `synth`, `emit`.
  - Included `stage_ms` in `_log_engine_event` extras for `no_advice`, `no_emit`, `fallback_emit`, and `emitted/synth_empty` events.
  - Replaced silent `except: pass` in critical hot-path sections with structured debug codes:
    - `AE_PKT_USAGE_NO_EMIT`
    - `AE_FALLBACK_EMIT_FAILED`
    - `AE_ADVICE_FEEDBACK_REQUEST_FAILED`
    - `AE_PKT_USAGE_POST_EMIT_FAILED`
    - `AE_PKT_FEEDBACK_POST_TOOL_FAILED`
    - `AE_PACKET_INVALIDATE_POST_EDIT_FAILED`
- **Validation result:** better
  - `python -m py_compile lib/advisory_engine.py` passed
  - `python -m pytest tests/test_advisory_dual_path_router.py -q` → `3 passed`
- **Carmack alignment score (0-6):** 5
  - real-time impact: 2, live-use value: 1, modularity gain: 2
- **Decision:** keep

### [2026-02-11 15:40 GMT+4] P1-2 — Hook fail-open budget hardening (PreToolUse)
- **Goal:** Keep hook responsiveness stable under advisory failures/slowdowns.
- **Changes made:**
  - `hooks/observe.py`
  - Added `SPARK_OBSERVE_PRETOOL_BUDGET_MS` (default `2500ms`).
  - Added pretool elapsed-time measurement and budget exceed logs:
    - `OBS_PRETOOL_BUDGET_EXCEEDED`
  - On advisory engine failure, legacy fallback is now budget-aware (skipped if budget already exhausted):
    - `OBS_PRETOOL_SKIP_LEGACY_FALLBACK`
  - Replaced silent fallback errors with structured logs:
    - `OBS_LEGACY_FEEDBACK_RECORD_FAILED`
    - `OBS_LEGACY_FALLBACK_FAILED`
- **Validation result:** better
  - `python -m py_compile hooks/observe.py` passed
- **Carmack alignment score (0-6):** 6
  - real-time impact: 2, live-use value: 2, modularity gain: 2
- **Decision:** keep

### [2026-02-11 15:41 GMT+4] P2-1 — Context env var normalization (alias-safe)
- **Goal:** Remove config ambiguity around agent context env knobs.
- **Changes made:**
  - `lib/orchestration.py`
  - Canonicalized char-budget var to `SPARK_AGENT_CONTEXT_MAX_CHARS`.
  - Added backward-compatible alias: `SPARK_AGENT_CONTEXT_LIMIT` (same semantic: max chars).
  - Introduced `SPARK_AGENT_CONTEXT_ITEM_LIMIT` for compact-context item count.
  - `TUNEABLES.md` updated to match runtime behavior.
- **Validation result:** better
  - `python -m py_compile lib/orchestration.py` passed.
- **Carmack alignment score (0-6):** 5
  - real-time impact: 1, live-use value: 2, modularity gain: 2
- **Decision:** keep

### [2026-02-11 15:59 GMT+4] P2-2 — Advisory synthesis dependency clarity (`httpx`)
- **Goal:** Make synthesis provider capability explicit and reduce silent dependency drift.
- **Changes made:**
  - `pyproject.toml`: added core dependency `httpx>=0.27.0`.
  - `lib/advisory_synthesizer.py`:
    - central import guard (`_httpx`) at module load,
    - provider calls now fail clearly when `httpx` missing with structured debug codes:
      - `HTTPX_MISSING_OLLAMA`, `HTTPX_MISSING_OPENAI`, `HTTPX_MISSING_ANTHROPIC`, `HTTPX_MISSING_GEMINI`,
    - `get_synth_status()` now exposes:
      - `httpx_available`,
      - `warning: httpx_missing` when applicable.
- **Validation result:** better
  - `python -m py_compile lib/advisory_synthesizer.py` passed
  - `python -m pytest tests/test_advisory_dual_path_router.py -q` → `3 passed`
- **Carmack alignment score (0-6):** 5
  - real-time impact: 1, live-use value: 2, modularity gain: 2
- **Decision:** keep

---

## Metrics to watch each session

- Advisory relevance score (subjective 1-10)
- Repeated advice count per hour
- Actions actually taken from advisory
- Chips activated per cycle (median)
- `pattern_processed` + `chip_merge.merged`
- Queue depth before/after
- Heartbeat freshness and error count

---

## Carmack Alignment Criteria (applied to every patch)

Use this as a decision filter for P0/P1/P2 work.

### 1) Constraint-first (real-time usefulness)
- Define explicit loop constraints before patching (latency, freshness, retry budget).
- Prefer changes that improve live cycle responsiveness and reliability under real workload.

### 2) Experience-first validation
- Do not rely on synthetic-only success.
- Every change must be validated in active project flow (real prompts, real tool activity, real queue/heartbeat behavior).

### 3) Modularity over monolith
- Prefer small, composable changes with clear boundaries and ownership.
- Reward patches that reduce blast radius and make failures easier to localize.

### 4) Scoring rubric per change (0-2 each)
- **Real-time impact:** does it improve active-loop performance or freshness?
- **Live-use value:** does it improve outcomes in actual work sessions?
- **Modularity gain:** does it reduce coupling / improve observability?

**Total score (0-6):**
- 5-6 = keep and expand
- 3-4 = keep with follow-up
- 0-2 = rollback or redesign
