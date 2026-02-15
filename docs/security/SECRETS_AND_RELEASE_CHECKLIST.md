# Secrets + Release Checklist (Pre-Public)

Date: 2026-02-15

Use this checklist before any public release (alpha/beta/GA).

## Secrets Hygiene

- Confirm `.env` and credential files are gitignored:
  - `.env`, `.env.*`
  - `*.secret`, `secrets.json`
  - `twitter_credentials*`, `.twitter_keys`
  - `.moltbook/`, `moltbook_credentials.json`
- Scan repo for common secret patterns (excluding `node_modules/`, logs, and reports):
  - private keys, GitHub tokens, API keys, Slack tokens, AWS keys
- Ensure example credential files are clearly labeled as examples:
  - `*.env.example` only

## Service Exposure

- Dashboards bind to `127.0.0.1` by default (do not expose on LAN).
- If any service is intentionally exposed, document:
  - auth model
  - rate limits
  - threat model assumptions

## sparkd Hardening

- Mutating endpoints require auth when `SPARKD_TOKEN` is set.
- Per-IP rate limiting is enabled.
- Invalid-event quarantine retention is bounded.
- Logs do not include secrets or raw auth headers.

## Guardrails / Responsible Release

- Guardrails run in the execution path (not just docs).
- Strict enforcement option works and is documented:
  - `SPARK_EIDOS_ENFORCE_BLOCK=1`
- Tests pass:
  - `python -m pytest -q tests/test_safety_guardrails.py tests/test_sparkd_hardening.py`

## Supply Chain

- Pin/lock dependencies where possible.
- Prefer signed releases/tags for public distribution.
- Document the installer’s trust model (what it downloads, from where).

