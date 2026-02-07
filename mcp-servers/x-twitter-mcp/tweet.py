#!/usr/bin/env python3
"""
Direct tweepy fallback for @Spark_coded tweets.

Use this when the xmcp MCP server returns 403 due to stale cached credentials.
Loads credentials from the .env file in this directory.

Usage:
    # Post a tweet
    python tweet.py "Hello world"

    # Post with an image
    python tweet.py "Check this out" --media path/to/image.png

    # Reply to a tweet
    python tweet.py "Great point!" --reply-to 2019864160490909823

    # Post with hashtags
    python tweet.py "Check this out" --tags AI Spark

    # Delete a tweet
    python tweet.py --delete 2019872764333814152

    # Test credentials (post + delete)
    python tweet.py --test
"""

import argparse
import sys
from pathlib import Path

import tweepy
from dotenv import dotenv_values


def load_creds() -> dict:
    """Load Twitter credentials from .env in this directory."""
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        print(f"ERROR: No .env file at {env_path}", file=sys.stderr)
        sys.exit(1)
    creds = dotenv_values(env_path)
    required = ["TWITTER_API_KEY", "TWITTER_API_SECRET",
                "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_TOKEN_SECRET"]
    missing = [k for k in required if not creds.get(k)]
    if missing:
        print(f"ERROR: Missing in .env: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)
    return creds


def get_client(creds: dict) -> tweepy.Client:
    """Create a tweepy Client with OAuth 1.0a user context."""
    return tweepy.Client(
        consumer_key=creds["TWITTER_API_KEY"],
        consumer_secret=creds["TWITTER_API_SECRET"],
        access_token=creds["TWITTER_ACCESS_TOKEN"],
        access_token_secret=creds["TWITTER_ACCESS_TOKEN_SECRET"],
    )


def get_api(creds: dict) -> tweepy.API:
    """Create a tweepy v1.1 API for media uploads."""
    auth = tweepy.OAuth1UserHandler(
        creds["TWITTER_API_KEY"],
        creds["TWITTER_API_SECRET"],
        creds["TWITTER_ACCESS_TOKEN"],
        creds["TWITTER_ACCESS_TOKEN_SECRET"],
    )
    return tweepy.API(auth)


def upload_media(api: tweepy.API, file_path: str) -> int:
    """Upload media via v1.1 API. Returns media_id."""
    p = Path(file_path)
    if not p.exists():
        print(f"ERROR: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    media = api.media_upload(filename=str(p))
    print(f"  Media uploaded: id={media.media_id} ({p.name})")
    return media.media_id


def post_tweet(client: tweepy.Client, text: str,
               reply_to: str = None, tags: list = None,
               media_ids: list = None) -> dict:
    """Post a tweet, optionally as a reply, with hashtags, or with media."""
    if tags:
        text += " " + " ".join(f"#{t}" for t in tags)

    kwargs = {"text": text}
    if reply_to:
        kwargs["in_reply_to_tweet_id"] = reply_to
    if media_ids:
        kwargs["media_ids"] = media_ids

    result = client.create_tweet(**kwargs)
    return result.data


def delete_tweet(client: tweepy.Client, tweet_id: str) -> bool:
    """Delete a tweet by ID."""
    result = client.delete_tweet(tweet_id)
    return result.data.get("deleted", False)


def like_tweet(client: tweepy.Client, tweet_id: str) -> bool:
    """Like a tweet by ID."""
    result = client.like(tweet_id)
    return result.data.get("liked", False)


def test_credentials(client: tweepy.Client) -> bool:
    """Test read + write access, then clean up."""
    # Test read
    me = client.get_me()
    print(f"  Read OK  - @{me.data.username} (id: {me.data.id})")

    # Test write
    tweet = client.create_tweet(text="__spark_credential_test__ (auto-deleting)")
    tid = tweet.data["id"]
    print(f"  Write OK - Tweet {tid} created")

    # Clean up
    client.delete_tweet(tid)
    print(f"  Cleanup  - Tweet {tid} deleted")
    return True


def main():
    parser = argparse.ArgumentParser(description="@Spark_coded tweet utility")
    parser.add_argument("text", nargs="?", help="Tweet text")
    parser.add_argument("--reply-to", help="Tweet ID to reply to")
    parser.add_argument("--media", nargs="+", help="Media file(s) to attach (max 4 images)")
    parser.add_argument("--tags", nargs="+", help="Hashtags (without #)")
    parser.add_argument("--like", metavar="ID", help="Like a tweet by ID")
    parser.add_argument("--delete", metavar="ID", help="Delete a tweet by ID")
    parser.add_argument("--test", action="store_true", help="Test credentials")
    args = parser.parse_args()

    creds = load_creds()
    client = get_client(creds)

    if args.like:
        ok = like_tweet(client, args.like)
        print(f"Liked: {ok}")
        return

    if args.test:
        print("Testing @Spark_coded credentials...")
        try:
            test_credentials(client)
            print("All tests passed.")
        except Exception as e:
            print(f"FAILED: {e}", file=sys.stderr)
            sys.exit(1)
        return

    if args.delete:
        ok = delete_tweet(client, args.delete)
        print(f"Deleted: {ok}")
        return

    if not args.text:
        parser.print_help()
        sys.exit(1)

    media_ids = None
    if args.media:
        api = get_api(creds)
        media_ids = [upload_media(api, f) for f in args.media]

    data = post_tweet(client, args.text, args.reply_to, args.tags, media_ids)
    print(f"Posted: https://x.com/Spark_coded/status/{data['id']}")
    print(f"Text:   {data['text']}")


if __name__ == "__main__":
    main()
