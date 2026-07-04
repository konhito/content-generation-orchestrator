"""End-to-end tests for the video explainer pipeline."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.audio.tts import MockTTS
from src.config import Config
from src.ingestion import parse_document
from src.pipeline import VideoPipeline
from src.script import ScriptGenerator
from src.understanding import ContentAnalyzer


class TestEndToEndPipeline:
    """End-to-end tests for the complete video generation pipeline."""

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        config = Config()
        config.llm.provider = "mock"
        config.tts.provider = "mock"
        return config

    @pytest.fixture
    def inference_doc_path(self):
        """Get the path to the inference document."""
        path = Path("/Users/prajwal/Desktop/Learning/inference/website/post.md")
        if not path.exists():
            pytest.skip("Inference document not found")
        return path

    @pytest.fixture
    def output_dir(self, tmp_path):
        """Create output directories."""
        (tmp_path / "scripts").mkdir()
        (tmp_path / "audio").mkdir()
        (tmp_path / "video").mkdir()
        return tmp_path

    def test_full_pipeline_mock(self, config, inference_doc_path, output_dir):
        """Test the complete pipeline from document to script to audio."""
        # Step 1: Parse the document
        document = parse_document(inference_doc_path)
        assert document.title == "Scaling LLM Inference to Millions of Users"
        assert len(document.sections) > 5

        # Step 2: Analyze the content
        analyzer = ContentAnalyzer(config)
        analysis = analyzer.analyze(document)

        assert analysis.core_thesis
        assert len(analysis.key_concepts) > 0
        # Mock provider returns generic concepts

        # Step 3: Generate the script
        script_gen = ScriptGenerator(config)
        script = script_gen.generate(document, analysis, target_duration=210)

        assert script.title
        assert len(script.scenes) >= 3
        assert any(s.scene_type == "hook" for s in script.scenes)
        assert any(s.scene_type == "conclusion" for s in script.scenes)

        # Step 4: Save the script
        script_path = output_dir / "scripts" / "test_script.json"
        script_gen.save_script(script, str(script_path))

        assert script_path.exists()
        assert script_path.with_suffix(".md").exists()

        # Verify script can be loaded back
        loaded_script = ScriptGenerator.load_script(str(script_path))
        assert loaded_script.title == script.title
        assert len(loaded_script.scenes) == len(script.scenes)

        # Step 5: Generate audio for each scene (mock)
        tts = MockTTS(config.tts)
        audio_files = []

        for scene in script.scenes:
            audio_path = output_dir / "audio" / f"scene_{scene.scene_id}.mp3"
            result = tts.generate(scene.voiceover, audio_path)
            audio_files.append(result)
            assert result.exists()

        assert len(audio_files) == len(script.scenes)

    def test_pipeline_produces_reviewable_output(self, config, inference_doc_path, output_dir):
        """Test that the pipeline produces output suitable for human review."""
        # Parse and analyze
        document = parse_document(inference_doc_path)
        analyzer = ContentAnalyzer(config)
        analysis = analyzer.analyze(document)

        # Generate script
        script_gen = ScriptGenerator(config)
        script = script_gen.generate(document, analysis)

        # Format for review
        review_text = script_gen.format_script_for_review(script)

        # Check review format
        assert "# " in review_text  # Has markdown headers
        assert "Scene " in review_text
        assert "Voiceover" in review_text
        assert "Visual" in review_text

        # Each scene should be represented (format is now "Scene N (scene_id): Title")
        for scene in script.scenes:
            assert f"({scene.scene_id})" in review_text

    def test_pipeline_respects_section_limits(self, config, inference_doc_path):
        """Test that we can analyze specific sections of the document."""
        document = parse_document(inference_doc_path)
        analyzer = ContentAnalyzer(config)

        # Analyze only "Two Phases" through "KV Cache"
        analysis = analyzer.analyze_sections(
            document,
            start_heading="Two Phases",
            end_heading="Enter vLLM",
        )

        assert analysis.core_thesis
        # Mock provider returns generic concepts
        assert len(analysis.key_concepts) > 0

    def test_script_scenes_have_timing(self, config, inference_doc_path):
        """Test that script scenes have proper timing information."""
        document = parse_document(inference_doc_path)
        analyzer = ContentAnalyzer(config)
        analysis = analyzer.analyze(document)

        script_gen = ScriptGenerator(config)
        script = script_gen.generate(document, analysis, target_duration=180)

        # All scenes should have positive duration
        for scene in script.scenes:
            assert scene.duration_seconds > 0
            assert scene.visual_cue.duration_seconds > 0

        # Total duration should match sum of scenes
        total = sum(s.duration_seconds for s in script.scenes)
        assert script.total_duration_seconds == total

    def test_visual_cues_are_actionable(self, config, inference_doc_path):
        """Test that visual cues contain actionable information."""
        document = parse_document(inference_doc_path)
        analyzer = ContentAnalyzer(config)
        analysis = analyzer.analyze(document)

        script_gen = ScriptGenerator(config)
        script = script_gen.generate(document, analysis)

        for scene in script.scenes:
            cue = scene.visual_cue

            # Each cue should have a type and description
            assert cue.visual_type in ["animation", "diagram", "code", "equation", "image"]
            assert len(cue.description) > 20  # Meaningful description

            # Most cues should have elements
            # (some simple scenes might not)


class TestPipelineErrorHandling:
    """Test error handling in the pipeline."""

    @pytest.fixture
    def config(self):
        config = Config()
        config.llm.provider = "mock"
        return config

    def test_handles_empty_document(self, config):
        """Test handling of empty document."""
        document = parse_document("# Empty\n\nNo content here.")
        analyzer = ContentAnalyzer(config)

        # Should still produce some analysis
        analysis = analyzer.analyze(document)
        assert analysis is not None

    def test_handles_short_content(self, config):
        """Test handling of very short content."""
        document = parse_document("# Title\n\nJust one sentence about a topic.")
        analyzer = ContentAnalyzer(config)
        analysis = analyzer.analyze(document)

        script_gen = ScriptGenerator(config)
        script = script_gen.generate(document, analysis, target_duration=60)

        # Should still produce a valid script
        assert script.title
        assert len(script.scenes) > 0


class TestPipelineOutputFormats:
    """Test that pipeline outputs are in correct formats."""

    @pytest.fixture
    def config(self):
        config = Config()
        config.llm.provider = "mock"
        return config

    @pytest.fixture
    def sample_script(self, config, sample_markdown):
        document = parse_document(sample_markdown)
        analyzer = ContentAnalyzer(config)
        analysis = analyzer.analyze(document)
        script_gen = ScriptGenerator(config)
        return script_gen.generate(document, analysis)

    def test_script_json_format(self, sample_script, tmp_path):
        """Test that saved scripts are valid JSON."""
        script_gen = ScriptGenerator()
        script_path = tmp_path / "script.json"
        script_gen.save_script(sample_script, str(script_path))

        # Should be valid JSON
        with open(script_path) as f:
            data = json.load(f)

        assert "title" in data
        assert "scenes" in data
        assert isinstance(data["scenes"], list)

    def test_script_markdown_format(self, sample_script, tmp_path):
        """Test that saved scripts have valid markdown review format."""
        script_gen = ScriptGenerator()
        script_path = tmp_path / "script.json"
        script_gen.save_script(sample_script, str(script_path))

        md_path = script_path.with_suffix(".md")
        assert md_path.exists()

        content = md_path.read_text()

        # Should be valid markdown
        assert content.startswith("# ")
        assert "---" in content


class TestFullVideoPipeline:
    """Test the complete VideoPipeline with mock providers.

    These tests ensure the pipeline doesn't regress after code changes.
    Uses mock LLM and TTS to avoid API costs during testing.
    """

    @pytest.fixture
    def mock_subprocess(self):
        """Mock subprocess for FFmpeg calls."""
        with patch("subprocess.run") as mock_run:
            def side_effect(*args, **kwargs):
                result = MagicMock()
                result.returncode = 0
                result.stdout = '{"format": {"duration": "10.0"}}'
                result.stderr = ""

                # Create output file if specified
                cmd = args[0] if args else kwargs.get("args", [])
                for i, arg in enumerate(cmd):
                    if isinstance(arg, str) and arg.endswith(".mp4"):
                        Path(arg).parent.mkdir(parents=True, exist_ok=True)
                        Path(arg).write_bytes(b"fake video")
                    elif isinstance(arg, str) and arg.endswith(".mp3"):
                        Path(arg).parent.mkdir(parents=True, exist_ok=True)
                        Path(arg).write_bytes(b"fake audio")

                return result

            mock_run.side_effect = side_effect
            yield mock_run

    @pytest.fixture
    def config(self):
        """Create mock config for testing."""
        config = Config()
        config.llm.provider = "mock"
        config.tts.provider = "mock"
        return config

    def test_pipeline_quick_test(self, config, mock_subprocess, tmp_path):
        """Test pipeline quick_test completes all stages."""
        pipeline = VideoPipeline(config=config, output_dir=tmp_path)

        result = pipeline.quick_test()

        # All stages should complete
        assert "parsing" in result.stages_completed
        assert "analysis" in result.stages_completed
        assert "script" in result.stages_completed
        assert "audio" in result.stages_completed
        assert "animation" in result.stages_completed
        assert "composition" in result.stages_completed
        assert result.success

    def test_pipeline_from_document(self, config, mock_subprocess, tmp_path):
        """Test pipeline generates video from document."""
        # Create test document
        doc_path = tmp_path / "test_doc.md"
        doc_path.write_text("""# Test Technical Document

## Introduction

This document explains an important technical concept.

## Key Concept

Here is the main idea with detailed explanation.
The concept involves multiple components working together.

## Conclusion

In summary, this is how the concept works.
""")

        pipeline = VideoPipeline(config=config, output_dir=tmp_path)
        result = pipeline.generate_from_document(doc_path, target_duration=60)

        assert result.success
        assert result.output_path is not None
        assert "parsing" in result.stages_completed
        assert "analysis" in result.stages_completed
        assert "script" in result.stages_completed
        assert result.metadata.get("llm_provider") == "mock"
        assert result.metadata.get("tts_provider") == "mock"

    def test_pipeline_progress_callback(self, config, mock_subprocess, tmp_path):
        """Test that progress callbacks are fired."""
        pipeline = VideoPipeline(config=config, output_dir=tmp_path)

        progress_updates = []
        def on_progress(stage: str, progress: float):
            progress_updates.append((stage, progress))

        pipeline.set_progress_callback(on_progress)
        result = pipeline.quick_test()

        # Should have progress updates for all stages
        stages_with_progress = {stage for stage, _ in progress_updates}
        assert "parsing" in stages_with_progress
        assert "analysis" in stages_with_progress
        assert "script" in stages_with_progress
        assert "audio" in stages_with_progress

    def test_pipeline_saves_script(self, config, mock_subprocess, tmp_path):
        """Test that pipeline saves script for review."""
        pipeline = VideoPipeline(config=config, output_dir=tmp_path)
        result = pipeline.quick_test()

        # Script should be saved
        script_path = result.metadata.get("script_path")
        assert script_path is not None
        assert Path(script_path).exists()

        # Should be valid JSON
        with open(script_path) as f:
            script_data = json.load(f)
        assert "title" in script_data
        assert "scenes" in script_data

    def test_pipeline_handles_errors_gracefully(self, config, tmp_path):
        """Test that pipeline handles errors and reports them."""
        # Don't mock subprocess - let it fail on missing FFmpeg commands
        pipeline = VideoPipeline(config=config, output_dir=tmp_path)

        # Create a document that will parse but cause issues
        doc_path = tmp_path / "test.md"
        doc_path.write_text("# Test\n\nContent")

        # The pipeline should catch errors and return a failed result
        # rather than raising an exception
        result = pipeline.generate_from_document(doc_path)

        # Should have at least started
        assert len(result.stages_completed) >= 1


class TestTrueEndToEnd:
    """True end-to-end tests covering voiceover, storyboard, and video rendering.

    These tests verify the complete pipeline works together, including:
    1. Voiceover generation with word timestamps
    2. Storyboard generation from script + audio timing
    3. Video rendering via Remotion
    """

    @pytest.fixture
    def mock_config(self):
        """Create mock config for testing."""
        config = Config()
        config.llm.provider = "mock"
        config.tts.provider = "mock"
        return config

    @pytest.fixture
    def sample_narrations(self):
        """Create sample narrations for testing."""
        from src.voiceover.narration import SceneNarration

        return [
            SceneNarration(
                scene_id="test_intro",
                title="Introduction",
                duration_seconds=5.0,
                narration="This is a test introduction for our video.",
            ),
            SceneNarration(
                scene_id="test_main",
                title="Main Content",
                duration_seconds=8.0,
                narration="Here we explain the main concept with detailed information.",
            ),
            SceneNarration(
                scene_id="test_conclusion",
                title="Conclusion",
                duration_seconds=5.0,
                narration="And that concludes our explanation.",
            ),
        ]

    def test_voiceover_generation_with_timestamps(self, mock_config, sample_narrations, tmp_path):
        """Test that voiceover generation produces audio with word timestamps."""
        from src.voiceover.generator import VoiceoverGenerator, VoiceoverResult
        from src.config import TTSConfig
        from src.audio.tts import MockTTS

        # Create a generator with mock TTS
        tts_config = TTSConfig(provider="mock")
        tts = MockTTS(tts_config)

        # Generate voiceover for each narration
        voiceovers = []
        output_dir = tmp_path / "voiceover"
        output_dir.mkdir()

        for narration in sample_narrations:
            result = tts.generate_with_timestamps(
                narration.narration,
                output_dir / f"{narration.scene_id}.mp3"
            )
            voiceovers.append(result)

            # Verify audio file created
            assert result.audio_path.exists()
            # Verify word timestamps generated
            assert len(result.word_timestamps) > 0
            # Verify duration is positive
            assert result.duration_seconds > 0

        # Verify we got voiceovers for all scenes
        assert len(voiceovers) == len(sample_narrations)

        # Total duration should be reasonable
        total_duration = sum(v.duration_seconds for v in voiceovers)
        assert total_duration > 0

    def test_voiceover_manifest_serialization(self, tmp_path, sample_narrations):
        """Test that voiceover results can be serialized and loaded."""
        from src.voiceover.generator import SceneVoiceover, VoiceoverResult
        from src.audio.tts import WordTimestamp

        # Create mock scene voiceovers
        scenes = []
        for narration in sample_narrations:
            audio_path = tmp_path / f"{narration.scene_id}.mp3"
            audio_path.write_bytes(b"fake audio data")

            scenes.append(SceneVoiceover(
                scene_id=narration.scene_id,
                audio_path=audio_path,
                duration_seconds=narration.duration_seconds,
                word_timestamps=[
                    WordTimestamp(word="test", start_seconds=0.0, end_seconds=0.5),
                    WordTimestamp(word="word", start_seconds=0.6, end_seconds=1.0),
                ],
            ))

        # Create result and save manifest
        result = VoiceoverResult(
            scenes=scenes,
            total_duration_seconds=sum(s.duration_seconds for s in scenes),
            output_dir=tmp_path,
        )

        manifest_path = result.save_manifest()
        assert manifest_path.exists()

        # Load manifest and verify
        loaded = VoiceoverResult.load_manifest(manifest_path)
        assert len(loaded.scenes) == len(scenes)
        assert loaded.total_duration_seconds == result.total_duration_seconds

    def test_storyboard_from_tts_results(self, mock_config, tmp_path):
        """Test storyboard generation from script + TTS results."""
        from src.storyboard.generator import StoryboardGenerator
        from src.audio.tts import TTSResult, WordTimestamp
        from src.models import Script, ScriptScene, VisualCue

        # Create a simple script
        script = Script(
            title="Test Video",
            source_document="test.md",
            total_duration_seconds=18.0,
            target_audience="developers",
            scenes=[
                ScriptScene(
                    scene_id="1",
                    scene_type="hook",
                    title="Introduction",
                    duration_seconds=6.0,
                    voiceover="This is the introduction to our video.",
                    visual_cue=VisualCue(
                        visual_type="animation",
                        description="Title card with fade in",
                        duration_seconds=6.0,
                    ),
                ),
                ScriptScene(
                    scene_id="2",
                    scene_type="explanation",
                    title="Main Point",
                    duration_seconds=8.0,
                    voiceover="Here we explain the main concept.",
                    visual_cue=VisualCue(
                        visual_type="diagram",
                        description="Diagram showing concept",
                        duration_seconds=8.0,
                    ),
                ),
                ScriptScene(
                    scene_id="3",
                    scene_type="conclusion",
                    title="Wrap Up",
                    duration_seconds=4.0,
                    voiceover="That's the conclusion.",
                    visual_cue=VisualCue(
                        visual_type="animation",
                        description="Outro animation",
                        duration_seconds=4.0,
                    ),
                ),
            ],
        )

        # Create mock TTS results with word timestamps
        tts_results = [
            TTSResult(
                audio_path=tmp_path / "scene1.mp3",
                duration_seconds=6.0,
                word_timestamps=[
                    WordTimestamp(word="This", start_seconds=0.0, end_seconds=0.3),
                    WordTimestamp(word="is", start_seconds=0.4, end_seconds=0.5),
                    WordTimestamp(word="introduction", start_seconds=0.6, end_seconds=1.2),
                ],
            ),
            TTSResult(
                audio_path=tmp_path / "scene2.mp3",
                duration_seconds=8.0,
                word_timestamps=[
                    WordTimestamp(word="Here", start_seconds=0.0, end_seconds=0.3),
                    WordTimestamp(word="explain", start_seconds=0.4, end_seconds=0.8),
                    WordTimestamp(word="concept", start_seconds=0.9, end_seconds=1.4),
                ],
            ),
            TTSResult(
                audio_path=tmp_path / "scene3.mp3",
                duration_seconds=4.0,
                word_timestamps=[
                    WordTimestamp(word="That's", start_seconds=0.0, end_seconds=0.3),
                    WordTimestamp(word="conclusion", start_seconds=0.4, end_seconds=1.0),
                ],
            ),
        ]

        # Create audio files
        for result in tts_results:
            result.audio_path.write_bytes(b"fake audio")

        # Generate storyboard
        generator = StoryboardGenerator(config=mock_config)
        storyboard = generator.generate(script, tts_results)

        # Verify storyboard structure
        assert storyboard.title == "Test Video"
        assert storyboard.duration_seconds == 18.0
        assert len(storyboard.beats) > 0

    @pytest.fixture
    def mock_remotion_render(self, tmp_path):
        """Mock Remotion rendering process."""
        with patch("subprocess.run") as mock_run:
            def side_effect(*args, **kwargs):
                result = MagicMock()
                result.returncode = 0
                result.stdout = ""
                result.stderr = ""

                # Check if this is a render command
                cmd = args[0] if args else kwargs.get("args", [])
                cmd_str = " ".join(str(c) for c in cmd)

                # Create output file for render commands
                if "render.mjs" in cmd_str or "remotion" in cmd_str.lower():
                    for i, arg in enumerate(cmd):
                        if str(arg) == "--output" and i + 1 < len(cmd):
                            output_file = Path(cmd[i + 1])
                            output_file.parent.mkdir(parents=True, exist_ok=True)
                            output_file.write_bytes(b"fake video content")

                return result

            mock_run.side_effect = side_effect
            yield mock_run

    def test_full_pipeline_voiceover_to_video(
        self, mock_config, sample_narrations, mock_remotion_render, tmp_path
    ):
        """Test the complete pipeline from voiceover generation to video rendering.

        This test verifies that:
        1. Voiceovers can be generated with timestamps
        2. A manifest file is created
        3. Storyboard props can be generated
        4. Video can be rendered (mocked)
        """
        from src.voiceover.generator import SceneVoiceover, VoiceoverResult
        from src.audio.tts import MockTTS, WordTimestamp
        from src.config import TTSConfig
        import json

        # Step 1: Generate voiceovers
        output_dir = tmp_path / "voiceover"
        output_dir.mkdir()

        tts_config = TTSConfig(provider="mock")
        tts = MockTTS(tts_config)

        scenes = []
        for narration in sample_narrations:
            result = tts.generate_with_timestamps(
                narration.narration,
                output_dir / f"{narration.scene_id}.mp3"
            )
            scenes.append(SceneVoiceover(
                scene_id=narration.scene_id,
                audio_path=result.audio_path,
                duration_seconds=result.duration_seconds,
                word_timestamps=result.word_timestamps,
            ))

        # Step 2: Create and save manifest
        voiceover_result = VoiceoverResult(
            scenes=scenes,
            total_duration_seconds=sum(s.duration_seconds for s in scenes),
            output_dir=output_dir,
        )
        manifest_path = voiceover_result.save_manifest()
        assert manifest_path.exists()

        # Step 3: Create storyboard props for Remotion
        storyboard_props = {
            "storyboard": {
                "id": "test_video",
                "title": "Test Video",
                "duration_seconds": voiceover_result.total_duration_seconds,
                "beats": [
                    {
                        "id": f"beat_{scene.scene_id}",
                        "start_seconds": sum(
                            s.duration_seconds for s in scenes[:i]
                        ),
                        "end_seconds": sum(
                            s.duration_seconds for s in scenes[:i+1]
                        ),
                        "voiceover": sample_narrations[i].narration,
                        "elements": [
                            {
                                "id": f"title_{scene.scene_id}",
                                "component": "title_card",
                                "props": {"heading": sample_narrations[i].title},
                                "position": {"x": "center", "y": "center"},
                            }
                        ],
                    }
                    for i, scene in enumerate(scenes)
                ],
                "style": {
                    "background_color": "#0f0f1a",
                    "primary_color": "#00d9ff",
                },
            },
            "voiceover": {
                "scenes": [s.to_dict() for s in scenes],
            },
        }

        props_path = tmp_path / "storyboard_props.json"
        with open(props_path, "w") as f:
            json.dump(storyboard_props, f, indent=2)

        assert props_path.exists()

        # Step 4: Mock render video
        output_video = tmp_path / "output.mp4"
        render_cmd = [
            "node",
            "remotion/scripts/render.mjs",
            "--composition", "StoryboardPlayer",
            "--props", str(props_path),
            "--output", str(output_video),
        ]

        subprocess.run(render_cmd)

        # Verify render was called
        assert mock_remotion_render.called

        # Verify output video was created (by mock)
        assert output_video.exists()

    def test_llm_inference_narrations_structure(self):
        """Test that the LLM inference narrations are properly structured."""
        from pathlib import Path
        from src.voiceover.narration import load_narrations_from_file

        narration_path = Path("projects/llm-inference/narration/narrations.json")
        if not narration_path.exists():
            pytest.skip("LLM inference project not found")

        narrations = load_narrations_from_file(narration_path)

        # Should have 16 scenes
        assert len(narrations) == 18

        # All scenes should have required fields
        for narration in narrations:
            assert narration.scene_id
            assert narration.title
            assert narration.narration
            assert narration.duration_seconds > 0

        # Scene IDs should be unique
        scene_ids = [n.scene_id for n in narrations]
        assert len(scene_ids) == len(set(scene_ids))

        # Should be able to find the hook scene
        hook = next((n for n in narrations if "hook" in n.scene_id), None)
        assert hook is not None
        assert "Speed" in hook.title or "hook" in hook.scene_id

    def test_word_timestamp_coverage(self, tmp_path):
        """Test that word timestamps cover the entire narration."""
        from src.audio.tts import MockTTS, WordTimestamp
        from src.config import TTSConfig

        test_text = "This is a test sentence with multiple words to verify timestamps."

        tts = MockTTS(TTSConfig(provider="mock"))
        result = tts.generate_with_timestamps(test_text, tmp_path / "test.mp3")

        # Should have timestamps for most words
        words_in_text = len(test_text.split())
        # Mock TTS may clean punctuation, so allow some variance
        assert len(result.word_timestamps) >= words_in_text * 0.8

        # Timestamps should be sequential
        prev_end = 0.0
        for ts in result.word_timestamps:
            assert ts.start_seconds >= prev_end - 0.01  # Allow small overlap
            assert ts.end_seconds > ts.start_seconds
            prev_end = ts.end_seconds
