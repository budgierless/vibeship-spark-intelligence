# OpenClaw Emotion-Memory-Intelligence Live Validation

Generated: `2026-02-18T00:55:04.077279+00:00`

## Run status

- Stuck process killed: `PID 124608` (`KILLED_OK`)
- Clean A/B rerun completed across weights: `0.0, 0.1, 0.2, 0.3, 0.4`
- Cases: `91` labeled real-user retrieval cases (`hybrid_agentic`)

## A/B results

| weight | precision@5 | mrr | top1_hit_rate | p95_latency_ms | error_rate | promoted |
|---|---:|---:|---:|---:|---:|---|
| 0.0 | 0.1143 | 0.2756 | 0.2088 | 274 | 0.0000 | false |
| 0.1 | 0.1143 | 0.2756 | 0.2088 | 229 | 0.0000 | false |
| 0.2 | 0.1143 | 0.2756 | 0.2088 | 274 | 0.0000 | false |
| 0.3 | 0.1143 | 0.2756 | 0.2088 | 286 | 0.0000 | false |
| 0.4 | 0.1143 | 0.2756 | 0.2088 | 231 | 0.0000 | false |

Gate policy:
- quality: `mrr` must be strictly above baseline (`0.0`) with no precision/top1 regression
- latency: `p95 <= baseline * 1.15`
- error: `error_rate <= baseline`

Decision:
- Winner under strict gate: `None`
- Recommended default now: `0.15`
- Reason: no weight in {0.0,0.1,0.2,0.3,0.4} passed strict quality-uplift gate; keep canary default
- Rollback: `memory_emotion.enabled=false` or `memory_emotion.advisory_rerank_weight=0.0`

## Live integration checks

1. OpenClaw hook events (`recent 300`)
- sample size: `300`
- hook counts: `{'llm_input': 146, 'llm_output': 147, 'build_integrity': 7}`

2. Queue ingestion from OpenClaw (`recent 300`)
- total queue rows: `300`
- openclaw rows: `220`
- openclaw ratio: `0.7333`
- openclaw kind counts: `{'system': 208, 'message': 3, 'tool': 5, 'command': 4}`

3. Retrieval router emotion fields (`recent 300`)
- rows with emotion routing fields: `52`
- ratio: `0.1733`

## Signal density

- Cognitive insights with `emotion_state`: `0/276` (`0.0`)
- Recent memories with `meta.emotion`: `1/500` (`0.002`)

## Next 3 tasks

1. Backfill emotion_state on top cognitive insights and recent high-value memory rows to increase retrieval signal density.
2. Wire post-tool success/failure reconsolidation to memory confidence updates with explicit evidence deltas.
3. Add automated promotion gate in CI/cron for emotion_state_weight with strict quality/latency/error checks and one-click rollback tuneables.
