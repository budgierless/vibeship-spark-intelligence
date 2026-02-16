import { createHash } from "node:crypto";
import { mkdirSync, appendFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import type {
  OpenClawPluginApi,
  PluginHookAgentContext,
  PluginHookLlmInputEvent,
  PluginHookLlmOutputEvent,
} from "openclaw/plugin-sdk";

type Json = Record<string, unknown>;

type TelemetryConfig = {
  spoolFile: string;
  includePromptPreview: boolean;
  includeOutputPreview: boolean;
  previewChars: number;
  // New: lightweight build-integrity guardrails
  buildIntegrityEnabled: boolean;
  injectNoHallucinationGuard: boolean;
  stallSeconds: number;
};

type BuildState = {
  active: boolean;
  awaitingStartProof: boolean;
  mode: "building" | "paused" | "idle";
  startedAtMs?: number;
  lastProgressAtMs?: number;
  contractAtMs?: number;
  lastRunId?: string;
  baselineToolishCount?: number;
  lastStallAlertAtMs?: number;
};

const PLUGIN_ID = "spark-telemetry-hooks";
const DEFAULT_SPOOL_FILE = process.env.SPARK_OPENCLAW_HOOK_EVENTS_FILE
  || path.join(os.homedir(), ".spark", "openclaw_hook_events.jsonl");

const BUILD_PROMISE_RE = /\b(i\s*(?:am|'m)\s*(?:building|working\s+on|implementing|shipping)|i\s+will\s+(?:build|implement|ship|report\s+back)|resuming\s+now|on\s+it\s+now|build\s+mode|in\s+progress)\b/i;
const BUILD_DONE_RE = /\b(done|completed|shipped|commit\s*[:#]|ready\s+to\s+wire|finalized|finished)\b/i;
const BUILD_FAIL_RE = /\b(failed|error|blocked|stalled|cannot\s+proceed|rollback)\b/i;
const BUILD_PAUSE_RE = /\b(paused|parked|on\s+hold|resume\s+later)\b/i;

function asObject(value: unknown): Json {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Json)
    : {};
}

function asString(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

function asBool(value: unknown, fallback = false): boolean {
  return typeof value === "boolean" ? value : fallback;
}

function asInt(value: unknown, fallback: number): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return Math.max(1, Math.floor(value));
  }
  return fallback;
}

function hashText(text: string): string {
  return createHash("sha256").update(text).digest("hex").slice(0, 20);
}

function preview(text: string, limit: number): string {
  return text.slice(0, limit);
}

function countToolishMessages(history: unknown[]): number {
  let toolish = 0;
  for (const row of history) {
    if (!row || typeof row !== "object") continue;
    const obj = row as Record<string, unknown>;
    const role = String(obj.role || "").toLowerCase();
    if (role === "tool" || role === "toolresult") {
      toolish += 1;
      continue;
    }
    const content = obj.content;
    if (!Array.isArray(content)) continue;
    for (const block of content) {
      if (!block || typeof block !== "object") continue;
      const blockType = String((block as Record<string, unknown>).type || "").toLowerCase();
      if (blockType === "toolcall" || blockType === "toolresult") {
        toolish += 1;
        break;
      }
    }
  }
  return toolish;
}

function readPluginConfig(api: OpenClawPluginApi): TelemetryConfig {
  const fromApi = asObject(api.pluginConfig);
  const plugins = asObject((api.config as Json).plugins);
  const entries = asObject(plugins.entries);
  const entry = asObject(entries[PLUGIN_ID]);
  const fromEntry = asObject(entry.config);

  const raw = { ...fromEntry, ...fromApi };
  return {
    spoolFile: asString(raw.spoolFile) || DEFAULT_SPOOL_FILE,
    includePromptPreview: asBool(raw.includePromptPreview, false),
    includeOutputPreview: asBool(raw.includeOutputPreview, false),
    previewChars: asInt(raw.previewChars, 240),
    buildIntegrityEnabled: asBool(raw.buildIntegrityEnabled, true),
    injectNoHallucinationGuard: asBool(raw.injectNoHallucinationGuard, true),
    stallSeconds: asInt(raw.stallSeconds, 300),
  };
}

function appendSpoolRow(spoolFile: string, payload: Json): void {
  const resolved = path.resolve(spoolFile);
  mkdirSync(path.dirname(resolved), { recursive: true });
  appendFileSync(resolved, `${JSON.stringify(payload)}\n`, { encoding: "utf8" });
}

function baseRow(
  hook: "llm_input" | "llm_output" | "build_integrity",
  cfg: TelemetryConfig,
  event: Json,
  ctx: PluginHookAgentContext,
): Json {
  const runId = asString(event.runId) || asString(event.run_id);
  const sessionId = asString(event.sessionId) || asString(event.session_id) || asString(ctx.sessionId);
  const provider = asString(event.provider);
  const model = asString(event.model);
  return {
    schema_version: 1,
    ts: Date.now() / 1000,
    source: "openclaw_plugin",
    plugin_id: PLUGIN_ID,
    hook,
    run_id: runId,
    session_id: sessionId,
    session_key: asString(ctx.sessionKey),
    agent_id: asString(ctx.agentId),
    message_provider: asString(ctx.messageProvider),
    provider,
    model,
    spool_file: cfg.spoolFile,
  };
}

function mapLlmInput(
  cfg: TelemetryConfig,
  event: PluginHookLlmInputEvent,
  ctx: PluginHookAgentContext,
): Json {
  const prompt = typeof event.prompt === "string" ? event.prompt : "";
  const systemPrompt = typeof event.systemPrompt === "string" ? event.systemPrompt : "";
  const history = Array.isArray(event.historyMessages) ? event.historyMessages : [];

  const row: Json = {
    ...baseRow("llm_input", cfg, event as unknown as Json, ctx),
    prompt_chars: prompt.length,
    prompt_hash: hashText(prompt),
    system_prompt_chars: systemPrompt.length,
    system_prompt_hash: systemPrompt ? hashText(systemPrompt) : undefined,
    history_count: history.length,
    history_toolish_count: countToolishMessages(history),
    images_count: Number.isFinite(event.imagesCount) ? event.imagesCount : 0,
  };
  if (cfg.includePromptPreview && prompt) {
    row.prompt_preview = preview(prompt, cfg.previewChars);
  }
  return row;
}

function mapLlmOutput(
  cfg: TelemetryConfig,
  event: PluginHookLlmOutputEvent,
  ctx: PluginHookAgentContext,
): Json {
  const texts = Array.isArray(event.assistantTexts)
    ? event.assistantTexts.filter((v): v is string => typeof v === "string")
    : [];
  const outputChars = texts.reduce((n, text) => n + text.length, 0);
  const row: Json = {
    ...baseRow("llm_output", cfg, event as unknown as Json, ctx),
    output_count: texts.length,
    output_chars: outputChars,
    output_hashes: texts.slice(0, 3).map((text) => hashText(text)),
    usage: event.usage
      ? {
          input: event.usage.input,
          output: event.usage.output,
          cacheRead: event.usage.cacheRead,
          cacheWrite: event.usage.cacheWrite,
          total: event.usage.total,
        }
      : undefined,
  };
  if (cfg.includeOutputPreview && texts[0]) {
    row.output_preview = preview(texts[0], cfg.previewChars);
  }
  return row;
}

function resolveSessionKey(ctx: PluginHookAgentContext, event: Json): string {
  return asString(event.sessionId)
    || asString(event.session_id)
    || asString(ctx.sessionKey)
    || asString(ctx.sessionId)
    || "unknown";
}

function appendBuildIntegrityRow(
  cfg: TelemetryConfig,
  ctx: PluginHookAgentContext,
  event: Json,
  kind: string,
  detail: Json = {},
): void {
  appendSpoolRow(cfg.spoolFile, {
    ...baseRow("build_integrity", cfg, event, ctx),
    kind,
    ...detail,
  });
}

const plugin = {
  id: PLUGIN_ID,
  name: "Spark Telemetry Hooks",
  description: "Capture redacted llm_input/llm_output telemetry for Spark ingestion.",
  register(api: OpenClawPluginApi) {
    const cfg = readPluginConfig(api);
    api.logger.info(`[${PLUGIN_ID}] spoolFile=${cfg.spoolFile}`);

    const buildBySession = new Map<string, BuildState>();

    const getBuildState = (session: string): BuildState => {
      const state = buildBySession.get(session);
      if (state) return state;
      const initial: BuildState = {
        active: false,
        awaitingStartProof: false,
        mode: "idle",
      };
      buildBySession.set(session, initial);
      return initial;
    };

    if (cfg.buildIntegrityEnabled) {
      setInterval(() => {
        const now = Date.now();
        for (const [session, state] of buildBySession.entries()) {
          if (!state.awaitingStartProof && !state.active) continue;
          const last = state.lastProgressAtMs ?? state.contractAtMs ?? now;
          const stalledFor = now - last;
          if (stalledFor < cfg.stallSeconds * 1000) continue;
          if (state.lastStallAlertAtMs && now - state.lastStallAlertAtMs < cfg.stallSeconds * 1000) continue;
          state.lastStallAlertAtMs = now;
          appendSpoolRow(cfg.spoolFile, {
            schema_version: 1,
            ts: now / 1000,
            source: "openclaw_plugin",
            plugin_id: PLUGIN_ID,
            hook: "build_integrity",
            kind: "stall_alert",
            session_key: session,
            stalled_seconds: Math.floor(stalledFor / 1000),
            awaiting_start_proof: state.awaitingStartProof,
            mode: state.mode,
          });
        }
      }, 15_000);
    }

    api.on("llm_input", (event, ctx) => {
      try {
        if (cfg.injectNoHallucinationGuard && typeof (event as any).systemPrompt === "string") {
          const guard = "\n\nBuild-status integrity:\n- Do not claim active building unless a real action already started in this run/session.\n- If work is paused/stalled, say so explicitly.\n- End build-mode updates with one of: done, failed, paused.";
          if (!String((event as any).systemPrompt).includes("Build-status integrity:")) {
            (event as any).systemPrompt = `${(event as any).systemPrompt}${guard}`;
          }
        }

        const row = mapLlmInput(cfg, event, ctx);
        appendSpoolRow(cfg.spoolFile, row);

        if (cfg.buildIntegrityEnabled) {
          const session = resolveSessionKey(ctx, event as unknown as Json);
          const state = getBuildState(session);
          const toolishCount = Number(row.history_toolish_count ?? 0);

          if (state.awaitingStartProof && state.baselineToolishCount !== undefined) {
            if (toolishCount > state.baselineToolishCount) {
              state.awaitingStartProof = false;
              state.active = true;
              state.mode = "building";
              state.startedAtMs = Date.now();
              state.lastProgressAtMs = Date.now();
              appendBuildIntegrityRow(cfg, ctx, event as unknown as Json, "start_proof", {
                session_key: session,
                baseline_toolish_count: state.baselineToolishCount,
                current_toolish_count: toolishCount,
              });
            }
          }
        }
      } catch (err) {
        api.logger.warn(`[${PLUGIN_ID}] failed to write llm_input row: ${String(err)}`);
      }
    });

    api.on("llm_output", (event, ctx) => {
      try {
        const row = mapLlmOutput(cfg, event, ctx);
        appendSpoolRow(cfg.spoolFile, row);

        if (!cfg.buildIntegrityEnabled) return;

        const session = resolveSessionKey(ctx, event as unknown as Json);
        const state = getBuildState(session);
        const texts = Array.isArray(event.assistantTexts)
          ? event.assistantTexts.filter((v): v is string => typeof v === "string")
          : [];
        const combined = texts.join("\n");
        const now = Date.now();

        if (BUILD_PROMISE_RE.test(combined)) {
          state.awaitingStartProof = true;
          state.contractAtMs = now;
          state.lastProgressAtMs = now;
          state.baselineToolishCount = Number((row as any).history_toolish_count ?? state.baselineToolishCount ?? 0);
          appendBuildIntegrityRow(cfg, ctx, event as unknown as Json, "contract_declared", {
            session_key: session,
            snippet: preview(combined, 180),
          });
        }

        if (state.active || state.awaitingStartProof) {
          if (BUILD_DONE_RE.test(combined)) {
            state.active = false;
            state.awaitingStartProof = false;
            state.mode = "idle";
            state.lastProgressAtMs = now;
            appendBuildIntegrityRow(cfg, ctx, event as unknown as Json, "final_state_done", {
              session_key: session,
            });
          } else if (BUILD_FAIL_RE.test(combined)) {
            state.active = false;
            state.awaitingStartProof = false;
            state.mode = "idle";
            state.lastProgressAtMs = now;
            appendBuildIntegrityRow(cfg, ctx, event as unknown as Json, "final_state_failed", {
              session_key: session,
            });
          } else if (BUILD_PAUSE_RE.test(combined)) {
            state.active = false;
            state.awaitingStartProof = false;
            state.mode = "paused";
            state.lastProgressAtMs = now;
            appendBuildIntegrityRow(cfg, ctx, event as unknown as Json, "final_state_paused", {
              session_key: session,
            });
          }
        }
      } catch (err) {
        api.logger.warn(`[${PLUGIN_ID}] failed to write llm_output row: ${String(err)}`);
      }
    });
  },
};

export default plugin;
