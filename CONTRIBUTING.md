# Contributing

## Scope

This project is a dual-use autonomy/memory system. Contributions are welcome, but we deliberately keep the safe path safe-by-default.

## What We Will Not Accept

- Changes whose primary purpose is bypassing safety guardrails or increasing high-risk autonomy without clear, reviewable controls.
- "Stealth" behavior: hidden capabilities, obfuscated backdoors, or surprise network actions.
- Features that materially increase misuse risk without a written threat model, tests, and a safe default posture.

## What We Prefer

- Smaller, measurable changes with tests.
- Least-privilege capability design (typed tools, deny-by-default).
- Security fixes, guardrail hardening, and monitoring improvements.
- Documentation that makes safety and operational boundaries explicit.

## Security

If you find a vulnerability or a safety-critical issue, follow `SECURITY.md`.

