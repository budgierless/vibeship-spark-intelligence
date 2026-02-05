"""Layered Memory Banks (portable)

Goal
----
Support layered memory without platform coupling:
- Global user preferences (likes/dislikes, comms style, hard boundaries)
- Project-scoped memories (decisions, constraints, project-specific rules)
- Session/ephemeral (optional later)

Design constraints
------------------
- Lightweight + stable: local JSONL files, simple keyword retrieval
- Compatible everywhere: driven by Spark queue + SparkEventV1 payloads
- Natural-language-first UX: users should not need CLI; CLI is for dev/debug

"""

from __future__ import annotations

import json
import re
import time
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from lib.queue import read_recent_events, EventType, _tail_lines


BANK_DIR = Path.home() / ".spark" / "banks"
GLOBAL_FILE = BANK_DIR / "global_user.jsonl"
PROJECTS_DIR = BANK_DIR / "projects"


@dataclass
class BankEntry:
    entry_id: str
    created_at: float
    scope: str                 # global|project|session
    project_key: Optional[str]
    category: str
    text: str
    session_id: Optional[str] = None
    source: Optional[str] = None
    meta: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "created_at": self.created_at,
            "scope": self.scope,
            "project_key": self.project_key,
            "category": self.category,
            "text": self.text,
            "session_id": self.session_id,
            "source": self.source,
            "meta": self.meta or {},
        }


def _ensure_dirs():
    BANK_DIR.mkdir(parents=True, exist_ok=True)
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


def _hash_id(*parts: str) -> str:
    raw = "|".join([p or "" for p in parts]).encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:12]


def infer_project_key(max_events: int = 60) -> Optional[str]:
    """Infer the active project key from recent events.

    We intentionally avoid trusting repo name alone.
    Evidence-based heuristic:
    - Prefer cwd/workdir (if present)
    - Else look for file paths in tool input/results

    Returns a stable-ish project key (folder basename), or None.
    """

    try:
        events = read_recent_events(max_events)
    except Exception:
        return None

    paths: List[str] = []

    def _norm_path(p: str) -> str:
        return (p or "").replace("\\", "/")

    for e in reversed(events):
        data = e.data or {}
        cwd = data.get("cwd")
        if isinstance(cwd, str) and ("/" in cwd or "\\" in cwd):
            paths.append(_norm_path(cwd))

        payload = data.get("payload") or {}
        # Some adapters can put extra meta here
        meta = payload.get("meta") or {}
        for k in ("cwd", "workdir", "workspace"):
            v = meta.get(k)
            if isinstance(v, str) and ("/" in v or "\\" in v):
                paths.append(_norm_path(v))

        tool_input = e.tool_input or {}
        for k in ("path", "file_path", "filePath", "workdir", "cwd"):
            v = tool_input.get(k)
            if isinstance(v, str) and ("/" in v or "\\" in v):
                paths.append(_norm_path(v))

    if not paths:
        return None

    # Prefer something inside a repo-like structure
    def score(p: str) -> int:
        s = 0
        if "/Users/" in p or p.startswith("/"):
            s += 1
        if "/Desktop/" in p or "/clawd/" in p:
            s += 1
        if p.endswith(".py") or p.endswith(".md") or "/src/" in p:
            s += 2
        return s

    best = max(paths, key=score)
    # normalize to directory
    best = best.rstrip("/")
    if "." in Path(best).name:
        best = str(Path(best).parent)

    name = Path(best).name
    if not name:
        return None

    # Small sanitize: keep alnum, dash, underscore
    name = re.sub(r"[^a-zA-Z0-9_\-]", "_", name)
    return name.lower()


def choose_scope(text: str, category: str, project_key: Optional[str]) -> Tuple[str, Optional[str]]:
    """Decide storage scope for a memory entry.

    Rules (aligned with Meta's preferences):
    - 'I hate / I prefer / I love' defaults to GLOBAL
    - explicit project phrasing pushes to project
    - implementation-detail categories lean project when evidence exists
    """

    t = (text or "").lower()

    # Explicit scoping language
    if any(p in t for p in ["for this project", "in this repo", "in this codebase", "in this dashboard"]):
        return ("project", project_key)

    # Global preference defaults
    if re.search(r"\b(i hate|i prefer|i love|i don't like|i dont like)\b", t):
        return ("global", None)

    # Communication style is typically global
    if category in ("communication", "user_understanding"):
        return ("global", None)

    # Reasoning/context can be project-specific if we know project
    if category in ("reasoning", "context") and project_key:
        return ("project", project_key)

    # Meta/wisdom tend global unless explicitly project
    if category in ("meta_learning", "wisdom"):
        return ("global", None)

    # Default: project if we have strong project evidence; else global
    if project_key:
        return ("project", project_key)

    return ("global", None)


def append_entry(entry: BankEntry) -> None:
    _ensure_dirs()
    if entry.scope == "project" and entry.project_key:
        out = PROJECTS_DIR / f"{entry.project_key}.jsonl"
    else:
        out = GLOBAL_FILE

    with out.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")


def store_memory(text: str, category: str, session_id: Optional[str] = None, source: str = "spark") -> Optional[BankEntry]:
    _ensure_dirs()
    if _is_telemetry_memory(text):
        return None
    project_key = infer_project_key()
    scope, proj = choose_scope(text=text, category=category, project_key=project_key)

    entry_id = _hash_id(scope, proj or "", category, text.strip()[:120])
    entry = BankEntry(
        entry_id=entry_id,
        created_at=time.time(),
        scope=scope,
        project_key=proj,
        category=category,
        text=text.strip(),
        session_id=session_id,
        source=source,
        meta={},
    )
    append_entry(entry)
    try:
        from lib.memory_store import upsert_entry

        upsert_entry(
            memory_id=entry.entry_id,
            content=entry.text,
            scope=entry.scope,
            project_key=entry.project_key,
            category=entry.category,
            created_at=entry.created_at,
            source=entry.source or "spark",
            meta=entry.meta or {},
        )
    except Exception:
        pass
    return entry


def _read_jsonl(path: Path, limit: int = 500) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    try:
        lines = _tail_lines(path, max(0, int(limit or 0)))
        for line in reversed(lines):
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    except Exception:
        return []
    return out


def retrieve(query: str, project_key: Optional[str] = None, limit: int = 6) -> List[Dict[str, Any]]:
    """Retrieve relevant memories from project + global banks.

    Lightweight keyword match + recency.
    """

    q = (query or "").lower().strip()
    if not q:
        return []

    out: List[Dict[str, Any]] = []
    seen = set()
    try:
        from lib.memory_store import retrieve as store_retrieve

        out = store_retrieve(query, project_key=project_key, limit=limit)
        for it in out:
            text = (it.get("text") or "").strip()
            if _is_telemetry_memory(text):
                continue
            key = it.get("entry_id") or it.get("text")
            if key:
                seen.add(key)
    except Exception:
        out = []

    candidates: List[Dict[str, Any]] = []

    if project_key:
        candidates.extend(_read_jsonl(PROJECTS_DIR / f"{project_key}.jsonl", limit=800))

    candidates.extend(_read_jsonl(GLOBAL_FILE, limit=800))

    scored: List[Tuple[float, Dict[str, Any]]] = []
    q_words = [w for w in re.split(r"\W+", q) if len(w) > 2]

    for it in candidates:
        text = (it.get("text") or "").lower()
        if not text:
            continue
        if _is_telemetry_memory(text):
            continue

        # basic scoring
        score = 0.0
        if q in text:
            score += 2.0
        for w in q_words[:8]:
            if w in text:
                score += 0.25

        # project memories slightly boosted when in project
        if project_key and it.get("project_key") == project_key:
            score += 0.4

        # recency boost
        created = float(it.get("created_at") or 0.0)
        age = max(1.0, time.time() - created)
        score += min(0.4, 50000.0 / age / 100000.0)

        if score > 0.25:
            scored.append((score, it))

    scored.sort(key=lambda t: t[0], reverse=True)
    for _, it in scored:
        text = (it.get("text") or "").strip()
        if _is_telemetry_memory(text):
            continue
        key = it.get("entry_id") or it.get("text")
        if key and key in seen:
            continue
        out.append(it)
        if len(out) >= max(0, int(limit or 0)):
            break
    return out


# =============================================================================
# Phase 3.5: Sync Cognitive Insights to Memory Banks
# =============================================================================

def sync_insights_to_banks(
    min_reliability: float = 0.7,
    categories: Optional[List[str]] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Sync high-value cognitive insights to memory banks.

    This ensures that validated insights are stored in the appropriate
    memory bank (global or project) for fast retrieval.

    Args:
        min_reliability: Minimum reliability threshold (0.0-1.0)
        categories: Categories to sync (default: user_understanding, communication)
        dry_run: If True, don't store, just return what would be synced

    Returns:
        Stats about syncing: processed, synced, skipped, duplicates
    """
    from lib.cognitive_learner import get_cognitive_learner, CognitiveCategory

    if categories is None:
        categories = ["user_understanding", "communication", "wisdom"]

    # Map string categories to enum values
    category_map = {
        "user_understanding": CognitiveCategory.USER_UNDERSTANDING,
        "communication": CognitiveCategory.COMMUNICATION,
        "wisdom": CognitiveCategory.WISDOM,
        "reasoning": CognitiveCategory.REASONING,
        "context": CognitiveCategory.CONTEXT,
        "meta_learning": CognitiveCategory.META_LEARNING,
        "self_awareness": CognitiveCategory.SELF_AWARENESS,
    }

    target_categories = set()
    for cat in categories:
        if cat in category_map:
            target_categories.add(category_map[cat])

    cog = get_cognitive_learner()

    # Get existing entries to avoid duplicates
    existing_texts = set()
    for entry in _read_jsonl(GLOBAL_FILE, limit=2000):
        text = (entry.get("text") or "").strip().lower()
        if text:
            existing_texts.add(text[:120])

    stats = {"processed": 0, "synced": 0, "skipped": 0, "duplicates": 0, "entries": []}

    for key, insight in cog.insights.items():
        if insight.category not in target_categories:
            continue

        stats["processed"] += 1

        # Check reliability threshold
        reliability = getattr(insight, "reliability", 0.0)
        if reliability < min_reliability:
            stats["skipped"] += 1
            continue

        insight_text = getattr(insight, "insight", "") or str(insight)
        if not insight_text:
            stats["skipped"] += 1
            continue

        # Check for duplicates
        normalized = insight_text.strip().lower()[:120]
        if normalized in existing_texts:
            stats["duplicates"] += 1
            continue

        # Determine category string
        cat_str = insight.category.value if hasattr(insight.category, "value") else str(insight.category)

        if not dry_run:
            store_memory(
                text=insight_text,
                category=cat_str,
                source="cognitive_sync",
            )
            existing_texts.add(normalized)

        stats["synced"] += 1
        stats["entries"].append({
            "key": key,
            "category": cat_str,
            "reliability": round(reliability, 2),
            "preview": insight_text[:80],
        })

    return stats


def get_bank_stats() -> Dict[str, Any]:
    """Get statistics about memory banks."""
    _ensure_dirs()

    global_entries = _read_jsonl(GLOBAL_FILE, limit=5000)

    project_files = list(PROJECTS_DIR.glob("*.jsonl"))
    project_counts = {}
    for pf in project_files:
        entries = _read_jsonl(pf, limit=2000)
        project_counts[pf.stem] = len(entries)

    # Count by category
    by_category = {}
    for entry in global_entries:
        cat = entry.get("category", "unknown")
        by_category[cat] = by_category.get(cat, 0) + 1

    return {
        "global_entries": len(global_entries),
        "project_files": len(project_files),
        "project_counts": project_counts,
        "by_category": by_category,
    }


# =============================================================================
# Maintenance: Purge Telemetry/Sequence Noise
# =============================================================================

def _is_telemetry_memory(text: str) -> bool:
    """Return True if memory entry is operational telemetry or tool sequence noise."""
    if not text:
        return True
    t = text.strip()
    tl = t.lower()

    if t.startswith("Sequence '") or t.startswith('Sequence "'):
        return True
    if "sequence" in tl and ("worked" in tl or "pattern" in tl):
        return True
    if t.startswith("Pattern '") and "->" in t and "risky" not in tl:
        return True

    if "->" in t and any(s in tl for s in ["sequence", "pattern", "worked well", "works well"]):
        return True

    if re.search(r"\bheavy\s+\w+\s+usage\b", tl):
        return True
    if re.search(r"\busage\s*\(\d+\s*calls?\)", tl):
        return True
    if "usage count" in tl or tl.startswith("usage "):
        return True

    if t.startswith("User was satisfied after:") or t.startswith("User frustrated after:"):
        return True

    return False


def purge_telemetry_entries(
    include_global: bool = True,
    dry_run: bool = False,
    max_preview: int = 20,
) -> Dict[str, Any]:
    """Purge telemetry/sequence noise from memory banks."""
    _ensure_dirs()
    targets: List[Path] = []
    if include_global:
        targets.append(GLOBAL_FILE)
    targets.extend(PROJECTS_DIR.glob("*.jsonl"))

    removed = 0
    by_file: Dict[str, int] = {}
    preview: List[str] = []

    for path in targets:
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        kept: List[str] = []
        removed_here = 0
        for line in lines:
            try:
                row = json.loads(line)
            except Exception:
                # Keep malformed rows rather than delete.
                kept.append(line)
                continue
            text = (row.get("text") or "").strip()
            if _is_telemetry_memory(text):
                removed_here += 1
                if len(preview) < max(0, int(max_preview or 0)):
                    preview.append(text[:120])
                continue
            kept.append(line)

        if removed_here:
            removed += removed_here
            by_file[path.name] = removed_here
            if not dry_run:
                path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")

    return {
        "removed": removed,
        "by_file": by_file,
        "preview": preview,
        "dry_run": dry_run,
    }
