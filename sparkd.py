#!/usr/bin/env python3
"""sparkd - Spark daemon (platform-agnostic ingest)

Minimal HTTP server:
  GET  /health
  GET  /status
  POST /ingest  (SparkEventV1 JSON)

Stores events into the existing Spark queue (events.jsonl) so the rest of Spark
can process them.

This is intentionally dependency-free.
"""

import json
import os
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

import sys
sys.path.insert(0, str(Path(__file__).parent))

from lib.events import SparkEventV1
from lib.queue import quick_capture, EventType
from lib.orchestration import register_agent, recommend_agent, record_handoff, get_orchestrator

PORT = 8787
TOKEN = os.environ.get("SPARKD_TOKEN")
MAX_BODY_BYTES = int(os.environ.get("SPARKD_MAX_BODY_BYTES", "262144"))


def _json(handler: BaseHTTPRequestHandler, code: int, payload):
    raw = json.dumps(payload).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def _text(handler: BaseHTTPRequestHandler, code: int, body: str):
    raw = body.encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "text/plain; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            return _text(self, 200, "ok")
        if path == "/status":
            return _json(self, 200, {
                "ok": True,
                "now": time.time(),
                "port": PORT,
            })
        if path == "/agents":
            orch = get_orchestrator()
            return _json(self, 200, {"ok": True, "agents": orch.list_agents()})
        return _text(self, 404, "not found")

    def do_POST(self):
        path = urlparse(self.path).path

        if path == "/agent":
            length = int(self.headers.get("Content-Length", "0") or 0)
            body = self.rfile.read(length) if length else b"{}"
            try:
                data = json.loads(body.decode("utf-8") or "{}")
                ok = register_agent(
                    agent_id=data.get("agent_id") or data.get("name", "").lower().replace(" ", "-"),
                    name=data.get("name"),
                    capabilities=data.get("capabilities", []),
                    specialization=data.get("specialization", "general"),
                )
                return _json(self, 201 if ok else 400, {"ok": ok})
            except Exception as e:
                return _json(self, 400, {"ok": False, "error": str(e)[:200]})

        if path == "/orchestration/recommend":
            length = int(self.headers.get("Content-Length", "0") or 0)
            body = self.rfile.read(length) if length else b"{}"
            try:
                data = json.loads(body.decode("utf-8") or "{}")
                agent_id, reason = recommend_agent(
                    query=data.get("query", "") or data.get("task", ""),
                    task_type=data.get("task_type", ""),
                )
                return _json(self, 200, {"ok": True, "recommended_agent": agent_id, "reason": reason})
            except Exception as e:
                return _json(self, 400, {"ok": False, "error": str(e)[:200]})

        if path == "/handoff":
            length = int(self.headers.get("Content-Length", "0") or 0)
            body = self.rfile.read(length) if length else b"{}"
            try:
                data = json.loads(body.decode("utf-8") or "{}")
                hid = record_handoff(
                    from_agent=data.get("from_agent"),
                    to_agent=data.get("to_agent"),
                    context=data.get("context", {}),
                    success=data.get("success"),
                )
                return _json(self, 201, {"ok": True, "handoff_id": hid})
            except Exception as e:
                return _json(self, 400, {"ok": False, "error": str(e)[:200]})

        if path != "/ingest":
            return _text(self, 404, "not found")

        # Optional auth: if SPARKD_TOKEN is set, require Authorization: Bearer <token>
        if TOKEN:
            auth = self.headers.get("Authorization") or ""
            expected = f"Bearer {TOKEN}"
            if auth.strip() != expected:
                return _json(self, 401, {"ok": False, "error": "unauthorized"})

        length = int(self.headers.get("Content-Length", "0") or 0)
        if length > MAX_BODY_BYTES:
            return _json(self, 413, {"ok": False, "error": "payload_too_large"})
        body = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(body.decode("utf-8") or "{}")
            evt = SparkEventV1.from_dict(data)
        except Exception as e:
            return _json(self, 400, {"ok": False, "error": "invalid_event", "detail": str(e)[:200]})

        # Store as a Spark queue event (POST_TOOL/USER_PROMPT mapping is adapter-defined)
        # Here we just record it as a generic USER_PROMPT or POST_TOOL depending on kind.
        if evt.kind.value == "message":
            et = EventType.USER_PROMPT
        elif evt.kind.value == "tool":
            et = EventType.POST_TOOL
        else:
            et = EventType.LEARNING

        # Try to propagate working-directory hints for project inference.
        meta = (evt.payload or {}).get("meta") or {}
        cwd_hint = meta.get("cwd") or meta.get("workdir") or meta.get("workspace")

        ok = quick_capture(
            event_type=et,
            session_id=evt.session_id,
            data={
                "source": evt.source,
                "kind": evt.kind.value,
                "payload": evt.payload,
                "trace_id": evt.trace_id,
                "v": evt.v,
                "ts": evt.ts,
                "cwd": cwd_hint,
            },
            tool_name=evt.payload.get("tool_name"),
            tool_input=evt.payload.get("tool_input"),
            error=evt.payload.get("error"),
        )

        return _json(self, 200, {"ok": bool(ok)})


def main():
    print(f"sparkd listening on http://127.0.0.1:{PORT}")
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
