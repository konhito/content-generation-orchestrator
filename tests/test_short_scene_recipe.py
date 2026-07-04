from src.short.generator import ShortGenerator
from src.short.models import (
    RecipeCamera,
    RecipeCharacterLayer,
    RecipeComponentLayer,
    RecipeMemeLayer,
    RecipeTransition,
    ShortBeatMode,
    ShortsBeat,
    ShortsStoryboard,
    ShortsVisual,
    VisualRecipe,
    VisualType,
)


def test_visual_recipe_round_trips_through_shorts_storyboard(tmp_path):
    storyboard = ShortsStoryboard(
        id="recipe_demo",
        title="Recipe demo",
        total_duration_seconds=6.0,
        beats=[
            ShortsBeat(
                id="beat_001",
                start_seconds=0.0,
                end_seconds=6.0,
                visual=ShortsVisual(
                    type=VisualType.TEXT_HIGHLIGHT,
                    primary_text="not truth",
                ),
                caption_text="AI predicts text, not truth",
                mode=ShortBeatMode.CHARACTER,
                visual_recipe=VisualRecipe(
                    recipe_id="host_foreground_concept_backdrop",
                    layout="character_foreground_visual_backdrop",
                    intent="explain_surprise",
                    attention_strategy="host_demonstrates_concept",
                    character=RecipeCharacterLayer(
                        presence="primary",
                        position="lower_center",
                        scale=0.82,
                        pose_intent="explain",
                        emotion="curious",
                    ),
                    component=RecipeComponentLayer(
                        role="main_explanation",
                        component_type="probability_bars",
                        position="background_stage",
                        emphasis_words=["predicts", "not truth"],
                    ),
                    meme=RecipeMemeLayer(
                        role="accent",
                        style="sticker_pop",
                        timing="after_key_claim",
                        intensity=0.35,
                    ),
                    camera=RecipeCamera(
                        motion="slow_push",
                        punch_zoom_on="not truth",
                    ),
                    transition=RecipeTransition(
                        transition_in="match_cut",
                        transition_out="accent_whip",
                    ),
                ),
            )
        ],
    )

    generator = ShortGenerator()
    path = tmp_path / "shorts_storyboard.json"
    generator.save_shorts_storyboard(storyboard, path)

    loaded = generator.load_shorts_storyboard(path)

    assert loaded.beats[0].visual_recipe is not None
    assert loaded.beats[0].visual_recipe.recipe_id == "host_foreground_concept_backdrop"
    assert loaded.beats[0].visual_recipe.character.position == "lower_center"
    assert loaded.beats[0].visual_recipe.component.emphasis_words == [
        "predicts",
        "not truth",
    ]
    assert loaded.beats[0].visual_recipe.meme.intensity == 0.35
