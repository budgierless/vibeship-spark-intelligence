#!/usr/bin/env python3
"""Mind Lite+ (minimal) server for Spark

This is a lightweight, dependency-free implementation of the Mind API expected by
Spark's MindBridge.

Endpoints:
  GET  /health
  POST /v1/memories/          (create memory)
  POST /v1/memories/retrieve  (simple keyword retrieval)

Storage:
  SQLite at ~/.mind/lite/memories.db (shared with Mind Lite)

Note: Retrieval is intentionally simple (keyword scoring) to keep this
server zero-dependency. We can upgrade to embeddings later.
"""

import json
import os
import sqlite3
import uuid
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

PORT = 8080
DB_PATH = Path.home() / ".mind" / "lite" / "memories.db"
TOKEN = os.environ.get("MIND_TOKEN")
MAX_BODY_BYTES = int(os.environ.get("MIND_MAX_BODY_BYTES", "262144"))
MAX_CONTENT_CHARS = int(os.environ.get("MIND_MAX_CONTENT_CHARS", "4000"))
MAX_QUERY_CHARS = int(os.environ.get("MIND_MAX_QUERY_CHARS", "1000"))
_FTS_AVAILABLE = None
_RRF_K = 60


def _ensure_db(conn: sqlite3.Connection):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memories (
          memory_id TEXT PRIMARY KEY,
          user_id TEXT NOT NULL,
          content TEXT NOT NULL,
          content_type TEXT,
          temporal_level INTEGER,
          salience REAL,
          created_at TEXT NOT NULL
        );
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id);")
    _ensure_fts(conn)
    conn.commit()


def _tokenize(q: str):
    return [t for t in (q or "").lower().replace("\n", " ").split() if t]


def _score(content: str, tokens):
    if not tokens:
        return 0
    c = (content or "").lower()
    return sum(c.count(t) for t in tokens)


def _ensure_fts(conn: sqlite3.Connection) -> bool:
    global _FTS_AVAILABLE
    if _FTS_AVAILABLE is False:
        return False
    if _FTS_AVAILABLE is True:
        return True
    try:
        conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
            USING fts5(content, memory_id UNINDEXED, user_id UNINDEXED);
            """
        )
        _FTS_AVAILABLE = True
    except sqlite3.OperationalError:
        _FTS_AVAILABLE = False
    return _FTS_AVAILABLE


def _normalize_scores(scores):
    if not scores:
        return {}
    max_val = max(scores.values()) if scores else 0
    if max_val <= 0:
        return {k: 0.0 for k in scores}
    return {k: v / max_val for k, v in scores.items()}


def _rrf_merge(rank_lists, k: int = _RRF_K):
    out = {}
    for ranked in rank_lists:
        for idx, mid in enumerate(ranked):
            out[mid] = out.get(mid, 0.0) + 1.0 / (k + idx + 1)
    return out


def _sanitize_fts_token(token: str) -> str:
    return "".join(ch for ch in token if ch.isalnum())


def _build_fts_query(tokens):
    terms = [_sanitize_fts_token(t) for t in tokens]
    terms = [t for t in terms if t]
    if not terms:
        return ""
    return " OR ".join(terms)


class Handler(BaseHTTPRequestHandler):
    def _json(self, code: int, payload):
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _text(self, code: int, body: str):
        raw = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt, *args):
        # quiet
        return

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            return self._text(200, "ok")
        if path == "/v1/stats":
            return self._get_stats()
        if path == "/":
            return self._json(200, {
                "service": "Mind Lite+",
                "version": "1.0.0",
                "status": "running"
            })
        return self._text(404, "not found")

    def _get_stats(self):
        conn = self._db()
        try:
            row = conn.execute("SELECT COUNT(*) as total FROM memories").fetchone()
            total = row["total"] if row else 0
            users = conn.execute("SELECT COUNT(DISTINCT user_id) as users FROM memories").fetchone()
            user_count = users["users"] if users else 0
        finally:
            conn.close()
        return self._json(200, {
            "total_memories": total,
            "total": total,
            "count": total,
            "total_learnings": total,
            "users": user_count,
            "status": "healthy"
        })

    def do_POST(self):
        path = urlparse(self.path).path

        # Optional auth: if MIND_TOKEN is set, require Authorization: Bearer <token>
        if TOKEN:
            auth = (self.headers.get("Authorization") or "").strip()
            if auth != f"Bearer {TOKEN}":
                return self._json(401, {"error": "unauthorized"})

        length = int(self.headers.get("Content-Length", "0") or 0)
        if length > MAX_BODY_BYTES:
            return self._json(413, {"error": "payload_too_large"})
        body = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(body.decode("utf-8") or "{}")
        except Exception:
            return self._json(400, {"error": "invalid_json"})

        if path == "/v1/memories/":
            return self._create_memory(data)
        if path == "/v1/memories/retrieve":
            return self._retrieve(data)

        return self._text(404, "not found")

    def _db(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        _ensure_db(conn)
        return conn

    def _create_memory(self, data):
        user_id = data.get("user_id")
        content = data.get("content")
        if not user_id or not content:
            return self._json(400, {"error": "missing_user_id_or_content"})
        if len(str(content)) > MAX_CONTENT_CHARS:
            return self._json(413, {"error": "content_too_large"})

        memory_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat() + "Z"

        content_type = data.get("content_type")
        temporal_level = data.get("temporal_level")
        salience = data.get("salience")

        conn = self._db()
        try:
            conn.execute(
                "INSERT INTO memories (memory_id, user_id, content, content_type, temporal_level, salience, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (memory_id, user_id, content, content_type, temporal_level, salience, created_at),
            )
            if _ensure_fts(conn):
                conn.execute(
                    "INSERT INTO memories_fts (content, memory_id, user_id) VALUES (?, ?, ?)",
                    (content, memory_id, user_id),
                )
            conn.commit()
        finally:
            conn.close()

        return self._json(201, {"memory_id": memory_id})

    def _retrieve(self, data):
        user_id = data.get("user_id")
        query = data.get("query", "")
        limit = int(data.get("limit") or 5)
        limit = max(1, min(limit, 50))

        if not user_id:
            return self._json(400, {"error": "missing_user_id"})

        query = str(query)[:MAX_QUERY_CHARS]
        tokens = _tokenize(query)
        fts_query = _build_fts_query(tokens)

        conn = self._db()
        try:
            rows = conn.execute(
                "SELECT memory_id, user_id, content, content_type, temporal_level, salience, created_at FROM memories WHERE user_id = ?",
                (user_id,),
            ).fetchall()
            fts_rows = []
            if fts_query and _ensure_fts(conn):
                fts_rows = conn.execute(
                    """
                    SELECT memory_id, bm25(memories_fts) AS bm25
                    FROM memories_fts
                    WHERE memories_fts MATCH ? AND user_id = ?
                    ORDER BY bm25
                    LIMIT ?
                    """,
                    (fts_query, user_id, max(limit * 5, 20)),
                ).fetchall()
        finally:
            conn.close()

        row_by_id = {r["memory_id"]: r for r in rows}
        legacy_scores = {}
        for r in rows:
            s = _score(r["content"], tokens)
            if tokens and s == 0:
                continue
            # small boost for salience
            sal = r["salience"] if r["salience"] is not None else 0.5
            legacy_scores[r["memory_id"]] = s + (sal * 0.1)

        fts_scores = {}
        for r in fts_rows:
            mid = r["memory_id"]
            bm = r["bm25"]
            if bm is None:
                continue
            fts_scores[mid] = 1.0 / (1.0 + float(bm))

        if fts_scores:
            legacy_ranked = sorted(
                legacy_scores.items(), key=lambda x: x[1], reverse=True
            )[: max(limit * 5, 20)]
            fts_ranked = sorted(
                fts_scores.items(), key=lambda x: x[1], reverse=True
            )[: max(limit * 5, 20)]

            rrf_scores = _rrf_merge(
                [
                    [mid for mid, _ in legacy_ranked],
                    [mid for mid, _ in fts_ranked],
                ]
            )
            legacy_norm = _normalize_scores(legacy_scores)
            fts_norm = _normalize_scores(fts_scores)

            fused = {}
            for mid in set(list(legacy_scores.keys()) + list(fts_scores.keys())):
                fused[mid] = (
                    rrf_scores.get(mid, 0.0)
                    + (0.2 * legacy_norm.get(mid, 0.0))
                    + (0.2 * fts_norm.get(mid, 0.0))
                )

            scored = sorted(fused.items(), key=lambda x: x[1], reverse=True)
            top = [
                {
                    "memory_id": row_by_id[mid]["memory_id"],
                    "content": row_by_id[mid]["content"],
                    "content_type": row_by_id[mid]["content_type"],
                    "temporal_level": row_by_id[mid]["temporal_level"],
                    "salience": row_by_id[mid]["salience"],
                    "created_at": row_by_id[mid]["created_at"],
                    "score": float(score),
                }
                for mid, score in scored[:limit]
                if mid in row_by_id
            ]
            return self._json(200, {"memories": top})

        scored = sorted(legacy_scores.items(), key=lambda x: x[1], reverse=True)
        top = [
            {
                "memory_id": row_by_id[mid]["memory_id"],
                "content": row_by_id[mid]["content"],
                "content_type": row_by_id[mid]["content_type"],
                "temporal_level": row_by_id[mid]["temporal_level"],
                "salience": row_by_id[mid]["salience"],
                "created_at": row_by_id[mid]["created_at"],
                "score": float(score),
            }
            for mid, score in scored[:limit]
            if mid in row_by_id
        ]

        return self._json(200, {"memories": top})


def main():
    print(f"Mind Lite+ listening on http://127.0.0.1:{PORT}")
    print(f"DB: {DB_PATH}")
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
