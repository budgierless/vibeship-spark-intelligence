from __future__ import annotations

import json
import time

import lib.advisory_packet_store as store


def _patch_store_paths(monkeypatch, tmp_path):
    packet_dir = tmp_path / "advice_packets"
    monkeypatch.setattr(store, "PACKET_DIR", packet_dir)
    monkeypatch.setattr(store, "INDEX_FILE", packet_dir / "index.json")
    monkeypatch.setattr(store, "PREFETCH_QUEUE_FILE", packet_dir / "prefetch_queue.jsonl")


def test_packet_store_create_lookup_invalidate(monkeypatch, tmp_path):
    _patch_store_paths(monkeypatch, tmp_path)

    packet = store.build_packet(
        project_key="proj",
        session_context_key="ctx",
        tool_name="Edit",
        intent_family="auth_security",
        task_plane="build_delivery",
        advisory_text="Validate auth server-side.",
        source_mode="deterministic",
        advice_items=[{"advice_id": "a1", "text": "Validate auth server-side."}],
        lineage={"sources": ["baseline"], "memory_absent_declared": False},
        ttl_s=120,
    )
    packet_id = store.save_packet(packet)

    fetched = store.lookup_exact(
        project_key="proj",
        session_context_key="ctx",
        tool_name="Edit",
        intent_family="auth_security",
    )
    assert fetched is not None
    assert fetched["packet_id"] == packet_id

    assert store.invalidate_packet(packet_id, reason="test") is True
    assert (
        store.lookup_exact(
            project_key="proj",
            session_context_key="ctx",
            tool_name="Edit",
            intent_family="auth_security",
        )
        is None
    )


def test_packet_store_requires_lineage_fields(monkeypatch, tmp_path):
    _patch_store_paths(monkeypatch, tmp_path)

    packet = store.build_packet(
        project_key="proj",
        session_context_key="ctx",
        tool_name="Read",
        intent_family="knowledge_alignment",
        task_plane="build_delivery",
        advisory_text="Read target files first.",
        source_mode="deterministic",
        lineage={"sources": ["x"], "memory_absent_declared": False},
    )
    packet["lineage"] = {"sources": ["x"]}

    try:
        store.save_packet(packet)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "missing_lineage_fields" in str(exc)


def test_packet_store_relaxed_lookup_prefers_matching_tool(monkeypatch, tmp_path):
    _patch_store_paths(monkeypatch, tmp_path)

    p1 = store.build_packet(
        project_key="proj",
        session_context_key="c1",
        tool_name="*",
        intent_family="auth_security",
        task_plane="build_delivery",
        advisory_text="Generic auth guidance.",
        source_mode="baseline",
        lineage={"sources": ["baseline"], "memory_absent_declared": False},
        ttl_s=120,
    )
    time.sleep(0.01)
    p2 = store.build_packet(
        project_key="proj",
        session_context_key="c2",
        tool_name="Edit",
        intent_family="auth_security",
        task_plane="build_delivery",
        advisory_text="Edit auth middleware safely.",
        source_mode="live",
        lineage={"sources": ["cognitive"], "memory_absent_declared": False},
        ttl_s=120,
    )
    store.save_packet(p1)
    store.save_packet(p2)

    relaxed = store.lookup_relaxed(
        project_key="proj",
        tool_name="Edit",
        intent_family="auth_security",
        task_plane="build_delivery",
    )
    assert relaxed is not None
    assert relaxed["tool_name"] == "Edit"


def test_prefetch_queue_append(monkeypatch, tmp_path):
    _patch_store_paths(monkeypatch, tmp_path)
    job_id = store.enqueue_prefetch_job({"session_id": "s1", "intent_family": "auth_security"})
    assert job_id.startswith("pf_")

    lines = store.PREFETCH_QUEUE_FILE.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["job_id"] == job_id

