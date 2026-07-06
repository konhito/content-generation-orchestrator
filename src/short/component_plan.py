"""Build Remotion-friendly component plans for high-retention Shorts."""

from __future__ import annotations

from typing import Any

from .meme_provider import get_default_meme_template_id

ANIMATED_COMPONENT_TYPES = {
    "attention_visual",
    "code_block",
    "diagram",
    "embedding_bars",
    "masked_grid",
    "patch_grid",
    "progress_bars",
    "token_grid",
}

EXPLANATION_TERMS = (
    "compare",
    "comparison",
    "diagram",
    "debug",
    "explain",
    "explains",
    "explaining",
    "flow",
    "how ",
    "how?",
    "mechanism",
    "model",
    "number",
    "pixel",
    "prompt",
    "process",
    "pipeline",
    "step",
    "steps",
    "token",
    "trace",
    "why ",
    "why?",
    "chart",
    "graph",
    "code",
    "bug",
    "error",
)

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
        overlay_type = _overlay_type_for_beat(beat_mode, visual_type, beat)
        if overlay_type == "meme":
            meme = next(planned_memes, {})
            image_path = meme.get("image_path", "")
            visual = {
                "type": "meme_card",
                "primary_text": meme.get("meme_text_top", ""),
                "secondary_text": meme.get("meme_text_bottom", meme.get("caption", "")),
                "template_hint": meme.get("template_hint", "surprised"),
                "template_id": meme.get("meme_template_id", get_default_meme_template_id()),
                "query": meme.get("query", ""),
                "scene_config": {
                    "component_type": "meme_card",
                    "image_path": image_path,
                    "caption": meme.get("caption", meme.get("meme_text_bottom", "")),
                },
            }
        components.append({
            "id": beat_id,
            "start_seconds": start,
            "end_seconds": end,
            "mode": beat_mode,
            "overlay_type": overlay_type,
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
                    "scene_config": {
                        "component_type": "meme_card",
                        "image_path": meme.get("image_path", ""),
                        "caption": meme.get("caption", meme.get("meme_text_bottom", "")),
                    },
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
    script_text = str(beat.get("script_text", "")).lower()
    visual_text = str(beat.get("visual_description", "")).lower()
    preferred = beat.get("preferred_types", []) or []
    if visual_text.endswith("?") or visual_text.startswith(("why ", "how ", "what ", "when ")):
        return "question" if index % 2 == 0 else "text_highlight"
    if script_text.endswith("?") or script_text.startswith(("why ", "how ", "what ", "when ")):
        return "question" if index % 2 == 0 else "text_highlight"
    text = script_text
    if any(term in text for term in ("compare", "compared", "comparison", "instead of", "versus", "tradeoff", "trade-off", " vs ")):
        return "comparison"
    if any(term in text for term in ("bug", "error", "crash", "fail", "broken", "debug", "debugging")):
        return "progress_bars"
    if any(term in text for term in ("token", "prompt")) and any(term in text for term in ("model", "context", "attention")):
        return "token_grid"
    if "attention_visual" in preferred:
        return "attention_visual"
    if any(term in text for term in ("step", "steps", "process", "pipeline", "workflow", "sequence")):
        return "flow_diagram"
    if any(term in text for term in ("image", "pixel", "patch", "vision")):
        return "patch_grid"
    if any(term in text for term in ("hidden", "mask", "masked", "fake")):
        return "masked_grid"
    if "number" in text or any(char.isdigit() for char in text):
        return "big_number"
    return "text_highlight"


def _overlay_type_for_beat(beat_mode: str, visual_type: str, beat: dict[str, Any]) -> str:
    if beat_mode == "meme":
        return "meme"
    if _should_show_explanation_component(beat, visual_type):
        return "component"
    return "none"


def _should_show_explanation_component(beat: dict[str, Any], visual_type: str) -> bool:
    text = " ".join(
        [
            str(beat.get("script_text", "")),
            str(beat.get("visual_description", "")),
            str(beat.get("caption_text", "")),
        ]
    ).lower()
    if visual_type in ANIMATED_COMPONENT_TYPES:
        return True
    return False


def _visual_config(visual_type: str, beat: dict[str, Any]) -> dict[str, Any]:
    entities = beat.get("entities", []) or []
    text = str(beat.get("script_text", "")).strip() or _beat_text(beat)
    primary = _primary_label(beat, text, entities)
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
        parts = _flow_parts(text, entities)
        return {
            "type": "flow_diagram",
            "primary_text": parts[0],
            "secondary_text": parts[1] if len(parts) > 1 else "",
            "tertiary_text": parts[2] if len(parts) > 2 else "",
        }
    if visual_type == "comparison":
        left, right = _comparison_parts(text, entities)
        return {
            "type": "comparison",
            "primary_text": left,
            "secondary_text": right,
            "tertiary_text": _beat_phrase(text, entities[2:3]) if len(entities) > 2 else "",
        }
    if visual_type == "big_number":
        return {"type": "big_number", "primary_text": _first_number(text) or "45-55s", "secondary_text": primary}
    if visual_type == "question":
        return {"type": "question", "primary_text": _question_text(text, primary)}
    return {"type": "text_highlight", "primary_text": primary, "secondary_text": _summary_text(text, primary)}


def _effect_for_index(index: int) -> str:
    return ["hard_cut", "punch_zoom", "pan", "shake", "zoom_in"][index % 5]


def _first_number(text: str) -> str:
    for token in text.split():
        if any(char.isdigit() for char in token):
            return token.strip(".,!?")
    return ""


def _beat_text(beat: dict[str, Any]) -> str:
    visual = str(beat.get("visual_description", "")).strip()
    script = str(beat.get("script_text", "")).strip()
    if _is_specific_text(visual):
        return visual
    return script or visual


def _is_specific_text(text: str) -> bool:
    if len(text.split()) < 3:
        return False
    lowered = text.lower()
    generic_fragments = (
        "pattern grid",
        "clean final card",
        "text highlight",
        "question",
        "meme",
        "card",
        "token grid",
        "flow diagram",
    )
    return not any(fragment in lowered for fragment in generic_fragments)


_WEAK_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "because",
    "but",
    "can",
    "do",
    "does",
    "did",
    "for",
    "from",
    "have",
    "here",
    "how",
    "if",
    "in",
    "is",
    "it",
    "just",
    "like",
    "many",
    "most",
    "my",
    "makes",
    "make",
    "made",
    "means",
    "mean",
    "gets",
    "get",
    "go",
    "goes",
    "going",
    "keep",
    "keeps",
    "look",
    "looks",
    "looking",
    "know",
    "knows",
    "knowing",
    "read",
    "reads",
    "reading",
    "search",
    "searches",
    "think",
    "thinks",
    "thinking",
    "type",
    "types",
    "typing",
    "write",
    "writes",
    "writing",
    "now",
    "of",
    "on",
    "or",
    "real",
    "so",
    "that",
    "the",
    "then",
    "this",
    "things",
    "to",
    "we",
    "what",
    "when",
    "why",
    "with",
    "you",
}


def _content_words(text: str) -> list[str]:
    words = [word.strip(".,!?") for word in text.split()]
    return [word for word in words if word and word.lower() not in _WEAK_WORDS]


def _beat_phrase(text: str, entities: list[str]) -> str:
    words = _content_words(text)
    if entities:
        meaningful_entities = [str(entity).strip(".,!?") for entity in entities if str(entity).strip(".,!?").lower() not in _WEAK_WORDS]
        if meaningful_entities:
            if len(meaningful_entities) == 1:
                return meaningful_entities[0][:48]
            return " ".join(meaningful_entities[:4])[:48]
    if not words:
        return text[:48]
    return " ".join(words[:6])[:56]


def _primary_label(beat: dict[str, Any], text: str, entities: list[str]) -> str:
    caption = str(beat.get("caption_text", "")).strip()
    if caption:
        return caption[:48]
    return _beat_phrase(text, entities)


def _summary_text(text: str, primary: str) -> str:
    summary = text.strip()
    if len(summary) > 72:
        summary = summary[:69].rstrip() + "..."
    if summary.lower() == primary.lower():
        return ""
    return summary


def _flow_parts(text: str, entities: list[str]) -> list[str]:
    words = _content_words(text)
    if entities:
        cleaned = [str(entity).strip(".,!?") for entity in entities if str(entity).strip(".,!?").lower() not in _WEAK_WORDS]
        if cleaned:
            return (cleaned + ["next", "result"])[:3]
    if len(words) >= 6:
        return [" ".join(words[:2]), " ".join(words[2:4]), " ".join(words[4:6])]
    return (words + ["next", "result"])[:3]


def _comparison_parts(text: str, entities: list[str]) -> tuple[str, str]:
    words = _content_words(text)
    if "but" in [word.lower() for word in words]:
        idx = [word.lower() for word in words].index("but")
        left = " ".join(words[:idx])[:36]
        right = " ".join(words[idx + 1 : idx + 7])[:36]
        return left or _beat_phrase(text, entities), right or "different result"
    if entities:
        cleaned = [str(entity).strip(".,!?") for entity in entities if str(entity).strip(".,!?").lower() not in _WEAK_WORDS]
        left = cleaned[0] if cleaned else _beat_phrase(text, entities)
        right = cleaned[1] if len(cleaned) > 1 else "instead"
        return left[:36], right[:36]
    return (_beat_phrase(text, entities), "instead")


def _question_text(text: str, primary: str) -> str:
    stripped = text.strip()
    if stripped.endswith("?") and len(stripped.split()) >= 3:
        return stripped[:72]
    words = _content_words(stripped)
    if len(words) >= 4:
        focus = " ".join(words[:5])
        return f"Why {focus}?"[:72]
    if stripped.lower().startswith(("why ", "how ", "what ", "when ")) and len(stripped.split()) >= 3:
        return (stripped[:71] + "?") if len(stripped) < 72 else stripped[:72]
    return f"Why {primary}?"[:72]
