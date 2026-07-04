"""Directed-randomness planner for mixed Shorts scenes."""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field

from src.short.models import (
    RecipeCamera,
    RecipeCharacterLayer,
    RecipeComponentLayer,
    RecipeMemeLayer,
    RecipeTransition,
    VisualRecipe,
)


@dataclass(frozen=True)
class SceneRecipeInput:
    """Inputs used to choose a layered visual recipe for one beat."""

    beat_id: str
    beat_index: int
    beat_count: int
    topic: str
    niche: str
    narration: str
    caption_text: str
    visual_description: str
    visual_elements: list[str] = field(default_factory=list)
    component_type: str = "concept_card"
    has_meme: bool = False
    seriousness_score: float = 0.0


NICHE_MEME_BASE = {
    "tech": 0.35,
    "finance": 0.25,
    "politics": 0.18,
    "news": 0.18,
    "gaming": 0.55,
    "science": 0.25,
    "motivation": 0.12,
    "entertainment": 0.5,
    "sports": 0.42,
}


def _rng(seed: str, beat_id: str) -> random.Random:
    digest = hashlib.sha256(f"{seed}:{beat_id}".encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def classify_intent(item: SceneRecipeInput) -> str:
    """Classify a beat into a broad editing intent."""

    text = f"{item.narration} {item.caption_text}".lower()
    if item.beat_index == 0:
        return "hook"
    if _contains_any(text, ("but", "however", "instead", "not ")):
        return "contrast"
    if _contains_any(text, ("because", "why", "that is why", "so ")):
        return "explain"
    if _contains_any(text, ("watch", "then", "suddenly", "turns into")):
        return "reveal"
    if _contains_any(text, ("wrong", "broke", "absurd", "confident")):
        return "joke"
    if item.beat_index == item.beat_count - 1:
        return "recap"
    return "explain"


def _attention_strategy(
    item: SceneRecipeInput,
    intent: str,
    chooser: random.Random,
) -> str:
    if item.seriousness_score >= 0.75:
        return chooser.choice(
            ["host_reacts_to_evidence", "timeline_walkthrough", "rapid_evidence_wall"]
        )
    if intent == "hook":
        return chooser.choice(["visual_metaphor", "host_demonstrates_concept"])
    if intent == "contrast":
        return chooser.choice(["before_after_comparison", "reaction_stack"])
    if intent == "joke" and item.has_meme:
        return "meme_interruption"
    if item.component_type in {"timeline", "scoreboard", "comparison"}:
        return "timeline_walkthrough"
    return chooser.choice(["host_demonstrates_concept", "host_reacts_to_evidence"])


def _recipe_id(strategy: str) -> tuple[str, str]:
    mapping = {
        "host_demonstrates_concept": (
            "host_foreground_concept_backdrop",
            "character_foreground_visual_backdrop",
        ),
        "host_reacts_to_evidence": (
            "host_sidecar_main_diagram",
            "character_sidecar_visual_main",
        ),
        "meme_interruption": (
            "meme_interruption",
            "character_primary_meme_pop",
        ),
        "reaction_stack": (
            "reaction_stack",
            "character_component_meme_stack",
        ),
        "visual_metaphor": (
            "visual_metaphor_stage",
            "character_interacts_with_props",
        ),
        "rapid_evidence_wall": (
            "rapid_evidence_wall",
            "character_anchor_evidence_cards",
        ),
        "timeline_walkthrough": (
            "host_sidecar_main_diagram",
            "character_sidecar_visual_main",
        ),
        "before_after_comparison": (
            "reaction_stack",
            "character_component_meme_stack",
        ),
    }
    return mapping[strategy]


def _meme_intensity(item: SceneRecipeInput, intent: str, strategy: str) -> float:
    if not item.has_meme:
        return 0.0
    base = NICHE_MEME_BASE.get(item.niche.lower(), 0.3)
    if intent == "joke" or strategy == "meme_interruption":
        base += 0.18
    if item.seriousness_score >= 0.75:
        base = min(base, 0.2)
    return round(max(0.0, min(base, 0.75)), 2)


def plan_scene_recipes(items: list[SceneRecipeInput], seed: str) -> list[VisualRecipe]:
    """Choose stable mixed-scene recipes for storyboard beats."""

    recipes: list[VisualRecipe] = []
    for item in items:
        chooser = _rng(seed, item.beat_id)
        intent = classify_intent(item)
        strategy = _attention_strategy(item, intent, chooser)
        recipe_id, layout = _recipe_id(strategy)
        meme_intensity = _meme_intensity(item, intent, strategy)
        component_role = (
            "supporting_evidence"
            if strategy in {"host_reacts_to_evidence", "rapid_evidence_wall"}
            else "main_explanation"
        )
        character_position = (
            "side_left" if layout == "character_sidecar_visual_main" else "lower_center"
        )
        character_scale = 0.58 if character_position == "side_left" else 0.82

        recipes.append(
            VisualRecipe(
                recipe_id=recipe_id,
                layout=layout,
                intent=intent,
                attention_strategy=strategy,
                character=RecipeCharacterLayer(
                    presence="primary",
                    position=character_position,
                    scale=character_scale,
                    pose_intent="react" if "reacts" in strategy else "explain",
                    emotion="curious" if intent in {"hook", "explain"} else "happy",
                ),
                component=RecipeComponentLayer(
                    role=component_role,
                    component_type=item.component_type or "concept_card",
                    position=(
                        "main_stage"
                        if layout == "character_sidecar_visual_main"
                        else "background_stage"
                    ),
                    emphasis_words=[
                        word.strip(".,!?").lower()
                        for word in item.caption_text.split()
                        if len(word.strip(".,!?")) > 4
                    ][:3],
                ),
                meme=RecipeMemeLayer(
                    role="accent" if meme_intensity > 0 else "none",
                    style=(
                        "sticker_pop"
                        if strategy != "meme_interruption"
                        else "interrupt_card"
                    ),
                    timing="after_key_claim" if meme_intensity > 0 else "none",
                    intensity=meme_intensity,
                ),
                camera=RecipeCamera(
                    motion=chooser.choice(["steady", "slow_push", "micro_parallax"]),
                    punch_zoom_on=None if meme_intensity < 0.45 else "key_claim",
                ),
                transition=RecipeTransition(
                    transition_in="match_cut",
                    transition_out=(
                        "accent_whip" if meme_intensity >= 0.45 else "soft_cut"
                    ),
                ),
            )
        )
    return recipes
