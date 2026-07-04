"""Sound library for frame-accurate SFX.

Redesigned for clean, minimal, professional sounds.

Design Philosophy:
- Subtle and refined, not attention-grabbing
- Clean sine waves with gentle harmonics
- Smooth envelopes, no harsh transients
- Warm low-mids, controlled highs
- Minimalist - 1-2 layers max
- Inspired by Apple/iOS UI aesthetics
"""

import wave
from pathlib import Path
from typing import Optional

import numpy as np

SAMPLE_RATE = 44100


# =============================================================================
# Core Audio Utilities
# =============================================================================


def sine(t: np.ndarray, freq: float) -> np.ndarray:
    """Pure sine wave."""
    return np.sin(2 * np.pi * freq * t)


def smooth_envelope(length: int, attack_ms: float = 5, release_ms: float = 50) -> np.ndarray:
    """Smooth attack and release envelope - no clicks or pops."""
    attack_samples = int(attack_ms * SAMPLE_RATE / 1000)
    release_samples = int(release_ms * SAMPLE_RATE / 1000)

    env = np.ones(length)

    # Smooth cosine attack (no click)
    if attack_samples > 0 and attack_samples < length:
        env[:attack_samples] = 0.5 * (1 - np.cos(np.pi * np.arange(attack_samples) / attack_samples))

    # Smooth exponential release
    if release_samples > 0 and release_samples < length:
        release_start = length - release_samples
        env[release_start:] *= np.exp(-3 * np.arange(release_samples) / release_samples)

    return env


def pitch_envelope(length: int, start_freq: float, end_freq: float) -> np.ndarray:
    """Smooth pitch sweep using exponential interpolation."""
    t = np.linspace(0, 1, length)
    # Exponential interpolation for natural pitch movement
    freq = start_freq * (end_freq / start_freq) ** t
    # Convert to phase
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    return np.sin(phase)


def filtered_noise(length: int, cutoff: float, resonance: float = 0.5) -> np.ndarray:
    """Gentle filtered noise - not harsh."""
    noise = np.random.randn(length) * 0.5

    # Simple lowpass via FFT
    fft = np.fft.rfft(noise)
    freqs = np.fft.rfftfreq(length, 1 / SAMPLE_RATE)

    # Gentle rolloff
    mask = 1 / (1 + (freqs / cutoff) ** 4)
    # Add subtle resonance bump
    mask *= 1 + resonance * np.exp(-((freqs - cutoff) ** 2) / (cutoff * 0.1) ** 2)

    return np.fft.irfft(fft * mask, length)


def normalize(samples: np.ndarray, target_db: float = -3.0) -> np.ndarray:
    """Normalize to target dB level."""
    max_val = np.max(np.abs(samples))
    if max_val > 0:
        target_amp = 10 ** (target_db / 20)
        samples = samples * (target_amp / max_val)
    return samples


def soft_saturate(samples: np.ndarray, amount: float = 0.3) -> np.ndarray:
    """Gentle saturation for warmth - not distortion."""
    return np.tanh(samples * (1 + amount)) / (1 + amount * 0.5)


def save_wav(samples: np.ndarray, filename: str, sample_rate: int = SAMPLE_RATE) -> None:
    """Save as 16-bit WAV."""
    samples = normalize(samples, -3.0)
    samples_int = np.int16(samples * 32767)

    with wave.open(filename, "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(samples_int.tobytes())


# For backwards compatibility with tests
def apply_envelope(
    samples: np.ndarray, attack: float, decay: float, sustain: float, release: float
) -> np.ndarray:
    """Apply ADSR envelope (kept for compatibility)."""
    total = len(samples)
    attack_samples = int(attack * total)
    decay_samples = int(decay * total)
    release_samples = int(release * total)
    sustain_samples = total - attack_samples - decay_samples - release_samples

    envelope = np.zeros(total)

    if attack_samples > 0:
        envelope[:attack_samples] = np.linspace(0, 1, attack_samples)

    decay_end = attack_samples + decay_samples
    if decay_samples > 0:
        envelope[attack_samples:decay_end] = np.linspace(1, sustain, decay_samples)

    sustain_end = decay_end + sustain_samples
    if sustain_samples > 0:
        envelope[decay_end:sustain_end] = sustain

    if release_samples > 0:
        envelope[sustain_end:] = np.linspace(sustain, 0, total - sustain_end)

    return samples * envelope


# =============================================================================
# Sound Generators - Clean, Minimal, Professional
# =============================================================================


def generate_ui_pop(duration: float = 0.08) -> np.ndarray:
    """Soft pop - like a gentle bubble or droplet.

    Clean pitched tone with quick pitch drop. Minimal and pleasant.
    """
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n)

    # Gentle pitch drop: 880 -> 440 Hz (octave down)
    tone = pitch_envelope(n, 880, 440)

    # Add subtle second harmonic for warmth
    tone2 = pitch_envelope(n, 1760, 880) * 0.15

    # Smooth envelope
    env = smooth_envelope(n, attack_ms=2, release_ms=60)

    samples = (tone + tone2) * env
    return soft_saturate(samples, 0.2)


def generate_text_tick(duration: float = 0.03) -> np.ndarray:
    """Subtle tick - barely there, like a soft tap.

    Very short, clean, unobtrusive.
    """
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n)

    # High but not harsh - 1200 Hz
    tone = sine(t, 1200)

    # Quick pitch drop for "tick" character
    tone *= np.exp(-t * 80)

    # Tiny bit of body
    body = sine(t, 400) * 0.2
    body *= np.exp(-t * 60)

    samples = tone + body
    env = smooth_envelope(n, attack_ms=1, release_ms=20)

    return samples * env


def generate_lock_click(duration: float = 0.06) -> np.ndarray:
    """Clean click - like a camera shutter or gentle latch.

    Precise, satisfying, not mechanical-sounding.
    """
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n)

    # Two detuned tones for subtle beating (more interesting)
    tone1 = sine(t, 1000)
    tone2 = sine(t, 1050) * 0.7

    # Low thump for body
    thump = sine(t, 150) * 0.5
    thump *= np.exp(-t * 40)

    click = (tone1 + tone2) * np.exp(-t * 50)

    samples = click + thump
    env = smooth_envelope(n, attack_ms=1, release_ms=40)

    return samples * env


def generate_data_flow(duration: float = 0.25) -> np.ndarray:
    """Gentle woosh - subtle movement sensation.

    Soft filtered noise sweep, not aggressive.
    """
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n)

    # Gentle noise, low cutoff
    noise = filtered_noise(n, 800, resonance=0.3)

    # Subtle pitch rise underneath
    tone = pitch_envelope(n, 200, 400) * 0.3

    # Smooth bell curve envelope
    env = np.exp(-((t - duration/2) ** 2) / (duration/4) ** 2)
    env = smooth_envelope(n, attack_ms=30, release_ms=80) * env

    samples = (noise * 0.6 + tone) * env
    return soft_saturate(samples, 0.15)


def generate_counter_sweep(duration: float = 0.2) -> np.ndarray:
    """Rising tone - clean pitch sweep upward.

    Musical, not sci-fi. Gentle acceleration feel.
    """
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n)

    # Clean rising sweep
    sweep = pitch_envelope(n, 300, 900)

    # Subtle harmonic
    sweep2 = pitch_envelope(n, 600, 1800) * 0.1

    env = smooth_envelope(n, attack_ms=10, release_ms=60)
    # Slight volume rise with pitch
    env *= 0.7 + 0.3 * (t / duration)

    samples = (sweep + sweep2) * env
    return soft_saturate(samples, 0.2)


def generate_reveal_hit(duration: float = 0.3) -> np.ndarray:
    """Soft impact - emphasis without aggression.

    Warm low tone with gentle attack. Think: "important moment".
    """
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n)

    # Warm fundamental with harmonics
    fundamental = 110  # A2 - warm, not boomy
    tone = sine(t, fundamental)
    tone += sine(t, fundamental * 2) * 0.4  # Octave
    tone += sine(t, fundamental * 3) * 0.15  # Fifth above octave

    # Gentle pitch drop for impact feel
    drop = pitch_envelope(n, 220, 110) * 0.3

    env = smooth_envelope(n, attack_ms=8, release_ms=200)
    env *= np.exp(-t * 6)  # Natural decay

    samples = (tone + drop) * env
    return soft_saturate(samples, 0.25)


def generate_warning_tone(duration: float = 0.25) -> np.ndarray:
    """Subtle tension - low tone that suggests caution.

    Not alarming, just a gentle "hmm" feeling.
    """
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n)

    # Low tone with slight dissonance (minor second)
    tone1 = sine(t, 130)  # C3
    tone2 = sine(t, 138) * 0.3  # C#3 - creates tension

    # Very subtle vibrato
    vibrato = 1 + 0.01 * sine(t, 5)

    env = smooth_envelope(n, attack_ms=20, release_ms=100)
    env *= np.exp(-t * 4)

    samples = (tone1 + tone2) * vibrato * env
    return soft_saturate(samples, 0.2)


def generate_success_tone(duration: float = 0.25) -> np.ndarray:
    """Pleasant chime - gentle major chord.

    Brief, uplifting, not celebratory or cheesy.
    """
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n)

    # Major third interval - universally pleasant
    note1 = sine(t, 523)  # C5
    note2 = sine(t, 659) * 0.7  # E5

    # Stagger slightly for richness
    delay = int(0.015 * SAMPLE_RATE)
    note2_delayed = np.zeros(n)
    note2_delayed[delay:] = note2[:-delay] if delay < n else 0

    env = smooth_envelope(n, attack_ms=5, release_ms=150)
    env *= np.exp(-t * 5)

    samples = (note1 + note2_delayed) * env
    return soft_saturate(samples, 0.2)


def generate_transition_whoosh(duration: float = 0.2) -> np.ndarray:
    """Gentle sweep - smooth transition feel.

    Like a soft breath or gentle wind.
    """
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n)

    # Filtered noise with moving cutoff
    noise = np.random.randn(n) * 0.3

    # Simple moving average filter (smooth)
    cutoff_env = 400 + 800 * np.sin(np.pi * t / duration)

    # Apply time-varying filter via short segments
    filtered = np.zeros(n)
    segment_size = 256
    for i in range(0, n - segment_size, segment_size // 2):
        segment = noise[i:i + segment_size]
        cutoff = cutoff_env[i + segment_size // 2]

        fft = np.fft.rfft(segment)
        freqs = np.fft.rfftfreq(segment_size, 1 / SAMPLE_RATE)
        mask = 1 / (1 + (freqs / cutoff) ** 2)
        segment_filtered = np.fft.irfft(fft * mask, segment_size)

        # Overlap-add
        filtered[i:i + segment_size] += segment_filtered * np.hanning(segment_size)

    env = np.sin(np.pi * t / duration)  # Bell curve
    env = smooth_envelope(n, attack_ms=15, release_ms=50) * env

    return filtered * env


def generate_cache_click(duration: float = 0.05) -> np.ndarray:
    """Digital blip - clean, precise, minimal.

    Like a soft notification ping.
    """
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n)

    # Clean tone with quick pitch drop
    tone = pitch_envelope(n, 1400, 800)

    # Tiny harmonic
    tone2 = pitch_envelope(n, 2800, 1600) * 0.1

    env = smooth_envelope(n, attack_ms=2, release_ms=35)

    samples = (tone + tone2) * env
    return soft_saturate(samples, 0.15)


# =============================================================================
# Additional Sounds for Semantic Mapping
# =============================================================================


def generate_keyboard_type(duration: float = 0.04) -> np.ndarray:
    """Soft key tap - gentle, not mechanical.

    Like typing on a quiet keyboard.
    """
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n)

    # Soft click - mid frequency
    click = sine(t, 800) + sine(t, 1200) * 0.3
    click *= np.exp(-t * 100)

    # Tiny thump
    thump = sine(t, 200) * 0.3
    thump *= np.exp(-t * 80)

    env = smooth_envelope(n, attack_ms=1, release_ms=25)

    return (click + thump) * env


def generate_keyboard_rapid(duration: float = 0.12) -> np.ndarray:
    """Quick typing burst - several soft taps.

    Gentle rhythm, not aggressive.
    """
    n = int(SAMPLE_RATE * duration)
    samples = np.zeros(n)

    # 3 soft taps
    tap_times = [0.0, 0.03, 0.065]

    for i, tap_time in enumerate(tap_times):
        start = int(tap_time * SAMPLE_RATE)
        tap_len = int(0.035 * SAMPLE_RATE)

        if start + tap_len > n:
            tap_len = n - start

        if tap_len > 0:
            t = np.linspace(0, tap_len / SAMPLE_RATE, tap_len)

            # Vary pitch slightly
            freq = 900 + i * 100
            tap = sine(t, freq)
            tap *= np.exp(-t * 90)

            env = smooth_envelope(tap_len, attack_ms=1, release_ms=20)

            # Decrease volume for later taps
            samples[start:start + tap_len] += tap * env * (0.8 - i * 0.15)

    return samples


def generate_bar_grow(duration: float = 0.2) -> np.ndarray:
    """Gentle rise - smooth ascending tone.

    Suggests growth or progress.
    """
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n)

    # Smooth pitch rise
    sweep = pitch_envelope(n, 250, 500)

    # Subtle harmonic
    sweep2 = pitch_envelope(n, 500, 1000) * 0.15

    env = smooth_envelope(n, attack_ms=15, release_ms=60)

    samples = (sweep + sweep2) * env
    return soft_saturate(samples, 0.15)


def generate_progress_tick(duration: float = 0.04) -> np.ndarray:
    """Tiny tick - very subtle increment sound.

    Almost imperceptible, just enough to register.
    """
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n)

    # High but soft
    tick = sine(t, 1500) * 0.7
    tick += sine(t, 2000) * 0.2
    tick *= np.exp(-t * 80)

    env = smooth_envelope(n, attack_ms=1, release_ms=25)

    return tick * env


def generate_digital_stream(duration: float = 0.3) -> np.ndarray:
    """Soft data flow - gentle continuous texture.

    Subtle background presence, not distracting.
    """
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n)

    # Very gentle filtered noise
    noise = filtered_noise(n, 600, resonance=0.2) * 0.4

    # Subtle tone underneath
    tone = sine(t, 400) * 0.2
    tone += sine(t, 600) * 0.1

    # Gentle pulsing
    pulse = 0.7 + 0.3 * sine(t, 8)

    env = smooth_envelope(n, attack_ms=40, release_ms=80)

    samples = (noise + tone) * pulse * env
    return soft_saturate(samples, 0.1)


def generate_impact_soft(duration: float = 0.12) -> np.ndarray:
    """Gentle thump - soft emphasis.

    Warm, not punchy.
    """
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n)

    # Warm low tone
    tone = sine(t, 150)
    tone += sine(t, 300) * 0.3
    tone *= np.exp(-t * 20)

    env = smooth_envelope(n, attack_ms=5, release_ms=80)

    return tone * env


def generate_impact_hard(duration: float = 0.18) -> np.ndarray:
    """Firmer impact - still restrained.

    More presence than soft, but not aggressive.
    """
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n)

    # Fuller low end
    tone = sine(t, 100)
    tone += sine(t, 200) * 0.5
    tone += sine(t, 400) * 0.2

    # Slight pitch drop
    drop = pitch_envelope(n, 300, 150) * 0.3

    env = smooth_envelope(n, attack_ms=5, release_ms=120)
    env *= np.exp(-t * 8)

    samples = (tone + drop) * env
    return soft_saturate(samples, 0.25)


# =============================================================================
# Sound Manifest and Library Class
# =============================================================================


SOUND_MANIFEST = {
    "ui_pop": {
        "description": "Soft pop for elements appearing",
        "generator": "generate_ui_pop",
    },
    "text_tick": {
        "description": "Subtle tick for text appearing",
        "generator": "generate_text_tick",
    },
    "lock_click": {
        "description": "Clean click for things locking into place",
        "generator": "generate_lock_click",
    },
    "data_flow": {
        "description": "Gentle woosh for data movement",
        "generator": "generate_data_flow",
    },
    "counter_sweep": {
        "description": "Rising tone for counters",
        "generator": "generate_counter_sweep",
    },
    "reveal_hit": {
        "description": "Soft impact for reveals",
        "generator": "generate_reveal_hit",
    },
    "warning_tone": {
        "description": "Subtle tension tone for problems",
        "generator": "generate_warning_tone",
    },
    "success_tone": {
        "description": "Pleasant chime for success",
        "generator": "generate_success_tone",
    },
    "transition_whoosh": {
        "description": "Gentle sweep for transitions",
        "generator": "generate_transition_whoosh",
    },
    "cache_click": {
        "description": "Clean blip for cache operations",
        "generator": "generate_cache_click",
    },
    "keyboard_type": {
        "description": "Soft key tap for typing",
        "generator": "generate_keyboard_type",
    },
    "keyboard_rapid": {
        "description": "Quick typing burst",
        "generator": "generate_keyboard_rapid",
    },
    "bar_grow": {
        "description": "Gentle rise for chart growth",
        "generator": "generate_bar_grow",
    },
    "progress_tick": {
        "description": "Tiny tick for progress",
        "generator": "generate_progress_tick",
    },
    "digital_stream": {
        "description": "Soft texture for streaming",
        "generator": "generate_digital_stream",
    },
    "impact_soft": {
        "description": "Gentle thump for subtle reveals",
        "generator": "generate_impact_soft",
    },
    "impact_hard": {
        "description": "Firmer impact for emphasis",
        "generator": "generate_impact_hard",
    },
}


GENERATORS = {
    "generate_ui_pop": generate_ui_pop,
    "generate_text_tick": generate_text_tick,
    "generate_lock_click": generate_lock_click,
    "generate_data_flow": generate_data_flow,
    "generate_counter_sweep": generate_counter_sweep,
    "generate_reveal_hit": generate_reveal_hit,
    "generate_warning_tone": generate_warning_tone,
    "generate_success_tone": generate_success_tone,
    "generate_transition_whoosh": generate_transition_whoosh,
    "generate_cache_click": generate_cache_click,
    "generate_keyboard_type": generate_keyboard_type,
    "generate_keyboard_rapid": generate_keyboard_rapid,
    "generate_bar_grow": generate_bar_grow,
    "generate_progress_tick": generate_progress_tick,
    "generate_digital_stream": generate_digital_stream,
    "generate_impact_soft": generate_impact_soft,
    "generate_impact_hard": generate_impact_hard,
}


class SoundLibrary:
    """Manages the SFX library for a project."""

    def __init__(self, sfx_dir: Path):
        """Initialize with path to sfx directory."""
        self.sfx_dir = sfx_dir

    def generate_all(self) -> list[str]:
        """Generate all sounds in the library."""
        self.sfx_dir.mkdir(parents=True, exist_ok=True)
        generated = []

        for name, info in SOUND_MANIFEST.items():
            generator_name = info["generator"]
            generator = GENERATORS.get(generator_name)

            if generator:
                samples = generator()
                output_path = self.sfx_dir / f"{name}.wav"
                save_wav(samples, str(output_path))
                generated.append(name)

        return generated

    def list_sounds(self) -> list[str]:
        """List available sounds."""
        return list(SOUND_MANIFEST.keys())

    def get_sound_info(self, name: str) -> Optional[dict]:
        """Get info about a specific sound."""
        return SOUND_MANIFEST.get(name)

    def sound_exists(self, name: str) -> bool:
        """Check if a sound file exists."""
        return (self.sfx_dir / f"{name}.wav").exists()

    def get_missing_sounds(self) -> list[str]:
        """Get list of sounds that haven't been generated yet."""
        return [name for name in SOUND_MANIFEST if not self.sound_exists(name)]
