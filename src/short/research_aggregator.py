"""Concurrent live research for short-first video generation."""

from __future__ import annotations

import concurrent.futures
import html
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any, Callable
from urllib.parse import parse_qs, unquote, urlencode, urlparse

import httpx


_WS_RE = re.compile(r"\s+")
_DEFAULT_SUBREDDITS = {
    "tech": ["technology", "programming", "MachineLearning", "artificial"],
    "gaming": ["gaming", "Games"],
    "finance": ["finance", "investing"],
    "general": ["todayilearned", "OutOfTheLoop"],
}


@dataclass
class ResearchItem:
    source: str
    title: str
    snippet: str = ""
    url: str = ""
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class ResearchAggregator:
    """Gather, deduplicate, and rank lightweight public research sources."""

    def __init__(
        self,
        topic: str,
        niche: str = "general",
        discovery: dict[str, Any] | None = None,
        logger: Callable[[str], None] | None = None,
    ):
        self.topic = topic.strip()
        self.niche = (niche or "general").strip().lower()
        self.discovery = discovery or {}
        self.logger = logger or (lambda _message: None)
        self.query = _extract_keywords(self.topic) or self.topic[:80]
        trends = self.discovery.get("google_trends", {}) or {}
        self.geo = str(trends.get("geo") or "US").strip().upper()
        self.trends_category = trends.get("category", "")

    def gather(self, limit: int = 8) -> list[ResearchItem]:
        sources = {
            "reddit": self.fetch_reddit,
            "rss": self.fetch_rss,
            "duckduckgo": self.fetch_duckduckgo,
            "web": self.fetch_web_pages,
            "pytrends": self.fetch_pytrends,
        }
        results: list[ResearchItem] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(sources)) as pool:
            futures = {pool.submit(fetch, limit): name for name, fetch in sources.items()}
            for future in concurrent.futures.as_completed(futures):
                source = futures[future]
                try:
                    items = future.result()
                    results.extend(items)
                    self.logger(f"Research: {source} -> {len(items)} item(s)")
                except Exception as exc:
                    self.logger(f"Research: {source} failed: {exc}")
        return self._dedupe_and_rank(results)[:limit]

    def fetch_reddit(self, limit: int = 8) -> list[ResearchItem]:
        configured = (self.discovery.get("reddit", {}) or {}).get("subreddits", [])
        subreddits = configured or _DEFAULT_SUBREDDITS.get(self.niche, _DEFAULT_SUBREDDITS["general"])
        per_subreddit = max(1, limit // max(1, len(subreddits)))
        items: list[ResearchItem] = []
        for subreddit in subreddits:
            params = urlencode({"q": self.query, "restrict_sr": 1, "sort": "relevance", "t": "month"})
            url = f"https://old.reddit.com/r/{subreddit}/search.rss?{params}"
            items.extend(self._fetch_rss_url(url, per_subreddit, "reddit", {"subreddit": subreddit}))
        return items[:limit]

    def fetch_rss(self, limit: int = 8) -> list[ResearchItem]:
        feeds = (self.discovery.get("rss", {}) or {}).get("feeds", [])
        if not feeds:
            return []
        per_feed = max(1, limit // len(feeds))
        items: list[ResearchItem] = []
        for url in feeds:
            items.extend(self._fetch_rss_url(str(url), per_feed, "rss", {"feed": str(url)}))
        return items[:limit]

    def _fetch_rss_url(
        self, url: str, limit: int, source: str, metadata: dict[str, Any]
    ) -> list[ResearchItem]:
        response = httpx.get(url, headers=_HEADERS, timeout=12, follow_redirects=True)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        entries = root.findall(".//item") or root.findall("{*}entry")
        items: list[ResearchItem] = []
        for entry in entries[:limit]:
            title = _element_text(entry, "title")
            snippet = _strip_html(
                _element_text(entry, "description")
                or _element_text(entry, "summary")
                or _element_text(entry, "content")
            )
            link = _entry_link(entry)
            if title:
                items.append(
                    ResearchItem(
                        source=source,
                        title=title,
                        snippet=_truncate(snippet, 400),
                        url=link,
                        score=max(0.1, self._text_relevance(f"{title} {snippet}")),
                        metadata=dict(metadata),
                    )
                )
        return items

    def fetch_duckduckgo(self, limit: int = 8) -> list[ResearchItem]:
        results = parse_ddg_results(_fetch_ddg(self.query), limit)
        return [
            ResearchItem(
                source="duckduckgo",
                title=result["title"],
                snippet=_truncate(result["snippet"], 400),
                url=result["url"],
                score=max(0.1, 0.9 - index * 0.05),
                metadata={"query": self.query},
            )
            for index, result in enumerate(results)
        ]

    def fetch_web_pages(self, limit: int = 8) -> list[ResearchItem]:
        results = parse_ddg_results(_fetch_ddg(self.query), min(limit, 10))
        if not results:
            return []
        items: list[ResearchItem] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(6, len(results))) as pool:
            futures = [pool.submit(_scrape_web_page, result, self.query) for result in results]
            for future in concurrent.futures.as_completed(futures):
                try:
                    item = future.result()
                    if item:
                        items.append(item)
                except Exception as exc:
                    self.logger(f"Research: webpage failed: {exc}")
        return sorted(items, key=lambda item: item.score, reverse=True)[:limit]

    def fetch_pytrends(self, limit: int = 8) -> list[ResearchItem]:
        try:
            from pytrends.request import TrendReq
        except ImportError:
            self.logger("Research: pytrends not installed; skipping")
            return []
        try:
            trends = TrendReq(hl="en-US", tz=330)
            category = int(self.trends_category) if str(self.trends_category).isdigit() else 0
            trends.build_payload([self.query], timeframe="now 7-d", geo=self.geo, cat=category)
            related = trends.related_queries() or {}
            query_data = related.get(self.query) or {}
        except Exception as exc:
            self.logger(f"Research: pytrends query failed: {exc}")
            return []
        items: list[ResearchItem] = []
        for section, base_score in (("rising", 0.85), ("top", 0.7)):
            frame = query_data.get(section)
            if frame is None:
                continue
            for index, row in frame.head(limit).iterrows():
                title = str(row.get("query", "")).strip()
                if title:
                    items.append(
                        ResearchItem(
                            "pytrends",
                            title,
                            f"{section}: {row.get('value', '')}",
                            score=max(0.1, base_score - int(index) * 0.04),
                            metadata={"section": section, "geo": self.geo},
                        )
                    )
        return items[:limit]

    def _dedupe_and_rank(self, items: list[ResearchItem]) -> list[ResearchItem]:
        unique: list[ResearchItem] = []
        seen: set[str] = set()
        for item in sorted(items, key=lambda value: value.score, reverse=True):
            key = _normalize_key(item.title, item.url)
            if not key or key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique

    def _text_relevance(self, text: str) -> float:
        tokens = {token for token in re.findall(r"[a-z0-9]+", self.topic.lower()) if len(token) > 2}
        if not tokens:
            return 0.0
        overlap = tokens & set(re.findall(r"[a-z0-9]+", text.lower()))
        return min(1.0, len(overlap) / max(1, min(len(tokens), 6)))


_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; video-explainer-research/1.0)"}


def _fetch_ddg(query: str) -> str:
    response = httpx.post(
        "https://html.duckduckgo.com/html/",
        data={"q": query},
        headers=_HEADERS,
        timeout=12,
        follow_redirects=True,
    )
    response.raise_for_status()
    return _decode_html(response)


def parse_ddg_results(html_text: str, limit: int = 10) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []

    class Parser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.capture = ""
            self.text: list[str] = []
            self.current: dict[str, str] | None = None

        def handle_starttag(self, tag, attrs):
            values = dict(attrs)
            classes = values.get("class", "")
            if tag == "a" and "result__a" in classes:
                self.capture = "title"
                self.text = []
                self.current = {"title": "", "url": _decode_ddg_url(values.get("href", "")), "snippet": ""}
            elif tag == "a" and "result__snippet" in classes and self.current is not None:
                self.capture = "snippet"
                self.text = []

        def handle_endtag(self, tag):
            if tag != "a" or not self.capture:
                return
            value = html.unescape("".join(self.text)).strip()
            if self.current is not None:
                self.current[self.capture] = value
                if self.capture == "snippet" and self.current.get("url"):
                    results.append(self.current)
                    self.current = None
            self.capture = ""
            self.text = []

        def handle_data(self, data):
            if self.capture:
                self.text.append(data)

    Parser().feed(html_text)
    return results[:limit]


def _scrape_web_page(result: dict[str, str], query: str) -> ResearchItem | None:
    response = httpx.get(result["url"], headers=_HEADERS, timeout=15, follow_redirects=True)
    response.raise_for_status()
    page_html = _decode_html(response)
    title_match = re.search(r"<title[^>]*>(.*?)</title>", page_html, re.I | re.S)
    image_match = re.search(
        r'<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\'][^>]+content=["\']([^"\']+)',
        page_html,
        re.I,
    )
    paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", page_html[:2_000_000], re.I | re.S)
    title = _strip_html(title_match.group(1)) if title_match else result.get("title", "")
    snippet = " ".join(_strip_html(paragraph) for paragraph in paragraphs[:5]) or result.get("snippet", "")
    if not title and not snippet:
        return None
    query_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
    text_tokens = set(re.findall(r"[a-z0-9]+", f"{title} {snippet}".lower()))
    relevance = len(query_tokens & text_tokens) / max(1, min(len(query_tokens), 6))
    return ResearchItem(
        "web",
        _truncate(title, 180),
        _truncate(snippet, 1200),
        str(response.url),
        max(0.15, min(1.0, relevance)),
        {"image_url": image_match.group(1) if image_match else "", "query": query},
    )


def _decode_ddg_url(url: str) -> str:
    if url.startswith("//"):
        url = "https:" + url
    redirect = parse_qs(urlparse(url).query).get("uddg", [])
    return unquote(redirect[0]) if redirect else url


def _decode_html(response: httpx.Response) -> str:
    """Web pages commonly mislabel UTF-8 as Latin-1; prefer valid UTF-8 bytes."""
    try:
        return response.content.decode("utf-8")
    except UnicodeDecodeError:
        return response.text


def _element_text(entry: ET.Element, local_name: str) -> str:
    for child in entry.iter():
        if child.tag.rsplit("}", 1)[-1] == local_name:
            return "".join(child.itertext()).strip()
    return ""


def _entry_link(entry: ET.Element) -> str:
    text = _element_text(entry, "link")
    if text:
        return text
    for child in entry.iter():
        if child.tag.rsplit("}", 1)[-1] == "link" and child.attrib.get("href"):
            return child.attrib["href"]
    return ""


def _extract_keywords(topic: str) -> str:
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9+#.-]*", topic)
    return " ".join(words[:12])


def _normalize_key(title: str, url: str) -> str:
    return _WS_RE.sub(" ", f"{title} {url}".lower()).strip()[:240]


def _strip_html(value: str) -> str:
    return _WS_RE.sub(" ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def _truncate(value: str, limit: int) -> str:
    return value.strip()[:limit]
