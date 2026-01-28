"""Project context detection and lightweight relevance filtering."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


CACHE_PATH = Path.home() / ".spark" / "project_context.json"
TOPLEVEL_FILES = (
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
)


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _load_cache() -> Dict[str, Any]:
    if not CACHE_PATH.exists():
        return {}
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_cache(cache: Dict[str, Any]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def _file_signatures(root: Path) -> Dict[str, Optional[float]]:
    sig: Dict[str, Optional[float]] = {}
    for name in TOPLEVEL_FILES:
        path = root / name
        if path.exists():
            try:
                sig[name] = path.stat().st_mtime
            except Exception:
                sig[name] = None
        else:
            sig[name] = None
    return sig


def _parse_package_json(path: Path) -> Dict[str, List[str]]:
    out = {"languages": ["javascript"], "frameworks": [], "tools": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return out

    deps: Dict[str, Any] = {}
    for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        if isinstance(data.get(key), dict):
            deps.update(data[key])

    dep_names = {k.lower() for k in deps.keys()}
    if "typescript" in dep_names:
        out["languages"].append("typescript")

    frameworks = [
        ("react", "react"),
        ("next", "next"),
        ("next.js", "next"),
        ("vue", "vue"),
        ("svelte", "svelte"),
    ]
    for token, label in frameworks:
        if token in dep_names and label not in out["frameworks"]:
            out["frameworks"].append(label)

    tools = [
        ("jest", "jest"),
        ("vitest", "vitest"),
        ("eslint", "eslint"),
        ("prettier", "prettier"),
    ]
    for token, label in tools:
        if token in dep_names and label not in out["tools"]:
            out["tools"].append(label)

    return out


def _parse_requirements(path: Path) -> List[str]:
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return []
    names = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name = re.split(r"[<=>;\\[]", line, maxsplit=1)[0].strip()
        if name:
            names.append(name.lower())
    return names


def detect_project_context(root: Path) -> Dict[str, Any]:
    """Detect project context using only top-level files."""
    root = Path(root).resolve()
    context = {
        "root": str(root),
        "languages": [],
        "frameworks": [],
        "tools": [],
        "detected_at": _now_iso(),
    }

    package_json = root / "package.json"
    if package_json.exists():
        parsed = _parse_package_json(package_json)
        context["languages"].extend(parsed.get("languages", []))
        context["frameworks"].extend(parsed.get("frameworks", []))
        context["tools"].extend(parsed.get("tools", []))

    if (root / "requirements.txt").exists() or (root / "pyproject.toml").exists():
        if "python" not in context["languages"]:
            context["languages"].append("python")

    if (root / "go.mod").exists():
        context["languages"].append("go")

    if (root / "Cargo.toml").exists():
        context["languages"].append("rust")

    if (root / "pom.xml").exists() or (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
        context["languages"].append("java")

    # Lightweight framework/tool hints from Python files
    reqs = _parse_requirements(root / "requirements.txt") if (root / "requirements.txt").exists() else []
    if (root / "pyproject.toml").exists():
        try:
            pyproject = (root / "pyproject.toml").read_text(encoding="utf-8").lower()
        except Exception:
            pyproject = ""
        for name in ("django", "flask", "fastapi"):
            if name in pyproject:
                context["frameworks"].append(name)
        if "pytest" in pyproject:
            context["tools"].append("pytest")
        if "poetry" in pyproject:
            context["tools"].append("poetry")

    for name in ("django", "flask", "fastapi"):
        if name in reqs and name not in context["frameworks"]:
            context["frameworks"].append(name)
    if "pytest" in reqs and "pytest" not in context["tools"]:
        context["tools"].append("pytest")

    # De-dupe while preserving order
    for key in ("languages", "frameworks", "tools"):
        seen = set()
        deduped = []
        for item in context[key]:
            if item in seen:
                continue
            seen.add(item)
            deduped.append(item)
        context[key] = deduped

    return context


def get_project_context(root: Path, use_cache: bool = True) -> Dict[str, Any]:
    root = Path(root).resolve()
    sig = _file_signatures(root)

    if use_cache:
        cache = _load_cache()
        entry = cache.get(str(root))
        if isinstance(entry, dict):
            cached_sig = entry.get("files") or {}
            if cached_sig == sig and isinstance(entry.get("context"), dict):
                return entry["context"]

    context = detect_project_context(root)
    cache = _load_cache() if use_cache else {}
    cache[str(root)] = {"files": sig, "context": context}
    _save_cache(cache)
    return context


_LANGUAGE_RULES = {
    "python": [
        r"\bpython\b",
        r"\bpytest\b",
        r"\bpyproject\b",
        r"\bpoetry\b",
        r"\bpip\b",
        r"\bvenv\b",
        r"\bdjango\b",
        r"\bflask\b",
        r"\bfastapi\b",
    ],
    "javascript": [
        r"\bjavascript\b",
        r"\bnode\b",
        r"\bnpm\b",
        r"\byarn\b",
        r"\bpnpm\b",
    ],
    "typescript": [
        r"\btypescript\b",
        r"\btsconfig\b",
    ],
    "go": [
        r"\bgolang\b",
        r"\bgo\\.mod\b",
    ],
    "rust": [
        r"\brust\b",
        r"\bcargo\b",
    ],
    "java": [
        r"\bjava\b",
        r"\bmaven\b",
        r"\bgradle\b",
    ],
}

_FRAMEWORK_RULES = {
    "react": [r"\breact\b"],
    "next": [r"\bnext\\.js\b", r"\bnextjs\b"],
    "vue": [r"\bvue\b"],
    "svelte": [r"\bsvelte\b"],
    "django": [r"\bdjango\b"],
    "flask": [r"\bflask\b"],
    "fastapi": [r"\bfastapi\b"],
}

_FRAMEWORK_BASE = {
    "react": "javascript",
    "next": "javascript",
    "vue": "javascript",
    "svelte": "javascript",
    "django": "python",
    "flask": "python",
    "fastapi": "python",
}


def _matches_any(text: str, patterns: Iterable[str]) -> bool:
    for pattern in patterns:
        if re.search(pattern, text):
            return True
    return False


def is_insight_relevant(insight_text: str, context: Dict[str, Any]) -> bool:
    if not insight_text:
        return True
    languages = set((context or {}).get("languages") or [])
    frameworks = set((context or {}).get("frameworks") or [])

    # If we cannot detect languages/frameworks, do not filter.
    if not languages and not frameworks:
        return True

    text = insight_text.lower()

    for lang, patterns in _LANGUAGE_RULES.items():
        if _matches_any(text, patterns):
            if languages and lang not in languages:
                return False

    for fw, patterns in _FRAMEWORK_RULES.items():
        if not _matches_any(text, patterns):
            continue
        base = _FRAMEWORK_BASE.get(fw)
        if fw in frameworks:
            continue
        if base and languages and base in languages:
            continue
        if base and languages and base not in languages:
            return False
        if frameworks and fw not in frameworks:
            return False

    return True


def filter_insights_for_context(
    insights: Iterable[Any],
    context: Dict[str, Any],
) -> List[Any]:
    """Filter insights by project context based on insight text."""
    filtered = []
    for ins in insights:
        text = getattr(ins, "insight", "")
        if is_insight_relevant(text, context):
            filtered.append(ins)
    return filtered
