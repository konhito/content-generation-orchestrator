import json

from src.short.component_plan import build_component_plan
from src.short.meme_copy import generate_meme_copy
from src.short.niche import get_script_context, get_voice_config, load_niche
from src.short.script_beats import build_script_beats


def test_loads_copied_tech_niche_profile():
    profile = load_niche("tech")

    assert profile["name"] == "tech"
    assert "script" in profile
    assert "hooks" in profile["script"]
    assert "edge_tts" in profile["voice"]["suggested_voices"]


def test_script_context_contains_real_niche_prompt_details():
    context = get_script_context(load_niche("tech"))

    assert "NICHE: Tech & AI News" in context
    assert "HOOK PATTERNS" in context
    assert "TARGET WORD COUNT: 150 to 170" in context
    assert "NEVER USE" in context


def test_voice_config_reads_edge_voice_from_niche():
    config = get_voice_config(load_niche("tech"), provider="edge", lang="en")

    assert config["voice_id"] == "en-US-GuyNeural"
    assert "160 words per minute" in config["pace"]


def test_build_script_beats_splits_attention_span_beats():
    beats = build_script_beats(
        "AI sounds confident. But the answer can still be fake. That is the hallucination problem.",
        niche="tech",
    )

    assert [beat["beat_id"] for beat in beats] == ["beat_001", "beat_002", "beat_003"]
    assert beats[0]["intent"] == "context"
    assert "web_research" in beats[0]["preferred_types"]
    assert len(beats[0]["search_queries"]) == 3


def test_meme_copy_replaces_generic_lines_without_repeating():
    plan = [
        {
            "type": "meme",
            "query": "AI hallucination",
            "template_hint": "surprised",
            "meme_text_top": "WAIT WHAT",
            "meme_text_bottom": "IT GETS WORSE",
        },
        {
            "type": "meme",
            "query": "confident wrong answer",
            "template_hint": "drake",
            "meme_text_top": "WHEN THE NEWS DROPS",
            "meme_text_bottom": "AND IT GETS WORSE",
        },
    ]

    result = generate_meme_copy(
        plan,
        script="AI can sound confident while making things up. The fix is checking sources.",
        transcript_words=[],
        provider="mock",
    )

    pairs = {(item["meme_text_top"], item["meme_text_bottom"]) for item in result}
    assert len(pairs) == 2
    assert ("WAIT WHAT", "IT GETS WORSE") not in pairs
    assert ("WHEN THE NEWS DROPS", "AND IT GETS WORSE") not in pairs


def test_component_plan_maps_beats_to_clean_remotion_visuals():
    beats = build_script_beats(
        "AI looks at patterns. Attention connects every token. Then bad context creates hallucinations.",
        niche="tech",
    )
    memes = [
        {
            "type": "meme",
            "query": "bad context",
            "meme_text_top": "MODEL SAID TRUST ME",
            "meme_text_bottom": "SOURCE SAID ABSOLUTELY NOT",
        }
    ]

    plan = build_component_plan(beats, memes, duration=50, niche="tech")

    assert len(plan["components"]) >= len(beats)
    assert any(item["visual"]["type"] == "attention_visual" for item in plan["components"])
    assert any(item["visual"]["type"] == "meme_card" for item in plan["components"])
    json.dumps(plan)
