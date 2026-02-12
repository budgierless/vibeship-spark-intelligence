#!/usr/bin/env python3
"""Style-aware X reply helper for Spark.

Draft flow:
  python scripts/x_reply.py "raw draft" --reply-to 123 --author @user

Post flow:
  python scripts/x_reply.py "raw draft" --reply-to 123 --author @user --post --like-parent --register
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import sys
from pathlib import Path
from typing import Optional

from dotenv import dotenv_values

from lib.convo_analyzer import get_convo_analyzer
from lib.x_client import get_x_client
from lib.x_evolution import register_spark_reply
from lib.x_voice import get_x_voice


ROOT = Path(__file__).resolve().parent.parent
TWITTER_ENV = ROOT / "mcp-servers" / "x-twitter-mcp" / ".env"
TWEET_SCRIPT = ROOT / "mcp-servers" / "x-twitter-mcp" / "tweet.py"

HASHTAG_RE = re.compile(r"(?<!\w)#\w+")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
EMOJI_RE = re.compile(
    "["
    "\U0001F1E6-\U0001F1FF"
    "\U0001F300-\U0001FAFF"
    "\U00002700-\U000027BF"
    "]",
    flags=re.UNICODE,
)


def _load_x_env() -> None:
    if not TWITTER_ENV.exists():
        return
    for key, value in dotenv_values(TWITTER_ENV).items():
        if key and value and not os.environ.get(key):
            os.environ[key] = value


def _fetch_parent_text(tweet_id: str) -> str:
    try:
        info = get_x_client().get_tweet_by_id(tweet_id)
        if not info:
            return ""
        return (info.get("text") or "").strip()
    except Exception:
        return ""


def _trim_reply_sentences(text: str, max_sentences: int = 3) -> str:
    parts = [p.strip() for p in SENTENCE_RE.split(text) if p.strip()]
    if len(parts) <= max_sentences:
        return text.strip()
    return " ".join(parts[:max_sentences]).strip()


def _style_reply(
    raw_text: str,
    author_handle: Optional[str],
    tone: str,
    allow_emoji: bool,
) -> str:
    voice = get_x_voice()
    styled = voice.render_tweet(
        content=raw_text,
        style=tone,
        reply_to_handle=author_handle or "@user",
        humanize=True,
    )
    styled = HASHTAG_RE.sub("", styled)
    if not allow_emoji:
        styled = EMOJI_RE.sub("", styled)
    styled = _trim_reply_sentences(styled, max_sentences=3)
    styled = re.sub(r"\s+", " ", styled).strip()
    styled = re.sub(r"^[,;:!.\-\s]+", "", styled)
    return styled.lower()


def _load_tweet_module():
    if not TWEET_SCRIPT.exists():
        raise FileNotFoundError(f"tweet.py not found at {TWEET_SCRIPT}")
    spec = importlib.util.spec_from_file_location("spark_tweet_cli", str(TWEET_SCRIPT))
    if not spec or not spec.loader:
        raise RuntimeError("Failed to load tweet.py module spec")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _score_reply(
    reply_text: str,
    parent_text: str,
    author_handle: Optional[str],
) -> None:
    if not parent_text:
        return
    analyzer = get_convo_analyzer()
    result = analyzer.score_reply_draft(
        draft=reply_text,
        parent_text=parent_text,
        author_handle=author_handle,
    )
    print("\nDraft score")
    print(f"  verdict: {result.get('verdict')}")
    print(f"  score:   {result.get('score')}/10")
    rec = result.get("recommendation") or {}
    print(f"  hook:    {rec.get('hook_type')} ({rec.get('tone')})")
    reason = rec.get("reasoning")
    if reason:
        print(f"  why:     {reason}")
    analysis = result.get("analysis") or {}
    suggestions = analysis.get("suggestions") or []
    if suggestions:
        print("  suggestions:")
        for item in suggestions[:3]:
            print(f"    - {item}")


def _post_reply(
    reply_text: str,
    reply_to_id: str,
    like_parent: bool,
    register: bool,
) -> None:
    tweet_mod = _load_tweet_module()
    creds = tweet_mod.load_creds()
    client = tweet_mod.get_client(creds)
    data = tweet_mod.post_tweet(client, reply_text, reply_to=reply_to_id)

    reply_id = str(data["id"])
    print("\nPosted")
    print(f"  url:  https://x.com/Spark_coded/status/{reply_id}")
    print(f"  text: {data['text']}")

    if like_parent:
        ok = tweet_mod.like_tweet(client, reply_to_id)
        print(f"  liked parent: {ok}")

    if register:
        register_spark_reply(reply_id, reply_to_id, reply_text)
        print("  evolution tracking: registered")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Spark style-aware X reply helper")
    parser.add_argument("text", help="Raw reply draft text")
    parser.add_argument("--reply-to", required=True, help="Parent tweet ID")
    parser.add_argument(
        "--author",
        help="Parent tweet author handle (for tone/warmth adaptation), e.g. @alice",
    )
    parser.add_argument(
        "--parent-text",
        help="Parent tweet text (optional; if missing, Spark tries to fetch it)",
    )
    parser.add_argument(
        "--tone",
        default="auto",
        choices=["auto", "witty", "technical", "conversational", "provocative"],
        help="Tone override (default: auto)",
    )
    parser.add_argument(
        "--allow-emoji",
        action="store_true",
        help="Keep emoji (default strips emoji for reply consistency)",
    )
    parser.add_argument(
        "--skip-score",
        action="store_true",
        help="Skip ConvoIQ draft scoring",
    )
    parser.add_argument(
        "--post",
        action="store_true",
        help="Post the styled reply (otherwise dry run only)",
    )
    parser.add_argument(
        "--like-parent",
        action="store_true",
        help="Like parent tweet after posting",
    )
    parser.add_argument(
        "--register",
        action="store_true",
        help="Register reply in x_evolution tracking after posting",
    )
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    _load_x_env()

    parent_text = (args.parent_text or "").strip()
    if not parent_text:
        parent_text = _fetch_parent_text(args.reply_to)

    styled = _style_reply(
        raw_text=args.text,
        author_handle=args.author,
        tone=args.tone,
        allow_emoji=args.allow_emoji,
    )

    print("Styled reply")
    print(f"  {styled}")

    if parent_text:
        print("\nParent tweet")
        print(f"  {parent_text}")

    if not args.skip_score:
        _score_reply(styled, parent_text, args.author)

    if not args.post:
        print("\nDry run complete. Add --post to send.")
        return

    try:
        _post_reply(
            reply_text=styled,
            reply_to_id=args.reply_to,
            like_parent=args.like_parent,
            register=args.register,
        )
    except Exception as exc:
        print(f"ERROR: Failed to post reply: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
