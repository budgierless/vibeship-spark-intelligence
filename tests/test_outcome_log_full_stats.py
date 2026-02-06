import json

from lib import outcome_log


def _write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def test_get_outcome_stats_full_scan_not_capped(tmp_path, monkeypatch):
    outcomes_file = tmp_path / "outcomes.jsonl"
    links_file = tmp_path / "outcome_links.jsonl"

    outcomes = []
    for i in range(1505):
        outcomes.append(
            {
                "outcome_id": f"o{i}",
                "polarity": "pos" if i % 2 == 0 else "neg",
                "created_at": float(i),
            }
        )
    links = []
    for i in range(1203):
        links.append(
            {
                "link_id": f"l{i}",
                "outcome_id": f"o{i}",
                "validated": i % 2 == 0,
                "created_at": float(i),
            }
        )

    _write_jsonl(outcomes_file, outcomes)
    _write_jsonl(links_file, links)
    monkeypatch.setattr(outcome_log, "OUTCOMES_FILE", outcomes_file)
    monkeypatch.setattr(outcome_log, "OUTCOME_LINKS_FILE", links_file)

    stats = outcome_log.get_outcome_stats()
    assert stats["total_outcomes"] == 1505
    assert stats["total_links"] == 1203
    assert stats["validated_links"] == 602
    assert stats["unlinked"] == 302
    assert stats["by_polarity"]["pos"] == 753
    assert stats["by_polarity"]["neg"] == 752


def test_read_and_link_limits_support_none(tmp_path, monkeypatch):
    outcomes_file = tmp_path / "outcomes.jsonl"
    links_file = tmp_path / "outcome_links.jsonl"

    _write_jsonl(
        outcomes_file,
        [{"outcome_id": f"o{i}", "polarity": "neutral", "created_at": float(i)} for i in range(25)],
    )
    _write_jsonl(
        links_file,
        [{"link_id": f"l{i}", "outcome_id": f"o{i}", "validated": False} for i in range(12)],
    )
    monkeypatch.setattr(outcome_log, "OUTCOMES_FILE", outcomes_file)
    monkeypatch.setattr(outcome_log, "OUTCOME_LINKS_FILE", links_file)

    assert len(outcome_log.read_outcomes(limit=None)) == 25
    assert len(outcome_log.read_outcomes(limit=10)) == 10
    assert len(outcome_log.get_outcome_links(limit=None)) == 12
    assert len(outcome_log.get_outcome_links(limit=5)) == 5
