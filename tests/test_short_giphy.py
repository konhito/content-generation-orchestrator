import json
from urllib.error import HTTPError

import src.short.giphy as giphy
from src.short.meme_provider import get_giphy_api_key, select_meme_asset_provider


def test_get_giphy_api_key_reads_env(monkeypatch):
    monkeypatch.setattr("src.short.meme_provider.load_dotenv", lambda: None)
    monkeypatch.setenv("GIPHY_API_KEY", "test-key")
    monkeypatch.delenv("IMGFLIP_USERNAME", raising=False)
    monkeypatch.delenv("IMGFLIP_PASSWORD", raising=False)

    assert get_giphy_api_key() == "test-key"
    assert select_meme_asset_provider(mock=False) == "giphy"


def test_select_meme_provider_uses_both_when_both_are_configured(monkeypatch):
    monkeypatch.setattr("src.short.meme_provider.load_dotenv", lambda: None)
    monkeypatch.setenv("GIPHY_API_KEY", "test-key")
    monkeypatch.setenv("IMGFLIP_USERNAME", "user")
    monkeypatch.setenv("IMGFLIP_PASSWORD", "pass")

    assert select_meme_asset_provider(mock=False) == "mixed"


def test_fetch_giphy_items_searches_gifs_with_api_key(monkeypatch):
    class Response:
        def read(self):
            return json.dumps({"data": [{"id": "abc", "title": "Anime girl coding"}]}).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    calls = []

    def fake_urlopen(request, timeout=0):
        calls.append((request.full_url, timeout))
        return Response()

    monkeypatch.setattr(giphy, "urlopen", fake_urlopen)

    items = giphy.fetch_giphy_items("reality of coding", api_key="key", limit=5)

    assert items[0]["id"] == "abc"
    assert "api_key=key" in calls[0][0]
    assert "q=reality+coding" in calls[0][0]
    assert "/v1/gifs/search" in calls[0][0]


def test_fetch_giphy_items_caps_long_queries(monkeypatch):
    class Response:
        def read(self):
            return json.dumps({"data": []}).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    calls = []

    def fake_urlopen(request, timeout=0):
        calls.append(request.full_url)
        return Response()

    monkeypatch.setattr(giphy, "urlopen", fake_urlopen)

    giphy.fetch_giphy_items("confidently wrong " * 80, api_key="key", limit=5)

    assert len(calls[0]) < 350


def test_fetch_giphy_items_retries_414_with_short_fallback(monkeypatch):
    class Response:
        def read(self):
            return json.dumps({"data": [{"id": "fallback"}]}).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    calls = []

    def fake_urlopen(request, timeout=0):
        calls.append(request.full_url)
        if len(calls) == 1:
            raise HTTPError(request.full_url, 414, "URI Too Long", hdrs=None, fp=None)
        return Response()

    monkeypatch.setattr(giphy, "urlopen", fake_urlopen)

    items = giphy.fetch_giphy_items("confidently wrong real story signal versus noise", api_key="key", limit=5)

    assert items[0]["id"] == "fallback"
    assert "q=anime+girl+reaction" in calls[1]


def test_download_giphy_asset_prefers_mp4_for_speed_control(tmp_path, monkeypatch):
    item = {
        "id": "gif123",
        "title": "Anime coding reaction",
        "url": "https://giphy.com/gifs/gif123",
        "images": {
            "fixed_height": {"mp4": "https://media.giphy.com/media/gif123/height.mp4"},
            "downsized": {"url": "https://media.giphy.com/media/gif123/giphy.gif"},
            "original": {"url": "https://media.giphy.com/media/gif123/original.gif"},
        },
    }

    class Response:
        def read(self):
            return b"mp4-bytes"

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(giphy, "urlopen", lambda request, timeout=0: Response())

    path = giphy.download_giphy_asset(item, tmp_path)

    assert path.name == "giphy_gif123.mp4"
    assert path.read_bytes() == b"mp4-bytes"
