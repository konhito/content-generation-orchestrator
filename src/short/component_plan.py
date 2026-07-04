"""Build Remotion-friendly component plans for high-retention Shorts."""

from __future__ import annotations

from typing import Any

from .meme_provider import get_default_meme_template_id

COMPONENT_ROTATION = [
    "attention_visual",
    "token_grid",
    "patch_grid",
    "masked_grid",
    "embedding_bars",
    "flow_diagram",
    "progress_bars",
    "text_highlight",
]


def build_component_plan(
    beats: list[dict[str, Any]],
    memes: list[dict[str, Any]],
    *,
    duration: float,
    niche: str,
    mode_plan: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Map script beats + memes to clean Remotion visual configs."""

    components: list[dict[str, Any]] = []
    total = max(1, len(beats))
    segment = float(duration) / total if duration else 5.0
    meme_by_slot = _spread_memes(memes, total)
    mode_by_id = {str(item.get("id")): str(item.get("mode", "component")) for item in (mode_plan or [])}
    planned_memes = iter(memes)

    for index, beat in enumerate(beats):
        start = round(index * segment, 3)
        end = round(float(duration), 3) if index == total - 1 else round((index + 1) * segment, 3)
        visual_type = _visual_type_for_beat(beat, index)
        beat_id = beat.get("beat_id", f"beat_{index + 1:03d}")
        beat_mode = mode_by_id.get(str(beat_id), "component")
        visual = _visual_config(visual_type, beat)
        if beat_mode == "meme":
            meme = next(planned_memes, {})
            visual = {
                "type": "meme_card",
                "primary_text": meme.get("meme_text_top", ""),
                "secondary_text": meme.get("meme_text_bottom", meme.get("caption", "")),
                "template_hint": meme.get("template_hint", "surprised"),
                "template_id": meme.get("meme_template_id", get_default_meme_template_id()),
                "query": meme.get("query", ""),
            }
        components.append({
            "id": beat_id,
            "start_seconds": start,
            "end_seconds": end,
            "mode": beat_mode,
            "caption_text": beat.get("script_text", ""),
            "intent": beat.get("intent", "context"),
            "visual": visual,
            "effect": _effect_for_index(index),
        })
        if mode_plan is None and index in meme_by_slot:
            meme = meme_by_slot[index]
            components.append({
                "id": f"meme_{index + 1:03d}",
                "start_seconds": round(max(start, end - min(2.4, (end - start) * 0.55)), 3),
                "end_seconds": end,
                "caption_text": meme.get("meme_text_bottom", meme.get("caption", "")),
                "intent": "meme",
                "visual": {
                    "type": "meme_card",
                    "primary_text": meme.get("meme_text_top", ""),
                    "secondary_text": meme.get("meme_text_bottom", ""),
                    "template_hint": meme.get("template_hint", "surprised"),
                    "template_id": meme.get("meme_template_id", get_default_meme_template_id()),
                    "query": meme.get("query", ""),
                },
                "effect": "punch_zoom",
            })

    return {
        "niche": niche,
        "duration_seconds": duration,
        "components": components,
        "component_types": sorted({item["visual"]["type"] for item in components}),
    }


def _spread_memes(memes: list[dict[str, Any]], slots: int) -> dict[int, dict[str, Any]]:
    result = {}
    if not memes or slots <= 0:
        return result
    if len(memes) == 1:
        result[max(0, slots // 2)] = memes[0]
        return result
    for index, meme in enumerate(memes):
        slot = min(slots - 1, round(index * (slots - 1) / max(1, len(memes) - 1)))
        result[int(slot)] = meme
    return result


def _visual_type_for_beat(beat: dict[str, Any], index: int) -> str:
    text = f"{beat.get('script_text', '')} {' '.join(beat.get('entities', []))}".lower()
    preferred = beat.get("preferred_types", [])
    if "attention_visual" in preferred or "attention" in text or "connect" in text:
        return "attention_visual"
    if "token" in text or "word" in text:
        return "token_grid"
    if "image" in text or "pixel" in text or "patch" in text:
        return "patch_grid"
    if "hidden" in text or "mask" in text or "fake" in text:
        return "masked_grid"
    if "number" in text or any(char.isdigit() for char in text):
        return "big_number"
    return COMPONENT_ROTATION[index % len(COMPONENT_ROTATION)]


def _visual_config(visual_type: str, beat: dict[str, Any]) -> dict[str, Any]:
    entities = beat.get("entities", []) or []
    text = beat.get("script_text", "")
    primary = entities[0] if entities else text[:36]
    if visual_type == "attention_visual":
        return {
            "type": "attention_visual",
            "primary_text": primary,
            "scene_config": {"component_type": "attention_visual", "size": 6, "pattern": "causal"},
        }
    if visual_type == "token_grid":
        return {
            "type": "token_grid",
            "primary_text": primary,
            "scene_config": {
                "component_type": "token_grid",
                "tokens": entities[:12],
                "mode": "prefill",
                "rows": 4,
                "cols": 4,
            },
        }
    if visual_type == "patch_grid":
        return {
            "type": "patch_grid",
            "primary_text": primary,
            "scene_config": {"component_type": "patch_grid", "rows": 7, "cols": 7, "highlight_indices": [3, 10, 22, 31]},
        }
    if visual_type == "masked_grid":
        return {
            "type": "masked_grid",
            "primary_text": primary,
            "scene_config": {"component_type": "masked_grid", "rows": 5, "cols": 5, "masked_indices": [2, 6, 13, 19]},
        }
    if visual_type == "embedding_bars":
        return {
            "type": "embedding_bars",
            "primary_text": primary,
            "scene_config": {"component_type": "embedding_bars", "dimensions": 12},
        }
    if visual_type == "progress_bars":
        return {
            "type": "progress_bars",
            "primary_text": primary,
            "scene_config": {
                "component_type": "progress_bars",
                "bars": [
                    {"label": "Attention", "value": 0.82},
                    {"label": "Curiosity", "value": 0.94},
                    {"label": "Clarity", "value": 0.76},
                ],
            },
        }
    if visual_type == "flow_diagram":
        parts = (entities + ["Signal", "Prediction", "Check"])[:3]
        return {
            "type": "flow_diagram",
            "primary_text": parts[0],
            "secondary_text": parts[1] if len(parts) > 1 else "",
            "tertiary_text": parts[2] if len(parts) > 2 else "",
        }
    if visual_type == "big_number":
        return {"type": "big_number", "primary_text": _first_number(text) or "45-55s", "secondary_text": primary}
    return {"type": "text_highlight", "primary_text": primary, "secondary_text": text[:72]}


def _effect_for_index(index: int) -> str:
    return ["hard_cut", "punch_zoom", "pan", "shake", "zoom_in"][index % 5]


def _first_number(text: str) -> str:
    for token in text.split():
        if any(char.isdigit() for char in token):
            return token.strip(".,!?")
    return ""
