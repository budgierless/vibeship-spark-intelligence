"""
Chip Runtime - Execute observers and store domain insights.

This is the final missing piece: actually DOING something with
the matched triggers and observers.

What this captures that was missing before:
- "GLB models need bounding box calculation for ground collision"
- "Health values tripled from 100 to 300 for better balance"
- "Kid's room environment with purple carpet and kiddie pools"

Instead of just: "Edit tool used" telemetry
"""

import json
import logging
import time
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

from .loader import Chip, ChipObserver, ChipLoader
from .registry import ChipRegistry
from .router import ChipRouter, TriggerMatch

log = logging.getLogger("spark.chips")

# Storage for chip insights
CHIP_INSIGHTS_DIR = Path.home() / ".spark" / "chip_insights"


@dataclass
class ChipInsight:
    """A domain-specific insight captured by a chip."""
    chip_id: str
    observer_name: str
    trigger: str
    content: str  # The actual insight
    captured_data: Dict[str, Any]
    confidence: float
    timestamp: str
    event_summary: str


class ChipRuntime:
    """
    The runtime that ties everything together:
    1. Load chips
    2. Match events to triggers
    3. Execute observers
    4. Store domain insights
    """

    def __init__(self):
        self.registry = ChipRegistry()
        self.router = ChipRouter()
        self._ensure_storage()

    def _ensure_storage(self):
        """Ensure chip insights directory exists."""
        CHIP_INSIGHTS_DIR.mkdir(parents=True, exist_ok=True)

    def process_event(self, event: Dict[str, Any], project_path: str = None) -> List[ChipInsight]:
        """
        Process an event through all active chips.

        This is the main entry point for the chip system.
        """
        insights = []

        # Get active chips (auto-activates based on content)
        content = self._extract_event_content(event)
        if content:
            self.registry.auto_activate_for_content(content, project_path)

        active_chips = self.registry.get_active_chips(project_path)
        if not active_chips:
            return insights

        # Route event to matching chips/observers
        matches = self.router.route_event(event, active_chips)
        if not matches:
            return insights

        return self._process_matches(matches, event)

    def process_event_for_chips(self, event: Dict[str, Any], chips: List[Chip]) -> List[ChipInsight]:
        """Process an event for a specific list of chips (no activation changes)."""
        if not chips:
            return []
        matches = self.router.route_event(event, chips)
        if not matches:
            return []
        return self._process_matches(matches, event)

    def _process_matches(self, matches: List[TriggerMatch], event: Dict[str, Any]) -> List[ChipInsight]:
        """Execute observers for matched triggers."""
        insights: List[ChipInsight] = []
        for match in matches:
            insight = self._execute_observer(match, event)
            if insight:
                insights.append(insight)
                self._store_insight(insight)
                log.info(
                    f"Captured insight from {match.chip.id}/{match.observer.name if match.observer else 'chip'}: "
                    f"{insight.content[:100]}"
                )
        return insights

    def _extract_event_content(self, event: Dict[str, Any]) -> str:
        """Extract content from event for trigger matching."""
        parts = []

        event_type = event.get('event_type') or event.get('hook_event') or event.get('type') or event.get('kind')
        if event_type:
            parts.append(str(event_type))

        for key in ['tool_name', 'tool', 'file_path', 'cwd']:
            if key in event and event[key]:
                parts.append(str(event[key]))

        inp = event.get('input') or event.get('tool_input') or {}
        if isinstance(inp, dict):
            for v in inp.values():
                if v and isinstance(v, str):
                    parts.append(v[:2000])
        elif isinstance(inp, str):
            parts.append(inp[:2000])

        output = event.get('output') or event.get('result') or ''
        if isinstance(output, str):
            parts.append(output[:1000])

        data = event.get('data')
        if isinstance(data, dict):
            for v in data.values():
                if v and isinstance(v, str):
                    parts.append(v[:1000])

        return ' '.join(parts)

    def _execute_observer(self, match: TriggerMatch, event: Dict[str, Any]) -> Optional[ChipInsight]:
        """
        Execute an observer and capture domain-specific data.

        This extracts MEANING, not just metadata.
        """
        try:
            # Build context from event
            content = self._extract_event_content(event)
            captured = self._capture_data(match, event)

            if match.observer:
                fields = self._extract_observer_fields(match.observer, event, content, match.content_snippet)
                field_confidence = self._field_confidence(match.observer, fields)
                captured['fields'] = fields
                captured['field_confidence'] = field_confidence

                if match.observer.capture_required and field_confidence < 0.5:
                    return None

            # Generate insight content
            content = self._generate_insight_content(match, captured, event)
            if not content:
                return None

            confidence = match.confidence
            if match.observer and 'field_confidence' in captured:
                confidence = min(confidence, captured['field_confidence'])

            return ChipInsight(
                chip_id=match.chip.id,
                observer_name=match.observer.name if match.observer else "chip_level",
                trigger=match.trigger,
                content=content,
                captured_data=captured,
                confidence=confidence,
                timestamp=datetime.now().isoformat(),
                event_summary=self._summarize_event(event)
            )
        except Exception as e:
            log.warning(f"Failed to execute observer: {e}")
            return None

    def _capture_data(self, match: TriggerMatch, event: Dict[str, Any]) -> Dict[str, Any]:
        """Capture relevant data based on observer definition."""
        captured = {
            'trigger': match.trigger,
            'chip': match.chip.id,
        }

        # Add file path context
        file_path = event.get('file_path')
        if not file_path:
            inp = event.get('input') or event.get('tool_input') or {}
            if isinstance(inp, dict):
                file_path = inp.get('file_path') or inp.get('path')
        if file_path:
            captured['file_path'] = str(file_path)

        # Add tool context
        tool = event.get('tool_name') or event.get('tool')
        if tool:
            captured['tool'] = tool

        # Add CWD (project context)
        cwd = event.get('cwd') or event.get('data', {}).get('cwd')
        if cwd:
            captured['project'] = str(cwd)

        # Try to extract meaningful changes from Edit/Write
        inp = event.get('input') or event.get('tool_input') or {}
        if isinstance(inp, dict):
            if 'old_string' in inp and 'new_string' in inp:
                captured['change_type'] = 'edit'
                captured['change_summary'] = self._summarize_change(
                    inp.get('old_string', ''),
                    inp.get('new_string', '')
                )
            elif 'content' in inp:
                captured['change_type'] = 'write'
                captured['content_summary'] = self._summarize_content(inp['content'])

        return captured

    def _extract_observer_fields(self, observer: ChipObserver, event: Dict[str, Any], content: str,
                                 trigger_snippet: str = "") -> Dict[str, Any]:
        """Extract fields from event using observer extraction rules."""
        fields: Dict[str, Any] = {}

        # Try extraction rules first
        for extraction in observer.extraction:
            field_name = extraction.get("field", "")
            if not field_name:
                continue
            value = None

            patterns = extraction.get("patterns", []) or []
            for pattern in patterns:
                try:
                    match = re.search(pattern, content, re.IGNORECASE)
                except re.error:
                    continue
                if match:
                    if match.groups():
                        value = match.group(1).strip()
                    else:
                        value = match.group(0).strip()
                    break

            if value is None:
                keywords = extraction.get("keywords", {}) or {}
                for keyword_value, keyword_patterns in keywords.items():
                    for kp in keyword_patterns:
                        if kp.lower() in content.lower():
                            value = keyword_value
                            break
                    if value is not None:
                        break

            if value is not None:
                fields[field_name] = value

        # Try to extract required fields from event directly
        for field_name in observer.capture_required:
            if field_name not in fields:
                if field_name == "pattern" and trigger_snippet:
                    fields[field_name] = trigger_snippet.strip()
                    continue
                value = self._get_event_field(event, field_name)
                if value is not None:
                    fields[field_name] = value

        # Try optional fields
        for field_name in observer.capture_optional:
            if field_name not in fields:
                value = self._get_event_field(event, field_name)
                if value is not None:
                    fields[field_name] = value

        return fields

    def _get_event_field(self, event: Dict[str, Any], field_name: str) -> Optional[Any]:
        """Best-effort lookup for a field in common event containers."""
        if field_name in event:
            return event[field_name]

        containers = [
            event.get("payload"),
            event.get("tool_input"),
            event.get("input"),
            event.get("data"),
        ]

        data = event.get("data")
        if isinstance(data, dict):
            containers.append(data.get("payload"))

        for container in containers:
            if isinstance(container, dict) and field_name in container:
                return container[field_name]

        return None

    def _field_confidence(self, observer: ChipObserver, fields: Dict[str, Any]) -> float:
        """Calculate confidence based on required fields captured."""
        required_count = len(observer.capture_required)
        if required_count == 0:
            return 1.0
        captured_required = sum(1 for f in observer.capture_required if f in fields)
        return captured_required / required_count

    def _summarize_change(self, old: str, new: str) -> str:
        """Summarize what changed between old and new."""
        old_lines = len(old.split('\n'))
        new_lines = len(new.split('\n'))

        # Look for key patterns
        patterns = []

        # Numbers that changed (like health values)
        old_nums = set(re.findall(r'\b\d+\b', old))
        new_nums = set(re.findall(r'\b\d+\b', new))
        changed_nums = new_nums - old_nums
        if changed_nums:
            patterns.append(f"numbers: {list(changed_nums)[:5]}")

        # Key terms that appeared
        keywords = ['health', 'damage', 'speed', 'position', 'collision', 'animation',
                    'physics', 'balance', 'baseY', 'bounding', 'scale']
        for kw in keywords:
            if kw.lower() in new.lower() and kw.lower() not in old.lower():
                patterns.append(f"added: {kw}")

        if patterns:
            return f"{old_lines}->{new_lines} lines, " + ", ".join(patterns[:3])
        return f"{old_lines}->{new_lines} lines"

    def _summarize_content(self, content: str) -> str:
        """Summarize content for new file writes."""
        lines = content.split('\n')
        return f"{len(lines)} lines"

    def _generate_insight_content(self, match: TriggerMatch, captured: Dict, event: Dict) -> str:
        """
        Generate human-readable insight content.

        Priority: extracted fields > event content > trigger context
        Goal: produce insights a human would find useful, not operational logs.
        """
        fields = captured.get("fields") or {}
        data = event.get("data") or event.get("input") or {}

        # Try to build a meaningful insight from extracted fields first
        if fields:
            return self._build_field_based_insight(match, fields, data)

        # For X research events, extract from content
        if event.get("event_type") == "x_research":
            content = data.get("content") or data.get("text", "")
            ecosystem = data.get("ecosystem", "")
            engagement = data.get("engagement", 0)
            sentiment = data.get("sentiment", "neutral")

            if content:
                # Truncate content meaningfully
                snippet = content[:150].strip()
                if len(content) > 150:
                    snippet = snippet.rsplit(' ', 1)[0] + "..."

                parts = []
                if ecosystem:
                    parts.append(f"[{ecosystem}]")
                if engagement and engagement > 20:
                    parts.append(f"(eng:{engagement})")
                parts.append(snippet)
                if sentiment != "neutral":
                    parts.append(f"[{sentiment}]")

                return " ".join(parts)

        # Fallback: provide context but not just "Triggered by X"
        chip_name = match.chip.name

        # Try to get meaningful content from event
        content = self._extract_event_content(event)
        if content and len(content) > 20:
            snippet = content[:200].strip()
            if len(content) > 200:
                snippet = snippet.rsplit(' ', 1)[0] + "..."
            return f"[{chip_name}] {snippet}"

        # Last resort: minimal trigger context (but filter these as primitive)
        if 'file_path' in captured:
            filename = Path(captured['file_path']).name
            return f"[{chip_name}] Activity in {filename}"

        # This will likely be filtered as primitive - that's intentional
        return f"[{chip_name}] Observation: {match.trigger}"

    def _build_field_based_insight(self, match: TriggerMatch, fields: Dict, data: Dict) -> str:
        """Build insight from extracted structured fields."""
        chip_id = match.chip.id
        observer_name = match.observer.name if match.observer else ""

        # Market intelligence patterns
        if chip_id == "market-intel":
            if "competitor" in fields and "gap_type" in fields:
                comp = fields["competitor"]
                gap = fields["gap_type"]
                opp = fields.get("opportunity", "")
                if opp:
                    return f"Competitor gap: {comp} lacks {gap} -> opportunity: {opp}"
                return f"Competitor gap: {comp} lacks {gap}"

            if "content_type" in fields and "engagement_signal" in fields:
                ct = fields["content_type"]
                eng = fields["engagement_signal"]
                hook = fields.get("hook", "")
                if hook:
                    return f"Viral pattern: {ct} with {eng} engagement, hook: \"{hook}\""
                return f"Viral pattern: {ct} content showing {eng} engagement"

            if "sentiment" in fields and "subject" in fields:
                sent = fields["sentiment"]
                subj = fields["subject"]
                return f"User sentiment: {sent} about {subj}"

            if "insight_type" in fields and "insight" in fields:
                return f"Product insight ({fields['insight_type']}): {fields['insight']}"

        # Game dev patterns
        if chip_id == "game_dev":
            if "balance_decision" in fields:
                return f"Balance decision: {fields['balance_decision']}"
            if "feel_factor" in fields:
                return f"Game feel: {fields['feel_factor']}"

        # Generic field-based insight
        key_fields = [(k, v) for k, v in fields.items() if v and k not in ("trigger", "chip")]
        if key_fields:
            summary = ", ".join(f"{k}: {v}" for k, v in key_fields[:3])
            return f"[{match.chip.name}] {summary}"

        return ""

    def _summarize_event(self, event: Dict[str, Any]) -> str:
        """Create a short summary of the event."""
        tool = event.get('tool_name') or event.get('tool') or 'unknown'
        file_path = event.get('file_path')
        if not file_path:
            inp = event.get('input') or event.get('tool_input') or {}
            if isinstance(inp, dict):
                file_path = inp.get('file_path') or inp.get('path')

        if file_path:
            return f"{tool} on {Path(file_path).name}"
        return tool

    # Maximum chip insight file size before rotation (10 MB)
    CHIP_MAX_BYTES = 10 * 1024 * 1024

    def _store_insight(self, insight: ChipInsight):
        """Store an insight to disk with size-based rotation."""
        try:
            chip_file = CHIP_INSIGHTS_DIR / f"{insight.chip_id}.jsonl"
            # Rotate if file exceeds size limit
            if chip_file.exists():
                try:
                    size = chip_file.stat().st_size
                    if size > self.CHIP_MAX_BYTES:
                        self._rotate_chip_file(chip_file)
                except Exception:
                    pass
            with open(chip_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(asdict(insight)) + '\n')
        except Exception as e:
            log.error(f"Failed to store insight: {e}")

    def _rotate_chip_file(self, chip_file: Path):
        """Rotate a chip insights file - keep only the last 25% of lines."""
        try:
            keep_bytes = self.CHIP_MAX_BYTES // 4  # Keep ~2.5 MB
            size = chip_file.stat().st_size
            if size <= keep_bytes:
                return
            # Read from the tail
            with open(chip_file, 'rb') as f:
                f.seek(max(0, size - keep_bytes))
                # Skip partial line
                f.readline()
                tail_data = f.read()
            # Rewrite
            tmp = chip_file.with_suffix('.jsonl.tmp')
            with open(tmp, 'wb') as f:
                f.write(tail_data)
            tmp.replace(chip_file)
            log.info(f"Rotated {chip_file.name}: {size:,} -> {len(tail_data):,} bytes")
        except Exception as e:
            log.warning(f"Chip file rotation failed for {chip_file}: {e}")

    def get_insights(self, chip_id: str = None, limit: int = 50) -> List[ChipInsight]:
        """Get recent insights, optionally filtered by chip."""
        insights = []

        if chip_id:
            files = [CHIP_INSIGHTS_DIR / f"{chip_id}.jsonl"]
        else:
            files = list(CHIP_INSIGHTS_DIR.glob("*.jsonl"))

        for file_path in files:
            if not file_path.exists():
                continue
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            insights.append(ChipInsight(**data))
            except Exception as e:
                log.warning(f"Failed to read {file_path}: {e}")

        # Sort by timestamp descending
        insights.sort(key=lambda i: i.timestamp, reverse=True)
        return insights[:limit]


# Singleton runtime
_runtime: Optional[ChipRuntime] = None


def get_runtime() -> ChipRuntime:
    """Get the singleton chip runtime."""
    global _runtime
    if _runtime is None:
        _runtime = ChipRuntime()
    return _runtime


def process_chip_events(events: List[Dict[str, Any]], project_path: str = None) -> Dict[str, Any]:
    """
    Process events through the chip system.

    This is the function to call from bridge_cycle.py.
    """
    runtime = get_runtime()
    stats = {
        'events_processed': 0,
        'insights_captured': 0,
        'chips_activated': [],
    }

    for event in events:
        insights = runtime.process_event(event, project_path)
        stats['events_processed'] += 1
        stats['insights_captured'] += len(insights)

    # Track which chips are active
    active = runtime.registry.get_active_chips(project_path)
    stats['chips_activated'] = [c.id for c in active]

    return stats
