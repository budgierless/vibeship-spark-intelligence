# Selective-AI Live Probe Tune Loop Report

- Generated (UTC): `2026-02-16 15:14:22`
- Rounds per pass: `40`
- Tuneables backup: `C:\Users\USER\.spark\backups\tuneables.json.live_probe_loop_20260216_151037.bak`
- Winner: `probe_pass2_note_1400_gate035`

## Pass Results

### probe_pass1_note_1400_gate050
- artifact: `docs\reports\20260216_151037_probe_pass1_note_1400_gate050_live_probe_loop.json`
- probe ids: session_prefix=`advisory-liveprobe-probe_pass1_note_1400_gate050`, trace_prefix=`liveprobe-probe_pass1_note_1400_gate050-20260216_151037`
- config: authority=`note`, min_remaining_ms=`1400`, note_threshold=`0.5`, whisper_threshold=`0.35`
- metrics: emitted=0, selective_hits=0, programmatic_forced=0, p50=0.0ms, p95=0.0ms, no_emit=25, score=-85.0

### probe_pass2_note_1400_gate035
- artifact: `docs\reports\20260216_151056_probe_pass2_note_1400_gate035_live_probe_loop.json`
- probe ids: session_prefix=`advisory-liveprobe-probe_pass2_note_1400_gate035`, trace_prefix=`liveprobe-probe_pass2_note_1400_gate035-20260216_151056`
- config: authority=`note`, min_remaining_ms=`1400`, note_threshold=`0.35`, whisper_threshold=`0.25`
- metrics: emitted=0, selective_hits=0, programmatic_forced=0, p50=0.0ms, p95=0.0ms, no_emit=0, score=-10.0

### probe_pass3_note_1100_gate030
- artifact: `docs\reports\20260216_151117_probe_pass3_note_1100_gate030_live_probe_loop.json`
- probe ids: session_prefix=`advisory-liveprobe-probe_pass3_note_1100_gate030`, trace_prefix=`liveprobe-probe_pass3_note_1100_gate030-20260216_151117`
- config: authority=`note`, min_remaining_ms=`1100`, note_threshold=`0.3`, whisper_threshold=`0.2`
- metrics: emitted=0, selective_hits=0, programmatic_forced=0, p50=0.0ms, p95=0.0ms, no_emit=0, score=-10.0

## Applied Runtime Config

- `force_programmatic_synth=True`
- `selective_ai_synth_enabled=True`
- `selective_ai_min_authority=note`
- `selective_ai_min_remaining_ms=1400`
- `advisory_gate.note_threshold=0.35`
- `advisory_gate.whisper_threshold=0.25`
