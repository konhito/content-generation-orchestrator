"""Resolve structured meme moments into local Imgflip assets."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Callable

from .giphy import download_giphy_asset, fetch_giphy_items
from .imgflip import create_meme, fetch_templates, select_template
from .meme_provider import get_giphy_api_key, get_imgflip_credentials


def resolve_meme_assets(
    memes: list[dict],
    out_dir: Path,
    *,
    public_root: Path | None = None,
    provider: str = "imgflip",
    logger: Callable[[str], None] | None = None,
) -> list[dict]:
    """Attach local meme image paths and Imgflip metadata to meme plan items."""

    result = deepcopy(memes)
    log = logger or (lambda _message: None)
    if provider == "mock":
        log(f"meme assets skipped provider={provider}")
        for item in result:
            item["provider"] = provider
        return result

    if provider == "giphy":
        return _resolve_giphy_assets(result, out_dir, public_root=public_root, logger=log)

    if provider == "mixed":
        resolved: list[dict] = []
        for index, item in enumerate(result):
            resolver = _resolve_imgflip_assets if index % 2 == 0 else _resolve_giphy_assets
            resolved.extend(resolver([item], out_dir, public_root=public_root, logger=log))
        return resolved

    if provider != "imgflip":
        raise RuntimeError(f"Unsupported meme provider: {provider}")

    return _resolve_imgflip_assets(result, out_dir, public_root=public_root, logger=log)


def _resolve_imgflip_assets(
    result: list[dict],
    out_dir: Path,
    *,
    public_root: Path | None,
    logger: Callable[[str], None],
) -> list[dict]:

    username, password = get_imgflip_credentials()
    templates = fetch_templates()
    if not templates:
        raise RuntimeError("No meme templates available from Imgflip")

    out_dir.mkdir(parents=True, exist_ok=True)
    seen: set[tuple[str, str]] = set()
    for index, item in enumerate(result):
        if item.get("type") != "meme":
            continue
        top = str(item.get("meme_text_top", "")).strip()
        bottom = str(item.get("meme_text_bottom", "")).strip()
        hint = str(item.get("template_hint", ""))
        query = str(item.get("query", ""))
        template = select_template(templates, hint=hint, text=f"{query} {top} {bottom}", offset=index)
        caption_key = (template.get("id", ""), top.upper(), bottom.upper())
        while caption_key in seen:
            template = select_template(templates, hint=hint, text=f"{query} {top} {bottom}", offset=index + len(seen) + 1)
            caption_key = (template.get("id", ""), top.upper(), bottom.upper())
        image_path = create_meme(
            str(template["id"]),
            top,
            bottom,
            out_dir,
            username=username,
            password=password,
        )
        stored_path = image_path
        if public_root is not None:
            try:
                stored_path = image_path.relative_to(public_root)
            except ValueError:
                stored_path = image_path
        item["provider"] = "imgflip"
        item["meme_template_id"] = str(template["id"])
        item["meme_template_name"] = str(template.get("name", ""))
        item["image_path"] = str(stored_path)
        seen.add(caption_key)
        logger(
            "meme asset[%d] template=%s image=%s"
            % (index, item["meme_template_name"] or item["meme_template_id"], item["image_path"])
        )
    return result


def _resolve_giphy_assets(
    memes: list[dict],
    out_dir: Path,
    *,
    public_root: Path | None,
    logger: Callable[[str], None],
) -> list[dict]:
    api_key = get_giphy_api_key()
    if not api_key:
        raise RuntimeError("GIPHY_API_KEY is required for GIPHY meme assets")

    out_dir.mkdir(parents=True, exist_ok=True)
    for index, item in enumerate(memes):
        if item.get("type") != "meme":
            continue
        query = _giphy_query(item)
        kind = _giphy_kind(item)
        items = fetch_giphy_items(query, api_key=api_key, limit=8, kind=kind)
        if not items and kind == "stickers":
            items = fetch_giphy_items(query, api_key=api_key, limit=8, kind="gifs")
            kind = "gifs"
        if not items:
            raise RuntimeError(f"GIPHY returned no assets for query: {query}")
        selected = _select_giphy_item(items, offset=index)
        image_path = download_giphy_asset(selected, out_dir)
        stored_path = image_path
        if public_root is not None:
            try:
                stored_path = image_path.relative_to(public_root)
            except ValueError:
                stored_path = image_path
        item["provider"] = "giphy"
        item["asset_kind"] = kind
        item["giphy_id"] = str(selected.get("id", ""))
        item["giphy_title"] = str(selected.get("title", ""))
        item["giphy_url"] = str(selected.get("url", ""))
        item["image_path"] = str(stored_path)
        logger("giphy asset[%d] kind=%s title=%s image=%s" % (index, kind, item["giphy_title"], item["image_path"]))
    return memes


def _giphy_query(item: dict) -> str:
    hint = str(item.get("template_hint", "")).lower()
    text = " ".join(
        [
            str(item.get("meme_text_top", "")),
            str(item.get("meme_text_bottom", "")),
            str(item.get("caption", "")),
        ]
    ).lower()
    mood = _anime_reaction_mood(f"{hint} {text}")
    return f"anime girl {mood} reaction" if mood else "anime girl reaction"


def _anime_reaction_mood(text: str) -> str:
    if any(term in text for term in ("shock", "shocked", "surprise", "surprised", "wait", "what", "wrong")):
        return "surprised"
    if any(term in text for term in ("angry", "mad", "rage", "annoyed")):
        return "angry"
    if any(term in text for term in ("cry", "sad", "pain", "worse")):
        return "sad"
    if any(term in text for term in ("happy", "win", "success", "based")):
        return "happy"
    if any(term in text for term in ("confused", "debug", "bug", "error")):
        return "confused"
    return ""


def _giphy_kind(item: dict) -> str:
    text = " ".join(
        [
            str(item.get("query", "")),
            str(item.get("template_hint", "")),
            str(item.get("caption", "")),
        ]
    ).lower()
    if any(term in text for term in ("sticker", "transparent", "emoji")):
        return "stickers"
    return "gifs"


def _select_giphy_item(items: list[dict], *, offset: int) -> dict:
    usable = [item for item in items if (item.get("images") or {})] or items
    anime = [item for item in usable if _is_anime_reaction(item)]
    pool = anime or usable
    return pool[offset % len(pool)]


def _is_anime_reaction(item: dict) -> bool:
    title = str(item.get("title", "")).lower()
    markers = (
        "anime",
        "girl",
        "hidive",
        "crunchyroll",
        "k on",
        "quintuplets",
        "shibuya station",
    )
    return any(marker in title for marker in markers)
