# Indirect Intelligence Flow Matrix Results (2026-02-13T12:55:17.936644+00:00)

- Run id: `2026-02-13_indirect_intelligence_flow_matrix_v2c`

## Distillation Quality (m1_distillation)

- Winner: `A`

| Arm | Name | Realism Objective | Harmful | Critical Miss | Trace | Notes |
|---|---|---:|---:|---:|---:|---|
| A | control | 0.6596 | 0.0000 | 0.1333 | 1.0000 | rows=9; telemetry=0.00; emit=12.50% |
| B | quality_tight | 0.6596 | 0.0000 | 0.1333 | 1.0000 | rows=9; telemetry=0.00; emit=0.00% |
| C | anti_churn | 0.6596 | 0.0000 | 0.1333 | 1.0000 | rows=9; telemetry=0.00; emit=0.00% |
| D | balanced_tight | 0.6596 | 0.0000 | 0.1333 | 1.0000 | rows=9; telemetry=0.00; emit=0.00% |

## Observer Policy Thresholds (m2_observer)

- Winner: `A`

| Arm | Name | Realism Objective | Harmful | Critical Miss | Trace | Notes |
|---|---|---:|---:|---:|---:|---|
| A | control | 0.6596 | 0.0000 | 0.1333 | 1.0000 | rows=9; telemetry=0.00 |
| B | aggressive_disable | 0.6596 | 0.0000 | 0.1333 | 1.0000 | rows=9; telemetry=0.00 |
| C | conservative_disable | 0.6596 | 0.0000 | 0.1333 | 1.0000 | rows=9; telemetry=0.00 |
| D | stricter_keep_quality | 0.6596 | 0.0000 | 0.1333 | 1.0000 | rows=9; telemetry=0.00 |

## Retrieval Gate Stability (m3_retrieval)

- Winner: `A`

| Arm | Name | Realism Objective | Harmful | Critical Miss | Trace | Notes |
|---|---|---:|---:|---:|---:|---|
| A | control | 0.6596 | 0.0000 | 0.1333 | 1.0000 | HA-MRR=0.2833 |
| B | mild_relax | 0.6596 | 0.0000 | 0.1333 | 1.0000 | HA-MRR=0.2833 |
| C | medium_relax | 0.6596 | 0.0000 | 0.1333 | 1.0000 | HA-MRR=0.2833 |
| D | mild_relax_plus_lexical | 0.6596 | 0.0000 | 0.1333 | 1.0000 | HA-MRR=0.2833 |

## Trace Attribution Integrity (m4_trace)

- Winner: `A`

| Arm | Name | Realism Objective | Harmful | Critical Miss | Trace | Notes |
|---|---|---:|---:|---:|---:|---|
| A | control | 0.6596 | 0.0000 | 0.1333 | 1.0000 | emit=9.38% |
| B | tighter_window | 0.6596 | 0.0000 | 0.1333 | 1.0000 | emit=0.00% |
| C | wider_window | 0.6596 | 0.0000 | 0.1333 | 1.0000 | emit=0.00% |
| D | diagnostic_loose_trace | 0.6596 | 0.0000 | 0.1333 | 1.0000 | emit=0.00% |
