"""
RepetitionDetector: Detects repeated requests.

MEDIUM VALUE - Strong preference signal when user asks same thing 3+ times.

Indicates:
1. AI didn't understand the first time
2. User has a strong preference that wasn't met
3. Potential blind spot in AI's understanding

Uses fuzzy matching to detect semantically similar requests.
"""

import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from .base import DetectedPattern, PatternDetector, PatternType


def _normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    # Lowercase
    text = text.lower()
    # Remove punctuation
    text = re.sub(r'[^\w\s]', '', text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _extract_keywords(text: str) -> set:
    """Extract significant keywords from text."""
    # Common stop words to ignore
    stop_words = {
        'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
        'ought', 'used', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by',
        'from', 'as', 'into', 'through', 'during', 'before', 'after',
        'above', 'below', 'between', 'under', 'again', 'further', 'then',
        'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all',
        'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
        'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just',
        'and', 'but', 'if', 'or', 'because', 'until', 'while', 'although',
        'though', 'since', 'unless', 'i', 'you', 'he', 'she', 'it', 'we',
        'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'its',
        'our', 'their', 'this', 'that', 'these', 'those', 'please', 'thanks',
        'thank', 'yes', 'no', 'ok', 'okay', 'sure', 'yeah', 'yep', 'nope',
    }

    words = _normalize_text(text).split()
    # Keep words that are not stop words and are at least 3 chars
    keywords = {w for w in words if w not in stop_words and len(w) >= 3}
    return keywords


def _jaccard_similarity(set1: set, set2: set) -> float:
    """Calculate Jaccard similarity between two sets."""
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


def _find_similar_requests(requests: List[Tuple[str, set]], min_similarity: float = 0.5) -> List[List[int]]:
    """
    Find groups of similar requests.

    Returns list of groups, where each group is indices of similar requests.
    """
    n = len(requests)
    if n < 2:
        return []

    # Track which requests are already in a group
    grouped = set()
    groups = []

    for i in range(n):
        if i in grouped:
            continue

        # Start new group
        group = [i]
        keywords_i = requests[i][1]

        for j in range(i + 1, n):
            if j in grouped:
                continue

            keywords_j = requests[j][1]
            similarity = _jaccard_similarity(keywords_i, keywords_j)

            if similarity >= min_similarity:
                group.append(j)
                grouped.add(j)

        if len(group) >= 2:
            groups.append(group)
            grouped.add(i)

    return groups


class RepetitionDetector(PatternDetector):
    """
    Detects when user repeatedly asks for the same thing.

    3+ similar requests = strong preference signal
    """

    def __init__(self):
        super().__init__("RepetitionDetector")
        # session_id -> list of (text, keywords) tuples
        self._requests: Dict[str, List[Tuple[str, set]]] = {}
        self._alerted: Dict[str, set] = {}  # Track which groups already triggered alerts

    def process_event(self, event: Dict) -> List[DetectedPattern]:
        """Process event and detect repetition patterns."""
        patterns: List[DetectedPattern] = []
        session_id = event.get("session_id", "unknown")
        hook_event = event.get("hook_event", "")

        # Only analyze user messages
        if hook_event != "UserPromptSubmit":
            return patterns

        payload = event.get("payload", {})
        text = payload.get("text", "") if isinstance(payload, dict) else ""

        if not text:
            text = event.get("prompt", "") or event.get("user_prompt", "")

        if not text or len(text) < 10:  # Ignore very short messages
            return patterns

        # Initialize session tracking
        if session_id not in self._requests:
            self._requests[session_id] = []
            self._alerted[session_id] = set()

        # Extract keywords and store request
        keywords = _extract_keywords(text)
        self._requests[session_id].append((text, keywords))

        # Keep only last 20 requests per session
        if len(self._requests[session_id]) > 20:
            self._requests[session_id] = self._requests[session_id][-20:]

        # Find similar request groups
        groups = _find_similar_requests(self._requests[session_id], min_similarity=0.5)

        for group in groups:
            if len(group) < 3:
                continue  # Need 3+ repetitions

            # Create group signature to avoid repeat alerts
            group_sig = frozenset(group)
            if group_sig in self._alerted[session_id]:
                continue

            self._alerted[session_id].add(group_sig)

            # Get the requests in this group
            requests_in_group = [self._requests[session_id][i][0] for i in group]

            # Find common keywords
            all_keywords = [self._requests[session_id][i][1] for i in group]
            common = all_keywords[0].copy()
            for kw in all_keywords[1:]:
                common &= kw

            # Calculate confidence based on group size
            confidence = min(0.95, 0.7 + (len(group) - 3) * 0.1)

            patterns.append(DetectedPattern(
                pattern_type=PatternType.REPETITION,
                confidence=confidence,
                evidence=[
                    f"Request appeared {len(group)} times",
                    f"Common keywords: {', '.join(list(common)[:5])}",
                    f"First request: {requests_in_group[0][:80]}...",
                    f"Latest request: {requests_in_group[-1][:80]}...",
                ],
                context={
                    "repetition_count": len(group),
                    "common_keywords": list(common),
                    "requests": requests_in_group,
                },
                session_id=session_id,
                suggested_insight=f"User persistently asking about: {', '.join(list(common)[:3])}",
                suggested_category="user_understanding",
            ))

        return patterns
