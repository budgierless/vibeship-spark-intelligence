# Contributing

## Scope

This project is a dual-use autonomy/memory system. Contributions are welcome, but we keep safety and observability first.

## Quick Start for Contributors

1. Fork the repo and clone:

```bash
git clone https://github.com/vibeforge1111/vibeship-spark-intelligence
cd vibeship-spark-intelligence
```

2. Create a branch:

```bash
git checkout -b your-change
```

3. Install dependencies:

```bash
python -m pip install -e .[dev]
```

4. Read the onboarding docs:
- `docs/GETTING_STARTED_5_MIN.md`
- `docs/QUICKSTART.md`
- `docs/ONBOARDING.md`

## What to contribute

- Prefer small, reversible changes with measurable intent.
- Include docs updates for behavior changes.
- Include tests for rule, scoring, and safety-path edits when possible.

## Expected PR flow

1. Open an issue or include a short problem statement in the PR.
2. Keep changes scoped to one clear outcome.
3. Include what changed and how to verify it.
4. Note safety impact in the description (if relevant).

## Development guardrails

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

## Good to know

- We intentionally avoid changing defaults that weaken safety or telemetry for convenience.
- Prefer deterministic behavior on critical paths unless you can show objective improvement.
