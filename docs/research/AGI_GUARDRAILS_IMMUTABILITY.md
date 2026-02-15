# AGI Guardrails Immutability (Practical Research)

Date: 2026-02-15
Repo: vibeship-spark-intelligence
Audience: system designers/operators building high-autonomy agents
Goal: Design guardrails that keep an AGI-class system oriented toward humanity's good, while making those guardrails effectively immutable (including "immutable even to the operator").

## 0) Reality Check: "Cannot Ever Be Changed" Is Not Achievable

If a system exists in the physical world, then in the limit:
- hardware can be replaced
- software can be bypassed by running a different binary on different hardware
- humans can collude, coerce, or make mistakes
- vulnerabilities can be discovered

So the correct engineering goal is:
- No unilateral change: no single person (including you) can modify core guardrails.
- Tamper-evident change: if anything changes, it is publicly/cryptographically detectable.
- Fail-closed safety: attempts to operate outside the guardrails stop the system, rather than "degrade gracefully" into unsafe behavior.
- Bounded capability: even if misaligned behavior emerges, the system cannot take irreversible harmful actions without external, diverse approval.

Think of this as "immutability by design + immutability by governance + immutability by cryptography", not metaphysical permanence.

## 1) Define "Humanity's Good" As a Process, Not a Single Static Sentence

"Humanity's good" is underspecified and contested. Hard-coding one person's definition creates a single point of moral failure.

Practical approach:
- Define a rights-and-harm baseline (negative constraints): the system must not cause or enable severe harm, coercion, unlawful violence, exploitation, or large-scale rights violations.
- Define a procedural commitment (positive constraints): when stakes are high or norms conflict, the system must defer to legitimate, plural human oversight processes rather than improvising.
- Treat value updates as governance events (slow, transparent, multi-party) rather than runtime tuning.

In practice, the "constitution" is a versioned policy corpus plus a change-control process, with cryptographic enforcement.

## 2) Threat Model: What You Are Trying To Prevent

You need explicit adversaries, otherwise "guardrails" become vibes.

Minimum threat model:
- Operator risk: you (or future maintainers) want to "just temporarily disable safety" to ship or to test.
- Insider risk: a privileged engineer/admin abuses access.
- External attacker: remote compromise, prompt injection, supply-chain compromise.
- Model risk: deception, power-seeking, goal misgeneralization, reward hacking, tool misuse.
- Governance capture: oversight bodies become captured, rubber-stamp changes, or are coerced.

Your architecture should make each of these expensive, detectable, and ideally impossible without broad collusion.

## 3) Architecture Pattern: Policy Kernel + Capability Firewall

The most robust pattern is to keep the trusted computing base (TCB) small:

1. Policy Kernel (PK)
- A small, deterministic, heavily-tested component that:
  - mediates tool calls (filesystem, network, code execution, money movement, messaging)
  - enforces hard constraints (allowlist/denylist, rate limits, data boundaries)
  - requires approvals for high-stakes actions
  - writes all decisions to an append-only log

2. Untrusted Intelligence Layer (UIL)
- The AGI/model(s), planners, retrievers, self-improvement loops.
- The UIL can propose actions, but it cannot directly execute privileged operations.

3. Capability Firewall (CF)
- The PK exposes only narrow, typed capabilities to the UIL.
- Capabilities are composable but bounded (least privilege).

This separation matters because it lets you "lock" the PK while still iterating on the intelligence layer.

## 4) Making Guardrails Effectively Immutable

Immutability requires multiple layers; any single layer can be bypassed.

### 4.1 Cryptographic Immutability (Who Can Authorize Change)

Goal: no single actor can change guardrails.

Mechanisms:
- Signed policy: PK only loads a policy/constitution bundle if it is signed by a threshold key (k-of-n).
- Threshold governance: split signing authority across independent parties:
  - separate organizations, jurisdictions, and incentive structures
  - include at least one party whose mission is safety/oversight, not shipping
- Timelocks: policy updates are staged and become active only after a delay window.
- Emergency stop, not emergency override: allow "stop the system" quickly, but do not allow "disable guardrails" quickly.

Operator-immutability variant (even you cannot change it):
- You do not hold enough key shares to meet the threshold.
- Your key shares (if any) are stored in a way you cannot access alone (e.g., HSM with dual control at an external custodian).

### 4.2 Hardware/Boot Immutability (What Code Is Actually Running)

Goal: prevent "just run a different binary".

Mechanisms:
- Secure/Measured boot: the machine boots only a signed OS + signed PK binary.
- TPM-backed attestation: PK proves to an external verifier that it is running the expected hashes/config.
- Remote attestation gate: critical capabilities are enabled only if attestation passes.
- No local admin path: remove root/admin routes to modify the PK partition at runtime.

Reality note:
- Physical access and supply-chain attacks are not fully solvable. You mitigate by diversity (multiple attestations), audits, and separation of duties.

### 4.3 Data Immutability (Tamper-Evident Logs and Transparency)

Goal: even if something changes, it becomes obvious.

Mechanisms:
- Append-only event log: every policy decision and every privileged action is logged.
- Hash chaining (Merkle/DAG): each log entry commits to prior entries (tamper evidence).
- External replication: logs stream to multiple independent third parties.
- Public transparency for high-stakes deployments: publish hashes and signed checkpoints so secret retroactive edits are detectable.

### 4.4 Operational Immutability (No "Oops, Debug Mode")

Goal: eliminate the normal foot-guns that defeat safety.

Mechanisms:
- No runtime "disable safety" flag.
- No hidden backdoors (including "dev-only" endpoints) in the PK.
- Break-glass = power-off: the only "bypass" is to halt the system.
- Configuration minimization: fewer knobs in production.
- Strict environment separation: dev/test environments exist, but production keys never enter them.

### 4.5 Socio-Legal Immutability (Deterrence and Accountability)

Technical controls are stronger when backed by institutions.

Mechanisms:
- Independent safety board with real authority (including veto/stop powers).
- Regular external audits/red-teaming.
- Legal commitments that create penalties for bypass/capture.
- Public incident reporting norms.

This is not "security through paperwork"; it is deterrence, visibility, and multi-party friction.

## 5) Guardrails That Actually Enforce "Work for Humanity's Good"

You need guardrails at three levels: action constraints, goal constraints, and learning constraints.

### 5.1 Action Constraints (Hard Stops)

Examples:
- Tool allowlists with typed schemas (no arbitrary shell/network).
- Sandboxed execution for any code run.
- Rate limits and budget limits (time, money, external calls).
- Mandatory approvals for irreversible actions:
  - financial transfers
  - contacting real people at scale
  - publishing/launching code that impacts safety-critical systems
  - any action that materially increases the system's autonomy or capability surface

### 5.2 Goal Constraints (No "Ends Justify Means")

Examples:
- Explicit forbidden strategies (coercion, deception to humans, manipulation, threats).
- Prohibitions on unauthorized data access and privacy violations.
- Requirements for consent and provenance for data/tools.

### 5.3 Learning/Self-Modification Constraints

If the system can self-improve, you must separate:
- what it can change (untrusted intelligence layer)
- what it cannot change (policy kernel and its constitution)

Rules:
- UIL may propose changes; PK cannot be modified by UIL.
- Any change to PK/constitution requires the same multi-party threshold process as above.
- Capability expansions require a "safety case" and staged rollout.

## 6) Verification: How You Know It Works

You want an assurance case, not vibes:
- Formal-ish spec for PK behavior (what must always hold).
- Property-based tests on policy enforcement.
- Reproducible builds and a verifiable SBOM for PK.
- Red-team exercises focused on:
  - prompt injection into tool calls
  - supply chain attacks
  - operator override attempts
  - covert channels and data exfil
- Continuous monitoring + anomaly detection:
  - abnormal tool call patterns
  - novel capability composition
  - repeated "near-miss" safety blocks

## 7) A Concrete "Immutable Guardrails" Build Plan

Phase 1: Policy Kernel MVP (small TCB)
- Define the privileged capability surface (file, network, exec, money, messaging).
- Implement a single gatekeeper that mediates every capability call.
- Add append-only logging with hash chaining.
- Add strict deny-by-default policies.

Phase 2: Threshold Update System (no unilateral changes)
- Implement signed policy bundles.
- Implement k-of-n threshold signing for updates.
- Remove any local override paths.

Phase 3: Attested Runtime (prove what's running)
- Add secure/measured boot.
- Add TPM-based attestation checks.
- Require attestation before enabling high-risk capabilities.

Phase 4: External Oversight + Transparency
- Independent log replication.
- Timelocked change announcements.
- Regular audits/red-team cadence.

Phase 5: Capability Scaling Under Control
- Add new tools only via typed, reviewable capabilities.
- Put irreversible actions behind human quorum approval.
- Continuously shrink and simplify the PK.

## 8) Design Principle Summary (Non-Negotiables)

- Separate "thinking" from "doing": the model is not trusted; the policy kernel is.
- Default-deny capabilities; everything privileged is mediated.
- No unilateral change to core guardrails (threshold governance).
- Detectability beats secrecy: append-only logs, attestation, replication.
- Break-glass stops the system; it does not remove constraints.
- "Humanity's good" is enforced via rights/harm baselines + legitimate plural oversight processes.

## 9) What This Still Does Not Solve

- If someone builds a new system outside your guardrails, your guardrails do not apply.
- A powerful actor with physical access can potentially replace hardware or bypass controls.
- Governance can be captured; you mitigate via diversity, transparency, and external accountability.
- Value conflicts are not "solved" by policy text; the best you can do is constrain harm and force high-stakes decisions back to legitimate human processes.
