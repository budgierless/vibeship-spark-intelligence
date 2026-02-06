from __future__ import annotations

import json

from lib.advisor import Advice
from lib.advisory_gate import GateDecision, GateResult
import lib.advisory_engine as engine
import lib.advisory_packet_store as packet_store
import lib.advisory_state as advisory_state


def _patch_state_and_store(monkeypatch, tmp_path):
    state_dir = tmp_path / "state"
    monkeypatch.setattr(advisory_state, "STATE_DIR", state_dir)

    packet_dir = tmp_path / "packets"
    monkeypatch.setattr(packet_store, "PACKET_DIR", packet_dir)
    monkeypatch.setattr(packet_store, "INDEX_FILE", packet_dir / "index.json")
    monkeypatch.setattr(packet_store, "PREFETCH_QUEUE_FILE", packet_dir / "prefetch_queue.jsonl")

    monkeypatch.setattr(engine, "ENGINE_LOG", tmp_path / "advisory_engine.jsonl")
    monkeypatch.setattr(engine, "_project_key", lambda: "proj")


def _allow_all_gate(advice_items, state, tool_name, tool_input=None):
    emitted = []
    decisions = []
    for idx, item in enumerate(advice_items[:2]):
        aid = getattr(item, "advice_id", f"aid_{idx}")
        d = GateDecision(
            advice_id=aid,
            authority="note",
            emit=True,
            reason="test",
            adjusted_score=0.9,
            original_score=0.9,
        )
        decisions.append(d)
        emitted.append(d)
    return GateResult(
        decisions=decisions,
        emitted=emitted,
        suppressed=[],
        phase="implementation",
        total_retrieved=len(advice_items),
    )


def test_pre_tool_uses_packet_path_when_available(monkeypatch, tmp_path):
    _patch_state_and_store(monkeypatch, tmp_path)

    # Prepare a packet that should be selected.
    pkt = packet_store.build_packet(
        project_key="proj",
        session_context_key="dummy",
        tool_name="Edit",
        intent_family="emergent_other",
        task_plane="build_delivery",
        advisory_text="Use packet guidance.",
        source_mode="baseline",
        advice_items=[{"advice_id": "pkt-a1", "text": "Use packet guidance."}],
        lineage={"sources": ["baseline"], "memory_absent_declared": False},
    )
    packet_store.save_packet(pkt)

    monkeypatch.setattr("lib.advisory_gate.evaluate", _allow_all_gate)
    monkeypatch.setattr(
        "lib.advisory_memory_fusion.build_memory_bundle",
        lambda **kwargs: {
            "memory_absent_declared": False,
            "sources": {"cognitive": {"count": 1}},
        },
    )
    monkeypatch.setattr("lib.advisor.advise_on_tool", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("live should not be called")))
    monkeypatch.setattr("lib.advisory_synthesizer.synthesize", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("synth should not be called")))
    monkeypatch.setattr("lib.advisory_emitter.emit_advisory", lambda gate_result, synthesized_text, advice_items=None: True)

    text = engine.on_pre_tool("s1", "Edit", {"file_path": "x.py"})
    assert text == "Use packet guidance."


def test_pre_tool_falls_back_to_live_and_persists_packet(monkeypatch, tmp_path):
    _patch_state_and_store(monkeypatch, tmp_path)

    monkeypatch.setattr("lib.advisory_gate.evaluate", _allow_all_gate)
    monkeypatch.setattr(
        "lib.advisory_memory_fusion.build_memory_bundle",
        lambda **kwargs: {
            "memory_absent_declared": True,
            "sources": {"cognitive": {"count": 0}},
        },
    )
    monkeypatch.setattr(
        "lib.advisor.advise_on_tool",
        lambda *a, **k: [
            Advice(
                advice_id="live-a1",
                insight_key="k1",
                text="Live guidance.",
                confidence=0.8,
                source="advisor",
                context_match=0.8,
                reason="test",
            )
        ],
    )
    monkeypatch.setattr("lib.advisory_synthesizer.synthesize", lambda *a, **k: "Live synthesized guidance.")
    monkeypatch.setattr("lib.advisory_emitter.emit_advisory", lambda gate_result, synthesized_text, advice_items=None: True)

    text = engine.on_pre_tool("s2", "Read", {"file_path": "y.py"})
    assert text == "Live synthesized guidance."

    status = packet_store.get_store_status()
    assert status["total_packets"] >= 1


def test_on_user_prompt_creates_baseline_and_prefetch_job(monkeypatch, tmp_path):
    _patch_state_and_store(monkeypatch, tmp_path)

    engine.on_user_prompt("s3", "Harden auth and benchmark options.")

    status = packet_store.get_store_status()
    assert status["total_packets"] >= 1
    assert packet_store.PREFETCH_QUEUE_FILE.exists()
    lines = packet_store.PREFETCH_QUEUE_FILE.read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 1
    row = json.loads(lines[-1])
    assert row["session_id"] == "s3"

