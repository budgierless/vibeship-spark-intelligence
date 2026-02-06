#!/usr/bin/env python3
"""Tests for lib/x_client.py -- tweepy wrapper with rate limit handling."""

import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Stub tweepy before importing x_client.
# TooManyRequests must be a real exception class for except clauses to work.
tweepy_mock = MagicMock()


class _FakeTooManyRequests(Exception):
    pass


tweepy_mock.TooManyRequests = _FakeTooManyRequests
tweepy_mock.Client = MagicMock

sys.modules["tweepy"] = tweepy_mock

from lib import x_client as mod


class TestXClientInit(unittest.TestCase):
    """Test client construction and env-var requirements."""

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_bearer_raises(self):
        # Reset singleton
        mod._instance = None
        with self.assertRaises(EnvironmentError):
            mod.XClient()

    @patch.dict(os.environ, {"TWITTER_BEARER_TOKEN": "tok123"})
    def test_creates_with_bearer(self):
        mod._instance = None
        client = mod.XClient()
        self.assertIsNotNone(client)


class TestSingleton(unittest.TestCase):
    """Singleton accessor returns same instance."""

    @patch.dict(os.environ, {"TWITTER_BEARER_TOKEN": "tok123"})
    def test_singleton(self):
        mod._instance = None
        a = mod.get_x_client()
        b = mod.get_x_client()
        self.assertIs(a, b)

    def tearDown(self):
        mod._instance = None


class TestBackoff(unittest.TestCase):
    """Rate-limit backoff timer."""

    @patch.dict(os.environ, {"TWITTER_BEARER_TOKEN": "tok123"})
    def setUp(self):
        mod._instance = None
        self.client = mod.XClient()

    def test_not_backed_off_initially(self):
        self.assertFalse(self.client._is_backed_off())

    def test_handle_rate_limit_activates_backoff(self):
        self.client._handle_rate_limit()
        self.assertTrue(self.client._is_backed_off())

    def test_backoff_expires(self):
        self.client._backoff_until = time.time() - 1
        self.assertFalse(self.client._is_backed_off())

    def tearDown(self):
        mod._instance = None


class TestGetAuthenticatedUser(unittest.TestCase):
    """get_authenticated_user tests."""

    @patch.dict(os.environ, {"TWITTER_BEARER_TOKEN": "tok123"})
    def setUp(self):
        mod._instance = None
        self.client = mod.XClient()

    def test_returns_cached(self):
        self.client._me = {"id": "1", "username": "test", "name": "Test"}
        result = self.client.get_authenticated_user()
        self.assertEqual(result["username"], "test")

    def test_returns_none_during_backoff(self):
        self.client._backoff_until = time.time() + 999
        self.assertIsNone(self.client.get_authenticated_user())

    def test_returns_none_on_empty_response(self):
        self.client._client.get_me = MagicMock(return_value=None)
        self.assertIsNone(self.client.get_authenticated_user())

    def test_parses_valid_response(self):
        user = MagicMock()
        user.id = 42
        user.username = "spark"
        user.name = "Spark Bot"
        resp = MagicMock()
        resp.data = user
        self.client._client.get_me = MagicMock(return_value=resp)
        result = self.client.get_authenticated_user()
        self.assertEqual(result, {"id": "42", "username": "spark", "name": "Spark Bot"})

    def test_rate_limit_triggers_backoff(self):
        self.client._client.get_me = MagicMock(
            side_effect=_FakeTooManyRequests("rate limited")
        )
        result = self.client.get_authenticated_user()
        self.assertIsNone(result)
        self.assertTrue(self.client._is_backed_off())

    def test_generic_exception_returns_none(self):
        self.client._client.get_me = MagicMock(side_effect=RuntimeError("boom"))
        self.assertIsNone(self.client.get_authenticated_user())

    def tearDown(self):
        mod._instance = None


class TestGetMentions(unittest.TestCase):
    """get_mentions tests."""

    @patch.dict(os.environ, {"TWITTER_BEARER_TOKEN": "tok123"})
    def setUp(self):
        mod._instance = None
        self.client = mod.XClient()
        self.client._me = {"id": "99", "username": "spark", "name": "Spark"}

    def test_returns_empty_during_backoff(self):
        self.client._backoff_until = time.time() + 999
        self.assertEqual(self.client.get_mentions(), [])

    def test_returns_empty_on_no_data(self):
        resp = MagicMock()
        resp.data = None
        self.client._client.get_users_mentions = MagicMock(return_value=resp)
        self.assertEqual(self.client.get_mentions(), [])

    def test_parses_mention(self):
        tweet = MagicMock()
        tweet.id = 100
        tweet.author_id = 200
        tweet.text = "hello @spark"
        tweet.public_metrics = {"like_count": 5, "retweet_count": 1, "reply_count": 0}
        tweet.referenced_tweets = None
        tweet.created_at = "2026-01-01T00:00:00Z"

        author = MagicMock()
        author.id = 200
        author.username = "alice"
        author.public_metrics = {"followers_count": 500}
        author.created_at = None

        resp = MagicMock()
        resp.data = [tweet]
        resp.includes = {"users": [author]}
        self.client._client.get_users_mentions = MagicMock(return_value=resp)

        results = self.client.get_mentions()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["tweet_id"], "100")
        self.assertEqual(results[0]["author"], "alice")
        self.assertEqual(results[0]["likes"], 5)
        self.assertFalse(results[0]["is_reply"])

    def test_detects_reply(self):
        ref = MagicMock()
        ref.type = "replied_to"
        ref.id = 50

        tweet = MagicMock()
        tweet.id = 101
        tweet.author_id = 200
        tweet.text = "replying"
        tweet.public_metrics = {}
        tweet.referenced_tweets = [ref]
        tweet.created_at = None

        resp = MagicMock()
        resp.data = [tweet]
        resp.includes = None
        self.client._client.get_users_mentions = MagicMock(return_value=resp)

        results = self.client.get_mentions()
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["is_reply"])
        self.assertEqual(results[0]["parent_tweet_id"], "50")

    def test_rate_limit_on_mentions(self):
        self.client._client.get_users_mentions = MagicMock(
            side_effect=_FakeTooManyRequests("rate limited")
        )
        self.assertEqual(self.client.get_mentions(), [])
        self.assertTrue(self.client._is_backed_off())

    def tearDown(self):
        mod._instance = None


class TestSearchTweets(unittest.TestCase):
    """search_tweets tests."""

    @patch.dict(os.environ, {"TWITTER_BEARER_TOKEN": "tok123"})
    def setUp(self):
        mod._instance = None
        self.client = mod.XClient()

    def test_returns_empty_during_backoff(self):
        self.client._backoff_until = time.time() + 999
        self.assertEqual(self.client.search_tweets("test"), [])

    def test_returns_empty_on_no_data(self):
        resp = MagicMock()
        resp.data = None
        self.client._client.search_recent_tweets = MagicMock(return_value=resp)
        self.assertEqual(self.client.search_tweets("test"), [])

    def test_parses_search_results(self):
        tweet = MagicMock()
        tweet.id = 300
        tweet.author_id = 400
        tweet.text = "search hit"
        tweet.public_metrics = {"like_count": 10, "retweet_count": 2, "reply_count": 1}
        tweet.created_at = "2026-01-15"

        author = MagicMock()
        author.id = 400
        author.username = "bob"
        author.public_metrics = {}

        resp = MagicMock()
        resp.data = [tweet]
        resp.includes = {"users": [author]}
        self.client._client.search_recent_tweets = MagicMock(return_value=resp)

        results = self.client.search_tweets("test")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["tweet_id"], "300")
        self.assertEqual(results[0]["author"], "bob")
        self.assertEqual(results[0]["likes"], 10)

    def tearDown(self):
        mod._instance = None


class TestGetTweetById(unittest.TestCase):
    """get_tweet_by_id tests."""

    @patch.dict(os.environ, {"TWITTER_BEARER_TOKEN": "tok123"})
    def setUp(self):
        mod._instance = None
        self.client = mod.XClient()

    def test_returns_none_during_backoff(self):
        self.client._backoff_until = time.time() + 999
        self.assertIsNone(self.client.get_tweet_by_id("123"))

    def test_returns_none_on_empty(self):
        self.client._client.get_tweet = MagicMock(return_value=None)
        self.assertIsNone(self.client.get_tweet_by_id("123"))

    def test_parses_tweet(self):
        tweet = MagicMock()
        tweet.id = 500
        tweet.text = "hello world"
        tweet.public_metrics = {
            "like_count": 3,
            "retweet_count": 1,
            "reply_count": 0,
            "impression_count": 100,
        }
        tweet.created_at = "2026-02-01"
        resp = MagicMock()
        resp.data = tweet
        self.client._client.get_tweet = MagicMock(return_value=resp)

        result = self.client.get_tweet_by_id("500")
        self.assertEqual(result["tweet_id"], "500")
        self.assertEqual(result["impressions"], 100)

    def tearDown(self):
        mod._instance = None


class TestGetUserProfile(unittest.TestCase):
    """get_user_profile tests."""

    @patch.dict(os.environ, {"TWITTER_BEARER_TOKEN": "tok123"})
    def setUp(self):
        mod._instance = None
        self.client = mod.XClient()

    def test_returns_none_during_backoff(self):
        self.client._backoff_until = time.time() + 999
        self.assertIsNone(self.client.get_user_profile("alice"))

    def test_strips_at_sign(self):
        self.client._client.get_user = MagicMock(return_value=None)
        self.client.get_user_profile("@alice")
        call_kwargs = self.client._client.get_user.call_args
        self.assertEqual(call_kwargs.kwargs.get("username") or call_kwargs[1].get("username"), "alice")

    def test_parses_profile(self):
        user = MagicMock()
        user.id = 600
        user.username = "carol"
        user.name = "Carol"
        user.public_metrics = {
            "followers_count": 1000,
            "following_count": 200,
            "tweet_count": 500,
        }
        user.created_at = "2020-01-01"
        user.description = "Builder"
        resp = MagicMock()
        resp.data = user
        self.client._client.get_user = MagicMock(return_value=resp)

        result = self.client.get_user_profile("carol")
        self.assertEqual(result["id"], "600")
        self.assertEqual(result["followers_count"], 1000)
        self.assertEqual(result["description"], "Builder")

    def tearDown(self):
        mod._instance = None


if __name__ == "__main__":
    unittest.main()
