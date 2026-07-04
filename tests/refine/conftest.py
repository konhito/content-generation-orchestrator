"""Test fixtures for the refine module."""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.config import LLMConfig
from src.project import Project, load_project
from src.understanding.llm_provider import MockLLMProvider


@pytest.fixture
def mock_llm_config():
    """Mock LLM configuration."""
    return LLMConfig(provider="mock", model="mock-model")


@pytest.fixture
def mock_llm_provider(mock_llm_config):
    """Mock LLM provider for testing."""
    return MockLLMProvider(mock_llm_config)


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory with proper structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Create directory structure
        (project_dir / "input").mkdir()
        (project_dir / "script").mkdir()
        (project_dir / "narration").mkdir()
        (project_dir / "voiceover").mkdir()
        (project_dir / "storyboard").mkdir()
        (project_dir / "scenes").mkdir()
        (project_dir / "output").mkdir()

        # Create config.json
        config = {
            "id": "test-project",
            "title": "Test Project",
            "description": "A test project",
            "version": "1.0.0",
            "video": {
                "resolution": {"width": 1920, "height": 1080},
                "fps": 30,
                "target_duration_seconds": 180,
            },
            "tts": {"provider": "mock", "voice_id": "test-voice"},
            "style": {
                "background_color": "#0f0f1a",
                "primary_color": "#00d9ff",
            },
            "paths": {
                "script": "script/script.json",
                "narration": "narration/narrations.json",
                "voiceover": "voiceover/",
                "storyboard": "storyboard/storyboard.json",
            },
        }
        with open(project_dir / "config.json", "w") as f:
            json.dump(config, f)

        yield project_dir


@pytest.fixture
def sample_narrations():
    """Sample narrations data."""
    return {
        "scenes": [
            {
                "scene_id": "scene1_hook",
                "title": "The Impossible Leap",
                "duration_seconds": 22,
                "narration": "83.3% versus 13.4%. That's OpenAI's o1 against GPT-4 on mathematical olympiad problems. Not an incremental gain—a six-fold explosion in reasoning power.",
            },
            {
                "scene_id": "scene2_context",
                "title": "The Discovery",
                "duration_seconds": 27,
                "narration": "The story begins in January 2022. Google researchers found that showing AI models how to think step-by-step dramatically improved their reasoning.",
            },
        ]
    }


@pytest.fixture
def sample_storyboard():
    """Sample storyboard data."""
    return {
        "title": "Test Video",
        "version": "2.0.0",
        "project": "test-project",
        "video": {"width": 1920, "height": 1080, "fps": 30},
        "scenes": [
            {
                "id": "scene1_hook",
                "type": "test-project/impossible_leap",
                "title": "The Impossible Leap",
                "audio_file": "scene1_hook.mp3",
                "audio_duration_seconds": 22.5,
            },
            {
                "id": "scene2_context",
                "type": "test-project/discovery",
                "title": "The Discovery",
                "audio_file": "scene2_context.mp3",
                "audio_duration_seconds": 27.0,
            },
        ],
        "total_duration_seconds": 49.5,
    }


@pytest.fixture
def sample_script():
    """Sample script data with visual_cues."""
    return {
        "title": "Test Video",
        "total_duration_seconds": 49.0,
        "scenes": [
            {
                "scene_id": "the_impossible_leap",
                "scene_type": "hook",
                "title": "The Impossible Leap",
                "voiceover": "83.3% versus 13.4%. That's OpenAI's o1 against GPT-4.",
                "duration_seconds": 22.0,
                "visual_cue": {
                    "description": "Dark glass panels with 3D depth showing comparison",
                    "visual_type": "animation",
                    "elements": [
                        "Dark glass panels with multi-layer shadows",
                        "Performance numbers with dramatic reveal",
                    ],
                    "duration_seconds": 22.0,
                },
            },
            {
                "scene_id": "the_discovery",
                "scene_type": "context",
                "title": "The Discovery",
                "voiceover": "The story begins in January 2022.",
                "duration_seconds": 27.0,
                "visual_cue": {
                    "description": "Timeline visualization of the discovery",
                    "visual_type": "animation",
                    "elements": [
                        "Timeline with key dates",
                        "Research paper highlights",
                    ],
                    "duration_seconds": 27.0,
                },
            },
        ],
    }


@pytest.fixture
def project_with_files(temp_project_dir, sample_narrations, sample_storyboard, sample_script):
    """Create a project with narrations, storyboard, and script files."""
    # Write narrations
    narrations_path = temp_project_dir / "narration" / "narrations.json"
    with open(narrations_path, "w") as f:
        json.dump(sample_narrations, f)

    # Write storyboard
    storyboard_path = temp_project_dir / "storyboard" / "storyboard.json"
    with open(storyboard_path, "w") as f:
        json.dump(sample_storyboard, f)

    # Write script.json with visual_cues
    script_path = temp_project_dir / "script" / "script.json"
    with open(script_path, "w") as f:
        json.dump(sample_script, f)

    # Create dummy voiceover files
    for scene in sample_storyboard["scenes"]:
        audio_file = temp_project_dir / "voiceover" / scene["audio_file"]
        # Create a minimal valid MP3 file (just header)
        audio_file.write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * 100)

    # Create a dummy scene file
    scene_file = temp_project_dir / "scenes" / "TheImpossibleLeapScene.tsx"
    scene_file.write_text(
        """
import React from "react";
import { AbsoluteFill } from "remotion";

export const TheImpossibleLeapScene: React.FC = () => {
    return <AbsoluteFill>Test Scene</AbsoluteFill>;
};
"""
    )

    # Load and return the project
    from src.project import load_project
    return load_project(temp_project_dir)


@pytest.fixture
def sample_beats():
    """Sample beats for testing."""
    from src.refine.models import Beat

    return [
        Beat(
            index=0,
            start_seconds=0,
            end_seconds=4,
            text="83.3% versus 13.4%",
            expected_visual="Large numbers with dramatic reveal",
        ),
        Beat(
            index=1,
            start_seconds=4,
            end_seconds=10,
            text="OpenAI's o1 against GPT-4",
            expected_visual="Model names and comparison",
        ),
        Beat(
            index=2,
            start_seconds=10,
            end_seconds=16,
            text="six-fold explosion in reasoning power",
            expected_visual="Explosive bar growth animation",
        ),
        Beat(
            index=3,
            start_seconds=16,
            end_seconds=22,
            text="September 2024 changed everything",
            expected_visual="Milestone marker",
        ),
    ]


@pytest.fixture
def mock_subprocess_run():
    """Mock subprocess.run for testing CLI commands."""
    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"beats": []}'
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        yield mock_run
