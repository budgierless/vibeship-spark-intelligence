# Advisory Repeat A/B/C/D (Controlled Delta)

Date: 2026-02-13

Workload: `python scripts/advisory_controlled_delta.py --rounds 160 --force-live`

## Summary

| Run | emitted_returns | engine.emitted | feedback_items | feedback_top_share | emit_norm_top | emit_norm_top_count |
|---|---:|---:|---:|---:|---|---:|
| A_baseline_current | 14 | 15 | 7 | 57.14% | FAM_read_before_edit | 3 |
| B_min_rank_0p55 | 14 | 18 | 7 | 57.14% | FAM_read_before_edit | 6 |
| C_max_items_3 | 14 | 23 | 11 | 36.36% | FAM_read_before_edit | 7 |
| D_min_rank_0p55_max_items_3 | 14 | 26 | 12 | 25.00% | FAM_git_push | 8 |

## Notes

- `feedback_*` is derived from `~/.spark/advice_feedback_requests.jsonl` within-run window.
- emit_norm_* is derived from ~/.spark/advisory_emit.jsonl within-run window, normalized into a few top noise families.

