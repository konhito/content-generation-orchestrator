"""Script beat extraction and transcript alignment for Shorts."""

from __future__ import annotations

import re
from typing import Any

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "for",
    "from", "has", "have", "here", "in", "is", "it", "its", "of", "on",
    "or", "our", "out", "so", "that", "the", "their", "this", "to", "we",
    "with", "you", "your",
}


def build_script_beats(script: str, niche: str = "general") -> list[dict[str, Any]]:
    text = str(script or "").strip()
    if not text:
        return []
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    if not sentences:
        sentences = [text]
    beats: list[dict[str, Any]] = []
    for index, sentence in enumerate(sentences[:14], 1):
        entities = _extract_entities(sentence)
        beats.append({
            "beat_id": f"beat_{index:03d}",
            "script_text": sentence,
            "intent": _infer_intent(sentence),
            "entities": entities,
            "visual_description": sentence,
            "search_queries": _build_search_queries(sentence, niche, entities),
            "preferred_types": _preferred_types(sentence),
            "avoid": _avoid_terms(sentence),
        })
    return beats


def align_transcript_to_beats(words: list[dict], beats: list[dict]) -> list[dict]:
    groups = _group_words(words)
    if not beats:
        return groups
    if not groups:
        return [{**beat, "transcript_text": "", "start": 0.0, "end": 0.0} for beat in beats]
    remaining = groups[:]
    aligned: list[dict[str, Any]] = []
    for beat in beats:
        group = remaining.pop(0) if remaining else groups[-1]
        aligned.append({
            **beat,
            "transcript_text": group["text"],
            "start": round(float(group["start"]), 3),
            "end": round(float(group["end"]), 3),
        })
    return aligned


def _group_words(words: list[dict]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    current: list[dict] = []
    last_end: float | None = None
    for word in words:
        start = float(word.get("start", word.get("start_seconds", 0.0)))
        end = float(word.get("end", word.get("end_seconds", start)))
        if current and last_end is not None and start - last_end > 0.5:
            groups.append(_finalize_group(current))
            current = []
        current.append({"word": word.get("word", ""), "start": start, "end": end})
        last_end = end
        if str(word.get("word", "")).strip().endswith((".", "!", "?", ",")):
            groups.append(_finalize_group(current))
            current = []
            last_end = None
    if current:
        groups.append(_finalize_group(current))
    return groups


def _finalize_group(words: list[dict]) -> dict[str, Any]:
    return {
        "text": " ".join(str(word.get("word", "")).strip() for word in words).strip(),
        "start": float(words[0].get("start", 0.0)),
        "end": float(words[-1].get("end", words[0].get("start", 0.0))),
    }


def _extract_entities(sentence: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9]+", sentence)
    entities = []
    for token in tokens:
        lowered = token.lower()
        if len(token) > 2 and lowered not in _STOPWORDS and lowered not in entities:
            entities.append(token)
    return entities[:5]


def _build_search_queries(sentence: str, niche: str, entities: list[str]) -> list[str]:
    first_entity = entities[0] if entities else sentence.split()[0] if sentence.split() else niche
    queries = [
        f"{sentence} {niche}".strip(),
        " ".join(entities[:3]).strip() or sentence[:48].rstrip(".!? ").strip() or niche,
        f"{niche} {first_entity}".strip(),
    ]
    normalized = []
    for query in queries:
        query = re.sub(r"\s+", " ", query).strip()
        if query and query not in normalized:
            normalized.append(query)
    while len(normalized) < 3:
        normalized.append(niche)
    return normalized[:3]


def _preferred_types(sentence: str) -> list[str]:
    lowered = sentence.lower()
    if any(word in lowered for word in ("leak", "rumor", "breaking", "update")):
        return ["meme", "attention_visual", "web_research"]
    if any(word in lowered for word in ("attention", "token", "connect")):
        return ["attention_visual", "token_grid", "meme"]
    return ["web_research", "meme", "flow_diagram"]


def _avoid_terms(sentence: str) -> list[str]:
    lowered = sentence.lower()
    terms = []
    if "gta 5" in lowered:
        terms.append("gta 5")
    if "mod" in lowered:
        terms.append("mods")
    return terms


def _infer_intent(sentence: str) -> str:
    lowered = sentence.lower()
    if any(word in lowered for word in ("leak", "revealed", "breaking", "drop", "shock")):
        return "shock"
    if any(word in lowered for word in ("joke", "meme", "lol", "laugh")):
        return "joke"
    if any(word in lowered for word in ("angry", "rage", "backlash", "hate")):
        return "backlash"
    return "context"
