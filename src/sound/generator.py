"""Generative SFX Library for Explainer Videos.

A flexible, theme-aware sound generation system that creates professional
sound effects based on scene context and video themes.

Design Principles:
- Theme-driven: Sounds adapt to video topic (AI, biology, finance, etc.)
- Event-based: Sound archetypes map to common animation events
- Parameterized: Each sound can be tuned for intensity, duration, pitch
- Layered synthesis: Multiple techniques combined for richness
- Professional quality: FM synthesis, filtering, reverb, proper mastering
"""

import wave
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Literal, Union, Tuple
from enum import Enum

import numpy as np
from scipy import signal
from scipy.ndimage import gaussian_filter1d

SAMPLE_RATE = 44100


# =============================================================================
# Theme System - Defines sonic palette for different video topics
# =============================================================================

class SoundTheme(Enum):
    """Video themes that influence sound design."""
    TECH_AI = "tech_ai"           # Neural networks, AI, computing
    SCIENCE = "science"           # Physics, chemistry, biology
    FINANCE = "finance"           # Markets, economics, business
    MEDICAL = "medical"           # Healthcare, biology, medicine
    SPACE = "space"               # Astronomy, space exploration
    NATURE = "nature"             # Environment, ecology
    ABSTRACT = "abstract"         # General educational content


@dataclass
class ThemePalette:
    """Sonic characteristics for a theme."""

    # Frequency ranges (Hz)
    bass_freq: tuple[float, float] = (40, 120)
    mid_freq: tuple[float, float] = (300, 2000)
    high_freq: tuple[float, float] = (3000, 8000)

    # Tonal characteristics
    root_note: float = 220.0  # A3 - root frequency for harmonic content
    scale: list[float] = field(default_factory=lambda: [1, 1.125, 1.25, 1.333, 1.5, 1.667, 1.875])  # Major scale ratios

    # Texture preferences (0-1)
    digital_amount: float = 0.5      # Digital vs organic
    brightness: float = 0.5          # Dark vs bright
    movement: float = 0.5            # Static vs evolving
    warmth: float = 0.5              # Cold vs warm

    # Reverb characteristics
    reverb_size: float = 0.3         # Room size (0=dry, 1=huge hall)
    reverb_damping: float = 0.5      # High frequency damping


# Theme presets
THEME_PALETTES = {
    SoundTheme.TECH_AI: ThemePalette(
        bass_freq=(50, 100),
        mid_freq=(400, 2500),
        high_freq=(4000, 12000),
        root_note=220.0,  # A3
        scale=[1, 1.189, 1.335, 1.498, 1.682, 1.888],  # Whole tone for sci-fi
        digital_amount=0.8,
        brightness=0.7,
        movement=0.6,
        warmth=0.3,
        reverb_size=0.25,
        reverb_damping=0.3,
    ),
    SoundTheme.SCIENCE: ThemePalette(
        bass_freq=(60, 150),
        mid_freq=(300, 2000),
        high_freq=(3000, 10000),
        root_note=261.63,  # C4
        scale=[1, 1.122, 1.26, 1.414, 1.587, 1.782],  # Lydian feel
        digital_amount=0.5,
        brightness=0.6,
        movement=0.5,
        warmth=0.5,
        reverb_size=0.4,
        reverb_damping=0.4,
    ),
    SoundTheme.FINANCE: ThemePalette(
        bass_freq=(80, 200),
        mid_freq=(400, 1500),
        high_freq=(2000, 6000),
        root_note=196.0,  # G3
        scale=[1, 1.125, 1.25, 1.5, 1.667],  # Pentatonic - professional
        digital_amount=0.4,
        brightness=0.4,
        movement=0.3,
        warmth=0.6,
        reverb_size=0.2,
        reverb_damping=0.6,
    ),
    SoundTheme.SPACE: ThemePalette(
        bass_freq=(30, 80),
        mid_freq=(200, 1500),
        high_freq=(2000, 15000),
        root_note=146.83,  # D3 - deeper
        scale=[1, 1.122, 1.335, 1.498, 1.782],  # Mysterious intervals
        digital_amount=0.6,
        brightness=0.8,
        movement=0.8,
        warmth=0.2,
        reverb_size=0.8,  # Big spacey reverb
        reverb_damping=0.2,
    ),
    SoundTheme.NATURE: ThemePalette(
        bass_freq=(60, 120),
        mid_freq=(250, 2000),
        high_freq=(2500, 8000),
        root_note=293.66,  # D4
        scale=[1, 1.125, 1.25, 1.333, 1.5, 1.667, 1.875],  # Natural major
        digital_amount=0.1,
        brightness=0.5,
        movement=0.4,
        warmth=0.8,
        reverb_size=0.5,
        reverb_damping=0.5,
    ),
    SoundTheme.ABSTRACT: ThemePalette(),  # Default values
}


# =============================================================================
# Event Types - Common animation events that need sounds
# =============================================================================

class SoundEvent(Enum):
    """Types of animation events that trigger sounds."""

    # Appearance events
    ELEMENT_APPEAR = "element_appear"       # Something fades/pops in
    ELEMENT_DISAPPEAR = "element_disappear" # Something fades out
    TEXT_REVEAL = "text_reveal"             # Text appearing character by character

    # Movement events
    TRANSITION = "transition"               # Moving between phases/scenes
    DATA_FLOW = "data_flow"                 # Data/information streaming
    TRANSFORM = "transform"                 # Shape changing/morphing

    # Interaction events
    CONNECTION = "connection"               # Two things connecting
    LOCK = "lock"                           # Something snapping into place
    UNLOCK = "unlock"                       # Something releasing

    # State events
    SUCCESS = "success"                     # Positive outcome
    WARNING = "warning"                     # Problem or caution
    ERROR = "error"                         # Failure state

    # Emphasis events
    REVEAL = "reveal"                       # Big moment, key insight
    COUNTER = "counter"                     # Numbers counting up/down
    PULSE = "pulse"                         # Rhythmic emphasis
    PING = "ping"                           # Quick attention grab


# =============================================================================
# Core Synthesis Utilities
# =============================================================================

def db_to_amp(db: float) -> float:
    """Convert decibels to amplitude."""
    return 10 ** (db / 20)


def amp_to_db(amp: float) -> float:
    """Convert amplitude to decibels."""
    return 20 * np.log10(amp + 1e-10)


def normalize(samples: np.ndarray, target_db: float = -3.0) -> np.ndarray:
    """Normalize to target dB level."""
    max_val = np.max(np.abs(samples))
    if max_val > 0:
        target_amp = db_to_amp(target_db)
        samples = samples * (target_amp / max_val)
    return samples


def soft_clip(samples: np.ndarray, threshold: float = 0.8) -> np.ndarray:
    """Soft saturation using tanh."""
    return np.tanh(samples / threshold) * threshold


def apply_fade(samples: np.ndarray, fade_in_ms: float = 5, fade_out_ms: float = 20) -> np.ndarray:
    """Apply fade in/out to prevent clicks."""
    fade_in_samples = int(fade_in_ms * SAMPLE_RATE / 1000)
    fade_out_samples = int(fade_out_ms * SAMPLE_RATE / 1000)

    if fade_in_samples > 0 and len(samples) > fade_in_samples:
        fade_in = np.linspace(0, 1, fade_in_samples) ** 0.5
        samples[:fade_in_samples] *= fade_in

    if fade_out_samples > 0 and len(samples) > fade_out_samples:
        fade_out = np.linspace(1, 0, fade_out_samples) ** 2
        samples[-fade_out_samples:] *= fade_out

    return samples


# =============================================================================
# Advanced Synthesis Components
# =============================================================================

def fm_oscillator(
    t: np.ndarray,
    carrier_freq: float,
    mod_freq: float,
    mod_index: float,
    carrier_harmonics: list[tuple[int, float]] = None
) -> np.ndarray:
    """FM synthesis oscillator with optional harmonics.

    Args:
        t: Time array
        carrier_freq: Carrier frequency in Hz
        mod_freq: Modulator frequency in Hz
        mod_index: Modulation depth (0-10 typical)
        carrier_harmonics: List of (harmonic_number, amplitude) for carrier
    """
    modulator = np.sin(2 * np.pi * mod_freq * t)
    phase = 2 * np.pi * carrier_freq * t + mod_index * modulator

    carrier = np.sin(phase)

    if carrier_harmonics:
        for harmonic, amp in carrier_harmonics:
            carrier += amp * np.sin(harmonic * phase)
        carrier /= (1 + sum(amp for _, amp in carrier_harmonics))

    return carrier


def filtered_noise(
    n_samples: int,
    filter_type: Literal["lowpass", "highpass", "bandpass"],
    cutoff: Union[float, Tuple[float, float]],
    resonance: float = 1.0
) -> np.ndarray:
    """Generate filtered noise with resonance.

    Args:
        n_samples: Number of samples
        filter_type: Type of filter
        cutoff: Cutoff frequency (or tuple for bandpass)
        resonance: Filter resonance (Q factor), 0.5-10
    """
    noise = np.random.randn(n_samples)

    nyquist = SAMPLE_RATE / 2

    if filter_type == "bandpass":
        low, high = cutoff
        low_norm = min(low / nyquist, 0.99)
        high_norm = min(high / nyquist, 0.99)
        if low_norm >= high_norm:
            high_norm = min(low_norm + 0.01, 0.99)
        sos = signal.butter(2, [low_norm, high_norm], btype='band', output='sos')
    else:
        cutoff_norm = min(cutoff / nyquist, 0.99)
        sos = signal.butter(4, cutoff_norm, btype=filter_type, output='sos')

    filtered = signal.sosfilt(sos, noise)

    # Apply resonance by boosting near cutoff
    if resonance > 1.0:
        boost = (resonance - 1) * 0.3
        filtered = filtered * (1 + boost)

    return filtered / (np.max(np.abs(filtered)) + 1e-10)


def granular_texture(
    source: np.ndarray,
    grain_size_ms: float = 50,
    density: float = 0.5,
    pitch_var: float = 0.1,
    position_var: float = 0.3
) -> np.ndarray:
    """Create granular texture from source audio.

    Args:
        source: Source audio samples
        grain_size_ms: Size of each grain in milliseconds
        density: How many grains per second (0-1 maps to sparse-dense)
        pitch_var: Random pitch variation (0-1)
        position_var: How much to randomize read position (0-1)
    """
    grain_samples = int(grain_size_ms * SAMPLE_RATE / 1000)
    output = np.zeros_like(source)

    # Calculate number of grains
    n_grains = int(len(source) / grain_samples * density * 3)

    for _ in range(n_grains):
        # Random position in output
        out_pos = np.random.randint(0, max(1, len(output) - grain_samples))

        # Random position in source (with variation)
        base_pos = out_pos + int(np.random.randn() * position_var * len(source) * 0.1)
        src_pos = max(0, min(len(source) - grain_samples, base_pos))

        # Extract grain
        grain = source[src_pos:src_pos + grain_samples].copy()

        # Apply pitch variation by resampling
        if pitch_var > 0:
            pitch_factor = 1 + np.random.randn() * pitch_var * 0.5
            pitch_factor = max(0.5, min(2.0, pitch_factor))
            new_len = int(len(grain) / pitch_factor)
            if new_len > 0:
                grain = np.interp(
                    np.linspace(0, len(grain) - 1, new_len),
                    np.arange(len(grain)),
                    grain
                )

        # Apply envelope to grain
        env = np.hanning(len(grain))
        grain *= env

        # Mix into output
        end_pos = min(out_pos + len(grain), len(output))
        grain_len = end_pos - out_pos
        output[out_pos:end_pos] += grain[:grain_len] * 0.3

    return output


def simple_reverb(samples: np.ndarray, size: float = 0.3, damping: float = 0.5) -> np.ndarray:
    """Simple algorithmic reverb using comb and allpass filters.

    Args:
        samples: Input audio
        size: Room size (0-1)
        damping: High frequency damping (0-1)
    """
    if size < 0.05:
        return samples

    # Scale delay times by size
    base_delays = [1557, 1617, 1491, 1422, 1277, 1356]
    delays = [int(d * (0.5 + size)) for d in base_delays]

    output = samples.copy()

    # Comb filters in parallel
    for delay in delays[:4]:
        if delay < len(samples):
            comb = np.zeros_like(samples)
            feedback = 0.7 * (1 - damping * 0.3)
            for i in range(delay, len(samples)):
                comb[i] = samples[i - delay] + feedback * comb[i - delay] if i >= delay else 0
            output += comb * 0.15

    # Simple lowpass for damping
    if damping > 0:
        output = gaussian_filter1d(output, sigma=damping * 3)

    return output


def envelope_adsr(
    n_samples: int,
    attack: float = 0.01,
    decay: float = 0.1,
    sustain: float = 0.7,
    release: float = 0.3
) -> np.ndarray:
    """Generate ADSR envelope.

    Args:
        n_samples: Total number of samples
        attack: Attack time (0-1 of total)
        decay: Decay time (0-1 of total)
        sustain: Sustain level (0-1)
        release: Release time (0-1 of total)
    """
    env = np.zeros(n_samples)

    a_samples = int(attack * n_samples)
    d_samples = int(decay * n_samples)
    r_samples = int(release * n_samples)
    s_samples = n_samples - a_samples - d_samples - r_samples

    pos = 0

    # Attack (exponential curve for punch)
    if a_samples > 0:
        env[pos:pos + a_samples] = np.linspace(0, 1, a_samples) ** 0.5
        pos += a_samples

    # Decay (exponential)
    if d_samples > 0:
        env[pos:pos + d_samples] = sustain + (1 - sustain) * np.exp(-np.linspace(0, 5, d_samples))
        pos += d_samples

    # Sustain
    if s_samples > 0:
        env[pos:pos + s_samples] = sustain
        pos += s_samples

    # Release (exponential)
    if r_samples > 0:
        env[pos:pos + r_samples] = sustain * np.exp(-np.linspace(0, 5, r_samples))

    return env


# =============================================================================
# Sound Event Generators
# =============================================================================

class SoundGenerator:
    """Generates sounds based on theme and event type."""

    def __init__(self, theme: SoundTheme = SoundTheme.TECH_AI):
        """Initialize with a theme."""
        self.theme = theme
        self.palette = THEME_PALETTES.get(theme, ThemePalette())

    def set_theme(self, theme: SoundTheme):
        """Change the active theme."""
        self.theme = theme
        self.palette = THEME_PALETTES.get(theme, ThemePalette())

    def generate(
        self,
        event: SoundEvent,
        duration: float = 0.3,
        intensity: float = 0.7,
        pitch_offset: float = 0.0,
        variation_seed: int = None
    ) -> np.ndarray:
        """Generate a sound for the given event.

        Args:
            event: Type of animation event
            duration: Duration in seconds
            intensity: How prominent the sound should be (0-1)
            pitch_offset: Pitch shift in semitones (-12 to +12)
            variation_seed: Random seed for reproducible variations
        """
        if variation_seed is not None:
            np.random.seed(variation_seed)

        # Map events to generator methods
        generators = {
            SoundEvent.ELEMENT_APPEAR: self._gen_appear,
            SoundEvent.ELEMENT_DISAPPEAR: self._gen_disappear,
            SoundEvent.TEXT_REVEAL: self._gen_text_reveal,
            SoundEvent.TRANSITION: self._gen_transition,
            SoundEvent.DATA_FLOW: self._gen_data_flow,
            SoundEvent.TRANSFORM: self._gen_transform,
            SoundEvent.CONNECTION: self._gen_connection,
            SoundEvent.LOCK: self._gen_lock,
            SoundEvent.UNLOCK: self._gen_unlock,
            SoundEvent.SUCCESS: self._gen_success,
            SoundEvent.WARNING: self._gen_warning,
            SoundEvent.ERROR: self._gen_error,
            SoundEvent.REVEAL: self._gen_reveal,
            SoundEvent.COUNTER: self._gen_counter,
            SoundEvent.PULSE: self._gen_pulse,
            SoundEvent.PING: self._gen_ping,
        }

        generator = generators.get(event, self._gen_appear)
        samples = generator(duration, intensity)

        # Apply pitch offset
        if pitch_offset != 0:
            factor = 2 ** (pitch_offset / 12)
            new_len = int(len(samples) / factor)
            samples = np.interp(
                np.linspace(0, len(samples) - 1, new_len),
                np.arange(len(samples)),
                samples
            )

        # Apply theme-based reverb
        samples = simple_reverb(
            samples,
            self.palette.reverb_size * intensity,
            self.palette.reverb_damping
        )

        # Final processing
        samples = apply_fade(samples)
        samples = soft_clip(samples)
        samples = normalize(samples, -6.0 - (1 - intensity) * 6)

        return samples

    def _get_note(self, degree: int = 0) -> float:
        """Get a note frequency from the theme's scale."""
        scale = self.palette.scale
        octave = degree // len(scale)
        scale_degree = degree % len(scale)
        return self.palette.root_note * scale[scale_degree] * (2 ** octave)

    # -------------------------------------------------------------------------
    # Individual Sound Generators
    # -------------------------------------------------------------------------

    def _gen_appear(self, duration: float, intensity: float) -> np.ndarray:
        """Element appearing - soft pop with shimmer."""
        n_samples = int(duration * SAMPLE_RATE)
        t = np.linspace(0, duration, n_samples)

        # Base frequency with slight rise
        base_freq = self._get_note(2) * (1 + self.palette.brightness * 0.5)
        freq_env = 1 + 0.3 * np.exp(-t * 15)

        # FM body with digital character
        mod_index = 2 + self.palette.digital_amount * 3
        body = fm_oscillator(t, base_freq * freq_env, base_freq * 2.5, mod_index)
        body *= envelope_adsr(n_samples, 0.01, 0.15, 0.3, 0.5)

        # Transient click
        click = filtered_noise(n_samples, "highpass", 2000 + self.palette.brightness * 4000)
        click *= np.exp(-t * 80) * 0.4

        # High shimmer
        shimmer_freq = base_freq * 4
        shimmer = np.sin(2 * np.pi * shimmer_freq * t)
        shimmer += 0.5 * np.sin(2 * np.pi * shimmer_freq * 1.5 * t)
        shimmer *= np.exp(-t * 12) * 0.2 * self.palette.brightness

        # Sub weight
        sub = np.sin(2 * np.pi * self.palette.bass_freq[0] * t)
        sub *= np.exp(-t * 20) * 0.3 * self.palette.warmth

        return body + click + shimmer + sub

    def _gen_disappear(self, duration: float, intensity: float) -> np.ndarray:
        """Element disappearing - reverse envelope, falling pitch."""
        n_samples = int(duration * SAMPLE_RATE)
        t = np.linspace(0, duration, n_samples)

        base_freq = self._get_note(1)

        # Falling pitch
        freq_env = base_freq * np.exp(-t * 3)

        # FM with decreasing modulation
        mod_env = 3 * (1 - t / duration)
        body = np.zeros(n_samples)
        for i in range(n_samples):
            phase = 2 * np.pi * np.sum(freq_env[:i+1]) / SAMPLE_RATE
            mod = mod_env[i] * np.sin(2 * np.pi * freq_env[i] * 0.5 * t[i])
            body[i] = np.sin(phase + mod)

        # Fade out envelope
        env = 1 - (t / duration) ** 0.5
        body *= env

        # Filtered noise tail
        noise = filtered_noise(n_samples, "bandpass", (300, 2000))
        noise *= (1 - t / duration) ** 2 * 0.2

        return body + noise

    def _gen_text_reveal(self, duration: float, intensity: float) -> np.ndarray:
        """Text appearing - crisp, typewriter-like."""
        n_samples = int(duration * SAMPLE_RATE)
        t = np.linspace(0, duration, n_samples)

        # Very short, crisp transient
        click_freq = 3000 + self.palette.brightness * 3000
        click = filtered_noise(n_samples, "highpass", click_freq, resonance=2.0)
        click *= np.exp(-t * 150)

        # Subtle tonal ping
        ping_freq = self._get_note(4)
        ping = np.sin(2 * np.pi * ping_freq * t)
        ping *= np.exp(-t * 60) * 0.3

        # Tiny mechanical body
        body_freq = 1200
        body = np.sin(2 * np.pi * body_freq * t)
        body *= np.exp(-t * 80) * 0.2

        return click + ping + body

    def _gen_transition(self, duration: float, intensity: float) -> np.ndarray:
        """Phase transition - smooth sweep with texture."""
        n_samples = int(duration * SAMPLE_RATE)
        t = np.linspace(0, duration, n_samples)

        # Frequency sweep
        start_freq = self.palette.mid_freq[0]
        end_freq = self.palette.mid_freq[1]
        freq = start_freq + (end_freq - start_freq) * (t / duration)

        # Swept filtered noise
        whoosh = np.zeros(n_samples)
        chunk_size = n_samples // 20
        for i in range(20):
            start = i * chunk_size
            end = min((i + 1) * chunk_size, n_samples)
            center_freq = start_freq + (end_freq - start_freq) * (i / 20)
            band = filtered_noise(end - start, "bandpass", (center_freq * 0.7, center_freq * 1.3))
            whoosh[start:end] = band

        # Envelope - swell in middle
        env = np.sin(np.pi * t / duration) ** 0.7
        whoosh *= env * 0.6

        # Tonal sweep underneath
        sweep = np.sin(2 * np.pi * np.cumsum(freq) / SAMPLE_RATE)
        sweep *= env * 0.3 * (1 - self.palette.digital_amount * 0.5)

        return whoosh + sweep

    def _gen_data_flow(self, duration: float, intensity: float) -> np.ndarray:
        """Data streaming - flowing, digital texture."""
        n_samples = int(duration * SAMPLE_RATE)
        t = np.linspace(0, duration, n_samples)

        # Base texture - filtered noise with movement
        texture = filtered_noise(n_samples, "bandpass", self.palette.mid_freq)

        # Add rhythmic pulses for "data packets"
        pulse_freq = 12 + self.palette.movement * 8
        pulses = 0.5 + 0.5 * np.sin(2 * np.pi * pulse_freq * t)
        texture *= pulses

        # Digital modulation
        if self.palette.digital_amount > 0.3:
            mod_freq = 50 + self.palette.digital_amount * 100
            digital_mod = 0.7 + 0.3 * np.sin(2 * np.pi * mod_freq * t)
            texture *= digital_mod

        # FM undertone
        base_freq = self._get_note(0)
        undertone = fm_oscillator(t, base_freq, base_freq * 1.5, 1.5)
        undertone *= 0.2 * self.palette.warmth

        # Envelope
        env = envelope_adsr(n_samples, 0.05, 0.1, 0.8, 0.15)

        return (texture * 0.5 + undertone) * env

    def _gen_transform(self, duration: float, intensity: float) -> np.ndarray:
        """Morphing/transformation - evolving texture."""
        n_samples = int(duration * SAMPLE_RATE)
        t = np.linspace(0, duration, n_samples)

        base_freq = self._get_note(1)

        # Morphing FM - modulation index changes over time
        mod_index = 1 + 4 * np.sin(np.pi * t / duration)
        morph = np.zeros(n_samples)
        for i in range(n_samples):
            mod = mod_index[i] * np.sin(2 * np.pi * base_freq * 1.5 * t[i])
            morph[i] = np.sin(2 * np.pi * base_freq * t[i] + mod)

        # Add granular texture for complexity
        grain_source = filtered_noise(n_samples, "bandpass", (500, 3000))
        grains = granular_texture(grain_source, 30, 0.4, 0.2, 0.2)

        # Blend based on digital amount
        blend = morph * (1 - self.palette.digital_amount * 0.5) + grains * self.palette.digital_amount * 0.3

        env = np.sin(np.pi * t / duration) ** 0.5

        return blend * env

    def _gen_connection(self, duration: float, intensity: float) -> np.ndarray:
        """Two things connecting - dual tones meeting."""
        n_samples = int(duration * SAMPLE_RATE)
        t = np.linspace(0, duration, n_samples)

        freq1 = self._get_note(0)
        freq2 = self._get_note(2)

        # Two tones that converge
        mid_freq = (freq1 + freq2) / 2

        # Frequency envelopes - start apart, meet in middle
        freq1_env = freq1 + (mid_freq - freq1) * (t / duration)
        freq2_env = freq2 + (mid_freq - freq2) * (t / duration)

        tone1 = np.sin(2 * np.pi * np.cumsum(freq1_env) / SAMPLE_RATE)
        tone2 = np.sin(2 * np.pi * np.cumsum(freq2_env) / SAMPLE_RATE)

        # Click at connection point
        connection_point = int(n_samples * 0.7)
        click = np.zeros(n_samples)
        click_len = min(int(0.02 * SAMPLE_RATE), n_samples - connection_point)
        click[connection_point:connection_point + click_len] = np.random.randn(click_len) * np.exp(-np.linspace(0, 10, click_len))

        # Envelope
        env = envelope_adsr(n_samples, 0.05, 0.15, 0.6, 0.3)

        return (tone1 * 0.4 + tone2 * 0.4 + click * 0.3) * env

    def _gen_lock(self, duration: float, intensity: float) -> np.ndarray:
        """Locking into place - satisfying mechanical snap."""
        n_samples = int(duration * SAMPLE_RATE)
        t = np.linspace(0, duration, n_samples)

        # Sharp transient
        transient = filtered_noise(int(0.005 * SAMPLE_RATE), "highpass", 1500)
        transient = np.pad(transient, (0, n_samples - len(transient)))
        transient *= np.exp(-t * 100) * 1.5

        # Metallic ping - slightly detuned for realism
        freq1 = self._get_note(3)
        freq2 = freq1 * 1.015  # Slight detune
        metal = np.sin(2 * np.pi * freq1 * t) + np.sin(2 * np.pi * freq2 * t)
        metal += 0.3 * np.sin(2 * np.pi * freq1 * 2.7 * t)  # Inharmonic
        metal *= np.exp(-t * 25) * 0.4

        # Low thunk for weight
        thunk_freq = self.palette.bass_freq[1]
        thunk = np.sin(2 * np.pi * thunk_freq * t)
        thunk *= np.exp(-t * 30) * 0.5 * self.palette.warmth

        return transient + metal + thunk

    def _gen_unlock(self, duration: float, intensity: float) -> np.ndarray:
        """Releasing/unlocking - lighter than lock, rising pitch."""
        n_samples = int(duration * SAMPLE_RATE)
        t = np.linspace(0, duration, n_samples)

        # Rising pitch click
        base_freq = self._get_note(2)
        freq_env = base_freq * (1 + 0.5 * (t / duration))

        click = np.sin(2 * np.pi * np.cumsum(freq_env) / SAMPLE_RATE)
        click *= np.exp(-t * 40)

        # Airy release texture
        air = filtered_noise(n_samples, "highpass", 3000)
        air *= np.exp(-t * 15) * 0.3

        return click + air

    def _gen_success(self, duration: float, intensity: float) -> np.ndarray:
        """Positive outcome - warm, uplifting chord."""
        n_samples = int(duration * SAMPLE_RATE)
        t = np.linspace(0, duration, n_samples)

        # Major chord with staggered entry
        freqs = [self._get_note(0), self._get_note(2), self._get_note(4)]
        delays = [0, 0.02, 0.04]

        chord = np.zeros(n_samples)
        for freq, delay in zip(freqs, delays):
            delay_samples = int(delay * SAMPLE_RATE)
            note_len = n_samples - delay_samples

            if note_len > 0:
                note_t = np.linspace(0, note_len / SAMPLE_RATE, note_len)
                # Bell-like harmonics
                note = np.sin(2 * np.pi * freq * note_t)
                note += 0.3 * np.sin(2 * np.pi * freq * 2 * note_t)
                note += 0.15 * np.sin(2 * np.pi * freq * 3 * note_t)
                note *= np.exp(-note_t * 6)
                chord[delay_samples:] += note * 0.4

        # Sparkle on top
        sparkle = filtered_noise(n_samples, "highpass", 5000)
        sparkle *= np.exp(-t * 12) * 0.15 * self.palette.brightness

        return chord + sparkle

    def _gen_warning(self, duration: float, intensity: float) -> np.ndarray:
        """Problem/caution - low, unsettling rumble."""
        n_samples = int(duration * SAMPLE_RATE)
        t = np.linspace(0, duration, n_samples)

        # Low growl with harmonics
        freq = self.palette.bass_freq[0] * 1.5
        tone = fm_oscillator(t, freq, freq * 0.5, 2, [(2, 0.5), (3, 0.3)])

        # Tremolo for unease
        tremolo = 0.7 + 0.3 * np.sin(2 * np.pi * 6 * t)
        tone *= tremolo

        # Sub bass
        sub = np.sin(2 * np.pi * freq * 0.5 * t)
        sub *= 0.4

        env = envelope_adsr(n_samples, 0.02, 0.2, 0.6, 0.3)

        return (tone + sub) * env

    def _gen_error(self, duration: float, intensity: float) -> np.ndarray:
        """Failure - harsh, discordant."""
        n_samples = int(duration * SAMPLE_RATE)
        t = np.linspace(0, duration, n_samples)

        # Dissonant interval
        freq1 = self._get_note(0)
        freq2 = freq1 * 1.06  # Minor second - very dissonant

        tone1 = np.sin(2 * np.pi * freq1 * t)
        tone2 = np.sin(2 * np.pi * freq2 * t)

        # Distorted noise burst
        noise = filtered_noise(n_samples, "bandpass", (200, 1500))
        noise = np.clip(noise * 3, -1, 1)  # Hard clip for harshness
        noise *= np.exp(-t * 10) * 0.4

        env = envelope_adsr(n_samples, 0.01, 0.15, 0.4, 0.4)

        return (tone1 * 0.4 + tone2 * 0.4 + noise) * env

    def _gen_reveal(self, duration: float, intensity: float) -> np.ndarray:
        """Big reveal - cinematic impact with tail."""
        n_samples = int(duration * SAMPLE_RATE)
        t = np.linspace(0, duration, n_samples)

        # Massive transient
        transient = filtered_noise(int(0.01 * SAMPLE_RATE), "bandpass", (500, 4000))
        transient = np.pad(transient, (0, max(0, n_samples - len(transient))))[:n_samples]
        transient *= np.exp(-t * 50) * 2
        transient = soft_clip(transient, 0.6)

        # Sub drop
        sub_freq = self.palette.bass_freq[1] + 40 * np.exp(-t * 15)
        sub = np.sin(2 * np.pi * np.cumsum(sub_freq) / SAMPLE_RATE)
        sub *= np.exp(-t * 6) * 0.8

        # Mid punch
        mid_freq = self._get_note(0)
        mid = fm_oscillator(t, mid_freq, mid_freq * 1.5, 3)
        mid *= np.exp(-t * 10) * 0.5

        # Shimmer tail
        shimmer_freq = self._get_note(4)
        shimmer = np.sin(2 * np.pi * shimmer_freq * t)
        shimmer += 0.5 * np.sin(2 * np.pi * shimmer_freq * 1.5 * t)
        shimmer *= np.exp(-t * 4) * 0.25 * self.palette.brightness

        return transient + sub + mid + shimmer

    def _gen_counter(self, duration: float, intensity: float) -> np.ndarray:
        """Numbers counting - rising sweep with energy."""
        n_samples = int(duration * SAMPLE_RATE)
        t = np.linspace(0, duration, n_samples)

        # Accelerating frequency sweep
        start_freq = self._get_note(0)
        end_freq = self._get_note(7)  # Octave + third

        # Exponential sweep feels more energetic
        freq = start_freq * (end_freq / start_freq) ** (t / duration)

        sweep = np.sin(2 * np.pi * np.cumsum(freq) / SAMPLE_RATE)
        sweep2 = np.sin(4 * np.pi * np.cumsum(freq) / SAMPLE_RATE) * 0.3

        # Punchy transient at start
        transient = filtered_noise(n_samples, "highpass", 2000)
        transient *= np.exp(-t * 60) * 0.5

        env = envelope_adsr(n_samples, 0.02, 0.1, 0.7, 0.2)

        return (sweep + sweep2 + transient) * env

    def _gen_pulse(self, duration: float, intensity: float) -> np.ndarray:
        """Rhythmic pulse - heartbeat-like emphasis."""
        n_samples = int(duration * SAMPLE_RATE)
        t = np.linspace(0, duration, n_samples)

        freq = self._get_note(0)

        # Main pulse
        pulse = np.sin(2 * np.pi * freq * t)
        pulse += 0.5 * np.sin(2 * np.pi * freq * 2 * t)

        # Sharp attack, quick decay
        env = np.exp(-t * 15)

        # Sub thump
        sub = np.sin(2 * np.pi * 50 * t)
        sub *= np.exp(-t * 20) * 0.6

        return (pulse * 0.7 + sub) * env

    def _gen_ping(self, duration: float, intensity: float) -> np.ndarray:
        """Quick attention ping - bright and clear."""
        n_samples = int(duration * SAMPLE_RATE)
        t = np.linspace(0, duration, n_samples)

        # High, clear bell tone
        freq = self._get_note(5)  # Higher note

        # Bell harmonics (slightly inharmonic for realism)
        ping = np.sin(2 * np.pi * freq * t)
        ping += 0.4 * np.sin(2 * np.pi * freq * 2.0 * t)
        ping += 0.2 * np.sin(2 * np.pi * freq * 2.92 * t)  # Slightly sharp
        ping += 0.1 * np.sin(2 * np.pi * freq * 5.4 * t)

        env = np.exp(-t * 12)

        return ping * env * 0.7


# =============================================================================
# Project SFX Manager
# =============================================================================

def save_wav(samples: np.ndarray, filepath: Path, sample_rate: int = SAMPLE_RATE):
    """Save samples to WAV file."""
    samples = normalize(samples, -3.0)
    samples_int = np.int16(np.clip(samples, -1, 1) * 32767)

    filepath.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(filepath), 'w') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(samples_int.tobytes())


class ProjectSFXManager:
    """Manages SFX generation for a video project."""

    def __init__(self, project_dir: Path, theme: SoundTheme = SoundTheme.TECH_AI):
        """Initialize SFX manager for a project.

        Args:
            project_dir: Path to project directory
            theme: Sound theme for the project
        """
        self.project_dir = Path(project_dir)
        self.sfx_dir = self.project_dir / "sfx"
        self.generator = SoundGenerator(theme)
        self.theme = theme

    def generate_library(self) -> dict[str, Path]:
        """Generate a complete SFX library for all event types.

        Returns:
            Dictionary mapping sound names to file paths
        """
        self.sfx_dir.mkdir(parents=True, exist_ok=True)

        generated = {}

        # Generate sounds for each event type
        for event in SoundEvent:
            # Generate base version
            samples = self.generator.generate(event, duration=0.4, intensity=0.7)
            filename = f"{event.value}.wav"
            filepath = self.sfx_dir / filename
            save_wav(samples, filepath)
            generated[event.value] = filepath

            # Generate short version for quick events
            if event in [SoundEvent.TEXT_REVEAL, SoundEvent.PING, SoundEvent.PULSE]:
                samples_short = self.generator.generate(event, duration=0.15, intensity=0.6)
                filename_short = f"{event.value}_short.wav"
                filepath_short = self.sfx_dir / filename_short
                save_wav(samples_short, filepath_short)
                generated[f"{event.value}_short"] = filepath_short

            # Generate intense version for emphasis
            if event in [SoundEvent.REVEAL, SoundEvent.SUCCESS, SoundEvent.WARNING]:
                samples_intense = self.generator.generate(event, duration=0.6, intensity=1.0)
                filename_intense = f"{event.value}_intense.wav"
                filepath_intense = self.sfx_dir / filename_intense
                save_wav(samples_intense, filepath_intense)
                generated[f"{event.value}_intense"] = filepath_intense

        return generated

    def generate_custom(
        self,
        name: str,
        event: SoundEvent,
        duration: float = 0.3,
        intensity: float = 0.7,
        pitch_offset: float = 0.0
    ) -> Path:
        """Generate a custom sound with specific parameters.

        Args:
            name: Filename (without extension)
            event: Type of sound event
            duration: Duration in seconds
            intensity: Sound intensity (0-1)
            pitch_offset: Pitch shift in semitones

        Returns:
            Path to generated file
        """
        self.sfx_dir.mkdir(parents=True, exist_ok=True)

        samples = self.generator.generate(
            event,
            duration=duration,
            intensity=intensity,
            pitch_offset=pitch_offset
        )

        filepath = self.sfx_dir / f"{name}.wav"
        save_wav(samples, filepath)

        return filepath

    def list_sounds(self) -> list[str]:
        """List all generated sounds in the project."""
        if not self.sfx_dir.exists():
            return []
        return [f.stem for f in self.sfx_dir.glob("*.wav")]


def generate_project_sfx(
    project_dir: Path,
    theme: str = "tech_ai"
) -> dict[str, Path]:
    """Generate SFX library for a project.

    Args:
        project_dir: Path to project directory
        theme: Theme name (tech_ai, science, finance, space, nature, abstract)

    Returns:
        Dictionary of generated sound names to file paths
    """
    theme_enum = SoundTheme(theme) if theme in [t.value for t in SoundTheme] else SoundTheme.TECH_AI

    manager = ProjectSFXManager(project_dir, theme_enum)
    return manager.generate_library()


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python generator.py <project_dir> [theme]")
        print("Themes: tech_ai, science, finance, space, nature, abstract")
        sys.exit(1)

    project_dir = Path(sys.argv[1])
    theme = sys.argv[2] if len(sys.argv) > 2 else "tech_ai"

    print(f"Generating SFX for {project_dir} with theme '{theme}'...")

    generated = generate_project_sfx(project_dir, theme)

    print(f"\nGenerated {len(generated)} sounds:")
    for name, path in generated.items():
        print(f"  - {name}: {path}")
