"""
Spark Event Queue: Ultra-fast event capture

Events are captured in < 10ms and written to a local queue file.
Background processing handles the heavy lifting (learning, syncing).

This ensures:
1. Hooks never slow down the AI agent
2. No events are lost
3. Processing happens asynchronously
"""

import json
import os
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, asdict

from lib.diagnostics import log_debug

# ============= Configuration =============
QUEUE_DIR = Path.home() / ".spark" / "queue"
EVENTS_FILE = QUEUE_DIR / "events.jsonl"
MAX_EVENTS = 10000  # Rotate after this many events
LOCK_FILE = QUEUE_DIR / ".queue.lock"

# Read the tail in chunks to avoid loading large files into memory.
TAIL_CHUNK_BYTES = 64 * 1024


class EventType(Enum):
    """Types of events Spark captures."""
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    USER_PROMPT = "user_prompt"
    PRE_TOOL = "pre_tool"
    POST_TOOL = "post_tool"
    POST_TOOL_FAILURE = "post_tool_failure"
    STOP = "stop"
    LEARNING = "learning"
    ERROR = "error"


@dataclass
class SparkEvent:
    """A captured event."""
    event_type: EventType
    session_id: str
    timestamp: float
    data: Dict[str, Any]
    tool_name: Optional[str] = None
    tool_input: Optional[Dict] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        d = asdict(self)
        d["event_type"] = self.event_type.value
        return d
    
    @classmethod
    def from_dict(cls, data: Dict) -> "SparkEvent":
        """Create from dictionary."""
        data["event_type"] = EventType(data["event_type"])
        return cls(**data)


def quick_capture(event_type: EventType, session_id: str, data: Dict[str, Any],
                  tool_name: Optional[str] = None, tool_input: Optional[Dict] = None,
                  error: Optional[str] = None, trace_id: Optional[str] = None) -> bool:
    """
    Capture an event as fast as possible.
    
    Target: < 10ms
    Method: Append-only file write, no locking, minimal processing
    """
    try:
        if not isinstance(event_type, EventType):
            raise ValueError("invalid_event_type")
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("invalid_session_id")
        if not isinstance(data, dict):
            raise ValueError("invalid_data")

        QUEUE_DIR.mkdir(parents=True, exist_ok=True)
        
        event_ts = time.time()
        data_out = dict(data)
        trace_hint = ""
        if trace_id:
            data_out["trace_id"] = trace_id
        if not data_out.get("trace_id"):
            payload = data_out.get("payload")
            if isinstance(payload, dict):
                trace_hint = str(payload.get("text") or payload.get("intent") or payload.get("command") or "")[:80]
            raw = f"{session_id}|{event_type.value}|{event_ts}|{tool_name or ''}|{trace_hint}"
            data_out["trace_id"] = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]

        event = SparkEvent(
            event_type=event_type,
            session_id=session_id,
            timestamp=event_ts,
            data=data_out,
            tool_name=tool_name,
            tool_input=tool_input,
            error=error
        )
        
        with open(EVENTS_FILE, "a") as f:
            f.write(json.dumps(event.to_dict()) + "\n")

        # Best-effort rotation so the queue doesn't grow unbounded.
        rotate_if_needed()

        return True
        
    except Exception as e:
        # Never fail - just drop the event silently
        log_debug("queue", "quick_capture failed", e)
        return False


def read_events(limit: int = 100, offset: int = 0) -> List[SparkEvent]:
    """Read events from the queue."""
    events = []
    
    if not EVENTS_FILE.exists():
        return events
    
    try:
        with open(EVENTS_FILE, "r") as f:
            idx = 0
            for line in f:
                if idx < offset:
                    idx += 1
                    continue
                if len(events) >= limit:
                    break
                idx += 1
                try:
                    data = json.loads(line.strip())
                    events.append(SparkEvent.from_dict(data))
                except Exception:
                    continue
                
    except Exception as e:
        log_debug("queue", "read_events failed", e)
        pass
    
    return events


def read_recent_events(count: int = 50) -> List[SparkEvent]:
    """Read the most recent events."""
    if not EVENTS_FILE.exists():
        return []
    
    try:
        lines = _tail_lines(EVENTS_FILE, count)
        events = []
        for line in lines:
            try:
                data = json.loads(line.strip())
                events.append(SparkEvent.from_dict(data))
            except Exception:
                continue
        return events
        
    except Exception as e:
        log_debug("queue", "read_recent_events failed", e)
        return []


def count_events() -> int:
    """Count total events in queue."""
    if not EVENTS_FILE.exists():
        return 0
    
    try:
        with open(EVENTS_FILE, "r") as f:
            return sum(1 for _ in f)
    except Exception as e:
        log_debug("queue", "count_events failed", e)
        return 0


def clear_events() -> int:
    """Clear all events from queue. Returns count cleared."""
    count = count_events()
    
    if EVENTS_FILE.exists():
        with _queue_lock():
            if EVENTS_FILE.exists():
                EVENTS_FILE.unlink()
    
    return count


def rotate_if_needed() -> bool:
    """Rotate queue if it's too large."""
    count = count_events()
    
    if count <= MAX_EVENTS:
        return False
    
    try:
        with _queue_lock():
            # Keep only the last half
            keep_count = MAX_EVENTS // 2
            lines = _tail_lines(EVENTS_FILE, keep_count)
            with open(EVENTS_FILE, "w") as f:
                for line in lines:
                    if line:
                        f.write(line.rstrip("\r\n") + "\n")

            print(f"[SPARK] Rotated queue: {count} -> {keep_count} events")
            return True
        
    except Exception as e:
        log_debug("queue", "rotate_if_needed failed", e)
        return False


def get_queue_stats() -> Dict:
    """Get queue statistics."""
    count = count_events()
    size_bytes = 0
    
    if EVENTS_FILE.exists():
        size_bytes = EVENTS_FILE.stat().st_size
    
    return {
        "event_count": count,
        "size_bytes": size_bytes,
        "size_mb": round(size_bytes / (1024 * 1024), 2),
        "queue_file": str(EVENTS_FILE),
        "max_events": MAX_EVENTS,
        "needs_rotation": count > MAX_EVENTS
    }


def get_events_by_type(event_type: EventType, limit: int = 100) -> List[SparkEvent]:
    """Get events of a specific type."""
    events = []
    
    if not EVENTS_FILE.exists():
        return events
    
    try:
        with open(EVENTS_FILE, "r") as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    if data.get("event_type") == event_type.value:
                        events.append(SparkEvent.from_dict(data))
                        if len(events) >= limit:
                            break
                except Exception:
                    continue
    except Exception as e:
        log_debug("queue", "get_events_by_type failed", e)
        pass
    
    return events


def get_error_events(limit: int = 50) -> List[SparkEvent]:
    """Get recent error events."""
    return get_events_by_type(EventType.POST_TOOL_FAILURE, limit)


def get_session_events(session_id: str) -> List[SparkEvent]:
    """Get all events for a specific session."""
    events = []
    
    if not EVENTS_FILE.exists():
        return events
    
    try:
        with open(EVENTS_FILE, "r") as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    if data.get("session_id") == session_id:
                        events.append(SparkEvent.from_dict(data))
                except Exception:
                    continue
    except Exception:
        pass
    
    return events


def _tail_lines(path: Path, count: int) -> List[str]:
    """Read the last N lines of a file without loading the whole file."""
    if count <= 0:
        return []
    if not path.exists():
        return []

    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            pos = f.tell()
            buffer = b""
            lines: List[bytes] = []

            while pos > 0 and len(lines) <= count:
                read_size = min(TAIL_CHUNK_BYTES, pos)
                pos -= read_size
                f.seek(pos)
                data = f.read(read_size)
                buffer = data + buffer

                if b"\n" in buffer:
                    parts = buffer.split(b"\n")
                    buffer = parts[0]
                    lines = parts[1:] + lines

            if buffer:
                lines = [buffer] + lines

            # Drop possible trailing empty line
            # Normalize Windows CRLF to avoid double-CR issues on rewrite.
            out = [
                ln.decode("utf-8", errors="replace").rstrip("\r")
                for ln in lines
                if ln != b""
            ]
            return out[-count:]
    except Exception as e:
        log_debug("queue", "_tail_lines failed", e)
        return []


class _queue_lock:
    """Best-effort lock using an exclusive lock file."""

    def __init__(self, timeout_s: float = 0.5):
        self.timeout_s = timeout_s
        self.fd = None

    def __enter__(self):
        QUEUE_DIR.mkdir(parents=True, exist_ok=True)
        start = time.time()
        while True:
            try:
                self.fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_RDWR)
                return self
            except FileExistsError:
                if time.time() - start >= self.timeout_s:
                    return self
                time.sleep(0.01)
            except Exception as e:
                log_debug("queue", "lock acquire failed", e)
                return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if self.fd is not None:
                os.close(self.fd)
            if LOCK_FILE.exists():
                LOCK_FILE.unlink()
        except Exception as e:
            log_debug("queue", "lock release failed", e)
            pass
