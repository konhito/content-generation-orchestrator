import json

from src.short.first import ShortFirstGenerator
from src.short.first import _build_meme_items, _enforce_narration_budget
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
            "visual_direction": {
                "video_background": {
                    "name": "office",
                    "path": "characters/synctoon/character_1/background/office/office.png",
                    "reason": "clean, neutral tech backdrop",
                },
                "beats": [
                    {
                        "beat_id": "beat_001",
                        "body_type": "body15",
                        "head": "M",
                        "emotion": "content",
                        "gesture": "explain",
                        "reason": "opening explanation",
                    },
                    {
                        "beat_id": "beat_002",
                        "body_type": "body22",
                        "head": "L",
                        "emotion": "curious",
                        "gesture": "react",
                        "reason": "contrasting second beat",
                    },
                ],
            },
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


def test_live_research_uses_aggregator_and_preserves_metadata():
    calls = []

    class FakeAggregator:
        def __init__(self, topic, niche="general", discovery=None, logger=None):
            calls.append((topic, niche, discovery))

        def gather(self, limit=8):
            from src.short.research_aggregator import ResearchItem

            return [
                ResearchItem(
                    source="web",
                    title="Coding survey",
                    snippet="Most coding time is spent understanding systems.",
                    url="https://example.com/survey",
                    score=0.9,
                    metadata={"image_url": "https://example.com/chart.jpg"},
                )
            ]

    generator = ShortFirstGenerator(llm=FakeLLM(), research_aggregator_factory=FakeAggregator)

    bundle = generator.build_research_bundle("Reality of coding", research=True, niche="tech")

    assert calls and calls[0][0:2] == ("Reality of coding", "tech")
    assert bundle.notes[0].source == "web"
    assert bundle.notes[0].url == "https://example.com/survey"
    assert bundle.notes[0].metadata["image_url"].endswith("chart.jpg")


def test_disabled_live_research_does_not_create_aggregator():
    def fail_factory(*args, **kwargs):
        raise AssertionError("aggregator must not run")

    generator = ShortFirstGenerator(llm=FakeLLM(), research_aggregator_factory=fail_factory)

    bundle = generator.build_research_bundle("Reality of coding", research=False, niche="tech")

    assert bundle.notes[0].source == "topic"


def test_narration_budget_includes_cta_and_keeps_sentence_boundary():
    narration = " ".join(["First useful sentence."] * 60)
    cta = "Follow for more useful coding breakdowns."

    shortened = _enforce_narration_budget(narration, cta, duration_seconds=45)

    assert len((shortened + " " + cta).split()) <= 99
    assert shortened.endswith(".")


def test_loads_builtin_niche_fallback():
    generator = ShortFirstGenerator(llm=FakeLLM())

    profile = generator.load_niche_profile("unknown")

    assert profile.name == "general"
    assert profile.target_duration_seconds == 50
    assert profile.meme_density in {"low", "medium", "high"}


def test_generates_short_script_and_meme_plan(tmp_path, monkeypatch):
    source = tmp_path / "source.md"
    source.write_text("AI predicts the next useful pattern.", encoding="utf-8")
    project_dir = tmp_path / "projects" / "ai-short"

    def fake_resolve_meme_assets(memes, out_dir, public_root=None, provider="imgflip", logger=None):
        if logger is not None:
            logger("assets validated")
        return [
            {
                **item,
                "provider": provider,
                "meme_template_id": "12345",
                "meme_template_name": "Drake Hotline Bling",
                "image_path": str(out_dir / "imgflip_12345_0.jpg"),
            }
            for item in memes
        ]

    monkeypatch.setattr("src.short.first.resolve_meme_assets", fake_resolve_meme_assets)
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
    assert meme_plan["moments"][0]["image_path"]

    component_plan = json.loads(result.component_plan_path.read_text(encoding="utf-8"))
    assert "components" in component_plan
    assert any(
        item in component_plan["component_types"]
        for item in {"attention_visual", "question", "text_highlight", "flow_diagram"}
    )
    assert any(
        item["visual"]["scene_config"].get("image_path")
        for item in component_plan["components"]
        if item["visual"]["type"] == "meme_card"
    )

    mode_plan = json.loads(result.beat_mode_plan_path.read_text(encoding="utf-8"))
    assert len(mode_plan["beats"]) == len(
        json.loads(result.script_beats_path.read_text(encoding="utf-8"))["beats"]
    )
    assert {item["mode"] for item in mode_plan["beats"]} <= {"character", "component", "meme"}

    character_plan = json.loads(result.character_plan_path.read_text(encoding="utf-8"))
    assert character_plan["character_id"] == "character_1"
    assert character_plan["video_background"]["path"].endswith("office.png")
    assert character_plan["beat_modes"]["beat_001"]
    assert character_plan["beats"][0]["body_type"] == "body15"
    assert character_plan["beats"][1]["body_type"] == "body22"

    scene_recipe_plan = json.loads(result.scene_recipe_plan_path.read_text(encoding="utf-8"))
    assert scene_recipe_plan["recipes"]
    assert scene_recipe_plan["recipes"][0]["recipe_id"]
    assert scene_recipe_plan["recipes"][0]["character"]["presence"] == "primary"
    assert "/background/" in scene_recipe_plan["recipes"][0]["background_image"]
    assert not scene_recipe_plan["recipes"][0]["background_image"].endswith("office.png")
    assert {recipe["character"]["head"] for recipe in scene_recipe_plan["recipes"]} == {"M"}
    assert scene_recipe_plan["recipes"][0]["character"]["body_type"] == "body15"
    assert scene_recipe_plan["recipes"][0]["character"]["gesture"] == "explain"


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


def test_build_meme_items_raises_density_for_long_short():
    raw = {
        "meme_moments": [
            {
                "time_start": 8,
                "time_end": 11,
                "meme_type": "reaction_label",
                "caption": "first",
                "visual_style": "zoom",
            },
            {
                "time_start": 18,
                "time_end": 21,
                "meme_type": "reaction_label",
                "caption": "second",
                "visual_style": "zoom",
            },
        ]
    }
    script_beats = [{"script_text": f"beat {i}"} for i in range(12)]
    profile = {"editing": {"meme_beats": [1, 3]}}

    items = _build_meme_items(raw, script_beats, profile)

    assert len(items) == 3
