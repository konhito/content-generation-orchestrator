import json

import src.short.imgflip as imgflip
from src.short.meme_provider import validate_imgflip_credentials


def test_select_template_prefers_matching_template_name():
    templates = [
        {"id": "1", "name": "Distracted Boyfriend"},
        {"id": "2", "name": "Drake Hotline Bling"},
        {"id": "3", "name": "Surprised Pikachu"},
    ]

    selected = imgflip.select_template(templates, hint="drake", text="choice", offset=0)

    assert selected["id"] == "2"


def test_create_meme_downloads_image(tmp_path, monkeypatch):
    class Response:
        def __init__(self, payload=None, content=b""):
            self._payload = payload or {}
            self._content = content

        def read(self):
            if self._content:
                return self._content
            return json.dumps(self._payload).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    calls = []

    def fake_urlopen(request, timeout=0):
        url = getattr(request, "full_url", request)
        headers = getattr(request, "headers", {})
        calls.append(("get", url, timeout))
        if url.endswith("get_memes"):
            assert headers.get("User-agent") or headers.get("User-Agent")
            return Response({"success": True, "data": {"memes": []}})
        if url.endswith("caption_image"):
            assert headers.get("User-agent") or headers.get("User-Agent")
            return Response({"success": True, "data": {"url": "https://imgflip.example/test.jpg"}})
        if url.endswith("test.jpg"):
            assert headers.get("User-agent") or headers.get("User-Agent")
            return Response(content=b"jpg-bytes")
        return Response({"success": True, "data": {"url": "https://imgflip.example/test.jpg"}})

    monkeypatch.setattr(imgflip, "urlopen", fake_urlopen)

    out_path = imgflip.create_meme(
        "123",
        "HELLO",
        "WORLD",
        tmp_path,
        username="user",
        password="pass",
    )

    assert out_path.exists()
    assert out_path.read_bytes() == b"jpg-bytes"
    assert out_path.name.startswith("imgflip_123_")
    assert any(call[0] == "get" for call in calls)


def test_create_meme_surfaces_actionable_auth_error(tmp_path, monkeypatch):
    class Response:
        def __init__(self, payload=None):
            self._payload = payload or {}

        def read(self):
            return json.dumps(self._payload).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(request, timeout=0):
        return Response({"success": False, "error_message": "Invalid username/password combination"})

    monkeypatch.setattr(imgflip, "urlopen", fake_urlopen)

    try:
        imgflip.create_meme("123", "HELLO", "WORLD", tmp_path, username="bad", password="bad")
    except RuntimeError as exc:
        message = str(exc)
        assert "Check that IMGFLIP_USERNAME is the Imgflip account username" in message
    else:
        raise AssertionError("Expected Imgflip auth error")


def test_validate_imgflip_credentials_reports_missing_env(monkeypatch):
    monkeypatch.setattr("src.short.meme_provider.load_dotenv", lambda: None)
    monkeypatch.delenv("IMGFLIP_USERNAME", raising=False)
    monkeypatch.delenv("IMGFLIP_PASSWORD", raising=False)

    result = validate_imgflip_credentials()

    assert result.ok is False
    assert "missing IMGFLIP_USERNAME" in result.message


def test_validate_imgflip_credentials_handles_live_errors(monkeypatch):
    monkeypatch.setattr("src.short.meme_provider.load_dotenv", lambda: None)
    monkeypatch.setattr(
        "src.short.imgflip.fetch_templates",
        lambda: (_ for _ in ()).throw(RuntimeError("HTTP Error 403: Forbidden")),
    )

    monkeypatch.setenv("IMGFLIP_USERNAME", "user")
    monkeypatch.setenv("IMGFLIP_PASSWORD", "pass")

    result = validate_imgflip_credentials(live=True)

    assert result.ok is False
    assert "Imgflip live check failed" in result.message
