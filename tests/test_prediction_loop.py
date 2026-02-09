import json

from lib import prediction_loop as pl


def _read_jsonl(path):
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def test_build_predictions_applies_source_budgets(tmp_path, monkeypatch):
    pred_file = tmp_path / "predictions.jsonl"
    monkeypatch.setattr(pl, "PREDICTIONS_FILE", pred_file)

    exposures = []
    for i in range(6):
        exposures.append({"insight_key": f"k-chip-{i}", "text": f"chip insight {i}", "source": "chip_merge"})
    for i in range(4):
        exposures.append({"insight_key": f"k-sync-{i}", "text": f"sync insight {i}", "source": "sync_context"})
    for i in range(4):
        exposures.append({"insight_key": f"k-inj-{i}", "text": f"inject insight {i}", "source": "spark_inject"})

    monkeypatch.setattr(pl, "read_recent_exposures", lambda **_kwargs: exposures)
    monkeypatch.setattr(pl, "get_cognitive_learner", lambda: object())
    monkeypatch.setenv("SPARK_PREDICTION_TOTAL_BUDGET", "20")
    monkeypatch.setenv("SPARK_PREDICTION_DEFAULT_SOURCE_BUDGET", "10")
    monkeypatch.setenv(
        "SPARK_PREDICTION_SOURCE_BUDGETS",
        "chip_merge=2,sync_context=2,spark_inject=2",
    )

    built = pl.build_predictions()
    rows = _read_jsonl(pred_file)
    by_source = {}
    for row in rows:
        source = row.get("source")
        by_source[source] = by_source.get(source, 0) + 1

    assert built == 6
    assert sum(by_source.values()) == 6
    assert by_source.get("chip_merge", 0) <= 2
    assert by_source.get("sync_context", 0) <= 2
    assert by_source.get("spark_inject", 0) <= 2
