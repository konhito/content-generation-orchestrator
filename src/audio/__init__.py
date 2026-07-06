"""Audio generation module - TTS and audio processing."""

try:  # pragma: no cover - optional runtime dependency
    from .tts import (
        TTSProvider,
        ElevenLabsTTS,
        EdgeTTS,
        MockTTS,
        ManualVoiceoverProvider,
        TTSResult,
        WordTimestamp,
        get_tts_provider,
    )
except ModuleNotFoundError:  # pragma: no cover - keeps CLI importable without TTS deps
    TTSProvider = None
    ElevenLabsTTS = None
    EdgeTTS = None
    MockTTS = None
    ManualVoiceoverProvider = None
    TTSResult = None
    WordTimestamp = None

    def get_tts_provider(*args, **kwargs):  # type: ignore[override]
        raise ModuleNotFoundError(
            "TTS dependencies are not installed. Install the audio extras to use voiceover generation."
        )

from .transcribe import (
    WhisperTranscriber,
    FasterWhisperTranscriber,
    TranscriptionResult,
    get_transcriber,
    get_audio_duration,
)

__all__ = [
    # TTS providers
    "TTSProvider",
    "ElevenLabsTTS",
    "EdgeTTS",
    "MockTTS",
    "ManualVoiceoverProvider",
    "TTSResult",
    "WordTimestamp",
    "get_tts_provider",
    # Transcription
    "WhisperTranscriber",
    "FasterWhisperTranscriber",
    "TranscriptionResult",
    "get_transcriber",
    "get_audio_duration",
]
