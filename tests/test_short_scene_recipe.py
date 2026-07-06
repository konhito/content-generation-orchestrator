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
from src.short.scene_recipe import SceneRecipeInput, plan_scene_recipes


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
    assert loaded.beats[0].visual_recipe.character.motion == "gentle_bob"


def test_scene_recipe_planner_is_seeded_and_deterministic():
    inputs = [
        SceneRecipeInput(
            beat_id="beat_001",
            beat_index=0,
            beat_count=2,
            topic="Why AI hallucinates",
            niche="tech",
            narration="AI predicts likely text, not truth.",
            caption_text="AI predicts text, not truth",
            visual_description="probability bars",
            visual_elements=["tokens", "probability"],
            component_type="probability_bars",
            has_meme=True,
        ),
        SceneRecipeInput(
            beat_id="beat_002",
            beat_index=1,
            beat_count=2,
            topic="Why AI hallucinates",
            niche="tech",
            narration="That is why it can sound confident and still be wrong.",
            caption_text="confident and wrong",
            visual_description="wrong answer sticker",
            visual_elements=["meme", "reaction"],
            component_type="meme_card",
            has_meme=True,
        ),
    ]

    first = plan_scene_recipes(inputs, seed="synctoon-demo:demo")
    second = plan_scene_recipes(inputs, seed="synctoon-demo:demo")

    assert [recipe.model_dump() for recipe in first] == [
        recipe.model_dump() for recipe in second
    ]
    assert first[0].character.presence == "primary"
    assert first[0].component.role in {"main_explanation", "supporting_evidence"}
    assert first[1].meme.intensity > 0
    assert first[0].character.motion in {"lean_in", "gentle_bob", "side_bob", "subtle_bob", "quick_shift", "snap_shift"}
    assert first[1].character.position in {"side_left", "side_right", "upper_left", "upper_right", "center_float", "lower_center"}


def test_serious_topic_lowers_meme_intensity():
    inputs = [
        SceneRecipeInput(
            beat_id="beat_001",
            beat_index=0,
            beat_count=1,
            topic="Election misinformation during a disaster",
            niche="politics",
            narration="False claims spread during the emergency.",
            caption_text="false claims spread",
            visual_description="timeline of claims",
            visual_elements=["timeline", "evidence"],
            component_type="timeline",
            has_meme=True,
            seriousness_score=0.9,
        )
    ]

    recipes = plan_scene_recipes(inputs, seed="serious")

    assert recipes[0].meme.intensity <= 0.2
    assert recipes[0].attention_strategy in {
        "host_reacts_to_evidence",
        "timeline_walkthrough",
        "rapid_evidence_wall",
    }


def test_flat_explanation_background_is_replaced_with_rich_scene():
    item = SceneRecipeInput(
        beat_id="beat_001",
        beat_index=0,
        beat_count=1,
        topic="Game release news",
        niche="tech",
        narration="Official details are finally here.",
        caption_text="official details",
        visual_description="news breakdown",
        visual_elements=["news"],
        component_type="concept_card",
        background_image="characters/synctoon/character_1/background/explanation/explanation.png",
    )

    recipe = plan_scene_recipes([item], seed="background-demo")[0]

    assert recipe.background_image != item.background_image
    assert "/background/" in recipe.background_image


def test_scene_recipe_keeps_one_character_head_identity():
    item = SceneRecipeInput(
        beat_id="beat_001",
        beat_index=0,
        beat_count=1,
        topic="Tech",
        niche="tech",
        narration="Explain it",
        caption_text="Explain it",
        visual_description="diagram",
        visual_elements=[],
        component_type="token_grid",
        head="L",
    )

    recipe = plan_scene_recipes([item], seed="identity")[0]

    assert recipe.character.head == "M"
