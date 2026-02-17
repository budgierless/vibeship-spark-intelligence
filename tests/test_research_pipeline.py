from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from lib.research import intents, mastery, spark_research, web_research


def test_process_research_results_forwards_purpose_to_mastery_and_web(monkeypatch):
    captures: dict[str, str] = {}

    class _FakeWebResearcher:
        def research_domain_sync(self, domain, results, purpose="best_practices"):
            captures["web_purpose"] = purpose
            return SimpleNamespace(
                best_practices=["bp"],
                anti_patterns=["ap"],
                expert_insights=["ei"],
                common_mistakes=["cm"],
                total_sources=1,
            )

    class _FakeMasteryResearcher:
        def research_online(self, domain, results, purpose="best_practices"):
            captures["mastery_purpose"] = purpose
            return SimpleNamespace(markers=[], core_principles=[])

    monkeypatch.setattr(spark_research, "get_web_researcher", lambda: _FakeWebResearcher())
    monkeypatch.setattr(spark_research, "get_researcher", lambda: _FakeMasteryResearcher())

    out = spark_research.process_research_results(
        "api_design",
        [{"title": "x", "snippet": "y", "url": "https://example.com"}],
        purpose="anti_patterns",
    )

    assert out["purpose"] == "anti_patterns"
    assert captures["web_purpose"] == "anti_patterns"
    assert captures["mastery_purpose"] == "anti_patterns"


def test_mastery_research_online_forwards_purpose(monkeypatch, tmp_path):
    monkeypatch.setattr(mastery, "MASTERY_CACHE", tmp_path / "mastery")
    captures: dict[str, str] = {}

    class _FakeWebResearcher:
        def research_domain_sync(self, domain, search_results, purpose="best_practices"):
            captures["purpose"] = purpose
            return web_research.DomainResearch(domain=domain, best_practices=["Use tests."])

        def merge_into_mastery(self, research):
            return {
                "markers": [],
                "core_principles": ["Use tests."],
                "common_mistakes": ["Skip tests."],
                "expert_insights": ["Measure before tuning."],
                "sources": ["https://example.com"],
            }

    monkeypatch.setattr(
        web_research,
        "get_web_researcher",
        lambda: _FakeWebResearcher(),
    )

    researcher = mastery.MasteryResearcher()
    updated = researcher.research_online(
        "ai/safety:ops*",
        [{"title": "t", "snippet": "s", "url": "https://example.com"}],
        purpose="expert_insights",
    )

    assert captures["purpose"] == "expert_insights"
    assert "Use tests." in updated.core_principles


def test_web_research_unique_preserve_order_is_deterministic():
    values = [
        " Keep logs ",
        "keep logs",
        "Measure outcomes",
        "keep   logs",
        "MEASURE outcomes",
    ]
    out = web_research._unique_preserve_order(values, limit=10)
    assert out == ["Keep logs", "Measure outcomes"]


def test_intents_unique_preserve_order_is_deterministic():
    values = ["Speed", "speed", "Safety", "  safety  ", "Speed"]
    out = intents._unique_preserve_order(values, limit=10)
    assert out == ["Speed", "Safety"]


def test_web_research_save_uses_safe_cache_key(monkeypatch, tmp_path):
    monkeypatch.setattr(web_research, "RESEARCH_CACHE", tmp_path / "web_cache")
    researcher = web_research.WebResearcher()
    domain = "AI/Agent:Safety*"
    researcher._save_research(web_research.DomainResearch(domain=domain))

    expected = (tmp_path / "web_cache" / f"{web_research._safe_cache_key(domain)}.json")
    assert expected.exists()


def test_mastery_save_uses_safe_cache_key(monkeypatch, tmp_path):
    monkeypatch.setattr(mastery, "MASTERY_CACHE", tmp_path / "mastery_cache")
    researcher = mastery.MasteryResearcher()
    domain = "ML/Ops:Prod*"
    researcher._save_mastery(mastery.DomainMastery(domain=domain, description="x"))

    expected = (tmp_path / "mastery_cache" / f"{mastery._safe_cache_key(domain)}.json")
    assert expected.exists()


def test_generate_queries_uses_current_year_for_best_practices():
    researcher = web_research.WebResearcher()
    now_year = str(datetime.now().year)
    queries = researcher.generate_queries("python", purposes=["best_practices"])
    text = [q.query for q in queries]
    assert any(now_year in q for q in text)
    assert all("2025" not in q for q in text)
