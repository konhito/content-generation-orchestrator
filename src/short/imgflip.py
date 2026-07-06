"""Imgflip API client for Shorts meme assets."""

from __future__ import annotations

import re
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .meme_provider import get_imgflip_credentials

ALIASES = {
    "disaster": {"disaster", "girl"},
    "choice": {"drake", "buttons", "choice"},
    "surprised": {"surprised", "pikachu", "shock", "shocked"},
    "success": {"success", "kid", "win"},
}

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
}


def fetch_templates() -> list[dict]:
    request = Request("https://api.imgflip.com/get_memes", headers=DEFAULT_HEADERS)
    with urlopen(request, timeout=20.0) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not data.get("success"):
        raise RuntimeError("Imgflip template request failed")
    return data.get("data", {}).get("memes", [])


def select_template(templates: list[dict], hint: str = "", text: str = "", offset: int = 0) -> dict:
    if not templates:
        raise RuntimeError("Imgflip returned no meme templates")
    terms = set(re.findall(r"[a-z0-9]+", f"{hint} {text}".lower()))
    for key, aliases in ALIASES.items():
        if key in terms:
            terms.update(aliases)
    scored = []
    for index, template in enumerate(templates):
        name_terms = set(re.findall(r"[a-z0-9]+", str(template.get("name", "")).lower()))
        scored.append((len(terms & name_terms), -index, template))
    ranked = sorted(scored, key=lambda row: (row[0], row[1]), reverse=True)
    matching = [row for row in ranked if row[0] > 0] or ranked
    return matching[offset % len(matching)][2]


def create_meme(
    template_id: str,
    text_top: str,
    text_bottom: str,
    out_dir: Path,
    *,
    username: str | None = None,
    password: str | None = None,
) -> Path:
    username, password = (username, password) if username is not None else get_imgflip_credentials()
    if not username or not password:
        raise RuntimeError(
            "IMGFLIP_USERNAME and IMGFLIP_PASSWORD are required for Imgflip meme generation. "
            "Set the real Imgflip account username and password in .env or environment variables."
        )

    payload_data = urlencode(
        {
            "template_id": template_id,
            "username": username,
            "password": password,
            "text0": text_top,
            "text1": text_bottom,
        }
    ).encode("utf-8")
    request = Request(
        "https://api.imgflip.com/caption_image",
        data=payload_data,
        headers={**DEFAULT_HEADERS, "Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request, timeout=30.0) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not payload.get("success"):
        error_message = str(payload.get("error_message", "unknown error"))
        raise RuntimeError(
            "Imgflip caption failed: "
            f"{error_message}. "
            "Check that IMGFLIP_USERNAME is the Imgflip account username, not an email, "
            "and that IMGFLIP_PASSWORD matches that account."
        )

    image_url = payload["data"]["url"]
    image_request = Request(image_url, headers=DEFAULT_HEADERS)
    with urlopen(image_request, timeout=30.0) as image:
        image_bytes = image.read()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"imgflip_{template_id}_{len(list(out_dir.glob('imgflip_*')))}.jpg"
    out_path.write_bytes(image_bytes)
    return out_path
