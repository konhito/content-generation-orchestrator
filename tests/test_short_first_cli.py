from src.cli.main import build_parser
from src.cli.main import cmd_short
from argparse import Namespace
import json


def test_short_generate_accepts_short_first_options():
    parser = build_parser()

    args = parser.parse_args([
        "short",
        "generate",
        "ai-short",
        "--topic",
        "AI hallucinations",
        "--source",
        "input/source.md",
        "--niche",
        "tech",
        "--research",
        "--duration",
        "50",
    ])

    assert args.command == "short"
    assert args.short_command == "generate"
    assert args.project == "ai-short"
    assert args.topic == "AI hallucinations"
    assert args.source == ["input/source.md"]
    assert args.niche == "tech"
    assert args.research is True
    assert args.duration == 50


def test_short_step_commands_exist():
    parser = build_parser()

    commands = ["research", "beats", "memes", "components"]
    for command in commands:
        args = parser.parse_args(["short", command, "ai-short", "--variant", "default"])
        assert args.command == "short"
        assert args.short_command == command
        assert args.project == "ai-short"


def test_long_generate_parser_stays_on_cmd_generate():
    parser = build_parser()

    args = parser.parse_args(["generate", "my-video"])

    assert args.command == "generate"
    assert args.func.__name__ == "cmd_generate"


def test_short_generate_topic_runs_automatic_short_flow(tmp_path):
    projects_dir = tmp_path / "projects"
    args = Namespace(
        projects_dir=str(projects_dir),
        project="auto-short",
        topic="AI hallucinations",
        source=None,
        niche="tech",
        research=True,
        variant="default",
        duration=50,
        mode="hook",
        scenes=None,
        force=False,
        skip_voiceover=True,
        skip_custom_scenes=True,
        mock=True,
    )

    result = cmd_short(args)

    variant_dir = projects_dir / "auto-short" / "short" / "default"
    assert result == 0
    assert (variant_dir / "research" / "research.json").exists()
    assert (variant_dir / "short_script.json").exists()
    assert (variant_dir / "beats" / "script_beats.json").exists()
    assert (variant_dir / "memes" / "meme_plan.json").exists()
    assert (variant_dir / "components" / "component_plan.json").exists()
    assert (variant_dir / "storyboard" / "shorts_storyboard.json").exists()

    storyboard = json.loads((variant_dir / "storyboard" / "shorts_storyboard.json").read_text(encoding="utf-8"))
    visual_types = {beat["visual"]["type"] for beat in storyboard["beats"]}
    assert "meme_card" in visual_types
    assert "attention_visual" in visual_types
