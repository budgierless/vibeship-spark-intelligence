# Spark Indirect Advisory Optimization Plan v1

Date: 2026-02-13
Repo: `vibeship-spark-intelligence`

Goal: improve advisory output quality *indirectly* by tightening upstream signal flow, measurement, and retrieval reliability (no net-new product features).

## Current State (What We Now Know)

### 1) "Shadow" meaning (contract)
- "Shadow" is **not** production shadow traffic.
- It is a second benchmark suite: v1 labels (`benchmarks/data/advisory_realism_eval_v1.json`) run alongside the primary v2 labels (`benchmarks/data/advisory_realism_eval_v2.json`) per `benchmarks/data/advisory_realism_operating_contract_v1.json`.
- Shadow fails are currently explained by **label drift**: several cases are `should_emit=false` in v1 but `should_emit=true` in v2, so emitting is counted as "unsolicited" only in v1. See `docs/reports/2026-02-13_shadow_suite_analysis_v1.md`.

Decision already locked (2026-02-12):
- Primary (v2) is blocking; shadow (v1) is non-blocking telemetry. See `docs/reports/2026-02-12_advisory_realism_contract_decision.md`.

### 2) Observer telemetry cleanup
- Observer telemetry-heavy rows were pruned and policy is active (latest local policy: `C:\\Users\\USER\\.spark\\chip_observer_policy.json`).
- This resets the next sessions to be readable for "what actually changed" rather than drowning in noisy observer rows.

### 3) Advisory repetition measurement fix (today)
- `scripts/advisory_controlled_delta.py` previously window-filtered `~/.spark/advice_feedback_requests.jsonl` using `ts`, but those rows are timestamped with `created_at`.
- Fixed to accept `ts`/`created_at`/`timestamp` so A/B summaries actually populate.

### 4) Key advisory driver that remains
- The "repeat cooldown" only catches **exact** text (after lowercase + whitespace normalization). Semantically-similar variants ("Read before Edit" phrased 10 ways) bypass the cooldown.
- That's why cooldown changes help a bit but don't eliminate perceived repetition.

### 5) Retrieval gates are a real upstream bottleneck
- On the 20-case real-user retrieval set (2026-02-12), strict gates collapsed `hybrid` and `hybrid_agentic` to `non_empty_rate=0.0`, making embeddings-only "win" by default. See `docs/reports/2026-02-12_memory_retrieval_ab_real_user_scorecard.md`.
- With gates relaxed, `hybrid_agentic` produced a large MRR lift (quality win) with a latency tradeoff.

## Recommended Benchmark Sequence (Today)

Principle: tune the "evidence plumbing" before touching advisory policies further.

### A) Memory retrieval gate tuning (A/B/C/D)
Why: advisory quality depends on having *any* relevant memory in the bundle; strict gates currently zero out hybrid paths on real-user cases.

Dataset:
- `benchmarks/data/memory_retrieval_eval_real_user_2026_02_12.json` (20 cases)

Run matrix (same command, only thresholds differ):
1. A (current strict): establish baseline collapse behavior.
2. B (fully open): establish ceiling quality (already shown as strong).
3. C (moderate): find smallest relaxation that avoids `non_empty_rate=0` for hybrid/hybrid_agentic.
4. D (moderate+): trade precision for recall until non-empty is stable without exploding false positives.

Command template:
```bash
python benchmarks/memory_retrieval_ab.py ^
  --cases benchmarks/data/memory_retrieval_eval_real_user_2026_02_12.json ^
  --systems embeddings_only,hybrid,hybrid_agentic ^
  --top-k 5 ^
  --strict-labels ^
  --min-similarity <X> ^
  --min-fusion-score <Y> ^
  --out-prefix memory_retrieval_ab_real_user_gate_sweep_<label>
```

Success criteria:
- `hybrid_agentic.non_empty_rate >= 0.95` (no "silent empty" failures)
- MRR improves over embeddings-only, with p95 latency remaining acceptable for your workflow budget.

Results (2026-02-13 gate sweep, 20 cases):
- Strict (current tuneables: `min_similarity=0.58`, `min_fusion_score=0.5`): `hybrid_agentic` MRR `0.275`, p95 `101ms`.
- Open (`0.0/0.0`): `hybrid_agentic` MRR `0.3517`, p95 `211ms`.
- Relaxed (`0.2/0.1`): MRR `0.275`, p95 `98ms` (no meaningful lift vs strict).
- Very relaxed (`0.1/0.05`): MRR `0.2083` (worse).

Interpretation:
- "Open" improves retrieval ranking on this dataset but appears to introduce enough noise to hurt downstream advisory value (see contract A/B below).

### B) Advisory controlled-delta repeat suppression (A/B/C/D)
Why: we want "speak less, but don't miss critical guidance", and we need a repeat metric that reflects *perceived* repetition.

Current tuned live cooldowns (B profile) in `~/.spark/tuneables.json`:
- `advisory_engine.advisory_text_repeat_cooldown_s=9000`
- `advisory_gate.tool_cooldown_s=150`
- `advisory_gate.advice_repeat_cooldown_s=5400`

Completed A/B/C/D (2026-02-13):
- Summary: `docs/reports/2026-02-13_advisory_repeat_abcd_controlled_delta_v1.md`
- Runs:
  - A: `docs/reports/advisory_repeat_abcd_A_baseline_current.json`
  - B: `docs/reports/advisory_repeat_abcd_B_min_rank_0p55.json`
  - C: `docs/reports/advisory_repeat_abcd_C_max_items_3.json`
  - D: `docs/reports/advisory_repeat_abcd_D_min_rank_0p55_max_items_3.json`

Winner (by lowest `feedback_top_share` in this harness):
- D: set `advisor.min_rank_score=0.55` and `advisor.max_items=3` (and mirror `advisor.max_advice_items=3`).

Contract safety check for D (2026-02-13, baseline profile, repeats=1, force-live):
- PRIMARY: PASS, objective `0.8299`, high_value `72.22%`, theory_disc `88.89%`, trace `94.44%`.
  - `benchmarks/out/advisory_realism_primary_repeatD_20260213_report.json`

### C) Advisory realism contract (primary only for blocking)
Why: ensure no regression in high-value, theory discrimination, trace binding while we tune upstream.

Run:
```bash
python scripts/run_advisory_realism_contract.py --run-timeout-s 1200
```

Interpretation:
- Block on PRIMARY (v2) only.
- Track SHADOW (v1) as a strict-suppress sentinel, not a target.

Results (2026-02-13 semantic A/B, `profiles=baseline`, `repeats=1`, `force-live=true`):
- Semantic strict (current): PRIMARY objective `0.8266`, high_value `66.67%` (PASS).
  - `benchmarks/out/advisory_realism_primary_semA_strict_20260213_report.json`
- Semantic open (`semantic.min_similarity=0.0`, `semantic.min_fusion_score=0.0`): PRIMARY objective `0.8016`, high_value `55.56%` (PASS but worse).
  - `benchmarks/out/advisory_realism_primary_semB_open_20260213_report.json`

Recommendation from this evidence:
- Keep semantic gates at current strict values for now; don't open them globally without an additional precision mechanism.

### D) Chip learning diagnostics window refresh
Why: verify the observer prune/policy change didn't accidentally remove all learning signal.

Run:
```bash
python scripts/run_chip_learning_diagnostics.py --limit-per-chip 220 --active-only --project-path "C:\\Users\\USER\\Desktop\\vibeship-spark-intelligence" --max-age-days 14 --observer-limit 25 --out-prefix chip_learning_diagnostics_active_observer_today_v1
```

Success criteria:
- merge-eligible stays non-zero
- statement yield is not trending down across windows

## Concrete Recommendations (What To Optimize Next)

1. Fix retrieval gate collapse first (memory retrieval gate sweep). This improves advisory by giving it better evidence to work with.
2. Keep shadow suite as non-blocking; don't chase it unless product direction changes to "strict suppress".
3. After retrieval is stable, revisit advisory repetition via *text fingerprint normalization* (this is an optimization to an existing mechanism, not a new subsystem).
