"""Video composer - assemble videos from animation and audio assets."""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config import Config, load_config
from ..models import Script, Storyboard


@dataclass
class VideoSegment:
    """A segment of video with associated audio."""

    scene_id: str  # Slug-based ID like "the_impossible_leap"
    video_path: Path
    audio_path: Path | None
    duration_seconds: float
    start_time: float = 0.0


@dataclass
class CompositionResult:
    """Result of video composition."""

    output_path: Path
    duration_seconds: float
    resolution: tuple[int, int]
    file_size_bytes: int
    segments_used: int


class VideoComposer:
    """Compose final videos from animation and audio segments."""

    def __init__(self, config: Config | None = None):
        """Initialize the composer.

        Args:
            config: Configuration object. If None, loads default.
        """
        self.config = config or load_config()
        self._check_ffmpeg()

    def _check_ffmpeg(self) -> None:
        """Check if FFmpeg is available."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError("FFmpeg not working properly")
        except FileNotFoundError:
            raise RuntimeError(
                "FFmpeg not found. Please install FFmpeg to use video composition."
            )

    def compose(
        self,
        segments: list[VideoSegment],
        output_path: str | Path,
        background_music: Path | None = None,
        music_volume: float = 0.1,
    ) -> CompositionResult:
        """Compose a video from segments.

        Args:
            segments: List of video segments to combine
            output_path: Path for the output video
            background_music: Optional background music track
            music_volume: Volume for background music (0.0-1.0)

        Returns:
            CompositionResult with output info
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not segments:
            raise ValueError("No segments provided")

        # Create a temporary concat file
        concat_file = output_path.parent / f"{output_path.stem}_concat.txt"
        self._write_concat_file(segments, concat_file)

        try:
            # Build FFmpeg command
            cmd = self._build_compose_command(
                segments=segments,
                concat_file=concat_file,
                output_path=output_path,
                background_music=background_music,
                music_volume=music_volume,
            )

            # Run FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg failed: {result.stderr}")

            # Get output info
            duration = sum(s.duration_seconds for s in segments)
            file_size = output_path.stat().st_size

            return CompositionResult(
                output_path=output_path,
                duration_seconds=duration,
                resolution=(self.config.video.width, self.config.video.height),
                file_size_bytes=file_size,
                segments_used=len(segments),
            )

        finally:
            # Clean up concat file
            concat_file.unlink(missing_ok=True)

    def _write_concat_file(
        self, segments: list[VideoSegment], concat_file: Path
    ) -> None:
        """Write FFmpeg concat demuxer file."""
        with open(concat_file, "w") as f:
            for segment in segments:
                # FFmpeg concat requires proper escaping
                video_path = str(segment.video_path.absolute()).replace("'", "'\\''")
                f.write(f"file '{video_path}'\n")

    def _build_compose_command(
        self,
        segments: list[VideoSegment],
        concat_file: Path,
        output_path: Path,
        background_music: Path | None,
        music_volume: float,
    ) -> list[str]:
        """Build the FFmpeg command for composition."""
        cmd = ["ffmpeg", "-y"]  # -y to overwrite output

        # Input: concatenated video segments
        cmd.extend(["-f", "concat", "-safe", "0", "-i", str(concat_file)])

        # If we have audio, we need to handle it
        # For now, we'll assume the video segments already have audio baked in
        # In a full implementation, we'd mix audio tracks here

        if background_music:
            cmd.extend(["-i", str(background_music)])
            # Mix background music with video audio
            cmd.extend([
                "-filter_complex",
                f"[1:a]volume={music_volume}[bg];[0:a][bg]amix=inputs=2:duration=first[aout]",
                "-map", "0:v",
                "-map", "[aout]",
            ])

        # Output settings
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            str(output_path),
        ])

        return cmd

    def compose_with_audio_overlay(
        self,
        video_path: Path,
        audio_path: Path,
        output_path: Path,
    ) -> CompositionResult:
        """Combine a video with an audio track.

        Args:
            video_path: Path to the video file
            audio_path: Path to the audio file
            output_path: Path for the output video

        Returns:
            CompositionResult with output info
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")

        # Get duration from output file
        duration = self._get_video_duration(output_path)
        file_size = output_path.stat().st_size

        return CompositionResult(
            output_path=output_path,
            duration_seconds=duration,
            resolution=(self.config.video.width, self.config.video.height),
            file_size_bytes=file_size,
            segments_used=1,
        )

    def _get_video_duration(self, video_path: Path) -> float:
        """Get the duration of a video file."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            str(video_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return 0.0

        try:
            data = json.loads(result.stdout)
            return float(data.get("format", {}).get("duration", 0))
        except (json.JSONDecodeError, ValueError):
            return 0.0

    def generate_thumbnail(
        self,
        video_path: Path,
        output_path: Path,
        timestamp: float = 5.0,
    ) -> Path:
        """Generate a thumbnail from a video.

        Args:
            video_path: Path to the video
            output_path: Path for the thumbnail image
            timestamp: Time in seconds to capture

        Returns:
            Path to the thumbnail
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(timestamp),
            "-i", str(video_path),
            "-vframes", "1",
            "-q:v", "2",
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Thumbnail generation failed: {result.stderr}")

        return output_path

    def add_captions(
        self,
        video_path: Path,
        captions_path: Path,
        output_path: Path,
    ) -> CompositionResult:
        """Add captions/subtitles to a video.

        Args:
            video_path: Path to the video
            captions_path: Path to the SRT/VTT captions file
            output_path: Path for the output video

        Returns:
            CompositionResult with output info
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Burn subtitles into video
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vf", f"subtitles={captions_path}",
            "-c:a", "copy",
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Caption overlay failed: {result.stderr}")

        duration = self._get_video_duration(output_path)
        file_size = output_path.stat().st_size

        return CompositionResult(
            output_path=output_path,
            duration_seconds=duration,
            resolution=(self.config.video.width, self.config.video.height),
            file_size_bytes=file_size,
            segments_used=1,
        )
