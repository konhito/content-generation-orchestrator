"""SFX Cue Generator - converts SoundMoments to frame-accurate SFX cues.

This module handles the conversion from detected animation moments
to concrete SFX cues that can be rendered in the video.

It can either:
1. Use existing sounds from the library (simpler, faster)
2. Generate custom sounds per scene (richer, more tailored)
"""

from pathlib import Path
from typing import Optional

from .models import (
    SoundMoment,
    SFXCue,
    SceneAnalysisResult,
    calculate_volume,
    get_sound_for_moment,
    VOLUME_BY_TYPE,
    MOMENT_TO_SOUND,
)
from .generator import SoundGenerator, SoundEvent, SoundTheme, save_wav


# Mapping from moment types to SoundEvent enum
MOMENT_TO_EVENT = {
    "element_appear": SoundEvent.ELEMENT_APPEAR,
    "element_disappear": SoundEvent.ELEMENT_DISAPPEAR,
    "text_reveal": SoundEvent.TEXT_REVEAL,
    "reveal": SoundEvent.REVEAL,
    "counter": SoundEvent.COUNTER,
    "transition": SoundEvent.TRANSITION,
    "warning": SoundEvent.WARNING,
    "success": SoundEvent.SUCCESS,
    "lock": SoundEvent.LOCK,
    "data_flow": SoundEvent.DATA_FLOW,
    "connection": SoundEvent.CONNECTION,
    "highlight": SoundEvent.PING,
    "chart_grow": SoundEvent.COUNTER,
    "pulse": SoundEvent.PULSE,
}


class CueGenerator:
    """Generates SFX cues from detected sound moments.

    Can operate in two modes:
    1. Library mode: Use pre-generated sounds from the library
    2. Custom mode: Generate unique sounds per scene
    """

    def __init__(
        self,
        use_library: bool = True,
        theme: SoundTheme = SoundTheme.TECH_AI,
        sfx_dir: Optional[Path] = None,
    ):
        """Initialize the cue generator.

        Args:
            use_library: If True, use pre-generated library sounds.
                        If False, generate custom sounds per scene.
            theme: Sound theme for custom generation
            sfx_dir: Directory for custom sound files
        """
        self.use_library = use_library
        self.theme = theme
        self.sfx_dir = sfx_dir
        self.generator = SoundGenerator(theme) if not use_library else None

    def generate_cues(
        self,
        moments: list[SoundMoment],
        scene_id: str,
    ) -> list[SFXCue]:
        """Generate SFX cues from a list of sound moments.

        Args:
            moments: List of detected sound moments
            scene_id: Scene identifier (used for custom sound naming)

        Returns:
            List of SFXCue objects ready for storyboard
        """
        if self.use_library:
            return self._generate_library_cues(moments)
        else:
            return self._generate_custom_cues(moments, scene_id)

    def _generate_library_cues(self, moments: list[SoundMoment]) -> list[SFXCue]:
        """Generate cues using pre-existing library sounds."""
        cues = []

        for moment in moments:
            sound_name = get_sound_for_moment(moment.type)
            volume = calculate_volume(moment)

            cue = SFXCue(
                sound=sound_name,
                frame=moment.frame,
                volume=round(volume, 3),
                duration_frames=moment.duration_frames,
            )
            cues.append(cue)

        return cues

    def _generate_custom_cues(
        self,
        moments: list[SoundMoment],
        scene_id: str,
    ) -> list[SFXCue]:
        """Generate cues with custom sounds per scene."""
        if self.generator is None:
            self.generator = SoundGenerator(self.theme)

        if self.sfx_dir is None:
            raise ValueError("sfx_dir must be set for custom sound generation")

        self.sfx_dir.mkdir(parents=True, exist_ok=True)

        cues = []

        for i, moment in enumerate(moments):
            # Get the corresponding SoundEvent
            event = MOMENT_TO_EVENT.get(moment.type, SoundEvent.ELEMENT_APPEAR)

            # Calculate parameters based on moment context
            pitch_offset = self._calculate_pitch(moment, i, len(moments))
            duration = self._calculate_duration(moment)
            volume = calculate_volume(moment)

            # Generate unique sound with reproducible seed
            seed = hash(f"{scene_id}_{moment.type}_{i}_{moment.frame}") & 0xFFFFFFFF

            samples = self.generator.generate(
                event=event,
                duration=duration,
                intensity=moment.intensity,
                pitch_offset=pitch_offset,
                variation_seed=seed,
            )

            # Create unique sound name
            sound_name = f"{scene_id}_{moment.type}_{i}"
            sound_path = self.sfx_dir / f"{sound_name}.wav"
            save_wav(samples, sound_path)

            cue = SFXCue(
                sound=sound_name,
                frame=moment.frame,
                volume=round(volume, 3),
                duration_frames=moment.duration_frames,
            )
            cues.append(cue)

        return cues

    def _calculate_pitch(
        self,
        moment: SoundMoment,
        index: int,
        total: int,
    ) -> float:
        """Calculate pitch offset for variety and progression.

        Lower pitch at start, higher at climax, then settling.

        Args:
            moment: The sound moment
            index: Index of this moment in the scene
            total: Total number of moments

        Returns:
            Pitch offset in semitones (-12 to +12)
        """
        if total <= 1:
            return 0.0

        # Progress through scene (0 to 1)
        progress = index / (total - 1)

        # Create a gentle arc: start low, peak at 2/3, settle
        if progress < 0.67:
            # Rising
            pitch = -2 + progress * 6  # -2 to +2
        else:
            # Settling
            pitch = 2 - (progress - 0.67) * 6  # +2 to 0

        # Adjust based on moment type
        if moment.type == "reveal":
            pitch += 2  # Reveals are higher
        elif moment.type == "warning":
            pitch -= 3  # Warnings are lower
        elif moment.type == "success":
            pitch += 1  # Success is slightly higher

        return max(-12, min(12, pitch))

    def _calculate_duration(self, moment: SoundMoment) -> float:
        """Calculate appropriate sound duration for a moment.

        Args:
            moment: The sound moment

        Returns:
            Duration in seconds
        """
        # Base durations by type
        durations = {
            "element_appear": 0.15,
            "element_disappear": 0.12,
            "text_reveal": 0.05,
            "reveal": 0.5,
            "counter": 0.3,
            "transition": 0.35,
            "warning": 0.4,
            "success": 0.35,
            "lock": 0.12,
            "data_flow": 0.4,
            "connection": 0.15,
            "highlight": 0.1,
            "chart_grow": 0.3,
            "pulse": 0.15,
        }

        base_duration = durations.get(moment.type, 0.2)

        # Scale by intensity
        return base_duration * (0.8 + 0.4 * moment.intensity)


class SceneSFXGenerator:
    """High-level generator for scene sound effects.

    Combines analysis results with cue generation to produce
    complete SFX cues for a scene.
    """

    def __init__(
        self,
        theme: SoundTheme = SoundTheme.TECH_AI,
        use_library: bool = True,
        sfx_dir: Optional[Path] = None,
    ):
        """Initialize the scene SFX generator.

        Args:
            theme: Sound theme for the project
            use_library: Whether to use library sounds
            sfx_dir: Directory for custom sound files
        """
        self.theme = theme
        self.cue_generator = CueGenerator(
            use_library=use_library,
            theme=theme,
            sfx_dir=sfx_dir,
        )

    def generate_scene_cues(
        self,
        analysis: SceneAnalysisResult,
    ) -> list[SFXCue]:
        """Generate SFX cues for an analyzed scene.

        Args:
            analysis: Scene analysis result with detected moments

        Returns:
            List of SFXCue objects
        """
        return self.cue_generator.generate_cues(
            moments=analysis.moments,
            scene_id=analysis.scene_id,
        )

    def process_scenes(
        self,
        analyses: dict[str, SceneAnalysisResult],
    ) -> dict[str, list[SFXCue]]:
        """Process multiple scene analyses into cues.

        Args:
            analyses: Dict mapping scene IDs to analysis results

        Returns:
            Dict mapping scene IDs to lists of SFXCue
        """
        return {
            scene_id: self.generate_scene_cues(analysis)
            for scene_id, analysis in analyses.items()
        }


def generate_cues_from_moments(
    moments: list[SoundMoment],
    scene_id: str = "scene",
    use_library: bool = True,
) -> list[SFXCue]:
    """Convenience function to generate cues from moments.

    Args:
        moments: List of detected sound moments
        scene_id: Scene identifier
        use_library: Whether to use library sounds

    Returns:
        List of SFXCue objects
    """
    generator = CueGenerator(use_library=use_library)
    return generator.generate_cues(moments, scene_id)
