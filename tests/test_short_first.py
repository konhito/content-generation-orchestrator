import json

from src.short.first import ShortFirstGenerator
from src.short.models import ShortScript


class FakeLLM:
    def generate_json(self, prompt: str, system_prompt: str = "") -> dict:
        return {
            "title": "Why AI Guesses Wrong",
            "hook": "AI can sound right while being wrong.",
            "narration": (
                "AI does not memorize everything. It predicts patterns. "
                "When the pattern is weak, it guesses with confidence. "
                "That is why checking sources still matters."
            ),
            "beats": [
                {
                    "caption": "AI predicts patterns",
                    "start": 0,
                    "end": 15,
                    "visual": "pattern grid",
                },
                {
                    "caption": "Weak pattern, confident guess",
                    "start": 15,
                    "end": 35,
                    "visual": "warning stamp",
                },
            ],
            "cta": "Follow for the full breakdown.",
            "meme_moments": [
                {
                    "time_start": 18,
                    "time_end": 22,
                    "meme_type": "reaction_label",
                    "caption": "confidently wrong",
                    "visual_style": "zoom shake red stamp",
                    "reason": "The narration explains hallucination risk.",
                }
            ],
        }


def test_builds_research_bundle_from_topic_and_sources(tmp_path):
    source = tmp_path / "source.md"
    source.write_text("# AI\nAI learns by finding patterns.", encoding="utf-8")

    generator = ShortFirstGenerator(llm=FakeLLM())
    bundle = generator.build_research_bundle(
        topic="AI learning",
        source_paths=[source],
        research=False,
        niche="tech",
    )

    assert bundle.topic == "AI learning"
    assert bundle.niche == "tech"
    assert bundle.notes[0].source == "source"
    assert "AI learns" in bundle.notes[0].snippet


def test_loads_builtin_niche_fallback():
    generator = ShortFirstGenerator(llm=FakeLLM())

    profile = generator.load_niche_profile("unknown")

    assert profile.name == "general"
    assert profile.target_duration_seconds == 50
    assert profile.meme_density in {"low", "medium", "high"}


def test_generates_short_script_and_meme_plan(tmp_path):
    source = tmp_path / "source.md"
    source.write_text("AI predicts the next useful pattern.", encoding="utf-8")
    project_dir = tmp_path / "projects" / "ai-short"

    generator = ShortFirstGenerator(llm=FakeLLM())
    result = generator.generate(
        project_id="ai-short",
        project_dir=project_dir,
        topic="AI hallucinations",
        source_paths=[source],
        niche="tech",
        variant="default",
        duration=50,
        research=False,
    )

    assert result.success is True
    assert result.short_script_path.exists()
    assert result.script_beats_path.exists()
    assert result.meme_plan_path.exists()
    assert result.component_plan_path.exists()
    assert result.beat_mode_plan_path.exists()
    assert result.character_plan_path.exists()
    assert result.scene_recipe_plan_path is not None
    assert result.scene_recipe_plan_path.exists()

    script = ShortScript.model_validate_json(result.short_script_path.read_text(encoding="utf-8"))
    assert script.source_project == "ai-short"
    assert script.total_duration_seconds == 50
    assert script.hook_question == "AI can sound right while being wrong."

    meme_plan = json.loads(result.meme_plan_path.read_text(encoding="utf-8"))
    assert meme_plan["provider"] == "imgflip"
    assert meme_plan["env"]["username"] == "IMGFLIP_USERNAME"
    assert meme_plan["moments"][0]["meme_text_top"] != "WAIT WHAT"

    component_plan = json.loads(result.component_plan_path.read_text(encoding="utf-8"))
    assert "components" in component_plan
    assert "attention_visual" in component_plan["component_types"]

    mode_plan = json.loads(result.beat_mode_plan_path.read_text(encoding="utf-8"))
    assert len(mode_plan["beats"]) == len(
        json.loads(result.script_beats_path.read_text(encoding="utf-8"))["beats"]
    )
    assert {item["mode"] for item in mode_plan["beats"]} <= {"character", "component", "meme"}

    character_plan = json.loads(result.character_plan_path.read_text(encoding="utf-8"))
    assert character_plan["character_id"] == "character_1"

    scene_recipe_plan = json.loads(result.scene_recipe_plan_path.read_text(encoding="utf-8"))
    assert scene_recipe_plan["recipes"]
    assert scene_recipe_plan["recipes"][0]["recipe_id"]
    assert scene_recipe_plan["recipes"][0]["character"]["presence"] == "primary"


def test_mock_generation_does_not_call_llm(tmp_path):
    class ExplodingLLM:
        def generate_json(self, prompt: str, system_prompt: str = "") -> dict:
            raise AssertionError("LLM should not be called in mock mode")

    generator = ShortFirstGenerator(llm=ExplodingLLM())

    result = generator.generate(
        project_id="mock-short",
        project_dir=tmp_path / "mock-short",
        topic="AI testing",
        niche="tech",
        variant="default",
        duration=50,
        mock=True,
    )

    script = ShortScript.model_validate_json(result.short_script_path.read_text(encoding="utf-8"))
    assert script.title == "AI testing"
    assert "AI testing" in script.condensed_narration
