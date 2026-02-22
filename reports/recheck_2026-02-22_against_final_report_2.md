# Recheck Matrix Against `final_report (2).md`

- Recheck date: 2026-02-22
- Repo commit rechecked: `feff131`
- Source report: `C:\Users\USER\Downloads\final_report (2).md`

## Summary

All findings in the old consolidated report are resolved on current `main`.

- Resolved: 12
- Partially resolved / residual risk: 0
- Still open (original claim unchanged): 0

## Matrix

| ID | Recheck Status | Evidence (current repo) |
|---|---|---|
| H-01 Mind auth integration break | **Resolved** | `lib/mind_bridge.py` sends bearer headers on all POST paths (`:395`, `:465`, `:599`) and resolves token from `~/.spark/mind_server.token` (`:40`, `:112`, `:199`). `mind_server.py` still enforces bearer auth (`:292`..`:300`), and live call check succeeded (`health=True`, retrieval returned rows). |
| H-02 sparkd auth rollout mismatch | **Resolved** | Adapters now auto-resolve token from CLI/env/**token file**: `adapters/stdin_ingest.py:24`..`:37`, `adapters/openclaw_tailer.py:31`..`:94`, `adapters/clawdbot_tailer.py:25`..`:67`. Docs now match default mandatory POST auth: `docs/adapters.md:65`..`:66`, `docs/QUICKSTART.md:206`, `docs/launch/LAUNCH_SCOPE_AND_GATES.md:72`, `docs/PROGRAM_STATUS.md:26`, `docs/security/THREAT_MODEL.md:69`. |
| H-03 queue data-loss race | **Resolved** | Overflow path now uses lock + shard fallback, avoiding contention drops in tested runs (`lib/queue.py:356`..`:358`), and merge handles shard files (`lib/queue.py:207`, `lib/queue.py:235`). Hook path now surfaces capture failures (`hooks/observe.py:929`, `hooks/observe.py:937`). |
| M-01 benchmark entrypoint broken | **Resolved** | `benchmarks/generators/` exists with required modules; `python benchmarks/run_benchmarks.py --help` passes; import smoke check passes (`from benchmarks.comprehensive_pipeline_benchmark import run_benchmark`). |
| M-02 broad pytest baseline red/noisy | **Resolved** | `python -m pytest -q -m "not integration"` passed (`892 passed, 23 deselected`) and `python scripts/verify_test_baseline.py` passed; repeated contention check `tests/test_queue_concurrency.py::test_concurrent_overflow_writes_no_loss` passed 20/20 reruns after queue fallback hardening. |
| M-03 queue tests stale after `QUEUE_STATE_FILE` refactor | **Resolved** | Test helper now patches `QUEUE_STATE_FILE` directly (`tests/test_queue_concurrency.py:17`). |
| M-04 opportunity scanner import-order flake | **Resolved** | Test now patches adapter alias target (`tests/test_opportunity_scanner.py:176`) and advisor imports through adapter (`lib/advisor.py:3633`). `tests/test_opportunity_scanner.py` passed (`21 passed`). |
| M-05 maturity misrepresentation in `SELF_IMPROVEMENT_SYSTEMS.md` | **Resolved** | Top-level status and accuracy note explicitly scope roadmap/non-OSS modules (`docs/SELF_IMPROVEMENT_SYSTEMS.md:6`, `:9`) and repeated section notes mark historical/internal claims. |
| M-06 retired `advisory_profile_sweeper.py` references | **Resolved** | File exists again (`benchmarks/advisory_profile_sweeper.py`) and test passes (`tests/test_advisory_profile_sweeper.py`: `3 passed`). |
| L-01 README dashboard wording stale | **Resolved** | README now points to observatory dashboard (`README.md:186`, `README.md:203`). |
| L-02 EIDOS quickstart wrong dashboard path | **Resolved** | Quickstart now uses `python scripts/eidos_dashboard.py` (`EIDOS_QUICKSTART.md:305`). |
| L-03 `consume_processed()` docstring stale | **Resolved** | Docstring now matches head-byte `QUEUE_STATE_FILE` design (`lib/queue.py:501`..`:502`). |

## Residual Risks Worth Tracking

No high-confidence residuals from the original matrix remain after current fixes.
