"""GIPHY API client for animated Shorts reaction assets."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
}


def fetch_giphy_items(
    query: str,
    *,
    api_key: str,
    limit: int = 8,
    kind: str = "gifs",
) -> list[dict]:
    """Search GIPHY GIFs or stickers and return raw item payloads."""

    if not api_key:
        raise RuntimeError("GIPHY_API_KEY is required for GIPHY asset search")
    search_kind = "stickers" if kind == "stickers" else "gifs"
    safe_query = _compact_query(query)
    try:
        payload = _search(search_kind, safe_query, api_key=api_key, limit=limit)
    except HTTPError as exc:
        if exc.code != 414:
            raise
        payload = _search(search_kind, "anime girl reaction", api_key=api_key, limit=limit)
    return list(payload.get("data") or [])


def download_giphy_asset(item: dict, out_dir: Path) -> Path:
    """Download best available animated rendition for a GIPHY item."""

    url = _best_giphy_image_url(item)
    if not url:
        raise RuntimeError("GIPHY item has no downloadable image URL")
    request = Request(url, headers=DEFAULT_HEADERS)
    with urlopen(request, timeout=30.0) as response:
        content = response.read()
    out_dir.mkdir(parents=True, exist_ok=True)
    item_id = _safe_id(str(item.get("id") or "asset"))
    extension = _extension_from_url(url)
    out_path = out_dir / f"giphy_{item_id}{extension}"
    out_path.write_bytes(content)
    return out_path


def _best_giphy_image_url(item: dict) -> str:
    images = item.get("images") or {}
    for key in ("fixed_height", "fixed_width", "downsized_small", "original"):
        image = images.get(key) or {}
        url = image.get("mp4")
        if url:
            return str(url)
    for key in ("downsized", "fixed_height", "fixed_width", "original"):
        image = images.get(key) or {}
        url = image.get("url") or image.get("webp")
        if url:
            return str(url)
    return ""


def _extension_from_url(url: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in {".gif", ".webp", ".mp4", ".jpg", ".jpeg", ".png"}:
        return suffix
    return ".gif"


def _safe_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_") or "asset"


def _search(search_kind: str, query: str, *, api_key: str, limit: int) -> dict:
    params = urlencode(
        {
            "api_key": api_key,
            "q": query,
            "limit": max(1, min(limit, 25)),
            "rating": "pg-13",
            "lang": "en",
        }
    )
    request = Request(f"https://api.giphy.com/v1/{search_kind}/search?{params}", headers=DEFAULT_HEADERS)
    with urlopen(request, timeout=20.0) as response:
        return json.loads(response.read().decode("utf-8"))


def _compact_query(query: str, *, max_chars: int = 45) -> str:
    words = re.findall(r"[a-zA-Z0-9]+", query.lower())
    keep: list[str] = []
    seen: set[str] = set()
    for word in words:
        if len(word) <= 2 or word in seen:
            continue
        seen.add(word)
        keep.append(word)
        if len(" ".join(keep)) >= max_chars:
            break
    compact = " ".join(keep).strip()
    if not compact:
        return "anime girl reaction"
    return compact[:max_chars].rstrip()
