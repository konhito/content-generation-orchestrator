"""Imgflip meme provider configuration for Shorts."""

from __future__ import annotations

import os
import re

ALIASES = {
    "disaster": {"disaster", "girl"},
    "choice": {"drake", "buttons", "choice"},
    "surprised": {"surprised", "pikachu", "shock", "shocked"},
    "success": {"success", "kid", "win"},
}


def get_imgflip_credentials() -> tuple[str, str]:
    return os.getenv("IMGFLIP_USERNAME", ""), os.getenv("IMGFLIP_PASSWORD", "")


def get_default_meme_template_id() -> str:
    return os.getenv("MCP_MEME_TEMPLATE_ID", "")


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
