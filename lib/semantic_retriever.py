"""Semantic retrieval for cognitive insights (hybrid: triggers + semantic + outcomes).

Designed to be low-risk:
- Disabled by default unless enabled in ~/.spark/tuneables.json or SPARK_SEMANTIC_ENABLED=1
- Falls back gracefully if embeddings are unavailable
- Uses lightweight SQLite index for vectors
"""

from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import time
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .embeddings import embed_text, embed_texts
from .diagnostics import log_debug


DEFAULT_CONFIG = {
    "enabled": False,
    "embedding_provider": "local",
    "embedding_model": "BAAI/bge-small-en-v1.5",
    "min_similarity": 0.6,
    "min_fusion_score": 0.5,
    "weight_recency": 0.2,
    "weight_outcome": 0.3,
    "mmr_lambda": 0.5,
    "dedupe_similarity": 0.92,
    "max_results": 8,
    "index_on_write": True,
    "index_on_read": True,
    "index_backfill_limit": 300,
    "index_cache_ttl_seconds": 120,
    "exclude_categories": [],
    "trigger_rules_file": "~/.spark/trigger_rules.yaml",
    "category_caps": {
        "cognitive": 3,
        "trigger": 2,
        "default": 2,
    },
    "category_exclude": [],
    "triggers_enabled": False,
    "log_retrievals": True,
}


DEFAULT_TRIGGER_RULES = {
    "version": 1,
    "rules": [
        {
            "name": "auth_security",
            "pattern": r"auth|login|password|token|session|jwt|oauth",
            "priority": "high",
            "surface_text": [
                "Validate authentication inputs server-side and avoid trusting client checks.",
                "Never log secrets or tokens; redact sensitive data in logs.",
            ],
        },
        {
            "name": "destructive_commands",
            "pattern": r"rm -rf|delete.*prod|drop table|truncate",
            "priority": "critical",
            "interrupt": True,
            "surface_text": [
                "Double-check destructive commands and confirm targets before executing.",
                "Run a dry-run or backup before irreversible operations.",
            ],
        },
        {
            "name": "deployment",
            "pattern": r"deploy|release|push.*main|merge.*master|prod",
            "priority": "high",
            "surface_text": [
                "Before deploy: run tests, verify migrations, and confirm env vars.",
            ],
        },
    ],
    "learned": [],
}


@dataclass
class TriggerMatch:
    rule_name: str
    priority: str
    surface: List[str]
    surface_text: List[str]
    interrupt: bool = False


@dataclass
class SemanticResult:
    insight_key: str
    insight_text: str
    semantic_sim: float = 0.0
    trigger_conf: float = 0.0
    recency_score: float = 0.0
    outcome_score: float = 0.5
    fusion_score: float = 0.0
    source_type: str = "semantic"  # semantic | trigger | both
    category: str = "cognitive"
    priority: str = "normal"
    why: str = ""


class TriggerMatcher:
    def __init__(self, rules_file: Optional[str] = None):
        self.rules_file = rules_file
        self.rules = self._load_rules()

    def _load_rules(self) -> Dict[str, Any]:
        rules = DEFAULT_TRIGGER_RULES
        path = Path(os.path.expanduser(self.rules_file or ""))
        if path and path.exists():
            try:
                import yaml
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("rules"):
                    rules = data
            except Exception:
                pass
        return rules

    def match(self, context: str) -> List[TriggerMatch]:
        if not context:
            return []
        matches: List[TriggerMatch] = []
        ctx = context.lower()
        for rule in self.rules.get("rules", []) or []:
            pattern = rule.get("pattern") or ""
            if not pattern:
                continue
            try:
                if not re.search(pattern, ctx, re.IGNORECASE):
                    continue
            except re.error:
                continue
            context_pattern = rule.get("context_pattern")
            if context_pattern:
                try:
                    if not re.search(context_pattern, ctx, re.IGNORECASE):
                        continue
                except re.error:
                    continue
            matches.append(
                TriggerMatch(
                    rule_name=str(rule.get("name") or "rule"),
                    priority=str(rule.get("priority") or "normal"),
                    surface=list(rule.get("surface") or []),
                    surface_text=list(rule.get("surface_text") or []),
                    interrupt=bool(rule.get("interrupt") or False),
                )
            )
        return matches


class SemanticIndex:
    def __init__(self, path: Optional[Path] = None, cache_ttl_s: int = 120):
        self.path = path or (Path.home() / ".spark" / "semantic" / "insights_vec.sqlite")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_ttl_s = cache_ttl_s
        self._cache_ts = 0.0
        self._cache: Optional[List[Tuple[str, List[float], float]]] = None
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS insights_vec (
                    insight_key TEXT PRIMARY KEY,
                    content_hash TEXT,
                    dim INTEGER,
                    vector BLOB,
                    updated_at REAL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path))
        conn.row_factory = sqlite3.Row
        return conn

    def _vector_to_blob(self, vec: List[float]) -> bytes:
        import array
        arr = array.array("f", vec)
        return arr.tobytes()

    def _blob_to_vector(self, blob: bytes) -> List[float]:
        import array
        arr = array.array("f")
        arr.frombytes(blob)
        return list(arr)

    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()

    def _invalidate_cache(self) -> None:
        self._cache = None
        self._cache_ts = 0.0

    def _load_cache(self) -> List[Tuple[str, List[float], float]]:
        now = time.time()
        if self._cache is not None and now - self._cache_ts < self.cache_ttl_s:
            return self._cache
        items: List[Tuple[str, List[float], float]] = []
        with self._connect() as conn:
            rows = conn.execute("SELECT insight_key, vector FROM insights_vec").fetchall()
        for row in rows:
            vec = self._blob_to_vector(row["vector"])
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            items.append((row["insight_key"], vec, norm))
        self._cache = items
        self._cache_ts = now
        return items

    def existing_hashes(self) -> Dict[str, str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT insight_key, content_hash FROM insights_vec").fetchall()
        return {r["insight_key"]: r["content_hash"] for r in rows}

    def add_many(self, items: List[Tuple[str, str]]) -> int:
        if not items:
            return 0
        hashes = self.existing_hashes()
        to_embed: List[Tuple[str, str, str]] = []
        for key, text in items:
            if not text:
                continue
            content_hash = self._hash_text(text)
            if hashes.get(key) == content_hash:
                continue
            to_embed.append((key, text, content_hash))
        if not to_embed:
            return 0

        vectors = embed_texts([t for _, t, _ in to_embed])
        if not vectors:
            return 0

        now = time.time()
        with self._connect() as conn:
            for (key, _, content_hash), vec in zip(to_embed, vectors):
                conn.execute(
                    "INSERT OR REPLACE INTO insights_vec (insight_key, content_hash, dim, vector, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (key, content_hash, len(vec), self._vector_to_blob(vec), now),
                )
            conn.commit()

        self._invalidate_cache()
        return len(to_embed)

    def add(self, key: str, text: str) -> bool:
        return self.add_many([(key, text)]) > 0

    def upsert(self, key: str, vector: List[float]) -> bool:
        """Upsert a precomputed vector directly (no embedding)."""
        if not key or not vector:
            return False
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO insights_vec (insight_key, content_hash, dim, vector, updated_at) VALUES (?, ?, ?, ?, ?)",
                (key, None, len(vector), self._vector_to_blob(vector), now),
            )
            conn.commit()
        self._invalidate_cache()
        return True

    def get(self, key: str) -> Optional[List[float]]:
        """Return a vector for a given insight_key if present."""
        if not key:
            return None
        items = self._load_cache()
        for k, vec, _ in items:
            if k == key:
                return vec
        return None

    def ensure_index(self, insights: Dict[str, Any], max_items: int = 300) -> int:
        if not insights:
            return 0
        hashes = self.existing_hashes()
        def _score(item: Tuple[str, Any]) -> float:
            _, insight = item
            rel = getattr(insight, "reliability", 0.5)
            return rel
        items = sorted(insights.items(), key=_score, reverse=True)
        missing: List[Tuple[str, str]] = []
        for key, insight in items:
            text = f"{getattr(insight, 'insight', '')} {getattr(insight, 'context', '')}".strip()
            if not text:
                continue
            content_hash = self._hash_text(text)
            if hashes.get(key) == content_hash:
                continue
            missing.append((key, text))
            if len(missing) >= max_items:
                break
        return self.add_many(missing)

    def search(self, query_vec: List[float], limit: int = 10) -> List[Tuple[str, float]]:
        if not query_vec:
            return []
        qnorm = math.sqrt(sum(x * x for x in query_vec)) or 1.0
        items = self._load_cache()
        scores: List[Tuple[str, float]] = []
        for key, vec, vnorm in items:
            dot = 0.0
            for a, b in zip(query_vec, vec):
                dot += a * b
            sim = dot / (qnorm * vnorm)
            scores.append((key, sim))
        scores.sort(key=lambda t: t[1], reverse=True)
        return scores[:limit]


class SemanticRetriever:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or _load_config()
        self.trigger_matcher = TriggerMatcher(self.config.get("trigger_rules_file"))
        self.index = SemanticIndex(cache_ttl_s=int(self.config.get("index_cache_ttl_seconds", 120)))
        self._index_warmed = False

    def retrieve(self, context: str, insights: Dict[str, Any], limit: int = 8) -> List[SemanticResult]:
        if not context:
            return []

        start_ts = time.time()
        query = self._extract_intent(context)
        results: List[SemanticResult] = []
        seen: set[str] = set()
        trigger_matches: List[TriggerMatch] = []
        semantic_candidates: List[Tuple[str, float]] = []
        embedding_available = False

        # Trigger rules (optional)
        if self.config.get("triggers_enabled", False):
            trigger_matches = self.trigger_matcher.match(context)
            for match in trigger_matches:
                for text in match.surface_text or []:
                    key = f"trigger:{match.rule_name}:{hashlib.sha1(text.encode()).hexdigest()[:8]}"
                    if key in seen:
                        continue
                    seen.add(key)
                    results.append(
                        SemanticResult(
                            insight_key=key,
                            insight_text=text,
                            trigger_conf=1.0,
                            source_type="trigger",
                            category="trigger",
                            priority=match.priority,
                            why=f"Trigger: {match.rule_name}",
                        )
                    )
                for surface in match.surface or []:
                    # Exact key match
                    if surface in insights and surface not in seen:
                        seen.add(surface)
                        ins = insights[surface]
                        results.append(
                            SemanticResult(
                                insight_key=surface,
                                insight_text=getattr(ins, "insight", ""),
                                trigger_conf=1.0,
                                source_type="trigger",
                                category=self._infer_category(ins),
                                priority=match.priority,
                                why=f"Trigger: {match.rule_name}",
                            )
                        )
                        continue
                    # Fallback: find insights containing surface token
                    surface_lower = surface.lower()
                    for key, ins in insights.items():
                        if key in seen:
                            continue
                        text = getattr(ins, "insight", "") or ""
                        if surface_lower and surface_lower in text.lower():
                            seen.add(key)
                            results.append(
                                SemanticResult(
                                    insight_key=key,
                                    insight_text=text,
                                    trigger_conf=1.0,
                                    source_type="trigger",
                                    category=self._infer_category(ins),
                                    priority=match.priority,
                                    why=f"Trigger: {match.rule_name}",
                                )
                            )

        # Ensure index warmed
        if self.config.get("index_on_read", True) and not self._index_warmed:
            try:
                self.index.ensure_index(insights, max_items=int(self.config.get("index_backfill_limit", 300)))
            finally:
                self._index_warmed = True

        # Semantic search
        qvec = embed_text(query)
        if qvec:
            embedding_available = True
            semantic_candidates = self.index.search(qvec, limit=limit * 3)
            for key, sim in semantic_candidates:
                if key in seen:
                    continue
                insight = insights.get(key)
                if not insight:
                    continue
                seen.add(key)
                results.append(
                    SemanticResult(
                        insight_key=key,
                        insight_text=getattr(insight, "insight", ""),
                        semantic_sim=sim,
                        source_type="semantic",
                        category=self._infer_category(insight),
                        priority=self._infer_priority(sim),
                        why=f"Semantic: {sim:.2f} similar",
                    )
                )

        # Enrich scores
        for r in results:
            insight = insights.get(r.insight_key)
            if insight:
                r.recency_score = self._compute_recency(insight)
                r.outcome_score = self._get_outcome_effectiveness(r.insight_key, insight)

        # Category exclusions (semantic results only)
        exclude = set(self.config.get("category_exclude") or [])
        if exclude:
            results = [
                r for r in results
                if r.source_type == "trigger" or (r.category not in exclude)
            ]

        # Gate: semantic similarity (triggers bypass)
        min_sim = float(self.config.get("min_similarity", 0.6))
        results = [
            r for r in results
            if r.source_type == "trigger" or r.semantic_sim >= min_sim
        ]

        # Exclude noisy categories if configured
        exclude = {str(c).lower() for c in (self.config.get("exclude_categories") or []) if c}
        if exclude:
            results = [
                r for r in results
                if (r.category or "").lower() not in exclude
            ]

        # Fusion score
        for r in results:
            r.fusion_score = self._compute_fusion(r)

        # Filter by fusion score
        min_fusion = float(self.config.get("min_fusion_score", 0.5))
        results = [r for r in results if r.fusion_score >= min_fusion]

        # Sort by fusion score
        results.sort(key=lambda r: r.fusion_score, reverse=True)

        # Dedupe by embedding similarity (cheap, prevents near-duplicates)
        dedupe_sim = float(self.config.get("dedupe_similarity", 0.0) or 0.0)
        if dedupe_sim > 0:
            results = self._dedupe_by_embedding(results, dedupe_sim)

        # Diversity
        results = self._diversify_mmr(results, lambda_=float(self.config.get("mmr_lambda", 0.5)))
        results = self._cap_by_category(results)

        final_results = results[:limit]

        self._log_retrieval(
            context=context,
            intent=query,
            semantic_candidates_count=len(semantic_candidates),
            trigger_hits=len(trigger_matches),
            results=final_results,
            embedding_available=embedding_available,
            elapsed_ms=int((time.time() - start_ts) * 1000),
        )

        return final_results

    def _compute_fusion(self, r: SemanticResult) -> float:
        w_out = float(self.config.get("weight_outcome", 0.3))
        w_rec = float(self.config.get("weight_recency", 0.2))

        if r.source_type == "trigger":
            base = 0.9 + (r.outcome_score - 0.5) * w_out
        else:
            boosters = (r.outcome_score - 0.5) * w_out + r.recency_score * w_rec
            base = r.semantic_sim * (1 + boosters)

        priority_bonus = {"critical": 0.2, "high": 0.1, "normal": 0.0, "background": -0.1}
        base += priority_bonus.get(r.priority, 0.0)
        return max(0.0, min(1.0, base))

    def _compute_recency(self, insight: Any) -> float:
        ts = getattr(insight, "last_validated_at", None) or getattr(insight, "created_at", None)
        if not ts:
            return 0.5
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            age_days = max(0.0, (datetime.now(dt.tzinfo) - dt).total_seconds() / 86400.0)
        except Exception:
            return 0.5
        half_life = float(self.config.get("recency_half_life_days", 60))
        return float(2 ** (-age_days / max(1.0, half_life)))

    def _get_outcome_effectiveness(self, insight_key: str, insight: Any) -> float:
        try:
            from .meta_ralph import get_meta_ralph
            ralph = get_meta_ralph()
            eff = ralph.get_insight_effectiveness(insight_key)
            if eff is not None:
                return float(eff)
        except Exception:
            pass
        return float(getattr(insight, "reliability", 0.5) or 0.5)

    def _infer_priority(self, sim: float) -> str:
        if sim >= 0.9:
            return "high"
        if sim >= 0.75:
            return "normal"
        return "background"

    def _infer_category(self, insight: Any) -> str:
        cat = getattr(insight, "category", None)
        if hasattr(cat, "value"):
            return str(cat.value)
        if isinstance(cat, str):
            return cat
        return "cognitive"

    def _extract_intent(self, context: str) -> str:
        # Remove tool metadata noise
        intent = re.sub(r"file_path=.*?(?=\\s|$)", "", context)
        intent = re.sub(r"\\{.*?\\}", "", intent)
        intent = re.sub(r"\\s+", " ", intent).strip()

        action_patterns = [
            r"(edit|create|delete|update|fix|add|remove|change)\\s+([^\\.]+)",
            r"working on\\s+(.+?)(?:\\.|$)",
            r"implementing\\s+(.+?)(?:\\.|$)",
        ]
        for pattern in action_patterns:
            match = re.search(pattern, intent, re.IGNORECASE)
            if match:
                return match.group(0)
        return " ".join(intent.split()[:20])

    def _text_similarity(self, a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        aw = set(re.findall(r"[a-z0-9]+", a.lower()))
        bw = set(re.findall(r"[a-z0-9]+", b.lower()))
        if not aw or not bw:
            return 0.0
        return len(aw & bw) / max(1, len(aw | bw))

    def _cosine_sim(self, a: List[float], b: List[float]) -> float:
        if not a or not b:
            return 0.0
        dot = 0.0
        an = 0.0
        bn = 0.0
        for x, y in zip(a, b):
            dot += x * y
            an += x * x
            bn += y * y
        denom = math.sqrt(an) * math.sqrt(bn) or 1.0
        return dot / denom

    def _dedupe_by_embedding(self, results: List[SemanticResult], threshold: float) -> List[SemanticResult]:
        if not results or threshold <= 0:
            return results
        kept: List[SemanticResult] = []
        kept_vecs: Dict[str, List[float]] = {}
        seen_text: set[str] = set()
        for r in results:
            text_key = (r.insight_text or "").strip().lower()
            if text_key and text_key in seen_text:
                continue
            rvec = self.index.get(r.insight_key)
            too_similar = False
            for s in kept:
                if not rvec:
                    sim = self._text_similarity(r.insight_text, s.insight_text)
                else:
                    svec = kept_vecs.get(s.insight_key)
                    if not svec:
                        svec = self.index.get(s.insight_key)
                        if svec:
                            kept_vecs[s.insight_key] = svec
                    sim = self._cosine_sim(rvec, svec) if svec else self._text_similarity(r.insight_text, s.insight_text)
                if sim >= threshold:
                    too_similar = True
                    break
            if too_similar:
                continue
            kept.append(r)
            if rvec:
                kept_vecs[r.insight_key] = rvec
            if text_key:
                seen_text.add(text_key)
        return kept

    def _diversify_mmr(self, results: List[SemanticResult], lambda_: float = 0.5) -> List[SemanticResult]:
        selected: List[SemanticResult] = []
        remaining = list(results)
        while remaining and len(selected) < int(self.config.get("max_results", 8)):
            if not selected:
                best = max(remaining, key=lambda r: r.fusion_score)
            else:
                def mmr_score(r: SemanticResult) -> float:
                    relevance = r.fusion_score
                    max_sim = max(self._text_similarity(r.insight_text, s.insight_text) for s in selected)
                    return lambda_ * relevance - (1 - lambda_) * max_sim
                best = max(remaining, key=mmr_score)
            selected.append(best)
            remaining.remove(best)
        return selected

    def _cap_by_category(self, results: List[SemanticResult]) -> List[SemanticResult]:
        caps = self.config.get("category_caps", DEFAULT_CONFIG["category_caps"])
        counts: Dict[str, int] = {}
        capped: List[SemanticResult] = []
        for r in results:
            cat = r.category or "default"
            counts[cat] = counts.get(cat, 0) + 1
            if counts[cat] <= caps.get(cat, caps.get("default", 2)):
                capped.append(r)
        return capped

    def _log_retrieval(
        self,
        *,
        context: str,
        intent: str,
        semantic_candidates_count: int,
        trigger_hits: int,
        results: List[SemanticResult],
        embedding_available: bool,
        elapsed_ms: int,
    ) -> None:
        if not self.config.get("log_retrievals", True):
            return
        try:
            log_dir = Path.home() / ".spark" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            path = log_dir / "semantic_retrieval.jsonl"
            payload = {
                "ts": time.time(),
                "intent": intent[:200],
                "context_preview": (context or "")[:200],
                "semantic_candidates_count": int(semantic_candidates_count),
                "trigger_hits": int(trigger_hits),
                "embedding_available": bool(embedding_available),
                "elapsed_ms": int(elapsed_ms),
                "final_results": [
                    {
                        "key": r.insight_key,
                        "fusion": round(float(r.fusion_score or 0.0), 4),
                        "sim": round(float(r.semantic_sim or 0.0), 4),
                        "outcome": round(float(r.outcome_score or 0.0), 4),
                        "recency": round(float(r.recency_score or 0.0), 4),
                        "why": r.why,
                        "source": r.source_type,
                        "category": r.category,
                    }
                    for r in results
                ],
            }
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
            log_debug(
                "semantic",
                f"intent='{intent[:80]}' candidates={semantic_candidates_count} triggers={trigger_hits} final={len(results)}",
            )
        except Exception as e:
            log_debug("semantic", "log_retrieval failed", e)


def _load_config() -> Dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    try:
        tuneables = Path.home() / ".spark" / "tuneables.json"
        if tuneables.exists():
            data = json.loads(tuneables.read_text(encoding="utf-8"))
            semantic = data.get("semantic", {}) or {}
            triggers = data.get("triggers", {}) or {}
            config.update(semantic)
            if "enabled" in triggers:
                config["triggers_enabled"] = bool(triggers.get("enabled"))
            if "rules_file" in triggers:
                config["trigger_rules_file"] = triggers.get("rules_file")
    except Exception:
        pass

    # Env overrides
    if os.environ.get("SPARK_SEMANTIC_ENABLED", "").lower() in ("1", "true", "yes"):
        config["enabled"] = True
    if os.environ.get("SPARK_TRIGGERS_ENABLED", "").lower() in ("1", "true", "yes"):
        config["triggers_enabled"] = True

    return config


_RETRIEVER: Optional[SemanticRetriever] = None


def get_semantic_retriever() -> Optional[SemanticRetriever]:
    global _RETRIEVER
    config = _load_config()
    if not config.get("enabled", False):
        return None
    if _RETRIEVER is None or _RETRIEVER.config != config:
        _RETRIEVER = SemanticRetriever(config=config)
    return _RETRIEVER


def index_insight(insight_key: str, text: str, context: str = "") -> bool:
    retriever = get_semantic_retriever()
    if not retriever:
        return False
    if not retriever.config.get("index_on_write", True):
        return False
    combined = f"{text} {context}".strip()
    if not combined:
        return False
    return retriever.index.add(insight_key, combined)
