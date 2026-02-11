"""
Advisory Synthesizer: Compose coherent guidance from raw advice items.

Two tiers:
- Tier 1 (No AI): Programmatic composition using templates and priority rules.
  Works immediately, zero dependencies. Always available.

- Tier 2 (AI-Enhanced): Uses local LLM (Ollama) or cloud APIs to synthesize
  multiple insights into coherent, contextual guidance. Falls back to Tier 1.

The synthesizer takes ranked, gate-filtered advice items and produces
a single coherent advisory block suitable for injection into Claude's context.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

from .diagnostics import log_debug

try:
    import httpx as _httpx
except Exception:
    _httpx = None

# ============= Configuration =============

SYNTH_CONFIG_FILE = Path.home() / ".spark" / "tuneables.json"

# LLM provider config (reuses existing Pulse patterns)
OLLAMA_API = os.getenv("SPARK_OLLAMA_API", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("SPARK_OLLAMA_MODEL", "phi4-mini")  # Default quality-first local model; override via SPARK_OLLAMA_MODEL

# Cloud fallback (only used if local unavailable and keys present)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("CODEX_API_KEY")
OPENAI_MODEL = os.getenv("SPARK_OPENAI_MODEL", "gpt-4o-mini")  # Cost-efficient

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
ANTHROPIC_MODEL = os.getenv("SPARK_ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = os.getenv("SPARK_GEMINI_MODEL", "gemini-2.0-flash")

# Synthesis mode: "auto" (try AI → fall back to programmatic), "ai_only", "programmatic"
SYNTH_MODE = os.getenv("SPARK_SYNTH_MODE", "auto")

# Max time for AI synthesis (fail fast - hooks must be quick)
AI_TIMEOUT_S = float(os.getenv("SPARK_SYNTH_TIMEOUT", "3.0"))

# Cache synthesized results (same inputs → same output)
_synth_cache: Dict[str, tuple] = {}  # key → (result, timestamp)
CACHE_TTL_S = 120
MAX_CACHE_ENTRIES = 50
PREFERRED_PROVIDER: Optional[str] = None
_CONFIG_MTIME_S: Optional[float] = None


def _sanitize_mode(raw: Any) -> str:
    mode = str(raw or "").strip().lower()
    return mode if mode in {"auto", "ai_only", "programmatic"} else "auto"


def _sanitize_provider(raw: Any) -> Optional[str]:
    provider = str(raw or "").strip().lower()
    if provider in {"", "auto", "none"}:
        return None
    return provider if provider in {"ollama", "gemini", "openai", "anthropic"} else None


def _apply_synth_config(cfg: Dict[str, Any]) -> Dict[str, List[str]]:
    """Apply synthesizer config dict to module-level runtime settings."""
    global SYNTH_MODE, AI_TIMEOUT_S, CACHE_TTL_S, MAX_CACHE_ENTRIES, PREFERRED_PROVIDER
    applied: List[str] = []
    warnings: List[str] = []
    if not isinstance(cfg, dict):
        return {"applied": applied, "warnings": warnings}

    if "mode" in cfg:
        SYNTH_MODE = _sanitize_mode(cfg.get("mode"))
        applied.append("mode")

    if "ai_timeout_s" in cfg:
        try:
            AI_TIMEOUT_S = max(0.2, float(cfg.get("ai_timeout_s")))
            applied.append("ai_timeout_s")
        except Exception:
            warnings.append("invalid_ai_timeout_s")

    if "cache_ttl_s" in cfg:
        try:
            CACHE_TTL_S = max(0, int(cfg.get("cache_ttl_s")))
            applied.append("cache_ttl_s")
        except Exception:
            warnings.append("invalid_cache_ttl_s")

    if "max_cache_entries" in cfg:
        try:
            MAX_CACHE_ENTRIES = max(1, int(cfg.get("max_cache_entries")))
            applied.append("max_cache_entries")
            while len(_synth_cache) > MAX_CACHE_ENTRIES:
                oldest = min(_synth_cache, key=lambda k: _synth_cache[k][1])
                _synth_cache.pop(oldest, None)
        except Exception:
            warnings.append("invalid_max_cache_entries")

    if "preferred_provider" in cfg:
        PREFERRED_PROVIDER = _sanitize_provider(cfg.get("preferred_provider"))
        applied.append("preferred_provider")

    return {"applied": applied, "warnings": warnings}


def apply_synth_config(cfg: Dict[str, Any]) -> Dict[str, List[str]]:
    """Public runtime hook so Pulse can hot-apply synthesizer tuneables."""
    return _apply_synth_config(cfg)


def _load_synth_config() -> dict:
    """Load synthesis config from tuneables.json → 'synthesizer' section."""
    try:
        if SYNTH_CONFIG_FILE.exists():
            data = json.loads(SYNTH_CONFIG_FILE.read_text(encoding="utf-8"))
            return data.get("synthesizer") or {}
    except Exception:
        pass
    return {}


def _refresh_synth_config(force: bool = False) -> None:
    """Reload config from tuneables when file changes."""
    global _CONFIG_MTIME_S
    try:
        mtime = SYNTH_CONFIG_FILE.stat().st_mtime if SYNTH_CONFIG_FILE.exists() else None
    except Exception:
        mtime = None
    if not force and mtime == _CONFIG_MTIME_S:
        return
    _CONFIG_MTIME_S = mtime
    cfg = _load_synth_config()
    _apply_synth_config(cfg if isinstance(cfg, dict) else {})


_refresh_synth_config(force=True)


# ============= Tier 1: Programmatic Synthesis =============

def synthesize_programmatic(
    advice_items: list,
    phase: str = "implementation",
    user_intent: str = "",
    tool_name: str = "",
) -> str:
    """
    Compose a coherent advisory block from advice items WITHOUT any AI.

    Uses structured templates that group insights by type and priority.
    This is the always-available baseline.
    """
    if not advice_items:
        return ""

    sections = []

    # Group by authority/type
    warnings = []
    notes = []
    whispers = []

    for item in advice_items:
        authority = getattr(item, "_authority", "note")  # Set by gate
        text = getattr(item, "text", str(item))
        confidence = getattr(item, "confidence", 0.5)
        reason = getattr(item, "reason", "")
        source = getattr(item, "source", "")

        entry = {
            "text": text,
            "confidence": confidence,
            "reason": reason,
            "source": source,
        }

        if authority == "warning":
            warnings.append(entry)
        elif authority == "whisper":
            whispers.append(entry)
        else:
            notes.append(entry)

    # Build the block
    if warnings:
        sections.append("**Cautions:**")
        for w in warnings[:2]:
            conf = f" ({w['confidence']:.0%})" if w['confidence'] >= 0.7 else ""
            sections.append(f"- {w['text']}{conf}")

    if notes:
        if warnings:
            sections.append("")
        sections.append("**Relevant context:**")
        for n in notes[:3]:
            # Strip leading tags like [Caution], [Past Failure] for cleaner display
            text = n["text"]
            text = text.lstrip("[").split("]", 1)[-1].strip() if text.startswith("[") else text
            sections.append(f"- {text}")

    if not sections:
        return ""

    return "\n".join(sections)


# ============= Tier 2: AI-Enhanced Synthesis =============

def synthesize_with_ai(
    advice_items: list,
    phase: str = "implementation",
    user_intent: str = "",
    tool_name: str = "",
    provider: Optional[str] = None,
) -> Optional[str]:
    """
    Use LLM to synthesize advice into coherent contextual guidance.

    Returns None if AI is unavailable (Tier 1 fallback should be used).
    """
    if not advice_items:
        return None

    # Build the synthesis prompt
    prompt = _build_synthesis_prompt(advice_items, phase, user_intent, tool_name)

    # Try providers in order: Ollama (local) → OpenAI → Anthropic → Gemini
    providers = _get_provider_chain(provider)

    for prov in providers:
        try:
            result = _query_provider(prov, prompt)
            if result and len(result.strip()) > 10:
                return result.strip()
        except Exception as e:
            log_debug("advisory_synth", f"Provider {prov} failed", e)
            continue

    return None  # All providers failed


def _build_synthesis_prompt(
    advice_items: list,
    phase: str,
    user_intent: str,
    tool_name: str,
) -> str:
    """Build the prompt for AI synthesis."""
    items_text = ""
    for i, item in enumerate(advice_items, 1):
        text = getattr(item, "text", str(item))
        conf = getattr(item, "confidence", 0.5)
        source = getattr(item, "source", "unknown")
        items_text += f"  {i}. [{source}, {conf:.0%}] {text}\n"

    return f"""You are a concise coding advisor. Synthesize these learnings into 1-3 sentences of actionable guidance for the developer.

Current context:
- Task phase: {phase}
- Tool about to use: {tool_name}
- Developer intent: {user_intent or 'not specified'}

Raw insights:
{items_text}
Rules:
- Be direct and specific, no filler
- If insights conflict, note the tension briefly
- Prioritize warnings and failure patterns
- Max 3 sentences. If only 1 insight, 1 sentence is fine
- Do NOT say "based on past learnings" or "according to insights" - just give the guidance
- Format: plain text, no markdown headers"""


def _get_provider_chain(preferred: Optional[str] = None) -> List[str]:
    """Get ordered list of LLM providers to try."""
    chain = []
    preferred_provider = _sanitize_provider(preferred) or PREFERRED_PROVIDER
    if preferred_provider:
        chain.append(preferred_provider)

    # Local first (no cost, no latency to external API)
    if "ollama" not in chain:
        chain.append("ollama")
    # Then cloud fallbacks (by cost: cheapest first)
    if GEMINI_API_KEY and "gemini" not in chain:
        chain.append("gemini")
    if OPENAI_API_KEY and "openai" not in chain:
        chain.append("openai")
    if ANTHROPIC_API_KEY and "anthropic" not in chain:
        chain.append("anthropic")

    return chain


def _query_provider(provider: str, prompt: str) -> Optional[str]:
    """Query a specific LLM provider. Must be fast (< AI_TIMEOUT_S)."""
    if provider == "ollama":
        return _query_ollama(prompt)
    elif provider == "openai":
        return _query_openai(prompt)
    elif provider == "anthropic":
        return _query_anthropic(prompt)
    elif provider == "gemini":
        return _query_gemini(prompt)
    return None


def _query_ollama(prompt: str) -> Optional[str]:
    """Query local Ollama instance via chat API.

    Uses /api/chat (not /api/generate) because Qwen3 models route all
    output to a 'thinking' field with the generate API, producing empty
    responses.  The chat API with think=False avoids this.
    """
    try:
        if _httpx is None:
            log_debug("advisory_synth", "HTTPX_MISSING_OLLAMA", None)
            return None
        with _httpx.Client(timeout=AI_TIMEOUT_S) as client:
            resp = client.post(
                f"{OLLAMA_API}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "think": False,  # Disable thinking for Qwen3 models
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 100,  # 1-3 sentences ≈ 40-80 tokens
                    },
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                msg = data.get("message", {})
                return msg.get("content", "").strip()
    except Exception as e:
        log_debug("advisory_synth", "Ollama query failed", e)
    return None


def _query_openai(prompt: str) -> Optional[str]:
    """Query OpenAI API."""
    if not OPENAI_API_KEY:
        return None
    try:
        if _httpx is None:
            log_debug("advisory_synth", "HTTPX_MISSING_OPENAI", None)
            return None
        with _httpx.Client(timeout=AI_TIMEOUT_S) as client:
            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "model": OPENAI_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 200,
                    "temperature": 0.3,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log_debug("advisory_synth", "OpenAI query failed", e)
    return None


def _query_anthropic(prompt: str) -> Optional[str]:
    """Query Anthropic API."""
    if not ANTHROPIC_API_KEY:
        return None
    try:
        if _httpx is None:
            log_debug("advisory_synth", "HTTPX_MISSING_ANTHROPIC", None)
            return None
        with _httpx.Client(timeout=AI_TIMEOUT_S) as client:
            resp = client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": ANTHROPIC_MODEL,
                    "max_tokens": 200,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("content", [])
                if content:
                    return content[0].get("text", "").strip()
    except Exception as e:
        log_debug("advisory_synth", "Anthropic query failed", e)
    return None


def _query_gemini(prompt: str) -> Optional[str]:
    """Query Google Gemini API."""
    if not GEMINI_API_KEY:
        return None
    try:
        if _httpx is None:
            log_debug("advisory_synth", "HTTPX_MISSING_GEMINI", None)
            return None
        with _httpx.Client(timeout=AI_TIMEOUT_S) as client:
            resp = client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": 200,
                    },
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "").strip()
    except Exception as e:
        log_debug("advisory_synth", "Gemini query failed", e)
    return None


# ============= Main Synthesis Entry Point =============

def synthesize(
    advice_items: list,
    phase: str = "implementation",
    user_intent: str = "",
    tool_name: str = "",
    force_mode: Optional[str] = None,
) -> str:
    """
    Main entry point: synthesize advice into coherent guidance.

    Respects SPARK_SYNTH_MODE:
    - "auto": Try AI first, fall back to programmatic
    - "ai_only": AI only, return empty if unavailable
    - "programmatic": Skip AI entirely (fastest, zero network)

    Args:
        advice_items: Gate-filtered advice objects
        phase: Current task phase
        user_intent: What the user is trying to do
        tool_name: Tool about to be used
        force_mode: Override SYNTH_MODE for this call

    Returns:
        Synthesized advisory text (may be empty if nothing to say)
    """
    _refresh_synth_config()

    if not advice_items:
        return ""

    mode = _sanitize_mode(force_mode) if force_mode else SYNTH_MODE

    # Check cache first
    cache_key = _make_cache_key(advice_items, phase, user_intent, tool_name)
    cached = _synth_cache.get(cache_key)
    if cached:
        result, ts = cached
        if time.time() - ts < CACHE_TTL_S:
            return result

    result = ""

    if mode == "programmatic":
        result = synthesize_programmatic(advice_items, phase, user_intent, tool_name)
    elif mode == "ai_only":
        ai_result = synthesize_with_ai(advice_items, phase, user_intent, tool_name)
        result = ai_result or ""
    else:  # "auto"
        # Try AI synthesis (fast timeout protects hook speed)
        ai_result = synthesize_with_ai(advice_items, phase, user_intent, tool_name)
        if ai_result:
            result = ai_result
        else:
            # Fall back to programmatic
            result = synthesize_programmatic(advice_items, phase, user_intent, tool_name)

    # Cache result
    if result:
        _synth_cache[cache_key] = (result, time.time())
        # Keep cache bounded
        if len(_synth_cache) > MAX_CACHE_ENTRIES:
            oldest = min(_synth_cache, key=lambda k: _synth_cache[k][1])
            _synth_cache.pop(oldest, None)

    return result


def _make_cache_key(items: list, phase: str, intent: str, tool: str) -> str:
    """Generate cache key from inputs."""
    import hashlib
    parts = [phase, intent[:100], tool]
    for item in items[:5]:
        aid = getattr(item, "advice_id", str(item))
        parts.append(str(aid))
    payload = "|".join(parts)
    return hashlib.sha1(payload.encode("utf-8", errors="replace")).hexdigest()[:16]


# ============= AI Availability Check =============

def check_ai_available() -> Dict[str, bool]:
    """Check which AI providers are available. Useful for diagnostics."""
    available = {
        "ollama": False,
        "openai": bool(OPENAI_API_KEY),
        "anthropic": bool(ANTHROPIC_API_KEY),
        "gemini": bool(GEMINI_API_KEY),
    }

    # Quick Ollama check
    try:
        if _httpx is not None:
            with _httpx.Client(timeout=1.5) as client:
                resp = client.get(f"{OLLAMA_API}/api/tags")
                available["ollama"] = resp.status_code == 200
    except Exception:
        pass

    return available


def get_synth_status() -> Dict[str, Any]:
    """Get synthesis system status for diagnostics."""
    _refresh_synth_config()
    ai = check_ai_available()
    any_ai = any(ai.values())
    return {
        "mode": SYNTH_MODE,
        "ai_timeout_s": AI_TIMEOUT_S,
        "cache_ttl_s": CACHE_TTL_S,
        "max_cache_entries": MAX_CACHE_ENTRIES,
        "preferred_provider": PREFERRED_PROVIDER or "auto",
        "httpx_available": _httpx is not None,
        "warning": "httpx_missing" if _httpx is None else None,
        "ai_available": any_ai,
        "providers": ai,
        "tier": 2 if any_ai else 1,
        "tier_label": "AI-Enhanced" if any_ai else "Programmatic",
        "cache_size": len(_synth_cache),
        "ollama_model": OLLAMA_MODEL if ai.get("ollama") else None,
    }
