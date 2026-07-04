"""Text-to-Speech providers for voiceover generation."""

import asyncio
import base64
import os
import re
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import httpx

from ..config import Config, TTSConfig, load_config


@dataclass
class WordTimestamp:
    """Timestamp for a single word."""

    word: str
    start_seconds: float
    end_seconds: float


@dataclass
class TTSResult:
    """Result of TTS generation with optional timestamps."""

    audio_path: Path
    duration_seconds: float
    word_timestamps: list[WordTimestamp] = field(default_factory=list)


class TTSProvider(ABC):
    """Abstract base class for TTS providers."""

    def __init__(self, config: TTSConfig):
        self.config = config

    @abstractmethod
    def generate(self, text: str, output_path: str | Path) -> Path:
        """Generate speech from text and save to file.

        Args:
            text: The text to convert to speech
            output_path: Path to save the audio file

        Returns:
            Path to the generated audio file
        """
        pass

    @abstractmethod
    def generate_with_timestamps(
        self, text: str, output_path: str | Path
    ) -> TTSResult:
        """Generate speech with word-level timestamps.

        Args:
            text: The text to convert to speech
            output_path: Path to save the audio file

        Returns:
            TTSResult with audio path and word timestamps
        """
        pass

    @abstractmethod
    def generate_stream(self, text: str) -> Iterator[bytes]:
        """Generate speech from text as a stream.

        Args:
            text: The text to convert to speech

        Yields:
            Audio data chunks
        """
        pass

    @abstractmethod
    def get_available_voices(self) -> list[dict]:
        """Get list of available voices.

        Returns:
            List of voice info dictionaries
        """
        pass


class ElevenLabsTTS(TTSProvider):
    """ElevenLabs TTS provider."""

    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self, config: TTSConfig, api_key: str | None = None):
        """Initialize ElevenLabs TTS.

        Args:
            config: TTS configuration
            api_key: ElevenLabs API key (defaults to ELEVENLABS_API_KEY env var)
        """
        super().__init__(config)
        self.api_key = api_key or os.environ.get("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ElevenLabs API key required. Set ELEVENLABS_API_KEY environment variable "
                "or pass api_key parameter."
            )

        # Default voice if not specified
        self.voice_id = config.voice_id or "21m00Tcm4TlvDq8ikWAM"  # Rachel voice

    def _get_headers(self) -> dict[str, str]:
        """Get request headers."""
        return {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    def generate(self, text: str, output_path: str | Path) -> Path:
        """Generate speech from text and save to file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        url = f"{self.BASE_URL}/text-to-speech/{self.voice_id}"

        payload = {
            "text": text,
            "model_id": self.config.model,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        }

        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                url,
                headers=self._get_headers(),
                json=payload,
            )
            response.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(response.content)

        return output_path

    def generate_stream(self, text: str) -> Iterator[bytes]:
        """Generate speech from text as a stream."""
        url = f"{self.BASE_URL}/text-to-speech/{self.voice_id}/stream"

        payload = {
            "text": text,
            "model_id": self.config.model,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        }

        with httpx.Client(timeout=60.0) as client:
            with client.stream(
                "POST",
                url,
                headers=self._get_headers(),
                json=payload,
            ) as response:
                response.raise_for_status()
                for chunk in response.iter_bytes():
                    yield chunk

    def get_available_voices(self) -> list[dict]:
        """Get list of available voices."""
        url = f"{self.BASE_URL}/voices"

        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=self._get_headers())
            response.raise_for_status()
            data = response.json()

        return [
            {
                "voice_id": v["voice_id"],
                "name": v["name"],
                "category": v.get("category", "unknown"),
                "description": v.get("description", ""),
            }
            for v in data.get("voices", [])
        ]

    def generate_with_timestamps(
        self, text: str, output_path: str | Path
    ) -> TTSResult:
        """Generate speech with word-level timestamps using ElevenLabs API."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        url = f"{self.BASE_URL}/text-to-speech/{self.voice_id}/with-timestamps"

        payload = {
            "text": text,
            "model_id": self.config.model,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        }

        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                url,
                headers=self._get_headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        # Decode and save audio
        audio_bytes = base64.b64decode(data["audio_base64"])
        with open(output_path, "wb") as f:
            f.write(audio_bytes)

        # Parse character-level timestamps into word-level
        alignment = data.get("alignment", {})
        word_timestamps = self._parse_word_timestamps(
            alignment.get("characters", []),
            alignment.get("character_start_times_seconds", []),
            alignment.get("character_end_times_seconds", []),
        )

        # Calculate duration from last character end time
        end_times = alignment.get("character_end_times_seconds", [])
        duration = end_times[-1] if end_times else 0.0

        return TTSResult(
            audio_path=output_path,
            duration_seconds=duration,
            word_timestamps=word_timestamps,
        )

    def _parse_word_timestamps(
        self,
        characters: list[str],
        start_times: list[float],
        end_times: list[float],
    ) -> list[WordTimestamp]:
        """Convert character-level timestamps to word-level timestamps."""
        if not characters or not start_times or not end_times:
            return []

        word_timestamps = []
        current_word = ""
        word_start = None

        for i, char in enumerate(characters):
            if char.isspace():
                # End of word
                if current_word and word_start is not None:
                    word_timestamps.append(
                        WordTimestamp(
                            word=current_word,
                            start_seconds=word_start,
                            end_seconds=end_times[i - 1] if i > 0 else start_times[i],
                        )
                    )
                current_word = ""
                word_start = None
            else:
                # Part of a word
                if word_start is None:
                    word_start = start_times[i]
                current_word += char

        # Handle last word
        if current_word and word_start is not None:
            word_timestamps.append(
                WordTimestamp(
                    word=current_word,
                    start_seconds=word_start,
                    end_seconds=end_times[-1] if end_times else word_start,
                )
            )

        return word_timestamps

    def estimate_cost(self, text: str) -> float:
        """Estimate cost for generating speech.

        ElevenLabs charges per character.
        Current pricing: ~$0.30 per 1000 characters (Starter plan)

        Args:
            text: The text to estimate cost for

        Returns:
            Estimated cost in USD
        """
        # Approximate cost per character (varies by plan)
        cost_per_char = 0.0003  # $0.30 per 1000 chars
        return len(text) * cost_per_char


class EdgeTTS(TTSProvider):
    """Microsoft Edge TTS provider - free, high-quality voices."""

    # Popular natural-sounding voices
    DEFAULT_VOICES = {
        "male": "en-US-GuyNeural",
        "female": "en-US-AriaNeural",
        "british_male": "en-GB-RyanNeural",
        "british_female": "en-GB-SoniaNeural",
    }

    def __init__(self, config: TTSConfig, voice: str | None = None):
        """Initialize Edge TTS.

        Args:
            config: TTS configuration
            voice: Voice name (e.g., 'en-US-GuyNeural'). Defaults to en-US-GuyNeural.
        """
        super().__init__(config)
        self.voice = voice or config.voice_id or self.DEFAULT_VOICES["male"]

    def _run_async(self, coro):
        """Run an async coroutine synchronously."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # We're in an async context, create a new thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            return asyncio.run(coro)

    def generate(self, text: str, output_path: str | Path) -> Path:
        """Generate speech from text and save to file."""
        try:
            import edge_tts
        except ImportError:
            raise ImportError(
                "edge-tts is required for EdgeTTS provider. "
                "Install it with: pip install edge-tts"
            )

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        async def _generate():
            communicate = edge_tts.Communicate(text, self.voice)
            await communicate.save(str(output_path))

        self._run_async(_generate())
        return output_path

    def generate_with_timestamps(
        self, text: str, output_path: str | Path
    ) -> TTSResult:
        """Generate speech with word-level timestamps."""
        try:
            import edge_tts
        except ImportError:
            raise ImportError(
                "edge-tts is required for EdgeTTS provider. "
                "Install it with: pip install edge-tts"
            )

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        word_timestamps = []
        audio_data = b""

        async def _generate_with_timestamps():
            nonlocal audio_data, word_timestamps

            # Use boundary='WordBoundary' to get word-level timestamps
            communicate = edge_tts.Communicate(text, self.voice, boundary="WordBoundary")

            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
                elif chunk["type"] == "WordBoundary":
                    # Edge TTS provides word boundaries with offset and duration in 100-nanosecond units
                    offset_100ns = chunk["offset"]
                    duration_100ns = chunk["duration"]
                    start_seconds = offset_100ns / 10_000_000  # Convert 100ns to seconds
                    end_seconds = (offset_100ns + duration_100ns) / 10_000_000

                    word_timestamps.append(
                        WordTimestamp(
                            word=chunk["text"],
                            start_seconds=start_seconds,
                            end_seconds=end_seconds,
                        )
                    )

        self._run_async(_generate_with_timestamps())

        # Save audio to file
        with open(output_path, "wb") as f:
            f.write(audio_data)

        # Calculate duration from last word timestamp or audio analysis
        duration = 0.0
        if word_timestamps:
            duration = word_timestamps[-1].end_seconds
        else:
            # Fallback: estimate from audio file using ffprobe
            duration = self._get_audio_duration(output_path)

        return TTSResult(
            audio_path=output_path,
            duration_seconds=duration,
            word_timestamps=word_timestamps,
        )

    def _get_audio_duration(self, audio_path: Path) -> float:
        """Get audio duration using ffprobe."""
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(audio_path),
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return float(result.stdout.strip())
        except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
            pass
        return 0.0

    def generate_stream(self, text: str) -> Iterator[bytes]:
        """Generate speech from text as a stream."""
        try:
            import edge_tts
        except ImportError:
            raise ImportError(
                "edge-tts is required for EdgeTTS provider. "
                "Install it with: pip install edge-tts"
            )

        chunks = []

        async def _stream():
            communicate = edge_tts.Communicate(text, self.voice)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    chunks.append(chunk["data"])

        self._run_async(_stream())

        for chunk in chunks:
            yield chunk

    def get_available_voices(self) -> list[dict]:
        """Get list of available voices."""
        try:
            import edge_tts
        except ImportError:
            raise ImportError(
                "edge-tts is required for EdgeTTS provider. "
                "Install it with: pip install edge-tts"
            )

        async def _get_voices():
            voices = await edge_tts.list_voices()
            return voices

        voices = self._run_async(_get_voices())

        return [
            {
                "voice_id": v["ShortName"],
                "name": v["FriendlyName"],
                "category": v.get("VoiceTag", {}).get("VoicePersonalities", ["unknown"])[0]
                if v.get("VoiceTag") else "unknown",
                "description": f"{v['Locale']} - {v['Gender']}",
                "locale": v["Locale"],
                "gender": v["Gender"],
            }
            for v in voices
        ]

    def get_english_voices(self) -> list[dict]:
        """Get list of English voices only."""
        all_voices = self.get_available_voices()
        return [v for v in all_voices if v["locale"].startswith("en-")]


class ManualVoiceoverProvider(TTSProvider):
    """Provider for manually recorded voiceovers.

    This provider imports user-recorded audio files and uses Whisper
    to generate word-level timestamps for video synchronization.
    """

    def __init__(
        self,
        config: TTSConfig,
        audio_dir: Path | str,
        whisper_model: str = "base",
        whisper_backend: str = "auto",
    ):
        """Initialize manual voiceover provider.

        Args:
            config: TTS configuration
            audio_dir: Directory containing recorded audio files.
                       Files should be named by scene_id (e.g., scene1_hook.mp3)
            whisper_model: Whisper model size for transcription
            whisper_backend: Whisper backend ("auto", "whisper", "faster-whisper")
        """
        super().__init__(config)
        self.audio_dir = Path(audio_dir)
        self.whisper_model = whisper_model
        self.whisper_backend = whisper_backend
        self._transcriber = None

        if not self.audio_dir.exists():
            raise ValueError(f"Audio directory not found: {self.audio_dir}")

    def _get_transcriber(self):
        """Lazy load the transcriber."""
        if self._transcriber is None:
            from .transcribe import get_transcriber
            self._transcriber = get_transcriber(
                backend=self.whisper_backend,
                model=self.whisper_model,
            )
        return self._transcriber

    def _find_audio_file(self, scene_id: str) -> Path | None:
        """Find audio file for a given scene ID.

        Searches for files matching the scene_id with common audio extensions.
        """
        extensions = [".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"]

        for ext in extensions:
            # Try exact match
            audio_file = self.audio_dir / f"{scene_id}{ext}"
            if audio_file.exists():
                return audio_file

            # Try with underscores replaced by hyphens
            alt_name = scene_id.replace("_", "-")
            audio_file = self.audio_dir / f"{alt_name}{ext}"
            if audio_file.exists():
                return audio_file

        return None

    def generate(self, text: str, output_path: str | Path, scene_id: str = "") -> Path:
        """Copy recorded audio file to output path.

        Args:
            text: The expected narration text (used for verification)
            output_path: Path to save/copy the audio file
            scene_id: Scene ID to find the matching audio file

        Returns:
            Path to the copied audio file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # If no scene_id provided, try to extract from output_path
        if not scene_id:
            scene_id = output_path.stem

        # Find the source audio file
        source_file = self._find_audio_file(scene_id)
        if source_file is None:
            available = list(self.audio_dir.glob("*.*"))
            available_names = [f.stem for f in available if f.suffix in [".mp3", ".wav", ".m4a"]]
            raise FileNotFoundError(
                f"No audio file found for scene '{scene_id}' in {self.audio_dir}\n"
                f"Available files: {available_names}\n"
                f"Expected file like: {scene_id}.mp3"
            )

        # Copy to output location (or convert if needed)
        import shutil
        if source_file.suffix == output_path.suffix:
            shutil.copy2(source_file, output_path)
        else:
            # Convert using ffmpeg
            self._convert_audio(source_file, output_path)

        return output_path

    def _convert_audio(self, source: Path, dest: Path) -> None:
        """Convert audio file to target format using ffmpeg."""
        cmd = [
            "ffmpeg", "-y",
            "-i", str(source),
            "-c:a", "libmp3lame" if dest.suffix == ".mp3" else "aac",
            "-b:a", "192k",
            str(dest),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise RuntimeError(f"Audio conversion failed: {result.stderr}")

    def generate_with_timestamps(
        self, text: str, output_path: str | Path, scene_id: str = ""
    ) -> TTSResult:
        """Import audio and generate word timestamps using Whisper.

        Args:
            text: The expected narration text
            output_path: Path to save the audio file
            scene_id: Scene ID to find the matching audio file

        Returns:
            TTSResult with audio path, duration, and word timestamps
        """
        output_path = Path(output_path)

        # If no scene_id provided, try to extract from output_path
        if not scene_id:
            scene_id = output_path.stem

        # Copy/convert the audio file
        self.generate(text, output_path, scene_id)

        # Transcribe to get word timestamps
        transcriber = self._get_transcriber()
        result = transcriber.transcribe(output_path)

        return TTSResult(
            audio_path=output_path,
            duration_seconds=result.duration_seconds,
            word_timestamps=result.word_timestamps,
        )

    def generate_stream(self, text: str) -> Iterator[bytes]:
        """Not supported for manual recordings."""
        raise NotImplementedError(
            "Streaming is not supported for manual voiceover provider"
        )

    def get_available_voices(self) -> list[dict]:
        """List available audio files in the directory."""
        audio_files = []
        extensions = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"}

        for file in self.audio_dir.iterdir():
            if file.suffix.lower() in extensions:
                audio_files.append({
                    "voice_id": file.stem,
                    "name": file.name,
                    "category": "manual",
                    "description": f"Recorded audio: {file.name}",
                })

        return audio_files

    def list_missing_scenes(self, scene_ids: list[str]) -> list[str]:
        """Check which scenes are missing audio files.

        Args:
            scene_ids: List of scene IDs to check

        Returns:
            List of scene IDs that don't have matching audio files
        """
        missing = []
        for scene_id in scene_ids:
            if self._find_audio_file(scene_id) is None:
                missing.append(scene_id)
        return missing


class MockTTS(TTSProvider):
    """Mock TTS provider for testing."""

    def __init__(self, config: TTSConfig):
        super().__init__(config)

    def generate(self, text: str, output_path: str | Path) -> Path:
        """Generate a silent audio file for testing using FFmpeg."""
        import subprocess

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Estimate duration based on text length (~150 words per minute)
        words = len(text.split())
        duration_seconds = max(1.0, (words / 150) * 60)

        # Use FFmpeg to generate silent audio
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"anullsrc=r=44100:cl=mono:d={duration_seconds}",
            "-c:a", "libmp3lame",
            "-b:a", "128k",
            str(output_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                # Fallback: create minimal valid MP3 using sine wave
                cmd = [
                    "ffmpeg", "-y",
                    "-f", "lavfi",
                    "-i", f"sine=frequency=0:duration={duration_seconds}",
                    "-c:a", "libmp3lame",
                    "-b:a", "128k",
                    str(output_path),
                ]
                subprocess.run(cmd, capture_output=True, timeout=30)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # If FFmpeg not available, create a minimal file
            # This won't be playable but allows tests to pass
            output_path.write_bytes(b"\x00" * 1000)

        return output_path

    def generate_with_timestamps(
        self, text: str, output_path: str | Path
    ) -> TTSResult:
        """Generate mock audio with simulated word timestamps."""
        # Generate the audio file
        audio_path = self.generate(text, output_path)

        # Estimate duration based on text length (~150 words per minute)
        words = text.split()
        duration_seconds = max(1.0, (len(words) / 150) * 60)

        # Generate simulated word timestamps
        word_timestamps = []
        current_time = 0.0
        avg_word_duration = duration_seconds / max(len(words), 1)

        for word in words:
            # Clean word of punctuation for the timestamp
            clean_word = re.sub(r"[^\w\-']", "", word)
            if clean_word:
                # Vary duration slightly based on word length
                word_duration = avg_word_duration * (0.5 + 0.5 * len(clean_word) / 6)
                word_timestamps.append(
                    WordTimestamp(
                        word=clean_word,
                        start_seconds=current_time,
                        end_seconds=current_time + word_duration,
                    )
                )
                current_time += word_duration + 0.05  # Small gap between words

        return TTSResult(
            audio_path=audio_path,
            duration_seconds=duration_seconds,
            word_timestamps=word_timestamps,
        )

    def generate_stream(self, text: str) -> Iterator[bytes]:
        """Generate mock audio stream."""
        # Return some bytes that represent silence
        for _ in range(100):
            yield b"\x00" * 100

    def get_available_voices(self) -> list[dict]:
        """Return mock voices."""
        return [
            {
                "voice_id": "mock_voice_1",
                "name": "Mock Voice",
                "category": "mock",
                "description": "A mock voice for testing",
            }
        ]


def get_tts_provider(config: Config | None = None) -> TTSProvider:
    """Get the appropriate TTS provider based on configuration.

    Args:
        config: Configuration object. If None, uses default config.

    Returns:
        A TTS provider instance

    Supported providers:
        - elevenlabs: High-quality, paid service (requires API key)
        - edge: Microsoft Edge TTS, free, good quality
        - mock: Silent audio for testing
    """
    if config is None:
        config = load_config()

    provider_name = config.tts.provider.lower()

    if provider_name == "elevenlabs":
        return ElevenLabsTTS(config.tts)
    elif provider_name == "edge":
        return EdgeTTS(config.tts)
    elif provider_name == "mock":
        return MockTTS(config.tts)
    else:
        raise ValueError(
            f"Unknown TTS provider: {provider_name}. "
            f"Supported providers: elevenlabs, edge, mock"
        )
