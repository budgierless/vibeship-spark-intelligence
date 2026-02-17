# Selective-AI Tune Loop Report

- Generated (UTC): `2026-02-16 14:50:05`
- Rounds per pass: `120`
- Tuneables backup: `C:\Users\USER\.spark\backups\tuneables.json.selective_loop_20260216_144611.bak`
- Winner: `pass1_warning_1800`

## Pass Results

### pass1_warning_1800
- artifact: `docs\reports\20260216_144611_pass1_warning_1800_selective_loop.json`
- config: authority=`warning`, min_remaining_ms=`1800`, force_programmatic=`True`
- metrics: emitted=4, selective_hits=0, p50=310.3ms, p95=590.5ms, no_emit=103, score=-227.5

### pass2_note_1800
- artifact: `docs\reports\20260216_144733_pass2_note_1800_selective_loop.json`
- config: authority=`note`, min_remaining_ms=`1800`, force_programmatic=`True`
- metrics: emitted=1, selective_hits=0, p50=591.1ms, p95=591.1ms, no_emit=106, score=-277.0

### pass3_note_2400
- artifact: `docs\reports\20260216_144853_pass3_note_2400_selective_loop.json`
- config: authority=`note`, min_remaining_ms=`2400`, force_programmatic=`True`
- metrics: emitted=0, selective_hits=0, p50=0.0ms, p95=0.0ms, no_emit=107, score=-293.5

## Applied Runtime Config

- `force_programmatic_synth=True`
- `selective_ai_synth_enabled=True`
- `selective_ai_min_authority=warning`
- `selective_ai_min_remaining_ms=1800`
