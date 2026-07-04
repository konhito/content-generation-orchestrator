"""Build deterministic layered-character tracks for Shorts beats."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import httpx

from .models import BlinkCue, CharacterEvent, CharacterTrack, MouthCue, ShortBeatMode, ShortsBeat

LETTER_PHONEMES = {
    "a": "AE",
    "e": "EH",
    "i": "IH",
    "o": "OW",
    "u": "UH",
    "b": "B",
    "m": "M",
    "p": "P",
    "f": "F",
    "v": "V",
    "l": "L",
    "r": "R",
    "t": "T",
    "d": "D",
    "s": "S",
    "z": "Z",
}


def _mouth_shape(phoneme: str, emotion: str, mouth_map: dict[str, Any]) -> str:
    candidates = (phoneme, re.sub(r"\d+$", "", phoneme))
    mood = "sad" if emotion.startswith(("sad", "worried", "bore")) else "happy"
    for candidate in candidates:
        mapping = mouth_map.get(candidate, {})
        if mood in mapping:
            return str(mapping[mood])
        stressed_key = next((key for key in mouth_map if key.startswith(candidate) and key[len(candidate):].isdigit()), None)
        if stressed_key and mood in mouth_map[stressed_key]:
            return str(mouth_map[stressed_key][mood])
    return "m_b_close_s" if mood == "sad" else "m_b_close_h"


def mouth_cues_from_words(
    word_timestamps: list[dict[str, Any]],
    emotion: str,
    duration_seconds: float,
    mouth_map: dict[str, Any],
) -> list[MouthCue]:
    """Create conservative mouth cues inside existing word boundaries."""

    cues: list[MouthCue] = []
    for item in word_timestamps:
        start = max(0.0, float(item.get("start_seconds", 0.0)))
        end = min(duration_seconds, float(item.get("end_seconds", start)))
        letters = [char for char in str(item.get("word", "")).lower() if char.isalpha()]
        if end <= start or not letters:
            continue
        selected = letters[: min(6, len(letters))]
        segment = (end - start) / len(selected)
        for index, letter in enumerate(selected):
            cue_start = start + index * segment
            cue_end = end if index == len(selected) - 1 else start + (index + 1) * segment
            phoneme = LETTER_PHONEMES.get(letter, "AH")
            cues.append(
                MouthCue(
                    start=round(cue_start, 4),
                    end=round(cue_end, 4),
                    shape=_mouth_shape(phoneme, emotion, mouth_map),
                )
            )
    return cues


def mouth_cues_from_gentle(
    words: list[dict[str, Any]],
    emotion: str,
    duration_seconds: float,
    mouth_map: dict[str, Any],
) -> list[MouthCue]:
    """Convert Gentle's phone durations into precise mouth-shape intervals."""

    cues: list[MouthCue] = []
    for word in words:
        cursor = max(0.0, float(word.get("start", 0.0)))
        word_end = min(duration_seconds, float(word.get("end", cursor)))
        for phone in word.get("phones", []) or []:
            cue_end = min(word_end, cursor + float(phone.get("duration", 0.0)))
            if cue_end > cursor:
                cues.append(
                    MouthCue(
                        start=round(cursor, 4),
                        end=round(cue_end, 4),
                        shape=_mouth_shape(str(phone.get("phone", "")), emotion, mouth_map),
                    )
                )
            cursor = cue_end
        if cues and cursor < word_end:
            cues[-1].end = round(word_end, 4)
    return cues


def request_gentle_alignment(
    audio_path: Path,
    transcript: str,
    url: str,
    timeout: float,
    *,
    post: Any = httpx.post,
) -> list[dict[str, Any]]:
    """Request word and phone alignment from a Gentle-compatible service."""

    with audio_path.open("rb") as audio_file:
        response = post(
            url,
            files={
                "audio": (audio_path.name, audio_file, "application/octet-stream"),
                "transcript": ("transcript.txt", transcript, "text/plain"),
            },
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    return list(payload.get("words", []))


def _fallback_key(
    group: str,
    requested: str,
    manifest: dict[str, Any],
    warnings: list[str],
) -> str:
    assets = manifest.get("assets", {}).get(group, {})
    if requested in assets:
        return requested
    fallback = str(manifest.get("fallbacks", {}).get(group, ""))
    warnings.append(f"unknown {group} asset {requested!r}; using {fallback!r}")
    return fallback


def build_character_track(
    *,
    beat_id: str,
    duration_seconds: float,
    word_timestamps: list[dict[str, Any]],
    cue: dict[str, Any],
    manifest: dict[str, Any],
    gentle_words: list[dict[str, Any]] | None = None,
) -> tuple[CharacterTrack, list[str]]:
    """Build a validated track using manifest keys only."""

    warnings: list[str] = []
    pose = _fallback_key("body", str(cue.get("pose", "body1")), manifest, warnings)
    head = _fallback_key("head", str(cue.get("head", "M")), manifest, warnings)
    emotion_name = str(cue.get("emotion", "content"))
    eye_candidate = f"{emotion_name}_{head}"
    eyes = _fallback_key("eyes", eye_candidate, manifest, warnings)
    emotion = emotion_name if eyes == eye_candidate else "content"

    seed = int(hashlib.sha256(beat_id.encode("utf-8")).hexdigest()[:8], 16)
    blink_start = min(max(0.55, 0.9 + (seed % 90) / 100), max(0.55, duration_seconds - 0.18))
    blinks = []
    if duration_seconds >= 0.75:
        blinks.append(BlinkCue(start=round(blink_start, 3), end=round(min(duration_seconds, blink_start + 0.12), 3)))

    mouth_cues = (
        mouth_cues_from_gentle(
            gentle_words,
            emotion,
            duration_seconds,
            manifest.get("mouth_map", {}),
        )
        if gentle_words
        else mouth_cues_from_words(
            word_timestamps,
            emotion,
            duration_seconds,
            manifest.get("mouth_map", {}),
        )
    )
    track = CharacterTrack(
        character_id="character_1",
        duration_seconds=duration_seconds,
        base_pose=pose,
        base_emotion=emotion,
        events=[CharacterEvent(start=0, end=duration_seconds, pose=pose, emotion=emotion, head=head)],
        mouth_cues=mouth_cues,
        blink_cues=blinks,
    )
    return track, warnings


def attach_character_tracks(
    beats: list[ShortsBeat],
    manifest_path: Path,
    output_dir: Path,
    project_root: Path | None = None,
    audio_path: Path | None = None,
    aligner_url: str = "http://localhost:49153/transcriptions?async=false",
    aligner_timeout: float = 5.0,
) -> list[str]:
    """Generate track files and attach render-ready data to character beats."""

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    project_root = project_root or output_dir.parent.parent
    warnings: list[str] = []
    aligned_words: list[dict[str, Any]] = []
    if audio_path and audio_path.exists():
        transcript = " ".join(
            str(word.get("word", ""))
            for beat in beats
            for word in beat.word_timestamps
        ).strip()
        if transcript:
            try:
                aligned_words = request_gentle_alignment(
                    audio_path,
                    transcript,
                    aligner_url,
                    aligner_timeout,
                )
            except (OSError, httpx.HTTPError, ValueError) as exc:
                warnings.append(f"Gentle alignment unavailable; using word timing fallback: {exc}")
    for beat in beats:
        recipe_wants_character = (
            beat.visual_recipe is not None
            and beat.visual_recipe.character.presence == "primary"
        )
        if beat.mode != ShortBeatMode.CHARACTER and not recipe_wants_character:
            continue
        duration = beat.end_seconds - beat.start_seconds
        relative_words = [
            {
                **item,
                "start_seconds": max(0.0, float(item.get("start_seconds", 0)) - beat.start_seconds),
                "end_seconds": min(duration, float(item.get("end_seconds", 0)) - beat.start_seconds),
            }
            for item in beat.word_timestamps
            if float(item.get("end_seconds", 0)) > beat.start_seconds
            and float(item.get("start_seconds", 0)) < beat.end_seconds
        ]
        relative_gentle = [
            {
                **item,
                "start": max(0.0, float(item.get("start", 0)) - beat.start_seconds),
                "end": min(duration, float(item.get("end", 0)) - beat.start_seconds),
            }
            for item in aligned_words
            if float(item.get("end", 0)) > beat.start_seconds
            and float(item.get("start", 0)) < beat.end_seconds
        ]
        track, beat_warnings = build_character_track(
            beat_id=beat.id,
            duration_seconds=duration,
            word_timestamps=relative_words,
            cue={"pose": "body1", "emotion": "content", "head": "M"},
            manifest=manifest,
            gentle_words=relative_gentle,
        )
        track_path = output_dir / f"{beat.id}.json"
        track_path.write_text(track.model_dump_json(indent=2), encoding="utf-8")
        beat.character_track = track_path.relative_to(project_root).as_posix()
        beat.character_data = track
        warnings.extend(f"{beat.id}: {warning}" for warning in beat_warnings)
    return warnings
