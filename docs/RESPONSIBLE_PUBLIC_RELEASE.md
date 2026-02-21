# Responsible Public Release (Dual-Use Safety)

Date: 2026-02-15
Repo: vibeforge1111/vibeship-spark-intelligence

This repo is dual-use: the same autonomy/memory infrastructure that helps developers can be repurposed for harmful automation.

Related:
- Threat model: `docs/security/THREAT_MODEL.md`

## 1) Non-Negotiable Reality

If you publish fully-functional code, others can fork it and remove restrictions.
Open source improves auditability, but it does not prevent misuse.

So the goal of a responsible release is:
- reduce accidental harm (safe defaults, hard stops for dangerous actions)
- reduce capability misuse in the "official" distribution (guarded integrations)
- create strong norms + documentation + reporting paths
- keep the trusted computing base small and reviewable

## 2) Release Modes (Choose Deliberately)

Mode A: OSI Open Source License (MIT)
- Pros: maximal adoption and external audit.
- Cons: you cannot legally restrict harmful fields of use in an OSI-compliant license.

Mode B: Source-Available With Use Restrictions (RAIL / ethical-use)
- Pros: you can prohibit certain harmful uses in license text.
- Cons: not OSI open source; adoption drops; enforcement is imperfect and jurisdiction-dependent.

Mode C: Hybrid
- Open source the safe core.
- Gate high-risk capabilities behind an external service you control (with ToS/AUP, logging, and revocation).
- This cannot stop forks, but it can prevent misuse of your infrastructure and provide a "gold standard" safe deployment path.

## 3) Minimum Safety Bar Before Going Public

1. Threat model in writing
- operator misuse, insider abuse, external attacker, model failure modes

2. Safe-by-default runtime posture
- deny-by-default for risky capabilities
- explicit opt-in for expansion
- no silent "debug override" flags in production paths

3. Guardrails in the execution path (not only docs)
- pre-tool policy checks
- strong warnings and escalation when guardrails trigger
- (optional) enforcement if the host platform supports blocking tool calls

Implementation notes (this repo):
- EIDOS evaluates each `PreToolUse` event and emits `[EIDOS] BLOCKED: ...` when a guardrail triggers.
- If your host aborts tools on hook failure, you can enable strict enforcement:
  - `SPARK_EIDOS_ENFORCE_BLOCK=1`
  - This makes `hooks/observe.py` exit non-zero on a blocked decision.

4. Security hygiene
- `SECURITY.md` with vulnerability reporting
- signed releases/tags
- dependency audits (supply-chain risk)

5. Clear scope
- explicit intended use: developer productivity / coding assistant workflows
- explicit non-goals: autonomous cyber ops, mass persuasion, weaponization, covert surveillance

## 4) What We Can Enforce In This Repo vs What We Cannot

Enforceable (in normal deployments):
- guardrails that constrain tool usage (Bash, file writes, web fetch) via EIDOS checks and advisory output
- safe defaults and opt-in expansion

Not enforceable in the abstract:
- preventing a hostile fork from removing checks
- guaranteeing "only good outcomes" from a general model

If you need strong enforcement for real-world deployments, use:
- capability firewall + key/capability issuance service
- remote attestation + signed policy bundles
- multi-party threshold governance for changes
