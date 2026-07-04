"""Shorts niche intelligence ported from the verticals pipeline.

Profiles live in ``niches/*.yaml`` at the repo root. They shape script prompts,
voice selection, captions, music mood, editing pace, and meme density.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

NICHES_DIR = Path(__file__).resolve().parents[2] / "niches"
_cache: dict[str, dict] = {}


def load_niche(name: str = "general") -> dict:
    """Load a niche YAML profile, falling back to ``general``."""

    requested = (name or "general").strip().lower()
    if requested in _cache:
        return _cache[requested]

    path = NICHES_DIR / f"{requested}.yaml"
    if not path.exists():
        if requested != "general":
            return load_niche("general")
        return _minimal_profile(requested)

    try:
        profile = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        profile = _minimal_profile(requested)
    profile.setdefault("name", requested)
    _cache[requested] = profile
    return profile


def list_niches() -> list[str]:
    if not NICHES_DIR.exists():
        return ["general"]
    names = sorted(path.stem for path in NICHES_DIR.glob("*.yaml"))
    return names or ["general"]


def get_script_context(profile: dict) -> str:
    """Build the full script prompt context from a niche profile."""

    script = profile.get("script", {}) or {}
    parts: list[str] = []
    parts.append(f"NICHE: {profile.get('display_name', profile.get('name', 'General'))}")
    if script.get("tone"):
        parts.append(f"TONE: {script['tone']}")
    if script.get("pacing"):
        parts.append(f"PACING: {script['pacing']}")
    if script.get("perspective"):
        parts.append(f"PERSPECTIVE: {script['perspective']}")
    if script.get("word_count"):
        parts.append(f"TARGET WORD COUNT: {script['word_count']}")
    if script.get("sentence_style"):
        parts.append(f"SENTENCE STYLE: {script['sentence_style']}")

    hooks = script.get("hooks", []) or []
    if hooks:
        parts.append("HOOK PATTERNS (pick the most appropriate for this topic):")
        for hook in hooks:
            template = hook.get("template", "")
            if not template:
                continue
            line = f"  {hook.get('id', 'hook')}: \"{template}\""
            if hook.get("when"):
                line += f" (use when: {hook['when']})"
            parts.append(line)

    structure = script.get("structure", {}) or {}
    if structure:
        parts.append("SCRIPT STRUCTURE:")
        for key in ("opening", "middle", "closing"):
            if structure.get(key):
                parts.append(f"  {key.title()}: {structure[key]}")

    ctas = script.get("cta_variants", []) or []
    if ctas:
        parts.append(f"CTA OPTIONS (pick one): {', '.join(ctas)}")

    forbidden = script.get("forbidden_phrases", []) or script.get("forbidden", []) or []
    if forbidden:
        parts.append(f"NEVER USE: {', '.join(forbidden)}")

    return "\n".join(parts)


def get_visual_context(profile: dict) -> dict:
    return profile.get("visuals", {}) or {}


def get_voice_config(profile: dict, provider: str = "edge", lang: str = "en") -> dict:
    provider_key = {"edge": "edge_tts"}.get((provider or "edge").lower(), provider)
    voice = profile.get("voice", {}) or {}
    suggested = voice.get("suggested_voices", {}) or {}
    config = {
        "pace": voice.get("pace", ""),
        "energy": voice.get("energy", ""),
        "style": voice.get("style", ""),
    }
    provider_voices = suggested.get(provider_key, {})
    if isinstance(provider_voices, dict):
        config["voice_id"] = provider_voices.get(lang, provider_voices.get("en", ""))
        if provider_key in ("elevenlabs", "60db"):
            config["voice_id"] = provider_voices.get("voice_id", "")
            config["settings"] = provider_voices.get("settings", {})
    elif isinstance(provider_voices, str):
        config["voice_id"] = provider_voices
    return config


def get_caption_config(profile: dict) -> dict:
    defaults = {
        "highlight_color": "#FFFF00",
        "text_color": "#FFFFFF",
        "font_family": "Arial",
        "font_size": 72,
        "font_weight": "bold",
        "position": "lower_third",
        "background": "semi_transparent_dark",
        "words_per_group": 4,
    }
    defaults.update(profile.get("captions", {}) or {})
    return defaults


def get_editing_config(profile: dict) -> dict:
    defaults = {
        "style": "balanced",
        "cut_duration_seconds": [3, 6],
        "meme_beats": [1, 3],
        "effects": ["pan", "punch_zoom", "hard_cut", "shake"],
        "component_density": "high",
    }
    raw = {**defaults, **(profile.get("editing", {}) or {})}
    if os.environ.get("MCP_MEME_TEMPLATE_ID"):
        raw["meme_template_id"] = os.environ["MCP_MEME_TEMPLATE_ID"]
    return raw


def _minimal_profile(name: str) -> dict:
    return {
        "name": name,
        "display_name": name.title(),
        "script": {
            "tone": "clear, engaging, conversational",
            "pacing": "fast, no filler",
            "word_count": "130 to 150",
        },
        "visuals": {"style": "clean Remotion components, high contrast"},
        "voice": {},
        "captions": {},
        "editing": {},
    }
