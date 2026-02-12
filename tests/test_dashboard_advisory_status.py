import dashboard


def test_build_advisory_status_block_normalizes_state_and_summarizes():
    block = dashboard._build_advisory_status_block(
        {
            "enabled": True,
            "delivery_badge": {
                "state": "LIVE",
                "reason": "recent_emit",
                "age_s": "4.2",
                "event": "emitted",
                "delivery_mode": "live",
            },
            "emission_rate": 0.45,
            "total_events": "23",
            "recent_events": [
                {"ts": 995.0, "event": "emitted", "route": "live", "tool": "Read"},
            ],
            "packet_store": {"queue_depth": "12", "hit_rate": 0.33, "active_packets": 9, "fresh_packets": 2},
            "prefetch_worker": {"pending_jobs": "3", "paused": False},
            "synthesizer": {"tier_label": "AI-Enhanced", "preferred_provider": "auto"},
        },
        now_ts=1000.0,
    )

    assert block["available"] is True
    assert block["delivery_badge"]["state"] == "live"
    assert block["total_events"] == 23
    assert block["latest_event"]["event"] == "emitted"
    assert block["latest_event"]["age_s"] == 5.0
    assert block["packet_store"]["queue_depth"] == 12
    assert block["prefetch_worker"]["pending_jobs"] == 3
    assert block["synthesizer"]["tier_label"] == "AI-Enhanced"


def test_get_advisory_status_block_handles_fetch_failure():
    def _raise():
        raise RuntimeError("boom")

    block = dashboard._get_advisory_status_block(_raise)

    assert block["available"] is False
    assert block["delivery_badge"]["state"] == "blocked"
    assert block["delivery_badge"]["reason"] == "status_unavailable"
    assert "boom" in block["error"]


def test_generate_system_badges_includes_advisory_delivery_state():
    html = dashboard.generate_system_badges(
        {
            "systems": {},
            "eidos": {},
            "advisory": {"delivery_badge": {"state": "stale"}},
        }
    )
    assert "Advisory stale" in html
    assert "system-badge error" in html


def test_get_ops_data_includes_advisory_block(monkeypatch):
    def _fake_load(path):
        if path == dashboard.SKILLS_INDEX_FILE:
            return {"skills": []}
        return {}

    monkeypatch.setattr(dashboard, "_load_json", _fake_load)
    monkeypatch.setattr(dashboard, "_read_jsonl", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        dashboard,
        "_get_advisory_status_block",
        lambda: {"delivery_badge": {"state": "fallback"}, "available": True},
    )

    data = dashboard.get_ops_data()

    assert data["advisory"]["delivery_badge"]["state"] == "fallback"
