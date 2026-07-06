"""Imgflip meme provider configuration for Shorts."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency already present in repo
    load_dotenv = None

ALIASES = {
    "disaster": {"disaster", "girl"},
    "choice": {"drake", "buttons", "choice"},
    "surprised": {"surprised", "pikachu", "shock", "shocked"},
    "success": {"success", "kid", "win"},
}


@dataclass(frozen=True)
class ImgflipValidationResult:
    ok: bool
    message: str


def get_imgflip_credentials() -> tuple[str, str]:
    if load_dotenv is not None:
        load_dotenv()
    return os.getenv("IMGFLIP_USERNAME", ""), os.getenv("IMGFLIP_PASSWORD", "")


def get_giphy_api_key() -> str:
    if load_dotenv is not None:
        load_dotenv()
    return os.getenv("GIPHY_API_KEY", "").strip()


def select_meme_asset_provider(*, mock: bool = False) -> str:
    if mock:
        return "mock"
    username, password = get_imgflip_credentials()
    has_imgflip = bool(username and password)
    has_giphy = bool(get_giphy_api_key())
    if has_giphy and has_imgflip:
        return "mixed"
    if has_giphy:
        return "giphy"
    return "imgflip"


def get_default_meme_template_id() -> str:
    return os.getenv("MCP_MEME_TEMPLATE_ID", "")


def validate_imgflip_credentials(*, live: bool = False) -> ImgflipValidationResult:
    username, password = get_imgflip_credentials()
    if not username or not password:
        return ImgflipValidationResult(
            ok=False,
            message="missing IMGFLIP_USERNAME or IMGFLIP_PASSWORD",
        )
    if not live:
        return ImgflipValidationResult(
            ok=True,
            message="credentials present (set live=True to verify with Imgflip)",
        )

    try:
        from .imgflip import fetch_templates

        templates = fetch_templates()
        if not templates:
            return ImgflipValidationResult(ok=False, message="Imgflip returned no templates")
        return ImgflipValidationResult(
            ok=True,
            message=f"Imgflip templates reachable ({len(templates)} templates)",
        )
    except Exception as exc:
        return ImgflipValidationResult(ok=False, message=f"Imgflip live check failed: {exc}")


def select_template(templates: list[dict], hint: str = "", text: str = "", offset: int = 0) -> dict:
    if not templates:
        raise RuntimeError("No meme templates available")
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
