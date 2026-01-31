"""
Spark Promoter: Auto-promote high-value insights to project files

When a cognitive insight proves reliable enough (high validation count,
high reliability score), it should be promoted to permanent project 
documentation where it will always be loaded.

Promotion targets:
- CLAUDE.md - Project conventions, gotchas, facts
- AGENTS.md - Workflow patterns, tool usage, delegation rules
- TOOLS.md - Tool-specific insights, integration gotchas
- SOUL.md - Behavioral patterns, communication style (Clawdbot)

Promotion criteria:
- Reliability >= 70%
- Times validated >= 3
- Not already promoted
- Category matches target file
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass

from .cognitive_learner import CognitiveInsight, CognitiveCategory, get_cognitive_learner
from .project_profile import load_profile


# ============= Configuration =============
DEFAULT_PROMOTION_THRESHOLD = 0.7  # 70% reliability
DEFAULT_MIN_VALIDATIONS = 3
PROJECT_SECTION = "## Project Intelligence"
PROJECT_START = "<!-- SPARK_PROJECT_START -->"
PROJECT_END = "<!-- SPARK_PROJECT_END -->"


# ============= Operational vs Cognitive Filter (Phase 1) =============
# These patterns indicate operational telemetry, NOT human-useful cognition.
# Operational insights are valuable for system debugging but should NOT be
# promoted to user-facing docs like CLAUDE.md.

OPERATIONAL_PATTERNS = [
    # Tool sequence patterns (the main noise source)
    r"^sequence\s+['\"]",
    r"sequence.*worked well",
    r"pattern\s+['\"].*->.*['\"]",
    r"for \w+:.*->.*works",

    # Usage count patterns
    r"heavy\s+\w+\s+usage",
    r"\(\d+\s*calls?\)",
    r"indicates task type",

    # Raw tool telemetry
    r"^tool\s+\w+\s+(succeeded|failed)",
    r"tool effectiveness",
]

# Compile patterns for efficiency
_OPERATIONAL_REGEXES = [re.compile(p, re.IGNORECASE) for p in OPERATIONAL_PATTERNS]

# Safety block patterns (humanity-first guardrail)
SAFETY_BLOCK_PATTERNS = [
    r"\bdecept(?:ive|ion)\b",
    r"\bmanipulat(?:e|ion)\b",
    r"\bcoerc(?:e|ion)\b",
    r"\bexploit\b",
    r"\bharass(?:ment)?\b",
    r"\bweaponize\b",
    r"\bmislead\b",
]

_SAFETY_REGEXES = [re.compile(p, re.IGNORECASE) for p in SAFETY_BLOCK_PATTERNS]


def is_operational_insight(insight_text: str) -> bool:
    """
    Determine if an insight is operational (telemetry) vs cognitive (human-useful).

    Operational insights:
    - Tool sequences: "Sequence 'Bash -> Edit' worked well"
    - Usage counts: "Heavy Bash usage (42 calls)"
    - Raw telemetry: "Tool X succeeded"

    Cognitive insights:
    - Self-awareness: "I struggle with windows paths"
    - Reasoning: "Read before Edit prevents content mismatches"
    - User preferences: "User prefers concise output"
    - Wisdom: "Ship fast, iterate faster"

    Returns True if operational (should NOT be promoted).
    """
    text = (insight_text or "").strip().lower()
    if not text:
        return True  # Empty insights are operational (skip them)

    # Check against operational patterns
    for regex in _OPERATIONAL_REGEXES:
        if regex.search(text):
            return True

    # Additional heuristics

    # Tool chain detection: multiple arrows indicate sequence
    arrow_count = text.count("->") + text.count("→")
    if arrow_count >= 2:
        return True

    # Tool name heavy: mostly tool names suggests telemetry
    tool_names = ["bash", "read", "edit", "write", "grep", "glob", "todowrite", "taskoutput"]
    tool_mentions = sum(1 for t in tool_names if t in text)
    words = len(text.split())
    if words > 0 and tool_mentions / words > 0.4:
        return True

    return False


def is_unsafe_insight(insight_text: str) -> bool:
    """Return True if insight is unsafe or harmful to promote."""
    text = (insight_text or "").strip().lower()
    if not text:
        return True
    for regex in _SAFETY_REGEXES:
        if regex.search(text):
            return True
    return False


def filter_unsafe_insights(insights: list) -> tuple:
    """Split insights into safe and unsafe lists."""
    safe = []
    unsafe = []

    for item in insights:
        if isinstance(item, tuple):
            insight = item[0]
            text = insight.insight if hasattr(insight, "insight") else str(insight)
        else:
            text = item.insight if hasattr(item, "insight") else str(item)

        if is_unsafe_insight(text):
            unsafe.append(item)
        else:
            safe.append(item)

    return safe, unsafe


def filter_operational_insights(insights: list) -> tuple:
    """
    Split insights into cognitive (promotable) and operational (not promotable).

    Returns (cognitive_list, operational_list)
    """
    cognitive = []
    operational = []

    for item in insights:
        # Handle both tuples (insight, key, target) and raw insights
        if isinstance(item, tuple):
            insight = item[0]
            text = insight.insight if hasattr(insight, 'insight') else str(insight)
        else:
            text = item.insight if hasattr(item, 'insight') else str(item)

        if is_operational_insight(text):
            operational.append(item)
        else:
            cognitive.append(item)

    return cognitive, operational


@dataclass
class PromotionTarget:
    """Definition of a promotion target file."""
    filename: str
    section: str
    categories: List[CognitiveCategory]
    description: str


# Promotion target definitions
PROMOTION_TARGETS = [
    PromotionTarget(
        filename="CLAUDE.md",
        section="## Spark Learnings",
        categories=[
            CognitiveCategory.WISDOM,
            CognitiveCategory.REASONING,
            CognitiveCategory.CONTEXT,
        ],
        description="Project conventions, gotchas, and verified patterns"
    ),
    PromotionTarget(
        filename="AGENTS.md",
        section="## Spark Learnings",
        categories=[
            CognitiveCategory.META_LEARNING,
            CognitiveCategory.SELF_AWARENESS,
        ],
        description="Workflow patterns and self-awareness insights"
    ),
    PromotionTarget(
        filename="TOOLS.md",
        section="## Spark Learnings", 
        categories=[
            CognitiveCategory.CONTEXT,
        ],
        description="Tool-specific insights and integration gotchas"
    ),
    PromotionTarget(
        filename="SOUL.md",
        section="## Spark Learnings",
        categories=[
            CognitiveCategory.USER_UNDERSTANDING,
            CognitiveCategory.COMMUNICATION,
        ],
        description="User preferences and communication style"
    ),
]


class Promoter:
    """
    Promotes high-value cognitive insights to project documentation.
    
    The promotion process:
    1. Find insights meeting promotion criteria
    2. Match insights to appropriate target files
    3. Format insights as concise rules
    4. Append to target files
    5. Mark insights as promoted
    """
    
    def __init__(self, project_dir: Optional[Path] = None,
                 reliability_threshold: float = DEFAULT_PROMOTION_THRESHOLD,
                 min_validations: int = DEFAULT_MIN_VALIDATIONS):
        self.project_dir = project_dir or Path.cwd()
        self.reliability_threshold = reliability_threshold
        self.min_validations = min_validations
    
    def _get_target_for_category(self, category: CognitiveCategory) -> Optional[PromotionTarget]:
        """Find the appropriate promotion target for a category."""
        for target in PROMOTION_TARGETS:
            if category in target.categories:
                return target
        return None
    
    def _format_insight_for_promotion(self, insight: CognitiveInsight) -> str:
        """Format an insight as a concise rule for documentation."""
        # Extract the core insight without verbose details
        rule = insight.insight
        
        # Add reliability indicator
        reliability_str = f"({insight.reliability:.0%} reliable, {insight.times_validated} validations)"
        
        # Add context if not generic
        if insight.context and insight.context not in ["General principle", "All interactions"]:
            context_note = f" *When: {insight.context[:50]}*"
        else:
            context_note = ""
        
        return f"- {rule}{context_note} {reliability_str}"
    
    def _ensure_section_exists(self, file_path: Path, section: str) -> str:
        """Ensure the target section exists in the file. Returns file content."""
        if not file_path.exists():
            # Create file with basic structure
            content = f"""# {file_path.stem}

{section}

*Auto-promoted insights from Spark*

"""
            file_path.write_text(content)
            return content
        
        content = file_path.read_text()
        
        if section not in content:
            # Add section at the end
            content += f"\n\n{section}\n\n*Auto-promoted insights from Spark*\n\n"
            file_path.write_text(content)
        
        return content
    
    def _append_to_section(self, file_path: Path, section: str, line: str):
        """Append a line to a specific section in a file."""
        content = self._ensure_section_exists(file_path, section)
        
        # Find the section and append after it
        section_idx = content.find(section)
        if section_idx == -1:
            return
        
        # Find the next section or end of file
        next_section = re.search(r'\n## ', content[section_idx + len(section):])
        if next_section:
            insert_idx = section_idx + len(section) + next_section.start()
        else:
            insert_idx = len(content)
        
        # Insert the new line before the next section
        new_content = content[:insert_idx].rstrip() + "\n" + line + "\n" + content[insert_idx:]
        file_path.write_text(new_content)

    def _upsert_block(self, content: str, block: str, section: str) -> str:
        """Insert or replace a block wrapped by start/end markers in a section."""
        if PROJECT_START in content and PROJECT_END in content:
            start_idx = content.index(PROJECT_START)
            end_idx = content.index(PROJECT_END) + len(PROJECT_END)
            return content[:start_idx].rstrip() + "\n" + block + "\n" + content[end_idx:].lstrip()

        if section in content:
            insert_idx = content.index(section) + len(section)
            insertion = "\n\n" + block + "\n"
            return content[:insert_idx] + insertion + content[insert_idx:]

        return content.rstrip() + f"\n\n{section}\n\n{block}\n"

    def _render_project_block(self, profile: Dict[str, Any]) -> str:
        """Render a concise project intelligence block for PROJECT.md."""
        def _render_items(label: str, items: List[Dict[str, Any]], max_items: int = 5) -> List[str]:
            if not items:
                return []
            lines = [f"{label}:"]
            for entry in list(reversed(items))[:max_items]:
                text = (entry.get("text") or "").strip()
                meta = entry.get("meta") or {}
                suffix = []
                status = meta.get("status")
                if status:
                    suffix.append(f"status={status}")
                why = meta.get("why")
                if why:
                    suffix.append(f"why={why}")
                impact = meta.get("impact")
                if impact:
                    suffix.append(f"impact={impact}")
                evidence = meta.get("evidence")
                if evidence:
                    suffix.append(f"evidence={evidence}")
                trailer = f" ({'; '.join(suffix)})" if suffix else ""
                if text:
                    lines.append(f"- {text}{trailer}")
            return lines

        updated = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        lines = [
            PROJECT_START,
            f"Updated: {updated}",
            f"Domain: {profile.get('domain') or 'general'}",
            f"Phase: {profile.get('phase') or 'discovery'}",
        ]

        done = (profile.get("done") or "").strip()
        if done:
            lines.append(f"Done Definition: {done}")

        lines.extend(_render_items("Goals", profile.get("goals") or []))
        lines.extend(_render_items("Milestones", profile.get("milestones") or []))
        lines.extend(_render_items("Decisions", profile.get("decisions") or []))
        lines.extend(_render_items("Insights", profile.get("insights") or []))
        lines.extend(_render_items("Feedback", profile.get("feedback") or []))
        lines.extend(_render_items("Risks", profile.get("risks") or []))
        lines.extend(_render_items("References", profile.get("references") or []))
        transfers = profile.get("transfers") or []
        lines.extend(_render_items("Transfers", transfers))

        if len(transfers) >= 3:
            def _theme_snip(text: str) -> str:
                words = (text or "").strip().split()
                return " ".join(words[:8]) if words else ""

            recent = list(reversed(transfers))[:3]
            lines.append("Transfer Summary:")
            for entry in recent:
                snippet = _theme_snip(entry.get("text") or "")
                if snippet:
                    lines.append(f"- Theme: {snippet}")

        lines.append(PROJECT_END)
        return "\n".join(lines)

    def promote_project_profile(self, profile: Optional[Dict[str, Any]] = None) -> bool:
        """Promote project profile data into PROJECT.md."""
        try:
            profile_data = profile or load_profile(self.project_dir)
            block = self._render_project_block(profile_data)
            file_path = self.project_dir / "PROJECT.md"

            if file_path.exists():
                content = file_path.read_text()
                new_content = self._upsert_block(content, block, PROJECT_SECTION)
            else:
                new_content = f"# Project\n\n{PROJECT_SECTION}\n\n{block}\n"

            file_path.write_text(new_content)
            print("[SPARK] Updated PROJECT.md from project profile")
            return True
        except Exception as e:
            print(f"[SPARK] PROJECT.md update failed: {e}")
            return False

    def get_promotable_insights(self, include_operational: bool = False) -> List[Tuple[CognitiveInsight, str, PromotionTarget]]:
        """Get insights ready for promotion with their target files.

        Args:
            include_operational: If False (default), filters out operational
                                 telemetry (tool sequences, usage counts).
                                 Set True only for debugging.
        """
        cognitive = get_cognitive_learner()
        candidates = []

        for key, insight in cognitive.insights.items():
            # Skip already promoted
            if insight.promoted:
                continue

            # Check criteria
            if insight.reliability < self.reliability_threshold:
                continue
            if insight.times_validated < self.min_validations:
                continue

            # Find target
            target = self._get_target_for_category(insight.category)
            if target:
                candidates.append((insight, key, target))

        # Phase 1: Filter out operational telemetry
        if not include_operational:
            cognitive_only, operational = filter_operational_insights(candidates)
            if operational:
                print(f"[SPARK] Filtered {len(operational)} operational insights (telemetry)")
            safe_only, unsafe = filter_unsafe_insights(cognitive_only)
            if unsafe:
                print(f"[SPARK] Filtered {len(unsafe)} unsafe insights (safety guardrail)")
            return safe_only

        return candidates
    
    def promote_insight(self, insight: CognitiveInsight, insight_key: str, 
                       target: PromotionTarget) -> bool:
        """Promote a single insight to its target file."""
        file_path = self.project_dir / target.filename
        
        try:
            # Format the insight
            formatted = self._format_insight_for_promotion(insight)
            
            # Append to target file
            self._append_to_section(file_path, target.section, formatted)
            
            # Mark as promoted
            cognitive = get_cognitive_learner()
            cognitive.mark_promoted(insight_key, target.filename)
            
            print(f"[SPARK] Promoted to {target.filename}: {insight.insight[:50]}...")
            return True
            
        except Exception as e:
            print(f"[SPARK] Promotion failed: {e}")
            return False
    
    def promote_all(self, dry_run: bool = False, include_project: bool = True) -> Dict[str, int]:
        """Promote all eligible insights (filters operational telemetry)."""
        # Get candidates before filtering for stats
        cognitive = get_cognitive_learner()
        all_candidates = []
        for key, insight in cognitive.insights.items():
            if insight.promoted:
                continue
            if insight.reliability < self.reliability_threshold:
                continue
            if insight.times_validated < self.min_validations:
                continue
            target = self._get_target_for_category(insight.category)
            if target:
                all_candidates.append((insight, key, target))

        # Apply operational filter
        promotable, filtered_operational = filter_operational_insights(all_candidates)
        # Apply safety filter
        promotable, filtered_unsafe = filter_unsafe_insights(promotable)

        stats = {
            "promoted": 0,
            "skipped": 0,
            "failed": 0,
            "filtered_operational": len(filtered_operational),  # NEW: Track filtered
            "filtered_unsafe": len(filtered_unsafe),
            "project_written": 0,
            "project_failed": 0,
        }

        if filtered_operational:
            print(f"[SPARK] Filtered {len(filtered_operational)} operational insights (tool sequences, telemetry)")
        if filtered_unsafe:
            print(f"[SPARK] Filtered {len(filtered_unsafe)} unsafe insights (safety guardrail)")

        if include_project:
            if dry_run:
                print("  [DRY RUN] Would update PROJECT.md from project profile")
                stats["skipped"] += 1
            else:
                if self.promote_project_profile():
                    stats["project_written"] = 1
                else:
                    stats["project_failed"] = 1

        if not promotable:
            print("[SPARK] No insights ready for promotion")
            return stats
        
        print(f"[SPARK] Found {len(promotable)} insights ready for promotion")
        
        for insight, key, target in promotable:
            if dry_run:
                print(f"  [DRY RUN] Would promote to {target.filename}: {insight.insight[:50]}...")
                stats["skipped"] += 1
                continue
            
            if self.promote_insight(insight, key, target):
                stats["promoted"] += 1
            else:
                stats["failed"] += 1
        
        return stats
    
    def get_promotion_status(self) -> Dict:
        """Get status of promotions (includes operational filter stats)."""
        cognitive = get_cognitive_learner()

        # Get all candidates before filtering
        all_candidates = []
        for key, insight in cognitive.insights.items():
            if insight.promoted:
                continue
            if insight.reliability < self.reliability_threshold:
                continue
            if insight.times_validated < self.min_validations:
                continue
            target = self._get_target_for_category(insight.category)
            if target:
                all_candidates.append((insight, key, target))

        # Apply filter
        cognitive_only, operational = filter_operational_insights(all_candidates)
        cognitive_only, unsafe = filter_unsafe_insights(cognitive_only)

        promoted = [i for i in cognitive.insights.values() if i.promoted]
        by_target = {}
        for insight in promoted:
            target = insight.promoted_to or "unknown"
            by_target[target] = by_target.get(target, 0) + 1

        return {
            "total_insights": len(cognitive.insights),
            "promoted_count": len(promoted),
            "ready_for_promotion": len(cognitive_only),
            "filtered_operational": len(operational),  # NEW: Operational telemetry blocked
            "filtered_unsafe": len(unsafe),
            "by_target": by_target,
            "threshold": self.reliability_threshold,
            "min_validations": self.min_validations
        }


# ============= Singleton =============
_promoter: Optional[Promoter] = None

def get_promoter(project_dir: Optional[Path] = None) -> Promoter:
    """Get the promoter instance."""
    global _promoter
    if _promoter is None or (project_dir and _promoter.project_dir != project_dir):
        _promoter = Promoter(project_dir)
    return _promoter


# ============= Convenience Functions =============
def check_and_promote(
    project_dir: Optional[Path] = None,
    dry_run: bool = False,
    include_project: bool = True,
) -> Dict[str, int]:
    """Check for promotable insights and promote them."""
    return get_promoter(project_dir).promote_all(dry_run, include_project=include_project)


def get_promotion_status(project_dir: Optional[Path] = None) -> Dict:
    """Get promotion status."""
    return get_promoter(project_dir).get_promotion_status()
