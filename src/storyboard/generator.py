"""Storyboard generator - creates storyboards from scripts and audio timing."""

import json
from pathlib import Path
from typing import Any

from ..audio.tts import TTSResult, WordTimestamp
from ..config import Config, load_config
from ..models import Script, ScriptScene
from ..understanding.llm_provider import LLMProvider, get_llm_provider
from .loader import parse_storyboard
from .models import Storyboard


STORYBOARD_SYSTEM_PROMPT = """You are an expert animation director creating storyboards for
educational explainer videos. Your storyboards are precise, visually compelling, and
perfectly synchronized with voiceover narration.

Your storyboards should:
1. Use timing that matches the voiceover exactly
2. Create smooth transitions between visual beats
3. Use sync_points to trigger animations on specific words
4. Choose appropriate components for each visual concept
5. Build visual complexity progressively

Available components:
- token_row: A row of text tokens that can activate in prefill (all at once) or decode (sequential) modes
- token: A single text token with activation state
- gpu_gauge: A progress bar showing GPU utilization with compute/memory status
- text_reveal: Text that reveals character by character
- title_card: A title card with heading and optional subheading
- progress_bar: A generic progress bar
- prompt_input: A text input field with typing animation (placeholder)
- container: A grouping container for other elements (placeholder)
- divider: A visual divider line (placeholder)
- highlight_overlay: An overlay for highlighting regions (placeholder)

Position values:
- x: "center", "left", "right", or pixel number (0-1920)
- y: "center", "top", "bottom", or pixel number (0-1080)

Transition types: "fade", "slide_up", "slide_down", "slide_left", "slide_right", "scale", "none"
Easing functions: "linear", "ease-in", "ease-out", "ease-in-out"

Always respond with valid JSON matching the storyboard schema."""


STORYBOARD_USER_PROMPT_TEMPLATE = """Create a detailed storyboard for this video scene.

Scene Information:
- Scene ID: {scene_id}
- Scene Type: {scene_type}
- Title: {scene_title}
- Duration: {duration} seconds (frames: {start_frame} to {end_frame} at 30fps)

Voiceover Text:
"{voiceover}"

Word Timestamps (for sync_points):
{word_timestamps}

Visual Cue from Script:
Type: {visual_type}
Description: {visual_description}
Elements: {visual_elements}

{example_context}

Create beats that:
1. Start at {start_seconds}s and end at {end_seconds}s
2. Have elements that appear, animate, and transition smoothly
3. Include sync_points to trigger animations on key words
4. Use appropriate components from the available list

Respond with JSON matching this schema:
{{
  "beats": [
    {{
      "id": "beat_id",
      "start_seconds": number,
      "end_seconds": number,
      "voiceover": "text for this beat",
      "elements": [
        {{
          "id": "element_id",
          "component": "component_name",
          "props": {{}},
          "position": {{"x": "center", "y": "center"}},
          "enter": {{"type": "fade", "duration_seconds": 0.5}},
          "exit": {{"type": "fade", "duration_seconds": 0.5}},
          "animations": [
            {{
              "action": "action_name",
              "at_seconds": number,
              "duration_seconds": number,
              "easing": "ease-out"
            }}
          ]
        }}
      ],
      "sync_points": [
        {{
          "trigger_word": "word",
          "trigger_seconds": number,
          "target": "element_id",
          "action": "action_name"
        }}
      ]
    }}
  ]
}}"""


class StoryboardGenerator:
    """Generates storyboards from scripts and audio timing."""

    def __init__(
        self,
        config: Config | None = None,
        llm: LLMProvider | None = None,
        examples_dir: Path | None = None,
    ):
        """Initialize the generator.

        Args:
            config: Configuration object. If None, loads default.
            llm: LLM provider. If None, creates one from config.
            examples_dir: Directory containing example storyboards.
        """
        self.config = config or load_config()
        self.llm = llm or get_llm_provider(self.config)

        if examples_dir is None:
            self.examples_dir = (
                Path(__file__).parent.parent.parent / "storyboards" / "examples"
            )
        else:
            self.examples_dir = Path(examples_dir)

    def generate(
        self,
        script: Script,
        tts_results: list[TTSResult],
    ) -> Storyboard:
        """Generate a storyboard from a script and TTS timing.

        Args:
            script: The video script with scenes.
            tts_results: TTS results for each scene with word timestamps.

        Returns:
            Complete storyboard with beats and elements.
        """
        if len(tts_results) != len(script.scenes):
            raise ValueError(
                f"Number of TTS results ({len(tts_results)}) must match "
                f"number of scenes ({len(script.scenes)})"
            )

        # Calculate scene timing
        scene_timings = self._calculate_scene_timing(tts_results)

        # Load example storyboards for context
        example_context = self._load_example_context()

        # Generate beats for each scene
        all_beats = []
        for i, (scene, tts_result) in enumerate(zip(script.scenes, tts_results)):
            start_seconds, end_seconds = scene_timings[i]

            beats = self._generate_scene_beats(
                scene=scene,
                tts_result=tts_result,
                start_seconds=start_seconds,
                end_seconds=end_seconds,
                example_context=example_context,
            )
            all_beats.extend(beats)

        # Calculate total duration
        total_duration = sum(r.duration_seconds for r in tts_results)

        # Build final storyboard
        storyboard_data = {
            "id": self._generate_id(script.title),
            "title": script.title,
            "description": f"Storyboard generated from script: {script.source_document}",
            "duration_seconds": total_duration,
            "beats": all_beats,
            "style": {
                "background_color": "#f4f4f5",
                "primary_color": "#00d9ff",
                "secondary_color": "#ff6b35",
            },
        }

        return parse_storyboard(storyboard_data)

    def _calculate_scene_timing(
        self, tts_results: list[TTSResult]
    ) -> list[tuple[float, float]]:
        """Calculate start and end times for each scene.

        Args:
            tts_results: TTS results with durations.

        Returns:
            List of (start_seconds, end_seconds) tuples.
        """
        timings = []
        current_time = 0.0

        for result in tts_results:
            start = current_time
            end = current_time + result.duration_seconds
            timings.append((start, end))
            current_time = end

        return timings

    def _load_example_context(self) -> str:
        """Load example storyboards for few-shot context.

        Returns:
            Formatted string with example storyboards.
        """
        examples = []

        if self.examples_dir.exists():
            for example_file in self.examples_dir.glob("*.json"):
                try:
                    with open(example_file) as f:
                        example = json.load(f)
                    # Extract just the beats for context
                    if "beats" in example and example["beats"]:
                        # Take first 2 beats as example
                        sample_beats = example["beats"][:2]
                        examples.append(
                            f"Example from '{example.get('title', example_file.stem)}':\n"
                            f"{json.dumps(sample_beats, indent=2)[:2000]}"
                        )
                except (json.JSONDecodeError, IOError):
                    continue

        if examples:
            return "Here are example beats for reference:\n\n" + "\n\n".join(examples)
        return ""

    def _generate_scene_beats(
        self,
        scene: ScriptScene,
        tts_result: TTSResult,
        start_seconds: float,
        end_seconds: float,
        example_context: str,
    ) -> list[dict[str, Any]]:
        """Generate beats for a single scene.

        Args:
            scene: The script scene.
            tts_result: TTS result with word timestamps.
            start_seconds: Scene start time.
            end_seconds: Scene end time.
            example_context: Example storyboards for context.

        Returns:
            List of beat dictionaries.
        """
        # Format word timestamps
        word_ts_lines = []
        for ts in tts_result.word_timestamps[:50]:  # Limit to avoid token overflow
            word_ts_lines.append(
                f"  {ts.word}: {ts.start_seconds + start_seconds:.2f}s - "
                f"{ts.end_seconds + start_seconds:.2f}s"
            )
        word_timestamps_text = "\n".join(word_ts_lines) if word_ts_lines else "None"

        # Build the prompt
        prompt = STORYBOARD_USER_PROMPT_TEMPLATE.format(
            scene_id=scene.scene_id,
            scene_type=scene.scene_type,
            scene_title=scene.title,
            duration=end_seconds - start_seconds,
            start_frame=int(start_seconds * 30),
            end_frame=int(end_seconds * 30),
            voiceover=scene.voiceover,
            word_timestamps=word_timestamps_text,
            visual_type=scene.visual_cue.visual_type,
            visual_description=scene.visual_cue.description,
            visual_elements=", ".join(scene.visual_cue.elements)
            if scene.visual_cue.elements
            else "None specified",
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            example_context=example_context,
        )

        # Generate beats via LLM
        result = self.llm.generate_json(prompt, STORYBOARD_SYSTEM_PROMPT)

        # Adjust beat timings to be absolute
        beats = result.get("beats", [])
        for beat in beats:
            # Ensure beat has required fields
            if "id" not in beat:
                beat["id"] = f"scene_{scene.scene_id}_beat"
            if "voiceover" not in beat:
                beat["voiceover"] = scene.voiceover

        return beats

    def _generate_id(self, title: str) -> str:
        """Generate a valid storyboard ID from title.

        Args:
            title: The storyboard title.

        Returns:
            Valid ID string (lowercase alphanumeric with underscores).
        """
        import re

        # Convert to lowercase, replace spaces and special chars with underscores
        id_str = re.sub(r"[^a-z0-9]+", "_", title.lower())
        # Remove leading/trailing underscores
        id_str = id_str.strip("_")
        # Ensure it starts with a letter
        if id_str and id_str[0].isdigit():
            id_str = "s_" + id_str
        return id_str or "storyboard"

    def generate_from_beats(
        self,
        title: str,
        beats: list[dict[str, Any]],
        duration_seconds: float,
        audio_file: str | None = None,
    ) -> Storyboard:
        """Create a storyboard from pre-generated beats.

        Useful for manually creating storyboards or combining beats
        from multiple sources.

        Args:
            title: Storyboard title.
            beats: List of beat dictionaries.
            duration_seconds: Total storyboard duration.
            audio_file: Optional audio file path.

        Returns:
            Complete storyboard.
        """
        storyboard_data: dict[str, Any] = {
            "id": self._generate_id(title),
            "title": title,
            "duration_seconds": duration_seconds,
            "beats": beats,
            "style": {
                "background_color": "#f4f4f5",
                "primary_color": "#00d9ff",
                "secondary_color": "#ff6b35",
            },
        }

        if audio_file:
            storyboard_data["audio"] = {
                "file": audio_file,
                "duration_seconds": duration_seconds,
            }

        return parse_storyboard(storyboard_data)
