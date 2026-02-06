#!/usr/bin/env python3
"""X/Twitter API client - thin tweepy wrapper with rate limit handling.

Provides authenticated access to X API v2 for the scheduler daemon.
All methods return dicts/lists and never raise exceptions to callers --
errors are logged and empty results returned.

Singleton: use get_x_client() to get the shared instance.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import tweepy

logger = logging.getLogger("spark.x_client")


class XClient:
    """Rate-limit-aware tweepy wrapper for Spark scheduler."""

    BACKOFF_SECONDS = 900  # 15 minutes on rate limit

    def __init__(self):
        bearer = os.environ.get("TWITTER_BEARER_TOKEN", "")
        api_key = os.environ.get("TWITTER_API_KEY", "")
        api_secret = os.environ.get("TWITTER_API_SECRET", "")
        access_token = os.environ.get("TWITTER_ACCESS_TOKEN", "")
        access_secret = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET", "")

        if not bearer:
            raise EnvironmentError("TWITTER_BEARER_TOKEN not set")

        self._client = tweepy.Client(
            bearer_token=bearer,
            consumer_key=api_key or None,
            consumer_secret=api_secret or None,
            access_token=access_token or None,
            access_token_secret=access_secret or None,
            wait_on_rate_limit=False,
        )
        self._me: Optional[Dict[str, Any]] = None
        self._backoff_until: float = 0.0

    def _is_backed_off(self) -> bool:
        if self._backoff_until > 0 and time.time() < self._backoff_until:
            remaining = self._backoff_until - time.time()
            logger.debug("Rate limit backoff active, %.0fs remaining", remaining)
            return True
        return False

    def _handle_rate_limit(self) -> None:
        self._backoff_until = time.time() + self.BACKOFF_SECONDS
        logger.warning("X API rate limited, backing off %ds", self.BACKOFF_SECONDS)

    # ------ Authenticated User ------

    def get_authenticated_user(self) -> Optional[Dict[str, Any]]:
        """Return {id, username, name} for the authenticated user."""
        if self._me:
            return self._me
        try:
            if self._is_backed_off():
                return None
            resp = self._client.get_me(user_fields=["id", "username", "name"])
            if not resp or not resp.data:
                return None
            u = resp.data
            self._me = {"id": str(u.id), "username": u.username, "name": u.name}
            return self._me
        except tweepy.TooManyRequests:
            self._handle_rate_limit()
            return None
        except Exception as e:
            logger.debug("get_authenticated_user failed: %s", e)
            return None

    # ------ Mentions ------

    def get_mentions(
        self,
        since_id: Optional[str] = None,
        max_results: int = 50,
    ) -> List[Dict[str, Any]]:
        """Fetch @mentions of the authenticated user.

        Returns list of dicts with keys: tweet_id, author, author_id, text,
        likes, retweets, replies, author_followers, author_account_age_days,
        created_at, is_reply, parent_tweet_id
        """
        try:
            if self._is_backed_off():
                return []
            me = self.get_authenticated_user()
            if not me:
                return []

            kwargs = {
                "id": me["id"],
                "max_results": min(max_results, 100),
                "tweet_fields": ["created_at", "public_metrics", "referenced_tweets"],
                "expansions": ["author_id"],
                "user_fields": ["public_metrics", "created_at", "username"],
            }
            if since_id:
                kwargs["since_id"] = since_id

            resp = self._client.get_users_mentions(**kwargs)
            if not resp or not resp.data:
                return []

            # Build author lookup from includes
            authors = {}
            if resp.includes and "users" in resp.includes:
                for u in resp.includes["users"]:
                    authors[str(u.id)] = u

            results = []
            for tweet in resp.data:
                author_user = authors.get(str(tweet.author_id))
                metrics = tweet.public_metrics or {}

                # Detect if reply
                is_reply = False
                parent_id = ""
                if tweet.referenced_tweets:
                    for ref in tweet.referenced_tweets:
                        if ref.type == "replied_to":
                            is_reply = True
                            parent_id = str(ref.id)
                            break

                # Calculate account age
                age_days = -1
                if author_user and hasattr(author_user, "created_at") and author_user.created_at:
                    try:
                        created = author_user.created_at
                        if isinstance(created, str):
                            created = datetime.fromisoformat(created.replace("Z", "+00:00"))
                        age_days = (datetime.now(timezone.utc) - created).days
                    except Exception:
                        pass

                author_metrics = {}
                if author_user and hasattr(author_user, "public_metrics"):
                    author_metrics = author_user.public_metrics or {}

                results.append({
                    "tweet_id": str(tweet.id),
                    "author": author_user.username if author_user else "",
                    "author_id": str(tweet.author_id),
                    "text": tweet.text or "",
                    "likes": metrics.get("like_count", 0),
                    "retweets": metrics.get("retweet_count", 0),
                    "replies": metrics.get("reply_count", 0),
                    "author_followers": author_metrics.get("followers_count", 0),
                    "author_account_age_days": age_days,
                    "created_at": str(tweet.created_at) if tweet.created_at else "",
                    "is_reply": is_reply,
                    "parent_tweet_id": parent_id,
                })

            return results
        except tweepy.TooManyRequests:
            self._handle_rate_limit()
            return []
        except Exception as e:
            logger.debug("get_mentions failed: %s", e)
            return []

    # ------ Search ------

    def search_tweets(
        self,
        query: str,
        max_results: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search recent tweets matching query.

        Returns list of dicts with: tweet_id, author, text, likes,
        retweets, replies, created_at
        """
        try:
            if self._is_backed_off():
                return []

            resp = self._client.search_recent_tweets(
                query=query,
                max_results=min(max_results, 100),
                tweet_fields=["created_at", "public_metrics", "author_id"],
                expansions=["author_id"],
                user_fields=["username", "public_metrics"],
            )
            if not resp or not resp.data:
                return []

            authors = {}
            if resp.includes and "users" in resp.includes:
                for u in resp.includes["users"]:
                    authors[str(u.id)] = u

            results = []
            for tweet in resp.data:
                metrics = tweet.public_metrics or {}
                author_user = authors.get(str(tweet.author_id))

                results.append({
                    "tweet_id": str(tweet.id),
                    "author": author_user.username if author_user else "",
                    "text": tweet.text or "",
                    "likes": metrics.get("like_count", 0),
                    "retweets": metrics.get("retweet_count", 0),
                    "replies": metrics.get("reply_count", 0),
                    "created_at": str(tweet.created_at) if tweet.created_at else "",
                })

            return results
        except tweepy.TooManyRequests:
            self._handle_rate_limit()
            return []
        except Exception as e:
            logger.debug("search_tweets failed: %s", e)
            return []

    # ------ Single Tweet ------

    def get_tweet_by_id(self, tweet_id: str) -> Optional[Dict[str, Any]]:
        """Get a single tweet with current engagement metrics."""
        try:
            if self._is_backed_off():
                return None

            resp = self._client.get_tweet(
                tweet_id,
                tweet_fields=["public_metrics", "created_at"],
            )
            if not resp or not resp.data:
                return None

            metrics = resp.data.public_metrics or {}
            return {
                "tweet_id": str(resp.data.id),
                "text": resp.data.text or "",
                "likes": metrics.get("like_count", 0),
                "retweets": metrics.get("retweet_count", 0),
                "replies": metrics.get("reply_count", 0),
                "impressions": metrics.get("impression_count", 0),
                "created_at": str(resp.data.created_at) if resp.data.created_at else "",
            }
        except tweepy.TooManyRequests:
            self._handle_rate_limit()
            return None
        except Exception as e:
            logger.debug("get_tweet_by_id failed: %s", e)
            return None

    # ------ User Profile ------

    def get_user_profile(self, handle: str) -> Optional[Dict[str, Any]]:
        """Get user profile info."""
        try:
            if self._is_backed_off():
                return None

            resp = self._client.get_user(
                username=handle.lstrip("@"),
                user_fields=["public_metrics", "created_at", "description"],
            )
            if not resp or not resp.data:
                return None

            u = resp.data
            metrics = u.public_metrics or {}
            return {
                "id": str(u.id),
                "username": u.username,
                "name": u.name,
                "followers_count": metrics.get("followers_count", 0),
                "following_count": metrics.get("following_count", 0),
                "tweet_count": metrics.get("tweet_count", 0),
                "created_at": str(u.created_at) if u.created_at else "",
                "description": u.description or "",
            }
        except tweepy.TooManyRequests:
            self._handle_rate_limit()
            return None
        except Exception as e:
            logger.debug("get_user_profile failed: %s", e)
            return None


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_instance: Optional[XClient] = None


def get_x_client() -> XClient:
    """Get the singleton XClient instance."""
    global _instance
    if _instance is None:
        _instance = XClient()
    return _instance
