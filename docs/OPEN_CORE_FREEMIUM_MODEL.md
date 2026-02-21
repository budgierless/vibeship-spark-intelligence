# Open Core + Freemium Model (Practical)

Date: 2026-02-15
Repo: vibeforge1111/vibeship-spark-intelligence

Goal: keep Spark's core open source for growth and auditability, while offering premium modules (chips, benchmark systems like Forge/DEPTH, curated packs) without weakening safety.

## 1) Boundary: What Must Stay Open

Keep these open and reviewable:
- event capture and ingestion (hooks/adapters)
- storage formats and schemas
- policy/guardrails and enforcement paths
- core evaluation harnesses (the "how to measure" scaffolding)

Rationale: safety depends on auditability and a small trusted computing base.

## 2) What Can Be Premium Without Becoming "Security Through Obscurity"

Premium should be:
- curated content packs (chip bundles, benchmark suites, domain matrices)
- hosted services (when you need strong gating, compute, or proprietary datasets)
- operational tooling (dashboards, managed deployments, collaboration workflows)
- social-tooling surfaces (social networks/research surfaces), kept opt-in behind `SPARK_PREMIUM_TOOLS=1`.

Avoid positioning premium as "the safety layer". Safety must exist in the OSS core.

## 3) Implementation Pattern: Plugin Interfaces

Design premium as installable plugins:
- OSS core defines stable interfaces (Python entry points / plugin registry).
- Premium packages register plugins (chips sources, benchmarks, scoring backends).
- OSS core runs with safe defaults when premium packages are absent.

Benefits:
- clean separation (no private code inside OSS repo)
- reduces pressure to add "hidden guardrails"
- makes review and testing easier

## 4) Safety Posture For Open Core

Because forks exist, the safety goal is:
- safe-by-default official distribution
- guardrails in real execution paths (EIDOS pre-tool checks)
- clear documentation of what is and is not enforceable in open source

See:
- `docs/RESPONSIBLE_PUBLIC_RELEASE.md`
- `docs/research/AGI_GUARDRAILS_IMMUTABILITY.md`

## 5) Recommended Packaging

- This repo: `vibeship-spark` OSS core (MIT; premium modules remain separate).
- Private packages:
  - `vibeship-spark-chips-premium`
  - `vibeship-spark-forge` (or a hosted Forge API)
  - `vibeship-spark-depth` (often best as hosted due to datasets/controls)

## 6) What This Does Not Prevent

- malicious forks removing guardrails
- third parties repackaging for harmful use

What it does provide:
- a safe, audited default path users actually adopt
- a clear upgrade path for premium capabilities without weakening the core
