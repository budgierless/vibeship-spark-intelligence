# OSS-only Manifest (Spark OSS launch)

Date: Saturday, February 21, 2026
Source: `vibeship-spark-intelligence (repo root)`

## Launch objective

- Keep Spark OSS minimal and safe to publish.
- Preserve core intelligence runtime, OpenClaw bridge compatibility, CLI/scripting interfaces, and documentation.
- Remove/disable premium and non-OSS artifacts for public visibility.

## Current publication set

- Kept: `CLAUDE.md`, `PROJECT.md`, `README.md`-style docs, `docs/` core guides, `lib/`, `scripts/`, `extensions/`, `prompts/`, `tests/`, and top-level config used by OSS runtime.
- Kept but inert by default: chip/evolution modules remain present for architecture continuity; execution is premium-gated in code and defaults.
- Kept for governance: sanitization and tuning files such as `config/tuneables.json`, `TUNEABLES.md`, `docs/ARCHITECTURE` docs, and `docs/openclaw` references.

## Sanitization/launch pass performed

Scans completed on tracked + ignored text/code surfaces for:
- credential formats (`sk-`, `Bearer`, `api_key`, `token`, `secret`)
- private key markers (`BEGIN ... KEY`)
- embedded URL credentials (`user:pass@host`)
- absolute path leaks (`<USER_HOME>`, `C:/...`)

Result:
- No real hardcoded secrets found in tracked files after redaction updates.
- Path hygiene now uses generic placeholders (`<USER_HOME>`, `%USERPROFILE%`, env-like tokens) where relevant.
- Exposure test fixtures were neutralized and assertion strings updated.

## Hygiene removals and deletions

The following folders/files were removed from the public tree for launch hygiene:
- `docs/reports/` (operational/private advisory outputs)
- `benchmarks/` (run artifacts)
- `.spark/`, `.pytest_cache/`, `__pycache__/`, and other runtime cache directories
- `sandbox/spark_sandbox/` tracked report/workspace metadata:
  - `sandbox/spark_sandbox/project/AGENTS.md`
  - `sandbox/spark_sandbox/project/CLAUDE.md`
  - `sandbox/spark_sandbox/project/PROJECT.md`
  - `sandbox/spark_sandbox/project/README.md`
  - `sandbox/spark_sandbox/project/SOUL.md`
  - `sandbox/spark_sandbox/project/TOOLS.md`
  - `sandbox/spark_sandbox/skills/sandbox-skill.yaml`
  - `sandbox/spark_sandbox/workspace/SPARK_CONTEXT.md`
- Local-only workflow artifacts not suitable for OSS:
  - `.cursorrules`
  - `.windsurfrules`

## Recommended publish check

- Confirm `docs/reports/` and benchmark paths are absent before packaging.
- Confirm `.gitignore` keeps non-OSS/generated files untracked.
- Confirm chips remain inert in OSS by default and only enable under explicit premium controls.
