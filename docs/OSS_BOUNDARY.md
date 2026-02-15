# Spark OSS Core Boundary (What Ships Here)

Date: 2026-02-15
Repo: spark-oss (private for now)

This document is the exact boundary for the Spark OSS Core distribution: what is included, what is intentionally excluded, and why.

## 1) Product Intent

Spark OSS Core should feel like "self-evolving intelligence" for coding agents:
- it captures real work signals
- learns durable preferences/patterns
- distills reusable rules (EIDOS)
- surfaces actionable context back into your agent workspace

It should NOT be a general-purpose automation platform for public influence, mass action, or high-dual-use behavior.

## 2) Included In OSS Core (Ships)

Core runtime and learning loops:
- Event ingest + queue: `sparkd.py`, `lib/queue.py`, `lib/events.py`, `lib/ingest_validation.py`
- Bridge cycle + context writing: `bridge_worker.py`, `lib/bridge_cycle.py`, `lib/context_sync.py`, `lib/output_adapters/`
- Learning + memory stores: `lib/cognitive_learner.py`, `lib/memory_*`, `lib/pattern_detection/`, `lib/outcomes/`
- Guardrails and deterministic enforcement (must remain OSS): `lib/eidos/`, `hooks/observe.py`
- Advisory engine + gating: `lib/advisory_engine.py`, `lib/advisory_gate.py`, `lib/advisor.py`

Local integrations:
- Claude Code hook capture: `hooks/observe.py`
- OpenClaw tailer capture: `adapters/openclaw_tailer.py`
- Workspace outputs for agents: `SPARK_CONTEXT.md`, `SPARK_ADVISORY.md`, `SPARK_NOTIFICATIONS.md` (via `lib/output_adapters/`)

Chips (safe default set):
- Keep a small set of coding-focused chips under `chips/` (examples + coding/workflow oriented)
- Chip runtime remains in `lib/chips/`

Docs that explain safety posture and release:
- `docs/RESPONSIBLE_PUBLIC_RELEASE.md`
- `docs/security/THREAT_MODEL.md`
- `docs/security/SECRETS_AND_RELEASE_CHECKLIST.md`
- `docs/research/AGI_GUARDRAILS_IMMUTABILITY.md`
- OSS definition: `docs/OSS_PRODUCT_DEFINITION.md`, `docs/OSS_SWOT.md`, `docs/OSS_ROADMAP.md`, `docs/OSS_SCHEMAS.md`

## 3) Excluded From OSS Core (Moved Out)

These are intentionally excluded because they raise dual-use risk and/or blur product scope.

Social network / agent-social automation:
- Moltbook integration and CLI (removed from this repo)

X/Twitter automation and trend pipelines:
- X-specific runtime modules (removed from this repo)
- X posting/reply/scheduled research scripts (removed from this repo)

Training suites and premium benchmark systems:
- DEPTH/Forge training runners and related code paths (moved out; premium/private)

High-risk capability surfaces:
- Anything that enables mass messaging, autonomous posting, or wide-scale external influence by default

## 4) Safety Defaults In OSS Core

Threat model: hostile actors can fork. Therefore OSS Core focuses on:
- safe-by-default official distribution
- guardrails enforced at a real choke point (pre-tool check)
- reduced "sharp tool" surfaces in the default package

Implemented guardrails (examples):
- EIDOS pre-tool guardrails run on `PreToolUse` via `hooks/observe.py`
- High-risk tool usage blocks in `lib/eidos/guardrails.py` (destructive shell patterns, pipe-to-shell, likely-secret file reads)
- Optional strict enforcement mode: `SPARK_EIDOS_ENFORCE_BLOCK=1` (host-dependent)

## 5) Open Core / Premium Compatibility (How We Grow)

OSS core stays:
- auditable
- capability-poor by default (no high-dual-use automations)
- stable contracts (schemas + plugin interfaces)

Premium value stays in:
- curated content packs (chips, benchmark suites)
- hosted services (capability brokerage, attestation, audits)

See: `docs/OPEN_CORE_FREEMIUM_MODEL.md`.

## 6) What This Cannot Prevent (Honest Limits)

- A hostile fork can remove guardrails and run privately.
- AGPL helps visibility for hosted forks (they must provide source to users), but cannot force runtime posture.

Therefore:
- the "official" build must remain safe-by-default
- high-risk capabilities should live behind external services or premium modules

