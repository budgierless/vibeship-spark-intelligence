# Selective-AI Live Probe Follow-Up (2026-02-16)

## Objective

Continue autonomous `run -> improve -> run` loop on non-benchmark probe traffic and determine whether selective-AI should be relaxed or kept conservative.

## Runs Executed

## 1) Live Probe Loop (80 rounds/pass)

Runner:
- `python scripts/run_advisory_selective_ai_live_probe_loop.py --rounds 80`

Artifacts:
- `docs/reports/20260216_145702_probe_pass1_warning_1800_live_probe_loop.json`
- `docs/reports/20260216_145741_probe_pass2_note_1400_live_probe_loop.json`
- `docs/reports/20260216_145818_probe_pass3_note_900_live_probe_loop.json`
- `docs/reports/20260216_145858_selective_ai_live_probe_loop_result.json`
- `docs/reports/20260216_145858_selective_ai_live_probe_loop_report.md`

Observed:
- Non-benchmark probe rows generated successfully.
- All candidates had `selective_hits=0`.
- Candidate scoring initially selected `note_1400`, but this was later identified as a scoring artifact because it did not penalize `global_dedupe_suppressed` and `synth_empty`.

## 2) Improved Live Probe Loop (40 rounds/pass, gate-threshold candidates)

Runner:
- `python scripts/run_advisory_selective_ai_live_probe_loop.py --rounds 40 --synth-timeout-s 0.8`

Artifacts:
- `docs/reports/20260216_151037_probe_pass1_note_1400_gate050_live_probe_loop.json`
- `docs/reports/20260216_151056_probe_pass2_note_1400_gate035_live_probe_loop.json`
- `docs/reports/20260216_151117_probe_pass3_note_1100_gate030_live_probe_loop.json`
- `docs/reports/20260216_151422_selective_ai_live_probe_loop_result.json`
- `docs/reports/20260216_151422_selective_ai_live_probe_loop_report.md`

Observed:
- Relaxing gate thresholds removed `AE_GATE_SUPPRESSED`, but did not produce emitted output.
- Events shifted toward:
  - `global_dedupe_suppressed`
  - `synth_empty`
- `emitted=0` for all three candidates.

## 3) Dedupe-Off Isolation Probe

Runner:
- `python scripts/advisory_controlled_delta.py --rounds 40 --label liveprobe_dedupe_off_note035 --session-prefix advisory-liveprobe-dedupeoff-note035 --trace-prefix liveprobe-dedupeoff-note035-<ts> --force-live --prompt-mode vary --tool-input-mode repo --out docs/reports/20260216_151516_liveprobe_dedupe_off_note035.json`
- Env overrides during run:
  - `SPARK_ADVISORY_GLOBAL_DEDUPE=0`
  - `SPARK_ADVISORY_LOW_AUTH_GLOBAL_DEDUPE=0`

Artifact:
- `docs/reports/20260216_151516_liveprobe_dedupe_off_note035.json`

Key result:
- Selective AI finally triggered:
  - `emitted_synth_policy_counts.selective_ai_auto=3`
- But latency tail became unacceptable:
  - `p95_ms=12069.4`
  - `p90_ms=10853.2`

Interpretation:
- Selective-AI path is functionally wired and can trigger.
- Current AI path is too slow for hot-path runtime in this slice.
- Global dedupe and synth-empty behavior heavily shape live-probe outcomes.

## 4) Continuation Loop Hardening + Fair Re-run (60 rounds/pass)

Runner:
- `python scripts/run_advisory_selective_ai_live_probe_loop.py --rounds 60`

Implementation improvements before rerun:
- Added per-candidate `synthesizer.ai_timeout_s` in candidate apply logic.
- Added score penalties for zero-emit profiles and `viable_live_profile` gating.
- Added dedupe-history reset between candidate passes (default), so pass scoring is not contaminated by earlier pass dedupe history.
- Added conservative fallback winner policy when no viable candidate exists.
- Updated default pass-3 candidate profile for future loop runs to `warning/1800 + gate 0.35/0.25 + timeout 0.9`.

Artifacts:
- `docs/reports/20260216_152403_probe_pass1_note_1400_gate050_t12_live_probe_loop.json`
- `docs/reports/20260216_152432_probe_pass2_note_1400_gate035_t09_live_probe_loop.json`
- `docs/reports/20260216_152502_probe_pass3_warning_1800_gate050_t07_live_probe_loop.json`
- `docs/reports/20260216_152532_selective_ai_live_probe_loop_result.json`
- `docs/reports/20260216_152532_selective_ai_live_probe_loop_report.md`

Observed:
- Winner became `probe_pass2_note_1400_gate035_t09` (`best_viable_profile`).
- Tail latency improved materially in this pass (`p95=204.9ms`).
- Selective-AI still did not trigger in winner pass (`selective_hits=0`).

## 5) Selective Eligibility Telemetry + Focused Probes

Instrumentation upgrades:
- `lib/advisory_engine.py`: emitted/synth-empty logs now include:
  - `selective_ai_eligible`
  - `selective_ai_min_authority`
  - `selective_ai_min_remaining_ms`
  - `remaining_ms_before_synth`
  - `emitted_authorities`
- `scripts/advisory_controlled_delta.py` summary now includes:
  - `engine.selective_ai_eligibility`
  - `engine.emitted_authority_counts`

### 5a) Focused note-profile probe

Runner:
- `python scripts/advisory_controlled_delta.py --rounds 80 --label liveprobe_focus_note1400_gate035_t09 --session-prefix advisory-liveprobe-focus-note1400-gate035-t09 --trace-prefix liveprobe-focus-note1400-gate035-t09-20260216 --force-live --prompt-mode vary --tool-input-mode repo --out docs/reports/20260216_152700_liveprobe_focus_note1400_gate035_t09.json`

Artifact:
- `docs/reports/20260216_152700_liveprobe_focus_note1400_gate035_t09.json`

Observed:
- `selective_ai_eligibility.not_eligible=32`
- `emitted_authority_counts.whisper=32`
- `emitted_synth_policy_counts` empty
- Interpretation: emitted authorities were whisper in this window, so note-threshold selective policy was not eligible.

### 5b) Whisper-threshold selective probe (backup/restore guarded)

Temporary runtime override during probe:
- `selective_ai_min_authority=whisper`
- `selective_ai_min_remaining_ms=1200`
- `advisory_gate.note_threshold=0.35`
- `advisory_gate.whisper_threshold=0.25`
- `synthesizer.ai_timeout_s=0.9`

Runner:
- `python scripts/advisory_controlled_delta.py --rounds 80 --label liveprobe_focus_whisper1200_gate035_t09 --session-prefix advisory-liveprobe-focus-whisper1200-gate035-t09 --trace-prefix liveprobe-focus-whisper1200-gate035-t09-20260216 --force-live --prompt-mode vary --tool-input-mode repo --out docs/reports/20260216_152830_liveprobe_focus_whisper1200_gate035_t09.json`

Artifact:
- `docs/reports/20260216_152830_liveprobe_focus_whisper1200_gate035_t09.json`

Observed:
- `selective_ai_eligibility.eligible=38`
- `emitted_synth_policy_counts.selective_ai_auto=1`
- `p95_ms=4520.9`
- Interpretation: selective path activates under whisper policy, but latency remains outside hot-path budget.

### 5c) Conservative selective policy + relaxed gate probe

Runtime profile tested:
- `selective_ai_min_authority=warning`
- `selective_ai_min_remaining_ms=1800`
- `advisory_gate.note_threshold=0.35`
- `advisory_gate.whisper_threshold=0.25`
- `synthesizer.ai_timeout_s=0.9`

Runner:
- `python scripts/advisory_controlled_delta.py --rounds 80 --label liveprobe_focus_warning1800_gate035_t09 --session-prefix advisory-liveprobe-focus-warning1800-gate035-t09 --trace-prefix liveprobe-focus-warning1800-gate035-t09-20260216 --force-live --prompt-mode vary --tool-input-mode repo --out docs/reports/20260216_153300_liveprobe_focus_warning1800_gate035_t09.json`

Artifact:
- `docs/reports/20260216_153300_liveprobe_focus_warning1800_gate035_t09.json`

Observed:
- `emitted=1`
- `selective_ai_eligibility.not_eligible=37`
- `emitted_synth_policy_counts.programmatic_forced=1`
- `p95_ms=606.4`
- Interpretation: gate suppression improves versus strict `note_threshold=0.5`, while selective-AI remains guarded and latency stays bounded.

## Keep / Rollback Decision

Keep:
- Telemetry upgrades (`synth_policy`, `gate_reason`, suppression histogram).
- Controlled delta harness metric upgrades.
- Loop hardening in `scripts/run_advisory_selective_ai_live_probe_loop.py`:
  - dedupe reset between passes
  - viability-gated winner selection
  - conservative fallback winner reason
  - per-candidate synth timeout tuning

Rollback:
- Whisper-authority selective profile (`selective_ai_min_authority=whisper`) due unacceptable tail latency (`p95~4.5s`).

Final active runtime (updated safe-improved profile):
- `force_programmatic_synth=true`
- `selective_ai_synth_enabled=true`
- `selective_ai_min_authority=warning`
- `selective_ai_min_remaining_ms=1800`
- `advisory_gate.note_threshold=0.35`
- `advisory_gate.whisper_threshold=0.25`
- `synthesizer.ai_timeout_s=0.9`

Rollback backup:
- `%USERPROFILE%\\.spark\\backups\\tuneables.json.post_liveprobe_revert_20260216_191624.bak`
- `%USERPROFILE%\\.spark\\backups\\tuneables.json.safe_improved_liveprobe_20260216_193719.bak`

## Next Actions

1. Keep collecting non-benchmark probe/live rows and watch for any natural `selective_ai_auto` events under conservative settings.
2. If AI latency improves (provider/model/runtime), re-run whisper-authority probe and require `p95 < 1500ms` before any authority relaxation.
3. Use new `engine.selective_ai_eligibility` + `engine.emitted_authority_counts` summary fields as mandatory evidence in every selective-policy decision.
