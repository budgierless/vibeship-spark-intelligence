#!/usr/bin/env python3
"""Build a multidomain memory-retrieval case set from existing real-user/advisory data."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


DEFAULT_INPUTS = [
    Path("benchmarks/data/memory_retrieval_eval_live_2026_02_12.json"),
    Path("benchmarks/data/memory_retrieval_eval_real_user_2026_02_12.json"),
    Path("benchmarks/data/advisory_quality_eval_extended.json"),
    Path("benchmarks/data/advisory_realism_eval_multidomain_v1.json"),
]
DEFAULT_OUT = Path("benchmarks/data/memory_retrieval_eval_multidomain_real_user_2026_02_16.json")

DOMAIN_MARKERS: Dict[str, Sequence[str]] = {
    "x_social": ("x_social", "x-social", "twitter", "tweet", "retweet", "timeline", "engagement"),
    "memory": ("memory", "retrieval", "distillation", "cross-session", "session", "index", "stale"),
    "testing": ("pytest", "unit test", "integration test", "assert", "coverage", "regression"),
    "coding": ("code", "coding", "debug", "refactor", "module", "function", "python", "typescript", "javascript"),
    "ui_design": ("ui", "ux", "layout", "visual", "design", "mobile", "desktop", "typography"),
    "strategy": ("strategy", "roadmap", "prioritize", "tradeoff", "risk", "moat"),
    "marketing": ("marketing", "campaign", "conversion", "audience", "brand", "growth"),
    "research": ("research", "analysis", "evaluate", "compare", "evidence", "paper"),
    "conversation": ("coaching", "advice", "self-improvement", "mindset", "feedback", "reflection"),
    "prompting": ("prompt", "system prompt", "instruction", "few-shot", "token budget"),
}
STOPWORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "with",
    "we",
    "you",
    "our",
}


def _load_rows(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = raw.get("cases") if isinstance(raw, dict) else raw
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _norm_domain(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return "general"
    text = re.sub(r"[^a-z0-9_]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    aliases = {
        "social": "x_social",
        "social_media": "x_social",
        "x": "x_social",
        "ui": "ui_design",
        "ux": "ui_design",
    }
    return aliases.get(text, text) or "general"


def _infer_domain(query: str, notes: str = "", tool: str = "") -> str:
    body = f"{query} {notes} {tool}".strip().lower()
    if not body:
        return "general"
    for domain, markers in DOMAIN_MARKERS.items():
        if any(marker in body for marker in markers):
            return domain
    return "general"


def _extract_keyword_labels(text: str, limit: int = 4) -> List[str]:
    tokens = [t for t in re.findall(r"[a-z0-9_]+", str(text or "").lower()) if len(t) >= 4 and t not in STOPWORDS]
    out: List[str] = []
    seen = set()
    for tok in tokens:
        if tok in seen:
            continue
        seen.add(tok)
        out.append(tok)
        if len(out) >= limit:
            break
    return out


def _as_list_text(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []
    return [str(v).strip() for v in values if str(v).strip()]


def build_cases(inputs: Iterable[Path]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen = set()
    idx = 0
    for source in inputs:
        rows = _load_rows(source)
        for row in rows:
            query = str(row.get("query") or row.get("prompt") or "").strip()
            if not query:
                continue
            notes = str(row.get("notes") or "")
            tool = str(row.get("tool") or "")
            domain = _norm_domain(row.get("domain") or _infer_domain(query=query, notes=notes, tool=tool))
            relevant_keys = _as_list_text(row.get("relevant_insight_keys"))
            relevant_contains = [v.lower() for v in _as_list_text(row.get("relevant_contains"))]
            expected = [v.lower() for v in _as_list_text(row.get("expected_contains"))]
            relevant_contains.extend(expected)
            if not relevant_contains and not relevant_keys:
                relevant_contains = _extract_keyword_labels(query, limit=4)
            relevant_contains = [v for v in dict.fromkeys(relevant_contains) if v]
            if not relevant_contains and not relevant_keys:
                continue
            dedupe_key = (domain, re.sub(r"\s+", " ", query.lower()).strip())
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            idx += 1
            out.append(
                {
                    "id": str(row.get("id") or row.get("case_id") or f"mdru_{idx:04d}"),
                    "domain": domain,
                    "query": query,
                    "relevant_insight_keys": relevant_keys,
                    "relevant_contains": relevant_contains,
                    "notes": f"source={source.name}; {notes}".strip(),
                }
            )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Build multidomain retrieval case set from real-user/advisory data")
    ap.add_argument(
        "--inputs",
        default=",".join(str(p) for p in DEFAULT_INPUTS),
        help="Comma-separated JSON files containing case lists",
    )
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON path")
    args = ap.parse_args()

    inputs = [Path(x.strip()) for x in str(args.inputs or "").split(",") if x.strip()]
    cases = build_cases(inputs)
    counts = Counter(str(row.get("domain") or "general") for row in cases)
    payload = {
        "description": "Multidomain real-user retrieval set built from memory/advisory case corpora.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": [str(p) for p in inputs],
        "case_count": len(cases),
        "domain_counts": dict(sorted(counts.items())),
        "cases": cases,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote: {out_path}")
    print(f"Cases: {len(cases)} domains={dict(sorted(counts.items()))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
