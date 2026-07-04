"""Select one full-frame visual mode for every Shorts script beat."""

from __future__ import annotations

from typing import Any

COMPONENT_TERMS = {
    "code", "diagram", "flow", "number", "compare", "comparison", "timeline",
    "transform", "mechanism", "token", "pixel", "chart", "graph", "step",
}
COMPONENT_INTENTS = {"mechanism", "comparison", "evidence", "demonstration", "process"}
CHARACTER_INTENTS = {"hook", "context", "bridge", "reaction", "conclusion", "question"}


def build_beat_mode_plan(
    beats: list[dict[str, Any]],
    meme_slots: set[int] | None = None,
) -> list[dict[str, Any]]:
    """Return a deterministic, guarded character/component/meme plan."""

    meme_slots = meme_slots or set()
    plan: list[dict[str, Any]] = []
    character_run = 0

    for index, beat in enumerate(beats):
        text = str(beat.get("script_text", "")).lower()
        intent = str(beat.get("intent", "context")).lower()
        contains_component_term = any(term in text for term in COMPONENT_TERMS)

        if index in meme_slots and (not plan or plan[-1]["mode"] != "meme"):
            mode = "meme"
            reason = "planned punchline"
        elif intent in COMPONENT_INTENTS or contains_component_term:
            mode = "component"
            reason = "visual mechanism"
        elif intent in CHARACTER_INTENTS:
            mode = "character"
            reason = "direct host explanation"
        else:
            mode = "component"
            reason = "safe explanatory fallback"

        if mode == "character" and character_run >= 2:
            mode = "component"
            reason = "character-run guardrail"

        character_run = character_run + 1 if mode == "character" else 0
        plan.append(
            {
                "id": beat.get("beat_id", f"beat_{index + 1:03d}"),
                "mode": mode,
                "reason": reason,
                "intent": intent,
                "script_text": beat.get("script_text", ""),
            }
        )

    if len(plan) >= 3 and not any(item["mode"] == "component" for item in plan):
        for item in plan:
            if item["mode"] == "character":
                item["mode"] = "component"
                item["reason"] = "minimum visual-explanation guardrail"
                break

    return plan
