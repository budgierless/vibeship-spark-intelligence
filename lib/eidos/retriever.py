"""
StructuralRetriever: Retrieve by EIDOS structure, not text similarity.

The key insight from the critique:
> "If retrieval is 'find similar logs,' you'll pull more tool junk.
> Instead retrieve in layers."

This module retrieves distillations by structural relevance:
1. Policies (what must we respect?) - Always first
2. Playbooks (if task matches) - Step-by-step procedures
3. Sharp edges (stack gotchas) - Warnings for the domain
4. Heuristics (if X then Y) - Learned patterns
5. Anti-patterns (avoid X) - What not to do
6. Similar failures - Learn from mistakes

Retrieval is by:
- Goal similarity (what are we trying to do?)
- Environment tags (repo/stack/domain)
- Failure mode similarity (error patterns)

NOT by:
- Raw text embedding similarity
- Tool log matching
"""

import re
from typing import Any, Dict, List, Optional, Set

from .models import Step, Distillation, DistillationType, Evaluation
from .store import EidosStore, get_store


class StructuralRetriever:
    """
    Retrieve distillations by EIDOS structure for maximum relevance.

    This replaces "find similar text" with "find structurally relevant knowledge":
    - Policies always apply
    - Playbooks when task matches triggers
    - Sharp edges for the tools/domain being used
    - Heuristics for the intent type
    - Anti-patterns to avoid known failures

    Usage:
        retriever = StructuralRetriever()
        distillations = retriever.retrieve_for_step(step)
        # Returns prioritized list of relevant distillations
    """

    # Priority order for distillation types
    TYPE_PRIORITY = {
        DistillationType.POLICY: 1,      # Always first - constraints
        DistillationType.PLAYBOOK: 2,    # Procedures for known tasks
        DistillationType.SHARP_EDGE: 3,  # Warnings / gotchas
        DistillationType.HEURISTIC: 4,   # Learned patterns
        DistillationType.ANTI_PATTERN: 5, # What to avoid
    }

    def __init__(self, store: Optional[EidosStore] = None, max_results: int = 10):
        """
        Initialize the retriever.

        Args:
            store: EIDOS store instance (uses singleton if not provided)
            max_results: Maximum distillations to return
        """
        self.store = store or get_store()
        self.max_results = max_results

        # Statistics
        self._stats = {
            "retrievals": 0,
            "by_type": {t.value: 0 for t in DistillationType},
            "empty_results": 0,
        }

    def retrieve_for_step(self, step: Step) -> List[Distillation]:
        """
        Retrieve relevant distillations for a step.

        This is the main entry point. It retrieves by structure:
        1. Policies first (always apply)
        2. Playbooks if task matches
        3. Sharp edges for tools/domain
        4. Heuristics matching intent
        5. Anti-patterns for similar failures

        Args:
            step: The EIDOS Step to retrieve for

        Returns:
            Prioritized list of relevant Distillations
        """
        self._stats["retrievals"] += 1
        results: List[Distillation] = []
        seen_ids: Set[str] = set()

        # 1. Policies first (constraints that always apply)
        policies = self._get_policies()
        for p in policies:
            if p.distillation_id not in seen_ids:
                results.append(p)
                seen_ids.add(p.distillation_id)
                self._stats["by_type"]["policy"] += 1

        # 2. Playbooks if task matches
        playbooks = self._get_playbooks(step.intent)
        for p in playbooks:
            if p.distillation_id not in seen_ids:
                results.append(p)
                seen_ids.add(p.distillation_id)
                self._stats["by_type"]["playbook"] += 1

        # 3. Sharp edges for tools being used
        tool = step.action_details.get("tool_used", "")
        if tool:
            edges = self._get_sharp_edges(tool)
            for e in edges:
                if e.distillation_id not in seen_ids:
                    results.append(e)
                    seen_ids.add(e.distillation_id)
                    self._stats["by_type"]["sharp_edge"] += 1

        # 4. Heuristics matching intent
        heuristics = self._get_heuristics(step.intent)
        for h in heuristics:
            if h.distillation_id not in seen_ids:
                results.append(h)
                seen_ids.add(h.distillation_id)
                self._stats["by_type"]["heuristic"] += 1

        # 5. Anti-patterns for similar contexts
        anti_patterns = self._get_anti_patterns(step.intent, step.hypothesis)
        for a in anti_patterns:
            if a.distillation_id not in seen_ids:
                results.append(a)
                seen_ids.add(a.distillation_id)
                self._stats["by_type"]["anti_pattern"] += 1

        # 6. If still have room, get similar failures
        if len(results) < self.max_results and step.hypothesis:
            failures = self._get_similar_failures(step.hypothesis)
            for f in failures:
                if f.distillation_id not in seen_ids:
                    results.append(f)
                    seen_ids.add(f.distillation_id)

        # Sort by type priority and confidence
        results = self._sort_by_relevance(results)

        # Record retrievals
        for d in results[:self.max_results]:
            self.store.record_distillation_retrieval(d.distillation_id)

        if not results:
            self._stats["empty_results"] += 1

        return results[:self.max_results]

    def retrieve_for_intent(self, intent: str) -> List[Distillation]:
        """
        Retrieve distillations matching an intent string.

        Simpler interface for when you don't have a full Step.

        Args:
            intent: The intent to match against

        Returns:
            Relevant Distillations
        """
        self._stats["retrievals"] += 1
        results: List[Distillation] = []
        seen_ids: Set[str] = set()

        # Policies — only include if relevant to intent (keyword overlap)
        for p in self._get_policies():
            if p.distillation_id not in seen_ids:
                if self._has_keyword_overlap(intent, p.statement, min_overlap=1):
                    results.append(p)
                    seen_ids.add(p.distillation_id)

        # Heuristics for this intent
        for h in self._get_heuristics(intent):
            if h.distillation_id not in seen_ids:
                results.append(h)
                seen_ids.add(h.distillation_id)

        # Anti-patterns
        for a in self._get_anti_patterns(intent, ""):
            if a.distillation_id not in seen_ids:
                results.append(a)
                seen_ids.add(a.distillation_id)

        results = self._sort_by_relevance(results)

        for d in results[:self.max_results]:
            self.store.record_distillation_retrieval(d.distillation_id)

        return results[:self.max_results]

    def retrieve_for_error(self, error_message: str) -> List[Distillation]:
        """
        Retrieve distillations relevant to an error.

        Useful for debugging - find sharp edges and anti-patterns
        that might explain the error.

        Args:
            error_message: The error message or pattern

        Returns:
            Relevant Distillations (sharp edges, anti-patterns)
        """
        self._stats["retrievals"] += 1
        results: List[Distillation] = []
        seen_ids: Set[str] = set()

        # Sharp edges first
        all_edges = self.store.get_distillations_by_type(DistillationType.SHARP_EDGE, limit=50)
        for edge in all_edges:
            if self._matches_error(error_message, edge):
                if edge.distillation_id not in seen_ids:
                    results.append(edge)
                    seen_ids.add(edge.distillation_id)

        # Anti-patterns
        all_anti = self.store.get_distillations_by_type(DistillationType.ANTI_PATTERN, limit=50)
        for anti in all_anti:
            if self._matches_error(error_message, anti):
                if anti.distillation_id not in seen_ids:
                    results.append(anti)
                    seen_ids.add(anti.distillation_id)

        results = self._sort_by_relevance(results)

        for d in results[:self.max_results]:
            self.store.record_distillation_retrieval(d.distillation_id)

        return results[:self.max_results]

    # ==================== Retrieval by Type ====================

    def _get_policies(self) -> List[Distillation]:
        """Get all active policies."""
        return self.store.get_distillations_by_type(
            DistillationType.POLICY,
            limit=10
        )

    def _get_playbooks(self, intent: str) -> List[Distillation]:
        """Get playbooks that match the intent."""
        all_playbooks = self.store.get_distillations_by_type(
            DistillationType.PLAYBOOK,
            limit=20
        )
        return [p for p in all_playbooks if self._matches_trigger(intent, p.triggers)]

    def _get_sharp_edges(self, tool: str) -> List[Distillation]:
        """Get sharp edges for a tool or domain."""
        # By tool name
        edges = self.store.get_distillations_by_domain(tool.lower(), limit=10)

        # Also get general sharp edges
        all_edges = self.store.get_distillations_by_type(
            DistillationType.SHARP_EDGE,
            limit=20
        )

        # Filter to those matching the tool
        tool_lower = tool.lower()
        for edge in all_edges:
            if tool_lower in str(edge.domains).lower():
                if edge not in edges:
                    edges.append(edge)
            if tool_lower in edge.statement.lower():
                if edge not in edges:
                    edges.append(edge)

        return edges[:10]

    def _get_heuristics(self, intent: str) -> List[Distillation]:
        """Get heuristics matching the intent."""
        # Extract intent category
        intent_key = self._normalize_intent(intent)

        # Search by trigger
        heuristics = self.store.get_distillations_by_trigger(intent_key, limit=10)

        # Also search by domain
        domain_heuristics = self.store.get_distillations_by_domain(intent_key, limit=10)
        for h in domain_heuristics:
            if h not in heuristics:
                heuristics.append(h)

        # Filter to heuristic type
        return [h for h in heuristics if h.type == DistillationType.HEURISTIC][:10]

    def _get_anti_patterns(self, intent: str, hypothesis: str) -> List[Distillation]:
        """Get anti-patterns for the context."""
        intent_key = self._normalize_intent(intent)

        # Get anti-patterns matching intent
        all_anti = self.store.get_distillations_by_type(
            DistillationType.ANTI_PATTERN,
            limit=30
        )

        relevant = []
        for anti in all_anti:
            # Check triggers
            if self._matches_trigger(intent_key, anti.anti_triggers):
                relevant.append(anti)
                continue

            # Check statement for keyword match
            if self._has_keyword_overlap(intent + " " + hypothesis, anti.statement):
                relevant.append(anti)

        return relevant[:10]

    def _get_similar_failures(self, hypothesis: str) -> List[Distillation]:
        """Get distillations from similar failed attempts."""
        # Get anti-patterns and sharp edges
        anti_patterns = self.store.get_distillations_by_type(
            DistillationType.ANTI_PATTERN,
            limit=20
        )
        sharp_edges = self.store.get_distillations_by_type(
            DistillationType.SHARP_EDGE,
            limit=20
        )

        # Filter by keyword overlap with hypothesis
        relevant = []
        hypothesis_words = set(re.findall(r'\b[a-z]+\b', hypothesis.lower()))

        for d in anti_patterns + sharp_edges:
            statement_words = set(re.findall(r'\b[a-z]+\b', d.statement.lower()))
            overlap = len(hypothesis_words & statement_words)
            if overlap >= 2:
                relevant.append((overlap, d))

        # Sort by overlap and return
        relevant.sort(key=lambda x: x[0], reverse=True)
        return [d for _, d in relevant[:5]]

    # ==================== Matching Helpers ====================

    def _matches_trigger(self, text: str, triggers: List[str]) -> bool:
        """Check if text matches any trigger."""
        text_lower = text.lower()
        return any(t.lower() in text_lower for t in triggers)

    def _matches_error(self, error: str, distillation: Distillation) -> bool:
        """Check if distillation is relevant to an error."""
        error_lower = error.lower()
        statement_lower = distillation.statement.lower()

        # Check triggers
        for trigger in distillation.triggers:
            if trigger.lower() in error_lower:
                return True

        # Check keyword overlap
        error_words = set(re.findall(r'\b[a-z]+\b', error_lower))
        statement_words = set(re.findall(r'\b[a-z]+\b', statement_lower))

        overlap = len(error_words & statement_words)
        return overlap >= 3

    def _has_keyword_overlap(self, text1: str, text2: str, min_overlap: int = 2) -> bool:
        """Check if two texts have significant keyword overlap."""
        stop_words = {
            "the", "a", "an", "and", "or", "but", "if", "then", "so", "to",
            "of", "in", "on", "for", "with", "by", "is", "are", "was", "were",
            "be", "been", "being", "user", "request", "when"
        }

        words1 = set(re.findall(r'\b[a-z]+\b', text1.lower())) - stop_words
        words2 = set(re.findall(r'\b[a-z]+\b', text2.lower())) - stop_words

        return len(words1 & words2) >= min_overlap

    def _normalize_intent(self, intent: str) -> str:
        """Normalize intent for matching."""
        intent_lower = intent.lower()

        # Remove common prefixes
        for prefix in ["fulfill user request:", "user wants:", "request:"]:
            if intent_lower.startswith(prefix):
                intent_lower = intent_lower[len(prefix):].strip()

        # Map to categories
        category_keywords = {
            "git": "git_operations",
            "push": "git_operations",
            "commit": "git_operations",
            "fix": "bug_fixing",
            "bug": "bug_fixing",
            "add": "feature_addition",
            "create": "feature_addition",
            "remove": "deletion",
            "delete": "deletion",
            "clean": "cleanup",
            "test": "testing",
            "deploy": "deployment",
        }

        for keyword, category in category_keywords.items():
            if keyword in intent_lower:
                return category

        # Fallback: extract first meaningful word
        words = re.findall(r'\b[a-z]+\b', intent_lower)
        if words:
            return words[0]

        return "general"

    def _sort_by_relevance(self, distillations: List[Distillation]) -> List[Distillation]:
        """Sort distillations by type priority and confidence."""
        def sort_key(d: Distillation) -> tuple:
            type_priority = self.TYPE_PRIORITY.get(d.type, 99)
            # Negative confidence for descending sort
            return (type_priority, -d.confidence, -d.times_helped)

        return sorted(distillations, key=sort_key)

    # ==================== Usage Feedback ====================

    def record_usage(self, distillation_id: str, helped: bool):
        """
        Record that a retrieved distillation was used.

        This feedback loop improves future retrieval by updating
        validation/contradiction counts.

        Args:
            distillation_id: The distillation that was used
            helped: Whether it helped (True) or not (False)
        """
        self.store.record_distillation_usage(distillation_id, helped)

    def get_stats(self) -> Dict[str, Any]:
        """Get retriever statistics."""
        return {
            **self._stats,
            "max_results": self.max_results,
        }


# Singleton instance
_retriever: Optional[StructuralRetriever] = None


def get_retriever() -> StructuralRetriever:
    """Get the global structural retriever instance."""
    global _retriever
    if _retriever is None:
        _retriever = StructuralRetriever()
    return _retriever
