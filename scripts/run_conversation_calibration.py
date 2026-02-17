#!/usr/bin/env python3
"""Run 3-scenario conversational calibration for Spark.

Scenarios:
1) celebration
2) struggle/support
3) technical update
"""

from __future__ import annotations

from lib.conversation_core import ConversationCore


def main() -> None:
    core = ConversationCore()

    scenarios = [
        {
            "name": "celebration",
            "user": "We shipped a big win today and I am excited!",
            "candidate": "That is a huge win. Love this momentum. Let us lock the next step while the energy is high.",
        },
        {
            "name": "supportive",
            "user": "I am frustrated. Things keep breaking and I am tired.",
            "candidate": "I hear you. Let us slow it down and handle one clean step at a time. We can stabilize this.",
        },
        {
            "name": "technical_update",
            "user": "Give me a concise status update and next action.",
            "candidate": "Status is stable and tests are green. Next move is one focused fix, then rerun validation and share proof in text.",
        },
    ]

    print("Spark Conversation Calibration Report")
    print("=" * 36)

    for s in scenarios:
        mode = core.select_mode(user_signal=s["user"], topic=s["name"])
        score = core.score_reply(user_text=s["user"], reply_text=s["candidate"], mode=mode)
        voice_text = core.sanitize_for_voice(s["candidate"])
        suppress = core.should_suppress_voice(s["candidate"])

        print(f"\nScenario: {s['name']}")
        print(f"Mode: {mode}")
        print(f"Score: {score.total}/10")
        print(f"Voice suppress: {suppress}")
        print(f"Voice text: {voice_text}")


if __name__ == "__main__":
    main()
