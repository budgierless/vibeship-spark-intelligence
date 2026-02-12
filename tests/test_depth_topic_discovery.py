from lib import depth_trainer as dt


def test_get_weak_topics_exposes_ordered_weak_level_ids(tmp_path, monkeypatch):
    monkeypatch.setattr(dt, "TOPIC_QUEUE", tmp_path / "depth_topic_queue.json")
    history = [
        {"topic": "cache invalidation", "total_score": 58, "weak_levels": [2, 3]},
        {"topic": "cache invalidation", "total_score": 61, "weak_levels": [2]},
        {"topic": "schema migration", "total_score": 80, "weak_levels": []},
    ]
    monkeypatch.setattr(dt, "get_training_history", lambda limit=80: history)

    discovery = dt.TopicDiscovery()
    weak = discovery._get_weak_topics()

    assert weak
    assert weak[0]["topic"] == "cache invalidation"
    assert weak[0]["weak_level_ids"] == [2, 3]
    assert "Architect" in weak[0]["weak_lenses"]


def test_discover_next_topics_adds_targeted_weak_lens_drills(tmp_path, monkeypatch):
    monkeypatch.setattr(dt, "TOPIC_QUEUE", tmp_path / "depth_topic_queue.json")
    discovery = dt.TopicDiscovery()
    monkeypatch.setattr(discovery, "_get_unexplored_topics", lambda: [])
    monkeypatch.setattr(
        discovery,
        "_get_weak_topics",
        lambda: [
            {
                "topic": "distributed caching",
                "avg_score": 60.0,
                "sessions": 3,
                "weak_lenses": "Architect, Profile",
                "weak_level_ids": [2, 5],
            }
        ],
    )
    monkeypatch.setattr(discovery, "_get_strong_topics", lambda: [])

    topics = discovery.discover_next_topics(count=4)
    names = [t["topic"] for t in topics]

    assert "architecture drill for distributed caching" in names
    assert "profiling drill for distributed caching" in names
    assert any("targeted weak lens" in t["reason"] for t in topics)


def test_build_weak_lens_drill_topic_falls_back_for_unmapped_depth():
    topic = dt._build_weak_lens_drill_topic("observability", 14)
    assert "drill for observability" in topic
