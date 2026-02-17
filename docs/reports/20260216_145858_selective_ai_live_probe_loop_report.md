# Selective-AI Live Probe Tune Loop Report

- Generated (UTC): `2026-02-16 14:58:58`
- Rounds per pass: `80`
- Tuneables backup: `C:\Users\USER\.spark\backups\tuneables.json.live_probe_loop_20260216_145702.bak`
- Winner: `probe_pass2_note_1400`

## Pass Results

### probe_pass1_warning_1800
- artifact: `docs\reports\20260216_145702_probe_pass1_warning_1800_live_probe_loop.json`
- probe ids: session_prefix=`advisory-liveprobe-probe_pass1_warning_1800`, trace_prefix=`liveprobe-probe_pass1_warning_1800-20260216_145702`
- config: authority=`warning`, min_remaining_ms=`1800`
- metrics: emitted=1, selective_hits=0, programmatic_forced=1, p50=690.0ms, p95=690.0ms, no_emit=56, score=-172.5

### probe_pass2_note_1400
- artifact: `docs\reports\20260216_145741_probe_pass2_note_1400_live_probe_loop.json`
- probe ids: session_prefix=`advisory-liveprobe-probe_pass2_note_1400`, trace_prefix=`liveprobe-probe_pass2_note_1400-20260216_145741`
- config: authority=`note`, min_remaining_ms=`1400`
- metrics: emitted=0, selective_hits=0, programmatic_forced=0, p50=0.0ms, p95=0.0ms, no_emit=50, score=-166.0

### probe_pass3_note_900
- artifact: `docs\reports\20260216_145818_probe_pass3_note_900_live_probe_loop.json`
- probe ids: session_prefix=`advisory-liveprobe-probe_pass3_note_900`, trace_prefix=`liveprobe-probe_pass3_note_900-20260216_145818`
- config: authority=`note`, min_remaining_ms=`900`
- metrics: emitted=0, selective_hits=0, programmatic_forced=0, p50=0.0ms, p95=0.0ms, no_emit=50, score=-166.0

## Applied Runtime Config

- `force_programmatic_synth=True`
- `selective_ai_synth_enabled=True`
- `selective_ai_min_authority=note`
- `selective_ai_min_remaining_ms=1400`
