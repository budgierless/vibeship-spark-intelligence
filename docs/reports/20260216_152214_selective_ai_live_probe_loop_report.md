# Selective-AI Live Probe Tune Loop Report

- Generated (UTC): `2026-02-16 15:22:14`
- Rounds per pass: `60`
- Tuneables backup: `C:\Users\USER\.spark\backups\tuneables.json.live_probe_loop_20260216_152043.bak`
- Winner: `probe_pass1_note_1400_gate050_t12`

## Pass Results

### probe_pass1_note_1400_gate050_t12
- artifact: `docs\reports\20260216_152043_probe_pass1_note_1400_gate050_t12_live_probe_loop.json`
- probe ids: session_prefix=`advisory-liveprobe-probe_pass1_note_1400_gate050_t12`, trace_prefix=`liveprobe-probe_pass1_note_1400_gate050_t12-20260216_152043`
- config: authority=`note`, min_remaining_ms=`1400`, note_threshold=`0.5`, whisper_threshold=`0.35`, ai_timeout_s=`1.2`
- metrics: emitted=0, selective_hits=0, programmatic_forced=0, p50=0.0ms, p95=0.0ms, no_emit=36, score=-122.0

### probe_pass2_note_1400_gate035_t09
- artifact: `docs\reports\20260216_152111_probe_pass2_note_1400_gate035_t09_live_probe_loop.json`
- probe ids: session_prefix=`advisory-liveprobe-probe_pass2_note_1400_gate035_t09`, trace_prefix=`liveprobe-probe_pass2_note_1400_gate035_t09-20260216_152111`
- config: authority=`note`, min_remaining_ms=`1400`, note_threshold=`0.35`, whisper_threshold=`0.25`, ai_timeout_s=`0.9`
- metrics: emitted=1, selective_hits=1, programmatic_forced=0, p50=4551.5ms, p95=4551.5ms, no_emit=4, score=-715.15

### probe_pass3_warning_1800_gate050_t07
- artifact: `docs\reports\20260216_152145_probe_pass3_warning_1800_gate050_t07_live_probe_loop.json`
- probe ids: session_prefix=`advisory-liveprobe-probe_pass3_warning_1800_gate050_t07`, trace_prefix=`liveprobe-probe_pass3_warning_1800_gate050_t07-20260216_152145`
- config: authority=`warning`, min_remaining_ms=`1800`, note_threshold=`0.5`, whisper_threshold=`0.35`, ai_timeout_s=`0.7`
- metrics: emitted=0, selective_hits=0, programmatic_forced=0, p50=0.0ms, p95=0.0ms, no_emit=36, score=-156.0

## Applied Runtime Config

- `force_programmatic_synth=True`
- `selective_ai_synth_enabled=True`
- `selective_ai_min_authority=note`
- `selective_ai_min_remaining_ms=1400`
- `advisory_gate.note_threshold=0.5`
- `advisory_gate.whisper_threshold=0.35`
- `synthesizer.ai_timeout_s=1.2`
