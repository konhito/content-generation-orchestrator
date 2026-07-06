import httpx

from src.short.research_aggregator import (
    ResearchAggregator,
    ResearchItem,
    _scrape_web_page,
    parse_ddg_results,
)


def test_parse_ddg_results_extracts_redirect_url():
    html = """
    <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fai">AI report</a>
    <a class="result__snippet">A sourced AI report.</a>
    """

    results = parse_ddg_results(html, limit=3)

    assert results == [
        {
            "title": "AI report",
            "url": "https://example.com/ai",
            "snippet": "A sourced AI report.",
        }
    ]


def test_gather_deduplicates_and_ranks_across_sources(monkeypatch):
    aggregator = ResearchAggregator("AI coding", niche="tech")
    duplicate = ResearchItem("reddit", "AI coding report", score=0.4, url="https://example.com/report")
    stronger = ResearchItem("web", "AI coding report", score=0.9, url="https://example.com/report")
    trend = ResearchItem("pytrends", "AI coding tools", score=0.8)
    monkeypatch.setattr(aggregator, "fetch_reddit", lambda limit: [duplicate])
    monkeypatch.setattr(aggregator, "fetch_rss", lambda limit: [])
    monkeypatch.setattr(aggregator, "fetch_duckduckgo", lambda limit: [])
    monkeypatch.setattr(aggregator, "fetch_web_pages", lambda limit: [stronger])
    monkeypatch.setattr(aggregator, "fetch_pytrends", lambda limit: [trend])

    items = aggregator.gather(limit=8)

    assert [item.source for item in items] == ["web", "pytrends"]


def test_gather_logs_source_failure_and_keeps_other_results(monkeypatch):
    messages = []
    aggregator = ResearchAggregator("AI coding", logger=messages.append)
    monkeypatch.setattr(aggregator, "fetch_reddit", lambda limit: (_ for _ in ()).throw(RuntimeError("blocked")))
    monkeypatch.setattr(aggregator, "fetch_rss", lambda limit: [])
    monkeypatch.setattr(aggregator, "fetch_duckduckgo", lambda limit: [ResearchItem("duckduckgo", "Result", score=1)])
    monkeypatch.setattr(aggregator, "fetch_web_pages", lambda limit: [])
    monkeypatch.setattr(aggregator, "fetch_pytrends", lambda limit: [])

    items = aggregator.gather(limit=8)

    assert [item.title for item in items] == ["Result"]
    assert any("reddit" in message and "blocked" in message for message in messages)


def test_scrape_web_page_prefers_utf8_over_incorrect_charset(monkeypatch):
    response = httpx.Response(
        200,
        headers={"content-type": "text/html; charset=iso-8859-1"},
        content="<title>Developer’s reality</title><p>Coding isn’t only typing.</p>".encode(),
        request=httpx.Request("GET", "https://example.com/article"),
    )
    monkeypatch.setattr("src.short.research_aggregator.httpx.get", lambda *args, **kwargs: response)

    item = _scrape_web_page(
        {"title": "Fallback", "url": "https://example.com/article", "snippet": ""},
        "developer reality",
    )

    assert item.title == "Developer’s reality"
    assert "isn’t" in item.snippet
