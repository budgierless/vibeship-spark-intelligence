"""Heuristics for filtering primitive/operational text from learnings."""

from __future__ import annotations

import re

from lib.noise_patterns import TOOL_TOKENS, TOOL_TOKEN_RE, PRIMITIVE_KEYWORDS, ARROW_RE

# Backward-compat aliases for any external consumers.
_TOOL_TOKENS = TOOL_TOKENS
_PRIM_KW = PRIMITIVE_KEYWORDS
_TOOL_RE = TOOL_TOKEN_RE
_TOOL_ERROR_KEY_RE = re.compile(r"\\btool[_\\s-]*\\d+[_\\s-]*error\\b", re.I)


def is_primitive_text(text: str) -> bool:
    """Return True when text looks like low-level operational telemetry."""
    if not text:
        return False
    tl = text.lower()
    if _TOOL_ERROR_KEY_RE.search(tl):
        return True
    if "i struggle with tool_" in tl and "_error" in tl:
        return True
    if "error_pattern:" in tl:
        return True
    if "status code 404" in tl and ("webfetch" in tl or "request failed" in tl):
        return True
    if "->" in text or "→" in text:
        return True
    if "sequence" in tl and ("work" in tl or "pattern" in tl):
        return True
    if _TOOL_RE.search(tl) and any(k in tl for k in _PRIM_KW):
        return True
    return False
