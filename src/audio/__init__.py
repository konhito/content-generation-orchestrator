"""Audio generation module - TTS and audio processing."""

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
