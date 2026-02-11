# Spark Intelligence — Major Gaps & Closure Plan

Date: 2026-02-12
Mode: Real-use-first
Owners: Meta (product/decisions), Spark (execution), repo maintainers per module

## 0) Current state (honest snapshot)
- Runtime health: core services up (`sparkd`, `bridge_worker`, `mind` when checked).
- Loop status: memory/advisory/feedback loops exist and are active.
- Delivery status: major P0/P1/P2 hardening shipped.
- Quality status: still too many **moderate** outcomes; not consistently at minor.
- Reliability status: semantic memory tooling still degraded in this environment due provider auth gaps.
- Sync status: OpenClaw/export writes succeed; some external targets still error.

---

## 1) Ranked major gaps

## Gap A (P0): Retrieval methodology proof is incomplete
**Symptom**: Hybrid+agentic is now default direction, but strict matched A/B evidence is not fully consolidated.

**Root causes**
- Uneven run conditions across comparisons
- Inconsistent run-time controls/timeouts
- Missing single canonical comparison artifact

**Fixes**
1. Run balanced mini-suite with fixed tasks, fixed iteration count, same model route.
2. Force retrieval mode per run (`semantic_only` vs `hybrid_agentic`) with identical prompts/seeds where possible.
3. Publish one table with run IDs + metrics deltas.

**Acceptance criteria**
- >=10 matched pairs completed
- One canonical report with per-pair and aggregate deltas
- Decision stamped: keep hybrid default or rollback

---

## Gap B (P0): Moderate-severity plateau
**Symptom**: Guardrails reduce collapse but do not consistently lift quality to minor.

**Root causes**
- Refinement objective still too broad
- Failure classes not directly targeted
- Closure pressure on unresolved failures insufficient

**Fixes**
1. Add class-based refine objective buckets:
   - correctness
   - edge handling
   - error semantics
   - concurrency/state consistency
2. Add explicit unresolved-failure closure section to refine prompt.
3. Penalize repeated unsupported decision patterns in scoring.

**Acceptance criteria**
- 3 consecutive validation batches with median severity = minor
- Unsupported decisions <=1 per run median
- Recurrence risk trend downward over 2 days

---

## Gap C (P1): Memory retrieval reliability (auth/provider)
**Symptom**: memory semantic recall and related tooling disabled in current environment.

**Root causes**
- Missing provider credentials in active agent auth store
- No finalized runbook executed end-to-end

**Fixes**
1. Execute auth runbook (`2026-02-12_kimi_auth_enablement_runbook.md`) for chosen provider path.
2. Validate with `openclaw models status --probe` and memory commands.
3. Document known-good provider order/profile policy.

**Acceptance criteria**
- `memory_search` path no longer returns provider-key disabled errors
- `openclaw memory status/index/search` complete successfully
- At least 3 successful semantic recall checks from real prompts

---

## Gap D (P1): Learning stream signal/noise
**Symptom**: residual low-value insight promotions still leak into context/advisory stream.

**Root causes**
- Promotion thresholds still permissive in some branches
- Duplicate/near-duplicate filtering can be tighter

**Fixes**
1. Tighten novelty + utility thresholds before promotion.
2. Add near-duplicate suppression window per cycle.
3. Add periodic quality sampling script for promoted insights.

**Acceptance criteria**
- Low-value sampled rate <10% in 100-item random checks
- Advisory relevance rating improves in checkpoint logs

---

## Gap E (P2): External sync target instability
**Symptom**: repeated errors in some sync targets despite core OpenClaw/export health.

**Root causes**
- Connector-specific auth/state drift
- Insufficient per-target fail-fast downgrade policy

**Fixes**
1. Add target-level health state and suppression after N failures.
2. Separate critical vs optional sync targets in status summaries.
3. Recover/re-auth each connector with explicit runbook.

**Acceptance criteria**
- Erroring optional targets do not degrade core health signal
- <5% failure rate on enabled critical targets

---

## 2) Strict balanced retrieval A/B validation protocol

## Design
- Dataset: fixed task set (same prompts/workload classes)
- Arms: `semantic_only` vs `hybrid_agentic`
- Controls: same provider route, iteration cap, timeout, temperature-equivalent settings
- Pairs: run each task in both arms within short temporal window

## Metrics (required)
- final score
- severity (`minor/moderate/critical`)
- completion status (`confirmed/provisional/failed`)
- recurrence risk
- unsupported decision count
- self-awareness score
- timeout/failure flags

## Statistical policy
- Report per-pair deltas + aggregate median/mean
- Flag confounders (timeouts/provider failures) separately
- Decision rule:
  - Keep hybrid default if aggregate quality lift is positive and stability not worse
  - Else rollback or split by task class

---

## 3) Risk register
| Risk | Impact | Likelihood | Mitigation |
|---|---:|---:|---|
| Provider auth remains missing | High | High | Execute runbook + probe validation immediately |
| Overfitting to guardrails | Medium | Medium | prioritize objective improvements over additional gates |
| Run interruptions/timeouts | Medium | High | use run timeout controls + rerun policy |
| Noisy learning promotions | Medium | Medium | tighten thresholds + sampling audits |
| Connector drift | Medium | Medium | per-target health downgrade and re-auth runbooks |

---

## 4) Execution plan

## Next 24 hours
1. Complete provider auth enablement and probe checks.
2. Run strict A/B mini-suite (at least 10 matched pairs).
3. Ship one targeted refine-objective patch (class-based closure) and re-run mini-suite.
4. Publish consolidated A/B report and go/no-go on retrieval default.

## Next 72 hours
1. Reduce moderate plateau via 2nd targeted patch if needed.
2. Add promotion-noise suppression upgrades.
3. Stabilize/downgrade flaky sync targets and clean status reporting.

## Next 7 days
1. Maintain daily checkpoint KPI reporting.
2. Reach sustained minor-severity median across 3+ batches.
3. Freeze a v1.1 "trustworthy loop" baseline and document rollback hooks.

---

## 5) KPI checkpoint template (copy/paste)

```md
### Spark Checkpoint — <timestamp>
- Health: sparkd=<ok|down>, bridge=<ok|down>, mind=<ok|down>
- Retrieval mode default: <hybrid_agentic|semantic_only>
- A/B status: pairs=<n>, winner=<mode|tie>, confounders=<n>
- Quality: median_score=<x.x>, median_severity=<minor|moderate|critical>
- Completion: confirmed=<n>, provisional=<n>, failed=<n>
- Decisions: unsupported_median=<n>, recurrence_trend=<up|flat|down>
- Memory semantic recall: <ok|blocked> (reason)
- Sync targets: critical_ok=<n>, optional_error=<n>
- Today’s action: <single most important next move>
```

---

## 6) Immediate command pack

```bash
# Auth + model checks
openclaw models status
openclaw models status --probe --probe-provider moonshot
openclaw models set moonshot/kimi-k2.5

# Memory checks (post-auth)
openclaw memory status --deep --agent main
openclaw memory index --agent main --verbose
openclaw memory search "recent advisory quality"

# Retrieval A/B execution (example)
set SPARK_FORGE_RETRIEVAL_MODE=semantic_only
python -m src.spark_forge.cli run ...
set SPARK_FORGE_RETRIEVAL_MODE=hybrid_agentic
python -m src.spark_forge.cli run ...
```
