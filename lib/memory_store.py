"""Local hybrid memory store (SQLite + optional embeddings).

Goal: cross-project sink with lightweight hybrid retrieval:
- SQLite FTS5 (BM25-ish lexical ranking)
- Optional embeddings for semantic matching

No server required. Falls back gracefully if embeddings or FTS5 are unavailable.
"""

from __future__ import annotations

import json
import sqlite3
from array import array
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from lib.embeddings import embed_texts

DB_PATH = Path.home() / ".spark" / "memory_store.sqlite"
_FTS_AVAILABLE: Optional[bool] = None

def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memories (
          memory_id TEXT PRIMARY KEY,
          content TEXT NOT NULL,
          scope TEXT,
          project_key TEXT,
          category TEXT,
          created_at REAL,
          source TEXT,
          meta TEXT
        );
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_project ON memories(project_key);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_scope ON memories(scope);")
    _ensure_fts(conn)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memories_vec (
          memory_id TEXT PRIMARY KEY,
          dim INTEGER,
          vector BLOB
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memory_edges (
          source_id TEXT NOT NULL,
          target_id TEXT NOT NULL,
          weight REAL,
          reason TEXT,
          created_at REAL,
          PRIMARY KEY (source_id, target_id)
        );
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_source ON memory_edges(source_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_target ON memory_edges(target_id);")
    conn.commit()


def _ensure_fts(conn: sqlite3.Connection) -> bool:
    global _FTS_AVAILABLE
    if _FTS_AVAILABLE is True:
        return True
    if _FTS_AVAILABLE is False:
        return False
    try:
        conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
            USING fts5(
              content,
              memory_id UNINDEXED,
              scope UNINDEXED,
              project_key UNINDEXED,
              category UNINDEXED
            );
            """
        )
        _FTS_AVAILABLE = True
    except sqlite3.OperationalError:
        _FTS_AVAILABLE = False
    return bool(_FTS_AVAILABLE)


def _sanitize_token(token: str) -> str:
    return "".join(ch for ch in token if ch.isalnum())


def _build_fts_query(text: str) -> str:
    tokens = [_sanitize_token(t) for t in (text or "").lower().split()]
    tokens = [t for t in tokens if t]
    if not tokens:
        return ""
    return " OR ".join(tokens)


def _embed_texts(texts: List[str]) -> Optional[List[List[float]]]:
    return embed_texts(texts)


def _vector_to_blob(vec: List[float]) -> bytes:
    buf = array("f", vec)
    return buf.tobytes()


def _blob_to_vector(blob: bytes) -> List[float]:
    buf = array("f")
    buf.frombytes(blob or b"")
    return list(buf)


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / ((na ** 0.5) * (nb ** 0.5))))


def _upsert_edge(
    conn: sqlite3.Connection,
    source_id: str,
    target_id: str,
    weight: float,
    reason: str,
    created_at: float,
) -> None:
    if not source_id or not target_id or source_id == target_id:
        return
    row = conn.execute(
        "SELECT weight FROM memory_edges WHERE source_id = ? AND target_id = ?",
        (source_id, target_id),
    ).fetchone()
    if row:
        new_weight = min(1.0, float(row["weight"] or 0.0) + 0.05)
        conn.execute(
            "UPDATE memory_edges SET weight = ?, reason = ?, created_at = ? WHERE source_id = ? AND target_id = ?",
            (new_weight, reason, created_at, source_id, target_id),
        )
    else:
        conn.execute(
            "INSERT OR REPLACE INTO memory_edges (source_id, target_id, weight, reason, created_at) VALUES (?, ?, ?, ?, ?)",
            (source_id, target_id, weight, reason, created_at),
        )


def _link_edges(
    conn: sqlite3.Connection,
    memory_id: str,
    project_key: Optional[str],
    scope: str,
    created_at: float,
    max_project_links: int = 5,
    max_global_links: int = 3,
) -> None:
    targets: List[sqlite3.Row] = []
    if project_key:
        targets.extend(
            conn.execute(
                """
                SELECT memory_id, project_key, scope
                FROM memories
                WHERE memory_id != ? AND project_key = ?
                ORDER BY created_at DESC
                LIMIT ?;
                """,
                (memory_id, project_key, max_project_links),
            ).fetchall()
        )

    targets.extend(
        conn.execute(
            """
            SELECT memory_id, project_key, scope
            FROM memories
            WHERE memory_id != ? AND scope = 'global'
            ORDER BY created_at DESC
            LIMIT ?;
            """,
            (memory_id, max_global_links),
        ).fetchall()
    )

    seen = set()
    for row in targets:
        tid = row["memory_id"]
        if not tid or tid in seen:
            continue
        seen.add(tid)
        reason = "cooccurrence:project" if row["project_key"] == project_key and project_key else "cooccurrence:global"
        weight = 0.6 if reason.endswith("project") else 0.4
        _upsert_edge(conn, memory_id, tid, weight, reason, created_at)
        _upsert_edge(conn, tid, memory_id, weight, reason, created_at)


def upsert_entry(
    *,
    memory_id: str,
    content: str,
    scope: str,
    project_key: Optional[str],
    category: str,
    created_at: float,
    source: str,
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO memories
            (memory_id, content, scope, project_key, category, created_at, source, meta)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                memory_id,
                content,
                scope,
                project_key,
                category,
                created_at,
                source,
                json.dumps(meta or {}),
            ),
        )

        if _ensure_fts(conn):
            conn.execute("DELETE FROM memories_fts WHERE memory_id = ?", (memory_id,))
            conn.execute(
                "INSERT INTO memories_fts (content, memory_id, scope, project_key, category) VALUES (?, ?, ?, ?, ?)",
                (content, memory_id, scope, project_key or "", category),
            )

        vectors = _embed_texts([content])
        if vectors:
            vec = vectors[0]
            conn.execute(
                "INSERT OR REPLACE INTO memories_vec (memory_id, dim, vector) VALUES (?, ?, ?)",
                (memory_id, len(vec), _vector_to_blob(vec)),
            )

        _link_edges(conn, memory_id, project_key, scope, created_at)

        conn.commit()
    finally:
        conn.close()


def _fetch_vectors(conn: sqlite3.Connection, ids: Iterable[str]) -> Dict[str, List[float]]:
    id_list = [i for i in ids if i]
    if not id_list:
        return {}
    placeholders = ",".join("?" for _ in id_list)
    rows = conn.execute(
        f"SELECT memory_id, vector FROM memories_vec WHERE memory_id IN ({placeholders})",
        id_list,
    ).fetchall()
    out: Dict[str, List[float]] = {}
    for r in rows:
        out[r["memory_id"]] = _blob_to_vector(r["vector"])
    return out


def retrieve(
    query: str,
    *,
    project_key: Optional[str] = None,
    limit: int = 6,
    candidate_limit: int = 50,
) -> List[Dict[str, Any]]:
    q = (query or "").strip()
    if not q:
        return []

    conn = _connect()
    try:
        items: List[Dict[str, Any]] = []

        if _ensure_fts(conn):
            fts_query = _build_fts_query(q)
            if not fts_query:
                return []
            params: List[Any] = [fts_query]
            where = "memories_fts MATCH ?"
            if project_key:
                where += " AND (scope = 'global' OR project_key = ?)"
                params.append(project_key)
            params.append(max(10, int(candidate_limit)))
            rows = conn.execute(
                f"""
                SELECT memory_id, content, scope, project_key, category, bm25(memories_fts) AS bm25
                FROM memories_fts
                WHERE {where}
                ORDER BY bm25
                LIMIT ?;
                """,
                params,
            ).fetchall()

            for r in rows:
                bm25 = float(r["bm25"]) if r["bm25"] is not None else 0.0
                bm25 = max(0.0, bm25)
                lex = 1.0 / (1.0 + bm25)
                items.append({
                    "entry_id": r["memory_id"],
                    "text": r["content"],
                    "scope": r["scope"],
                    "project_key": r["project_key"],
                    "category": r["category"],
                    "bm25": bm25,
                    "score": lex,
                })
        else:
            # FTS not available; fallback to simple scan
            rows = conn.execute(
                """
                SELECT memory_id, content, scope, project_key, category
                FROM memories
                ORDER BY created_at DESC
                LIMIT ?;
                """,
                (max(200, int(candidate_limit)),),
            ).fetchall()
            q_lower = q.lower()
            q_words = [w for w in q_lower.split() if len(w) > 2]
            for r in rows:
                text = (r["content"] or "").lower()
                score = 0.0
                if q_lower in text:
                    score += 2.0
                for w in q_words[:8]:
                    if w in text:
                        score += 0.25
                if project_key and r["project_key"] == project_key:
                    score += 0.4
                if score <= 0.25:
                    continue
                items.append({
                    "entry_id": r["memory_id"],
                    "text": r["content"],
                    "scope": r["scope"],
                    "project_key": r["project_key"],
                    "category": r["category"],
                    "bm25": None,
                    "score": score,
                })

        if not items:
            return []

        vectors = _embed_texts([q])
        if vectors:
            qvec = vectors[0]
            vecs = _fetch_vectors(conn, [i["entry_id"] for i in items])
            for it in items:
                vec = vecs.get(it["entry_id"])
                if vec:
                    cos = _cosine(qvec, vec)
                    it["score"] = (0.6 * it["score"]) + (0.4 * cos)

        items.sort(key=lambda i: i.get("score", 0.0), reverse=True)

        # Edge expansion (graph-lite): add related items with small score boost.
        want = max(0, int(limit or 0))
        if want <= 0:
            return []
        if len(items) >= want:
            return items[:want]

        seed_ids = [i["entry_id"] for i in items[: min(5, len(items))] if i.get("entry_id")]
        if not seed_ids:
            return items[:want]

        placeholders = ",".join("?" for _ in seed_ids)
        edge_rows = conn.execute(
            f"""
            SELECT source_id, target_id, weight, reason
            FROM memory_edges
            WHERE source_id IN ({placeholders})
            ORDER BY weight DESC
            LIMIT 25;
            """,
            seed_ids,
        ).fetchall()

        edge_targets = []
        for r in edge_rows:
            edge_targets.append((r["target_id"], float(r["weight"] or 0.0), r["reason"]))

        if not edge_targets:
            return items[:want]

        existing = {i["entry_id"] for i in items}
        target_ids = [t[0] for t in edge_targets if t[0] and t[0] not in existing]
        if not target_ids:
            return items[:want]

        placeholders = ",".join("?" for _ in target_ids)
        rows = conn.execute(
            f"""
            SELECT memory_id, content, scope, project_key, category
            FROM memories
            WHERE memory_id IN ({placeholders});
            """,
            target_ids,
        ).fetchall()
        row_map = {r["memory_id"]: r for r in rows}

        for tid, weight, reason in edge_targets:
            if len(items) >= want:
                break
            if tid in existing:
                continue
            r = row_map.get(tid)
            if not r:
                continue
            if project_key and r["project_key"] not in (project_key, None, "") and r["scope"] != "global":
                continue
            items.append({
                "entry_id": r["memory_id"],
                "text": r["content"],
                "scope": r["scope"],
                "project_key": r["project_key"],
                "category": r["category"],
                "bm25": None,
                "score": 0.15 * weight,
                "edge_reason": reason,
            })
            existing.add(tid)

        items.sort(key=lambda i: i.get("score", 0.0), reverse=True)
        return items[:want]
    finally:
        conn.close()
