"""
Spark Advisor: The Missing Link Between Learning and Action

This module closes the critical gap in Spark's architecture:
  Storage → Analysis → [ADVISOR] → Decision Impact

The Problem:
  - Spark captures insights beautifully (cognitive_learner, aha_tracker)
  - Spark stores them persistently (Mind sync, JSON files)
  - But insights are NEVER USED during actual task execution

The Solution:
  - Advisor queries relevant insights BEFORE actions
  - Advisor tracks whether advice was followed
  - Advisor learns which advice actually helps

KISS Principle: Single file, simple API, maximum impact.
"""

import json
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field, asdict

# Import existing Spark components
from .cognitive_learner import get_cognitive_learner, CognitiveCategory
from .mind_bridge import get_mind_bridge, HAS_REQUESTS
from .memory_banks import retrieve as bank_retrieve, infer_project_key


# ============= Configuration =============
ADVISOR_DIR = Path.home() / ".spark" / "advisor"
ADVICE_LOG = ADVISOR_DIR / "advice_log.jsonl"
EFFECTIVENESS_FILE = ADVISOR_DIR / "effectiveness.json"
RECENT_ADVICE_LOG = ADVISOR_DIR / "recent_advice.jsonl"
RECENT_ADVICE_MAX_AGE_S = 300
RECENT_ADVICE_MAX_LINES = 200

# Thresholds (Improvement #8: Advisor Integration tuneables)
MIN_RELIABILITY_FOR_ADVICE = 0.5  # Lowered from 0.6 for more advice coverage
MIN_VALIDATIONS_FOR_STRONG_ADVICE = 2
MAX_ADVICE_ITEMS = 8  # Raised from 5 for complex tasks
ADVICE_CACHE_TTL_SECONDS = 120  # 2 minutes (lowered from 5 for fresher advice)


# ============= Data Classes =============
@dataclass
class Advice:
    """A piece of advice derived from learnings."""
    advice_id: str
    insight_key: str
    text: str
    confidence: float
    source: str  # "cognitive", "mind", "pattern", "surprise"
    context_match: float  # How well it matches current context
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AdviceOutcome:
    """Tracks whether advice was followed and if it helped."""
    advice_id: str
    was_followed: bool
    was_helpful: Optional[bool] = None
    outcome_notes: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ============= Core Advisor =============
class SparkAdvisor:
    """
    The advisor that makes learnings actionable.

    Usage:
        advisor = get_advisor()

        # Before action: get relevant advice
        advice = advisor.advise("Edit", {"file": "main.py"}, "fixing bug")

        # After action: report outcome
        advisor.report_outcome(advice.advice_id, followed=True, helpful=True)
    """

    def __init__(self):
        ADVISOR_DIR.mkdir(parents=True, exist_ok=True)
        self.cognitive = get_cognitive_learner()
        self.mind = get_mind_bridge()
        self.effectiveness = self._load_effectiveness()
        self._cache: Dict[str, Tuple[List[Advice], float]] = {}

    def _load_effectiveness(self) -> Dict[str, Any]:
        """Load effectiveness tracking data."""
        if EFFECTIVENESS_FILE.exists():
            try:
                return json.loads(EFFECTIVENESS_FILE.read_text())
            except Exception:
                pass
        return {
            "total_advice_given": 0,
            "total_followed": 0,
            "total_helpful": 0,
            "by_source": {},
            "by_category": {},
        }

    def _save_effectiveness(self):
        """Save effectiveness data."""
        EFFECTIVENESS_FILE.write_text(json.dumps(self.effectiveness, indent=2))

    def _generate_advice_id(self, context: str) -> str:
        """Generate unique advice ID."""
        ts = str(time.time())
        return hashlib.sha256(f"{context}:{ts}".encode()).hexdigest()[:12]

    def _cache_key(self, tool: str, context: str) -> str:
        """Generate cache key for advice."""
        return f"{tool}:{context[:50]}"

    def _get_cached_advice(self, key: str) -> Optional[List[Advice]]:
        """Get cached advice if still valid."""
        if key in self._cache:
            advice, timestamp = self._cache[key]
            if time.time() - timestamp < ADVICE_CACHE_TTL_SECONDS:
                return advice
            del self._cache[key]
        return None

    def _cache_advice(self, key: str, advice: List[Advice]):
        """Cache advice for reuse."""
        self._cache[key] = (advice, time.time())
        # Keep cache bounded
        if len(self._cache) > 100:
            oldest = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest]

    # ============= Core Advice Generation =============

    def advise(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        task_context: str = "",
        include_mind: bool = True
    ) -> List[Advice]:
        """
        Get relevant advice before executing an action.

        This is the KEY function that closes the learning gap.

        Args:
            tool_name: The tool about to be used (e.g., "Edit", "Bash")
            tool_input: The input to the tool
            task_context: Optional description of what we're trying to do
            include_mind: Whether to query Mind for additional context

        Returns:
            List of Advice objects, sorted by relevance
        """
        # Build context string for matching
        context_parts = [tool_name]
        if tool_input:
            context_parts.append(str(tool_input)[:200])
        if task_context:
            context_parts.append(task_context)
        context = " ".join(context_parts).lower()

        # Check cache
        cache_key = self._cache_key(tool_name, context)
        cached = self._get_cached_advice(cache_key)
        if cached:
            return cached

        advice_list: List[Advice] = []

        # 1. Query memory banks (fast local)
        advice_list.extend(self._get_bank_advice(context))

        # 2. Query cognitive insights
        advice_list.extend(self._get_cognitive_advice(tool_name, context))

        # 3. Query Mind if available
        if include_mind and HAS_REQUESTS:
            advice_list.extend(self._get_mind_advice(context))

        # 4. Get tool-specific learnings
        advice_list.extend(self._get_tool_specific_advice(tool_name))

        # 5. Get surprise-based cautions
        advice_list.extend(self._get_surprise_advice(tool_name, context))

        # 6. Get skill-based hints
        advice_list.extend(self._get_skill_advice(context))

        # Sort by relevance (confidence * context_match * effectiveness_boost)
        advice_list = self._rank_advice(advice_list)

        # Limit to top N
        advice_list = advice_list[:MAX_ADVICE_ITEMS]

        # Log advice given
        self._log_advice(advice_list, tool_name, context)

        # Track retrievals in Meta-Ralph for outcome tracking
        try:
            from .meta_ralph import get_meta_ralph
            ralph = get_meta_ralph()
            for adv in advice_list:
                ralph.track_retrieval(
                    adv.advice_id,
                    adv.text,
                    insight_key=adv.insight_key,
                    source=adv.source,
                )
        except Exception:
            pass  # Don't break advice flow if tracking fails

        # Cache for reuse
        self._cache_advice(cache_key, advice_list)

        return advice_list

    def _get_cognitive_advice(self, tool_name: str, context: str) -> List[Advice]:
        """Get advice from cognitive insights."""
        advice = []

        # Query insights relevant to this context
        insights = self.cognitive.get_insights_for_context(context, limit=10, with_keys=True)

        # Also get tool-specific insights
        tool_insights = self.cognitive.get_insights_for_context(tool_name, limit=5, with_keys=True)

        # Combine and dedupe
        seen = set()
        for insight_key, insight in insights + tool_insights:
            key = insight_key or insight.insight[:50]
            if key in seen:
                continue
            seen.add(key)

            if insight.reliability < MIN_RELIABILITY_FOR_ADVICE:
                continue
            if hasattr(self.cognitive, "is_noise_insight") and self.cognitive.is_noise_insight(insight.insight):
                continue

            # Calculate context match
            context_match = self._calculate_context_match(insight.context, context)

            advice.append(Advice(
                advice_id=self._generate_advice_id(insight.insight),
                insight_key=insight_key,
                text=insight.insight,
                confidence=insight.reliability,
                source="cognitive",
                context_match=context_match,
            ))

        return advice

    def _get_bank_advice(self, context: str) -> List[Advice]:
        """Get advice from memory banks (project/global)."""
        advice: List[Advice] = []
        try:
            project_key = infer_project_key()
            memories = bank_retrieve(context, project_key=project_key, limit=5)
        except Exception:
            return advice

        for mem in memories:
            text = (mem.get("text") or "").strip()
            if not text:
                continue
            if hasattr(self.cognitive, "is_noise_insight") and self.cognitive.is_noise_insight(text):
                continue
            context_match = self._calculate_context_match(text, context)
            advice.append(Advice(
                advice_id=self._generate_advice_id(text),
                insight_key=f"bank:{mem.get('entry_id', '')}",
                text=text[:200],
                confidence=0.65,
                source="bank",
                context_match=context_match,
            ))

        return advice

    def _get_mind_advice(self, context: str) -> List[Advice]:
        """Get advice from Mind persistent memory."""
        advice = []

        try:
            if hasattr(self.mind, "_check_mind_health") and not self.mind._check_mind_health():
                return advice
            memories = self.mind.retrieve_relevant(context, limit=5)

            for mem in memories:
                content = mem.get("content", "")
                salience = mem.get("salience", 0.5)

                if salience < 0.5:
                    continue
                if hasattr(self.cognitive, "is_noise_insight") and self.cognitive.is_noise_insight(content):
                    continue

                advice.append(Advice(
                    advice_id=self._generate_advice_id(content),
                    insight_key=f"mind:{mem.get('memory_id', 'unknown')[:12]}",
                    text=content[:200],
                    confidence=salience,
                    source="mind",
                    context_match=0.7,  # Mind already does semantic matching
                ))
        except Exception:
            pass  # Mind unavailable, gracefully skip

        return advice

    def _get_tool_specific_advice(self, tool_name: str) -> List[Advice]:
        """Get advice specific to a tool based on past failures."""
        advice = []

        # Get self-awareness insights about this tool
        for insight in self.cognitive.get_self_awareness_insights():
            if tool_name.lower() in insight.insight.lower():
                advice.append(Advice(
                    advice_id=self._generate_advice_id(insight.insight),
                    insight_key=f"tool:{tool_name}",
                    text=f"[Caution] {insight.insight}",
                    confidence=insight.reliability,
                    source="self_awareness",
                    context_match=1.0,  # Direct tool match
                ))

        return advice

    def _get_surprise_advice(self, tool_name: str, context: str) -> List[Advice]:
        """Get advice from past surprises (unexpected failures)."""
        advice = []

        try:
            from .aha_tracker import get_aha_tracker
            aha = get_aha_tracker()

            # Get recent surprises related to this tool/context
            for surprise in aha.get_recent_surprises(30):
                if surprise.surprise_type != "unexpected_failure":
                    continue
                if tool_name.lower() not in str(surprise.context).lower():
                    continue
                lesson = surprise.lesson_extracted or "Be careful - this failed unexpectedly before"
                advice.append(Advice(
                    advice_id=self._generate_advice_id(lesson),
                    insight_key=f"surprise:{surprise.surprise_type}",
                    text=f"[Past Failure] {lesson}",
                    confidence=0.8,
                    source="surprise",
                    context_match=0.9,
                ))
        except Exception:
            pass  # aha_tracker might not be available

        return advice

    def _get_skill_advice(self, context: str) -> List[Advice]:
        """Get hints from relevant skills."""
        advice: List[Advice] = []
        try:
            from .skills_router import recommend_skills
            skills = recommend_skills(context, limit=3)
        except Exception:
            return advice

        for s in skills:
            sid = s.get("skill_id") or s.get("name") or "unknown-skill"
            desc = (s.get("description") or "").strip()
            if desc:
                text = f"Consider skill [{sid}]: {desc[:120]}"
            else:
                text = f"Consider skill [{sid}]"
            advice.append(Advice(
                advice_id=self._generate_advice_id(text),
                insight_key=f"skill:{sid}",
                text=text,
                confidence=0.6,
                source="skill",
                context_match=0.7,
            ))

        return advice

    def _calculate_context_match(self, insight_context: str, current_context: str) -> float:
        """Calculate how well an insight's context matches current context."""
        if not insight_context or not current_context:
            return 0.5

        insight_words = set(insight_context.lower().split())
        current_words = set(current_context.lower().split())

        if not insight_words:
            return 0.5

        overlap = len(insight_words & current_words)
        return min(1.0, overlap / max(len(insight_words), 1) + 0.3)

    def _rank_advice(self, advice_list: List[Advice]) -> List[Advice]:
        """Rank advice by relevance and effectiveness."""
        def score(a: Advice) -> float:
            base_score = a.confidence * a.context_match

            # Boost based on past effectiveness
            source_stats = self.effectiveness.get("by_source", {}).get(a.source, {})
            if source_stats.get("total", 0) > 0:
                helpful_rate = source_stats.get("helpful", 0) / source_stats["total"]
                base_score *= (0.5 + helpful_rate)  # 0.5x to 1.5x boost

            return base_score

        return sorted(advice_list, key=score, reverse=True)

    def _log_advice(self, advice_list: List[Advice], tool: str, context: str):
        """Log advice given for later analysis."""
        if not advice_list:
            return

        entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool,
            "context": context[:100],
            "advice_ids": [a.advice_id for a in advice_list],
            "advice_texts": [a.text[:100] for a in advice_list],
            "insight_keys": [a.insight_key for a in advice_list],
            "sources": [a.source for a in advice_list],
        }

        with open(ADVICE_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        self.effectiveness["total_advice_given"] += len(advice_list)
        self._save_effectiveness()

        # Keep a lightweight recent-advice log for outcome linkage.
        recent = {
            "ts": time.time(),
            "tool": tool,
            "advice_ids": [a.advice_id for a in advice_list],
            "insight_keys": [a.insight_key for a in advice_list],
            "sources": [a.source for a in advice_list],
        }
        try:
            with open(RECENT_ADVICE_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(recent) + "\n")
        except Exception:
            pass

    def _get_recent_advice_entry(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Return the most recent advice entry for a tool within TTL."""
        if not RECENT_ADVICE_LOG.exists():
            return None
        try:
            lines = RECENT_ADVICE_LOG.read_text(encoding="utf-8").splitlines()
        except Exception:
            return None

        now = time.time()
        tool_lower = tool_name.lower()  # Case-insensitive matching
        for line in reversed(lines[-RECENT_ADVICE_MAX_LINES:]):
            try:
                entry = json.loads(line)
            except Exception:
                continue
            # Case-insensitive tool name matching (fixes Task vs task mismatch)
            if entry.get("tool", "").lower() != tool_lower:
                continue
            ts = float(entry.get("ts") or 0.0)
            if now - ts <= RECENT_ADVICE_MAX_AGE_S:
                return entry
        return None

    def _find_recent_advice_by_id(self, advice_id: str) -> Optional[Dict[str, Any]]:
        """Find recent advice entry containing a specific advice_id."""
        if not RECENT_ADVICE_LOG.exists() or not advice_id:
            return None
        try:
            lines = RECENT_ADVICE_LOG.read_text(encoding="utf-8").splitlines()
        except Exception:
            return None
        for line in reversed(lines[-RECENT_ADVICE_MAX_LINES:]):
            try:
                entry = json.loads(line)
            except Exception:
                continue
            ids = entry.get("advice_ids") or []
            if advice_id in ids:
                return entry
        return None

    # ============= Outcome Tracking =============

    def report_outcome(
        self,
        advice_id: str,
        was_followed: bool,
        was_helpful: Optional[bool] = None,
        notes: str = ""
    ):
        """
        Report whether advice was followed and if it helped.

        This closes the feedback loop - we learn which advice actually works.

        Args:
            advice_id: ID of the advice
            was_followed: Did the user/agent follow this advice?
            was_helpful: If followed, did it help? (None if unclear)
            notes: Optional notes about the outcome
        """
        outcome = AdviceOutcome(
            advice_id=advice_id,
            was_followed=was_followed,
            was_helpful=was_helpful,
            outcome_notes=notes,
        )

        # Update effectiveness stats
        if was_followed:
            self.effectiveness["total_followed"] += 1
        if was_helpful:
            self.effectiveness["total_helpful"] += 1

        self._save_effectiveness()

        # Track outcome in Meta-Ralph
        try:
            from .meta_ralph import get_meta_ralph
            ralph = get_meta_ralph()
            outcome_str = "good" if was_helpful else ("bad" if was_helpful is False else "unknown")
            ralph.track_outcome(advice_id, outcome_str, notes)
        except Exception:
            pass  # Don't break outcome flow if tracking fails

        # Log outcome
        with open(ADVICE_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({"outcome": asdict(outcome)}) + "\n")

    def report_action_outcome(
        self,
        tool_name: str,
        success: bool,
        advice_was_relevant: bool = False
    ):
        """
        Simplified outcome reporting after any action.

        Call this after each tool execution to build the feedback loop.
        """
        # Update source effectiveness based on whether advice helped
        source = "cognitive"  # Default

        if source not in self.effectiveness.get("by_source", {}):
            self.effectiveness.setdefault("by_source", {})[source] = {
                "total": 0, "helpful": 0
            }

        self.effectiveness["by_source"][source]["total"] += 1
        if success and advice_was_relevant:
            self.effectiveness["by_source"][source]["helpful"] += 1

        self._save_effectiveness()

        # Report outcome to Meta-Ralph for feedback loop.
        # Track ALL outcomes, not just ones with prior advice.
        outcome_str = "good" if success else "bad"
        evidence = f"tool={tool_name} success={success}"

        try:
            from .meta_ralph import get_meta_ralph
            ralph = get_meta_ralph()

            # If there was prior advice, link outcomes to those advice IDs
            entry = self._get_recent_advice_entry(tool_name)
            if entry:
                advice_ids = entry.get("advice_ids") or []
                for aid in advice_ids:
                    ralph.track_outcome(aid, outcome_str, evidence)

            # Also track tool-level outcome (even without specific advice)
            tool_outcome_id = f"tool:{tool_name}"
            ralph.track_outcome(tool_outcome_id, outcome_str, evidence)
        except Exception:
            pass

    def record_advice_feedback(
        self,
        helpful: Optional[bool],
        notes: str = "",
        tool: Optional[str] = None,
        advice_id: Optional[str] = None,
        followed: bool = True,
    ) -> Dict[str, Any]:
        """Record explicit feedback on advice helpfulness.

        If advice_id is provided, records outcome for that advice.
        Else if tool is provided, uses the most recent advice entry for that tool.
        """
        if advice_id:
            self.report_outcome(advice_id, was_followed=followed, was_helpful=helpful, notes=notes or "")
            try:
                entry = self._find_recent_advice_by_id(advice_id)
                insight_keys = []
                sources = []
                tool_name = tool
                if entry:
                    tool_name = tool_name or entry.get("tool")
                    ids = entry.get("advice_ids") or []
                    idx = ids.index(advice_id) if advice_id in ids else -1
                    ik = entry.get("insight_keys") or []
                    src = entry.get("sources") or []
                    if 0 <= idx < len(ik):
                        insight_keys = [ik[idx]]
                    if 0 <= idx < len(src):
                        sources = [src[idx]]
                from .advice_feedback import record_feedback
                record_feedback(
                    advice_ids=[advice_id],
                    tool=tool_name,
                    helpful=helpful,
                    followed=followed,
                    notes=notes or "",
                    insight_keys=insight_keys,
                    sources=sources,
                )
            except Exception:
                pass
            return {"status": "ok", "advice_ids": [advice_id], "tool": tool}

        if tool:
            entry = self._get_recent_advice_entry(tool)
            if not entry:
                return {"status": "not_found", "message": "No recent advice found for tool", "tool": tool}
            advice_ids = entry.get("advice_ids") or []
            if not advice_ids:
                return {"status": "not_found", "message": "Recent advice had no advice_ids", "tool": tool}
            for aid in advice_ids:
                self.report_outcome(aid, was_followed=followed, was_helpful=helpful, notes=notes or "")
            try:
                insight_keys = entry.get("insight_keys") or []
                sources = entry.get("sources") or []
                from .advice_feedback import record_feedback
                record_feedback(
                    advice_ids=advice_ids,
                    tool=tool,
                    helpful=helpful,
                    followed=followed,
                    notes=notes or "",
                    insight_keys=insight_keys,
                    sources=sources,
                )
            except Exception:
                pass
            return {"status": "ok", "advice_ids": advice_ids, "tool": tool}

        return {"status": "error", "message": "Provide advice_id or tool"}

    # ============= Quick Access Methods =============

    def get_quick_advice(self, tool_name: str) -> Optional[str]:
        """
        Get single most relevant piece of advice for a tool.

        This is the simplest integration point - just call this before any action.
        """
        advice_list = self.advise(tool_name, {}, include_mind=False)
        if advice_list:
            return advice_list[0].text
        return None

    def should_be_careful(self, tool_name: str) -> Tuple[bool, str]:
        """
        Quick check: should we be extra careful with this tool?

        Returns (should_be_careful, reason)
        """
        # Check self-awareness for struggles with this tool
        for insight in self.cognitive.get_self_awareness_insights():
            if tool_name.lower() in insight.insight.lower():
                if "struggle" in insight.insight.lower() or "fail" in insight.insight.lower():
                    return True, insight.insight

        return False, ""

    def get_effectiveness_report(self) -> Dict:
        """Get report on how effective advice has been."""
        total = self.effectiveness.get("total_advice_given", 0)
        followed = self.effectiveness.get("total_followed", 0)
        helpful = self.effectiveness.get("total_helpful", 0)

        return {
            "total_advice_given": total,
            "follow_rate": followed / max(total, 1),
            "helpfulness_rate": helpful / max(followed, 1) if followed > 0 else 0,
            "by_source": self.effectiveness.get("by_source", {}),
        }

    # ============= Context Generation =============

    def generate_context_block(self, tool_name: str, task_context: str = "", include_mind: bool = False) -> str:
        """
        Generate a context block that can be injected into prompts.

        This is how learnings become actionable in the LLM context.
        """
        advice_list = self.advise(tool_name, {}, task_context, include_mind=include_mind)

        if not advice_list:
            return ""

        lines = ["## Spark Advisor Notes"]

        # Add cautions first
        cautions = [a for a in advice_list if "[Caution]" in a.text or "[Past Failure]" in a.text]
        if cautions:
            lines.append("### Cautions")
            for a in cautions[:2]:
                lines.append(f"- {a.text}")

        # Add recommendations
        recs = [a for a in advice_list if a not in cautions]
        if recs:
            lines.append("### Relevant Learnings")
            for a in recs[:3]:
                conf_str = f"({a.confidence:.0%} confident)" if a.confidence >= 0.7 else ""
                lines.append(f"- {a.text} {conf_str}")

        return "\n".join(lines)


# ============= Singleton =============
_advisor: Optional[SparkAdvisor] = None

def get_advisor() -> SparkAdvisor:
    """Get the global advisor instance."""
    global _advisor
    if _advisor is None:
        _advisor = SparkAdvisor()
    return _advisor


# ============= Convenience Functions =============
def advise_on_tool(tool_name: str, tool_input: Dict = None, context: str = "") -> List[Advice]:
    """Get advice before using a tool."""
    return get_advisor().advise(tool_name, tool_input or {}, context)


def get_quick_advice(tool_name: str) -> Optional[str]:
    """Get single most relevant advice for a tool."""
    return get_advisor().get_quick_advice(tool_name)


def should_be_careful(tool_name: str) -> Tuple[bool, str]:
    """Check if we should be careful with this tool."""
    return get_advisor().should_be_careful(tool_name)


def report_outcome(tool_name: str, success: bool, advice_helped: bool = False):
    """Report action outcome to close the feedback loop."""
    get_advisor().report_action_outcome(tool_name, success, advice_helped)


def record_advice_feedback(
    helpful: Optional[bool],
    notes: str = "",
    tool: Optional[str] = None,
    advice_id: Optional[str] = None,
    followed: bool = True,
):
    """Record explicit feedback on advice helpfulness."""
    return get_advisor().record_advice_feedback(
        helpful=helpful,
        notes=notes,
        tool=tool,
        advice_id=advice_id,
        followed=followed,
    )


def generate_context(tool_name: str, task: str = "") -> str:
    """Generate injectable context block."""
    return get_advisor().generate_context_block(tool_name, task)
