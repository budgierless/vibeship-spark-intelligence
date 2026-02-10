#!/usr/bin/env python3
"""OpenClaw adapter: tail session JSONL -> sparkd /ingest

Reads OpenClaw session transcripts (~/.openclaw/agents/<agent>/sessions/) and
emits normalized SparkEventV1 events to sparkd.

Usage:
  python3 adapters/openclaw_tailer.py --sparkd http://127.0.0.1:8787 --agent main

Notes:
- Tails the latest session file for a given agent.
- De-dupes using a line offset persisted in ~/.spark/adapters/openclaw-<agent>.json.
- Handles all OpenClaw JSONL types: session, message, model_change,
  thinking_level_change, custom.
- Extracts tool calls from assistant content blocks AND separate toolResult messages.
"""

import argparse
import datetime
import json
import hashlib
import os
import time
from pathlib import Path
from urllib.request import Request, urlopen

DEFAULT_SPARKD = os.environ.get("SPARKD_URL") or f"http://127.0.0.1:{os.environ.get('SPARKD_PORT', '8787')}"

STATE_DIR = Path.home() / ".spark" / "adapters"

MAX_TOOL_RESULT_CHARS = 4000


def _post_json(url: str, payload: dict, token: str = None):
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, data=data, headers=headers, method="POST")
    with urlopen(req, timeout=5) as resp:
        resp.read()


def _event(trace_id: str, session_id: str, source: str, kind: str, ts: float, payload: dict):
    return {
        "v": 1,
        "source": source,
        "kind": kind,
        "ts": ts,
        "session_id": session_id,
        "payload": payload,
        "trace_id": trace_id,
    }


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:20]


def _parse_ts(x):
    """Parse timestamp from various formats to epoch float."""
    if x is None:
        return time.time()
    if isinstance(x, (int, float)):
        return float(x) / 1000.0 if x > 2e10 else float(x)
    if isinstance(x, str):
        try:
            s = x.replace("Z", "+00:00")
            return datetime.datetime.fromisoformat(s).timestamp()
        except Exception:
            return time.time()
    return time.time()


def _truncate_content(content) -> str:
    """Extract text from content blocks and truncate to MAX_TOOL_RESULT_CHARS."""
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        text = "\n".join(parts)
    else:
        text = str(content) if content else ""
    if len(text) > MAX_TOOL_RESULT_CHARS:
        return text[:MAX_TOOL_RESULT_CHARS] + f"\n... [truncated {len(text) - MAX_TOOL_RESULT_CHARS} chars]"
    return text


def parse_openclaw_line(obj: dict, session_key: str) -> list:
    """Parse one JSONL line into zero or more SparkEventV1 events."""
    events = []
    line_type = obj.get("type")
    ts = _parse_ts(obj.get("timestamp"))

    if line_type == "session":
        events.append(_event(
            trace_id=_hash(obj.get("id", "")),
            session_id=session_key,
            source="openclaw",
            kind="command",
            ts=ts,
            payload={"command": "session_start", "cwd": obj.get("cwd")},
        ))

    elif line_type == "message":
        msg = obj.get("message") if isinstance(obj.get("message"), dict) else None
        if not msg:
            return events
        role = msg.get("role")
        content = msg.get("content", [])

        if role in ("user", "assistant"):
            text = None
            tool_calls = []
            meta = {}

            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "text" and text is None:
                        text = block.get("text")
                    elif block.get("type") == "toolCall":
                        tool_calls.append({
                            "id": block.get("id"),
                            "name": block.get("name"),
                            "arguments": block.get("arguments"),
                        })
                        # Harvest cwd hints
                        targs = block.get("arguments") or {}
                        wd = targs.get("workdir") or targs.get("cwd")
                        if isinstance(wd, str) and wd and "cwd" not in meta:
                            meta["cwd"] = wd

            events.append(_event(
                trace_id=_hash(obj.get("id", "")),
                session_id=session_key,
                source="openclaw",
                kind="message",
                ts=ts,
                payload={
                    "role": role,
                    "text": text,
                    "meta": meta,
                    "model": msg.get("model"),
                    "provider": msg.get("provider"),
                    "usage": msg.get("usage"),
                    "stop_reason": msg.get("stopReason"),
                },
            ))

            for tc in tool_calls:
                events.append(_event(
                    trace_id=_hash(tc.get("id") or ""),
                    session_id=session_key,
                    source="openclaw",
                    kind="tool",
                    ts=ts,
                    payload={
                        "tool_name": tc["name"],
                        "tool_input": tc.get("arguments") or {},
                        "call_id": tc.get("id"),
                    },
                ))

        elif role == "toolResult":
            result_text = _truncate_content(content)
            events.append(_event(
                trace_id=_hash(obj.get("id", "")),
                session_id=session_key,
                source="openclaw",
                kind="tool",
                ts=ts,
                payload={
                    "tool_name": msg.get("toolName"),
                    "tool_input": {},
                    "tool_result": result_text,
                    "call_id": msg.get("toolCallId"),
                    "is_error": msg.get("isError", False),
                },
            ))

    elif line_type in ("model_change", "thinking_level_change", "custom"):
        payload_data = {"type": line_type}
        if line_type == "model_change":
            payload_data["model"] = obj.get("modelId")
            payload_data["provider"] = obj.get("provider")
        elif line_type == "thinking_level_change":
            payload_data["thinking_level"] = obj.get("thinkingLevel")
        elif line_type == "custom":
            payload_data["custom_type"] = obj.get("customType")
            payload_data["data"] = obj.get("data")
        events.append(_event(
            trace_id=_hash(obj.get("id", "")),
            session_id=session_key,
            source="openclaw",
            kind="system",
            ts=ts,
            payload=payload_data,
        ))

    return events


def _find_latest_session(agent_dir: Path):
    """Find the latest session file and key from sessions.json or glob fallback."""
    sessions_json = agent_dir / "sessions.json"

    if sessions_json.exists():
        try:
            sj = json.loads(sessions_json.read_text(encoding="utf-8"))
            entries = list(sj.items())
            if entries:
                def keyfn(item):
                    v = item[1] or {}
                    return float(v.get("updatedAt") or v.get("lastMessageAt") or v.get("createdAt") or 0)
                entries.sort(key=keyfn, reverse=True)
                session_key, info = entries[0]
                session_file = info.get("sessionFile") or info.get("transcript")
                if session_file:
                    p = Path(session_file)
                    if p.exists():
                        return session_key, p
                # Try constructing path from key
                candidate = agent_dir / f"{session_key}.jsonl"
                if candidate.exists():
                    return session_key, candidate
        except Exception:
            pass

    # Fallback: glob for newest .jsonl
    jsonl_files = sorted(agent_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if jsonl_files:
        f = jsonl_files[0]
        return f.stem, f
    return None, None


def main():
    ap = argparse.ArgumentParser(description="OpenClaw adapter: tail session JSONL -> sparkd /ingest")
    ap.add_argument("--sparkd", default=DEFAULT_SPARKD, help="sparkd base URL")
    ap.add_argument("--agent", default="main", help="OpenClaw agent id")
    ap.add_argument("--poll", type=float, default=2.0, help="Poll interval seconds (default: 2.0)")
    ap.add_argument("--max-per-tick", type=int, default=50, help="Max lines to ingest per tick (default: 50)")
    ap.add_argument("--backfill", action="store_true", help="Backfill from the start of the transcript (default is tail-from-end)")
    ap.add_argument("--verbose", action="store_true", help="Log adapter activity")
    ap.add_argument("--token", default=None, help="sparkd auth token (or set SPARKD_TOKEN env)")
    args = ap.parse_args()

    token = args.token or os.environ.get("SPARKD_TOKEN")

    agent_dir = Path.home() / ".openclaw" / "agents" / args.agent / "sessions"
    if not agent_dir.exists():
        raise SystemExit(f"No sessions directory at {agent_dir}")

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state_file = STATE_DIR / f"openclaw-{args.agent}.json"
    state = {"sessionFile": None, "offset": 0}
    if state_file.exists():
        try:
            state.update(json.loads(state_file.read_text(encoding="utf-8")))
        except Exception:
            pass

    def save_state():
        state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")

    while True:
        try:
            if args.verbose:
                print("[openclaw_tailer] tick", flush=True)

            session_key, session_file = _find_latest_session(agent_dir)
            if not session_key or not session_file:
                if args.verbose:
                    print("[openclaw_tailer] no session file found", flush=True)
                time.sleep(args.poll)
                continue

            if args.verbose:
                print(f"[openclaw_tailer] using session {session_key} file={session_file}", flush=True)

            # New session file? default to tail-from-end unless --backfill.
            if state.get("sessionFile") != str(session_file):
                state["sessionFile"] = str(session_file)
                if args.backfill:
                    state["offset"] = 0
                else:
                    try:
                        state["offset"] = len(session_file.read_text(encoding="utf-8").splitlines())
                    except Exception:
                        state["offset"] = 0
                save_state()

            lines = session_file.read_text(encoding="utf-8").splitlines()
            if args.verbose:
                print(f"[openclaw_tailer] lines={len(lines)} offset={state.get('offset')}", flush=True)
            off = int(state.get("offset") or 0)
            new_lines = lines[off:]
            if not new_lines:
                time.sleep(args.poll)
                continue

            batch_size = max(1, int(args.max_per_tick))
            batch = new_lines[:batch_size]

            sent = 0
            for line in batch:
                try:
                    obj = json.loads(line)
                except Exception:
                    # Unparseable line — emit as raw system event
                    evt = _event(
                        trace_id=_hash(line),
                        session_id=session_key,
                        source="openclaw",
                        kind="system",
                        ts=time.time(),
                        payload={"raw": line},
                    )
                    try:
                        _post_json(args.sparkd.rstrip("/") + "/ingest", evt, token=token)
                    except Exception as post_err:
                        if args.verbose:
                            print(f"[openclaw_tailer] POST error: {post_err}", flush=True)
                        break
                    sent += 1
                    continue

                events = parse_openclaw_line(obj, session_key)
                if not events:
                    # Unrecognized type — pass through as system event
                    events = [_event(
                        trace_id=_hash(json.dumps(obj, sort_keys=True)),
                        session_id=session_key,
                        source="openclaw",
                        kind="system",
                        ts=_parse_ts(obj.get("timestamp")),
                        payload={"raw": obj},
                    )]

                post_ok = True
                for evt in events:
                    try:
                        _post_json(args.sparkd.rstrip("/") + "/ingest", evt, token=token)
                    except Exception as post_err:
                        if args.verbose:
                            print(f"[openclaw_tailer] POST error: {post_err}", flush=True)
                        post_ok = False
                        break

                if not post_ok:
                    break
                sent += 1

            state["offset"] = off + sent
            save_state()

            if args.verbose and sent:
                remaining = max(0, len(new_lines) - sent)
                print(f"[openclaw_tailer] sent {sent}, remaining {remaining}, offset {state['offset']}", flush=True)

        except Exception as e:
            if args.verbose:
                print(f"[openclaw_tailer] error: {e}", flush=True)

        time.sleep(args.poll)


if __name__ == "__main__":
    main()
