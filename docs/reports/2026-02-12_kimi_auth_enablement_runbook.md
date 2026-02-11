# Kimi 2.5 Auth Enablement Runbook (OpenClaw)

Date: 2026-02-12
Owner: Spark / Meta

## Goal
Enable Kimi 2.5 usage in OpenClaw auth + model routing without leaking secrets.

## What is true in this environment
- OpenClaw supports Moonshot (Kimi) provider docs at `docs/providers/moonshot.md`.
- Kimi can be routed via:
  1) `moonshot/kimi-k2.5` (Moonshot provider, `MOONSHOT_API_KEY`), or
  2) `kimi-coding/k2p5` (Kimi Coding provider, `KIMI_API_KEY`).
- Existing auth store currently has Anthropic + OpenAI Codex OAuth only.

## Recommended path (primary)
Use **Moonshot provider** with model ref `moonshot/kimi-k2.5`.

### Step 1: Add provider auth (interactive)
Run on gateway host:

```bash
openclaw models auth login --provider moonshot
```

If plugin login is unavailable, use manual token paste:

```bash
openclaw models auth paste-token --provider moonshot
```

### Step 2: Verify auth profile exists

```bash
openclaw models status
openclaw models status --probe --probe-provider moonshot
```

Expected: moonshot profile visible and probe succeeds.

### Step 3: Set default model to Kimi 2.5

```bash
openclaw models set moonshot/kimi-k2.5
openclaw models status
```

### Step 4: Persist daemon env (if required)
If daemon cannot read shell env, add to `~/.openclaw/.env`:

```env
MOONSHOT_API_KEY=***
```

Then restart gateway and re-check:

```bash
openclaw gateway restart
openclaw models status --probe --probe-provider moonshot
```

## Alternative path (secondary)
Use Kimi Coding provider:

```bash
openclaw models auth login --provider kimi-coding
# or
openclaw models auth paste-token --provider kimi-coding

openclaw models set kimi-coding/k2p5
openclaw models status --probe --probe-provider kimi-coding
```

## Critical notes
- Moonshot and Kimi Coding are separate providers; keys are **not interchangeable**.
- Do not commit keys into repo or `auth-profiles.json` snapshots.
- If you see `401 Unauthorized`, key/provider mismatch is likely.

## Fast validation checklist
- [ ] `openclaw models status` shows provider profile
- [ ] probe succeeds for chosen provider
- [ ] default model set to Kimi route
- [ ] one real generation call succeeds in target workflow

## Blocker declaration
This setup requires a secret not available in this session:
- `MOONSHOT_API_KEY` (preferred) **or** `KIMI_API_KEY` (secondary)
- Must be entered via OpenClaw auth CLI on gateway host (or daemon env)
