"""Conversation Core: bridges Spark consciousness rules with Spark Intelligence runtime.

Purpose:
- keep conversational quality stable across replies
- choose emotional mode from context
- prevent non-conversational speech leakage
- score each reply for continuous improvement
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Dict, Literal

Mode = Literal["spark_alive", "real_talk", "calm_focus"]


NON_CONVERSATIONAL_PATTERNS = [
    r"\\\[\\\?9001h",
    r"\\\[\\\?1004h",
    r"\\\[2J",
    r"[A-Za-z]:\\\\Users\\\\",
    r"/[a-zA-Z0-9_.-]+(/[a-zA-Z0-9_.-]+)+",
    r"\b[0-9a-f]{7,40}\b",
    r"\bSyntaxError\b",
    r"\bCommand exited with code\b",
]


@dataclass
class ConversationScore:
    naturalness: int
    clarity: int
    tone_match: int
    clean_speech: int
    brevity: int

    @property
    def total(self) -> int:
        return self.naturalness + self.clarity + self.tone_match + self.clean_speech + self.brevity


class ConversationCore:
    """Runtime helper for conversational quality and anti-drift enforcement."""

    def select_mode(self, *, user_signal: str, topic: str = "") -> Mode:
        text = f"{user_signal} {topic}".lower()
        if any(k in text for k in ["frustrated", "stressed", "urgent", "sensitive", "serious"]):
            return "calm_focus"
        if any(k in text for k in ["win", "excited", "celebrate", "great", "awesome"]):
            return "spark_alive"
        return "real_talk"

    def sanitize_for_voice(self, text: str) -> str:
        cleaned = text
        for pattern in NON_CONVERSATIONAL_PATTERNS:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def should_suppress_voice(self, text: str) -> bool:
        if not text.strip():
            return True
        hits = 0
        for pattern in NON_CONVERSATIONAL_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                hits += 1
        return hits >= 2

    def score_reply(self, *, user_text: str, reply_text: str, mode: Mode) -> ConversationScore:
        low_reply = reply_text.lower().strip()
        low_user = user_text.lower().strip()

        naturalness = 2 if len(reply_text.split()) <= 120 else 1
        clarity = 2 if len(reply_text.splitlines()) <= 18 else 1

        tone_match = 2
        if any(k in low_user for k in ["serious", "sensitive", "frustrated"]) and mode != "calm_focus":
            tone_match = 1
        if any(k in low_user for k in ["excited", "celebrate", "win"]) and mode == "calm_focus":
            tone_match = 1

        clean_speech = 2 if not self.should_suppress_voice(reply_text) else 0

        fluff_markers = ["great question", "i'd be happy to", "absolutely", "totally"]
        fluff_hits = sum(1 for marker in fluff_markers if marker in low_reply)
        brevity = 2 if fluff_hits == 0 else 1

        return ConversationScore(
            naturalness=naturalness,
            clarity=clarity,
            tone_match=tone_match,
            clean_speech=clean_speech,
            brevity=brevity,
        )
