# Prompt System Execution Plan (2026-02-16)

Owner: Spark operators  
Master index: `docs/reports/PROMPT_SYSTEM_MASTER_LOG.md`  
Primary run log: `docs/reports/2026-02-15_233443_prompt_run_10_2_6.md`

## Objective

Run an autonomous run-improve loop and finish prompt coverage with explicit evidence, decisions, and rollback-safe artifacts.

## Phases

## Phase 1 - Instrumentation Hardening (Status: completed)

Goal:
- Make suppression/synthesis decisions observable in engine logs.

Deliverables:
- `lib/advisory_engine.py` updates:
  - selective AI tuneables wired
  - `gate_reason`, `suppressed_count`, `suppressed_reasons`
  - `synth_policy`
- tests:
  - `tests/test_advisory_dual_path_router.py`

Exit criteria:
- Tests pass and runtime rows include new telemetry fields.

## Phase 2 - Harness Upgrade (Status: completed)

Goal:
- Make controlled-delta outputs directly comparable across synth policy/error outcomes.

Deliverables:
- `scripts/advisory_controlled_delta.py` now emits:
  - `engine.error_codes`
  - `engine.synth_policy_counts`
  - `engine.emitted_synth_policy_counts`

Exit criteria:
- Output JSON contains new fields for each run.

## Phase 3 - 3-Pass Tune Loop (Status: completed)

Goal:
- Execute `run -> improve -> run -> improve -> run` with automatic winner selection and apply best runtime config.

Deliverables:
- runner: `scripts/run_advisory_selective_ai_tune_loop.py`
- pass artifacts:
  - `docs/reports/20260216_144611_pass1_warning_1800_selective_loop.json`
  - `docs/reports/20260216_144733_pass2_note_1800_selective_loop.json`
  - `docs/reports/20260216_144853_pass3_note_2400_selective_loop.json`
- comparison:
  - `docs/reports/20260216_145005_selective_ai_tune_loop_result.json`
  - `docs/reports/20260216_145005_selective_ai_tune_loop_report.md`

Exit criteria:
- Winner selected and applied to `%USERPROFILE%\\.spark\\tuneables.json`.

## Phase 4 - Remaining Prompt Sweep (Status: completed)

Goal:
- Cover prompts #1/#3/#4/#5/#7 with explicit decisions and next steps.

Deliverables:
- `docs/reports/2026-02-16_prompt_sweep_1_3_4_5_7.md`

Exit criteria:
- Prompt coverage table can mark all 10 prompts as invoked.

## Phase 5 - Live-Probe Continuation Hardening (Status: completed)

Goal:
- Remove pass-to-pass scoring contamination in non-benchmark loops and make selective-AI trigger decisions evidence-complete.

Deliverables:
- `scripts/run_advisory_selective_ai_live_probe_loop.py` updates:
  - per-candidate `synthesizer.ai_timeout_s`
  - dedupe reset between passes
  - viability-gated winner selection + conservative fallback reason
- `lib/advisory_engine.py` telemetry updates:
  - `selective_ai_eligible`
  - `remaining_ms_before_synth`
  - `emitted_authorities`
- `scripts/advisory_controlled_delta.py` summary updates:
  - `engine.selective_ai_eligibility`
  - `engine.emitted_authority_counts`
- continuation artifacts:
  - `docs/reports/20260216_152532_selective_ai_live_probe_loop_result.json`
  - `docs/reports/20260216_152700_liveprobe_focus_note1400_gate035_t09.json`
  - `docs/reports/20260216_152830_liveprobe_focus_whisper1200_gate035_t09.json`
  - `docs/reports/20260216_153300_liveprobe_focus_warning1800_gate035_t09.json`

Exit criteria:
- Selective-AI latency risk and authority-trigger conditions are explicitly measured and reflected in a keep/rollback runtime decision.

## Tracking Log

| Time (UTC) | Phase | Update | Evidence |
|---|---|---|---|
| 2026-02-16 14:40 | Phase 1 | Wired selective-AI tuneables + suppression/synth telemetry into advisory engine and added tests. | `lib/advisory_engine.py`, `tests/test_advisory_dual_path_router.py` |
| 2026-02-16 14:42 | Phase 1 | Verified advisory tests and CLI/advisory preference tests. | `tests/test_advisory_dual_path_router.py`, `tests/test_advisory_gate_suppression.py`, `tests/test_advisor_tool_specific_matching.py`, `tests/test_advisory_preferences.py`, `tests/test_cli_advisory.py` |
| 2026-02-16 14:43 | Phase 2 | Upgraded controlled delta summary schema with error-code and synth-policy counters. | `scripts/advisory_controlled_delta.py` |
| 2026-02-16 14:50 | Phase 3 | Completed autonomous 3-pass selective-AI tune loop and auto-applied winner config. | `scripts/run_advisory_selective_ai_tune_loop.py`, `docs/reports/20260216_145005_selective_ai_tune_loop_result.json` |
| 2026-02-16 14:51 | Phase 4 | Completed prompt sweep for #1/#3/#4/#5/#7 and documented keep/cut decisions. | `docs/reports/2026-02-16_prompt_sweep_1_3_4_5_7.md` |
| 2026-02-16 15:14 | Post-phase | Ran non-benchmark live-probe loops and identified scoring blind spots (`global_dedupe_suppressed`, `synth_empty`) in winner selection. | `docs/reports/20260216_145858_selective_ai_live_probe_loop_result.json`, `scripts/run_advisory_selective_ai_live_probe_loop.py` |
| 2026-02-16 15:16 | Post-phase | Ran dedupe-off isolation probe: selective-AI activated, but latency tail exceeded hot-path budget (p95 ~12s). | `docs/reports/20260216_151516_liveprobe_dedupe_off_note035.json` |
| 2026-02-16 15:16 | Post-phase | Restored conservative runtime profile (`warning/1800`, default gate thresholds) and captured rollback backup. | `%USERPROFILE%\\.spark\\tuneables.json`, `%USERPROFILE%\\.spark\\backups\\tuneables.json.post_liveprobe_revert_20260216_191624.bak` |
| 2026-02-16 15:25 | Phase 5 | Hardened live-probe loop fairness (dedupe reset + viable winner policy), reran 3-pass 60-round loop, and applied best viable profile. | `scripts/run_advisory_selective_ai_live_probe_loop.py`, `docs/reports/20260216_152532_selective_ai_live_probe_loop_result.json` |
| 2026-02-16 15:27 | Phase 5 | Added selective eligibility/authority telemetry to controlled delta summary and advisory-engine emitted/synth logs. | `scripts/advisory_controlled_delta.py`, `lib/advisory_engine.py`, `docs/reports/20260216_152700_liveprobe_focus_note1400_gate035_t09.json` |
| 2026-02-16 15:31 | Phase 5 | Ran whisper-authority probe: selective path activated but exceeded latency budget (`p95~4.5s`), then rolled back whisper authority. | `docs/reports/20260216_152830_liveprobe_focus_whisper1200_gate035_t09.json` |
| 2026-02-16 15:33 | Phase 5 | Validated safe-improved profile (`warning/1800`, gate `0.35/0.25`, synth timeout `0.9`) with bounded latency and no selective eligibility in sampled window. | `docs/reports/20260216_153300_liveprobe_focus_warning1800_gate035_t09.json` |
| 2026-02-16 15:37 | Phase 5 | Captured rollback-safe backup after applying safe-improved runtime profile. | `%USERPROFILE%\\.spark\\backups\\tuneables.json.safe_improved_liveprobe_20260216_193719.bak` |
