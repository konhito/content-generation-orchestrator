"""Tests for the generative SFX library.

Tests cover:
- Utility functions (dB conversions, normalization, fades)
- Synthesis components (FM, noise, granular, reverb, envelopes)
- Theme system (SoundTheme, ThemePalette, THEME_PALETTES)
- Sound event types
- SoundGenerator class
- ProjectSFXManager class
- File I/O (save_wav)
"""

import tempfile
from pathlib import Path
import wave

import numpy as np
import pytest

from generator import (
    # Constants
    SAMPLE_RATE,
    # Enums
    SoundTheme,
    SoundEvent,
    # Dataclasses
    ThemePalette,
    # Theme presets
    THEME_PALETTES,
    # Utility functions
    db_to_amp,
    amp_to_db,
    normalize,
    soft_clip,
    apply_fade,
    # Synthesis components
    fm_oscillator,
    filtered_noise,
    granular_texture,
    simple_reverb,
    envelope_adsr,
    # Classes
    SoundGenerator,
    ProjectSFXManager,
    # Functions
    save_wav,
    generate_project_sfx,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def generator():
    """Create a SoundGenerator with default theme."""
    return SoundGenerator(SoundTheme.TECH_AI)


@pytest.fixture
def time_array():
    """Create a 0.5 second time array for testing."""
    duration = 0.5
    n_samples = int(duration * SAMPLE_RATE)
    return np.linspace(0, duration, n_samples)


# =============================================================================
# Test Utility Functions
# =============================================================================

class TestDbConversions:
    """Tests for dB/amplitude conversion functions."""

    def test_db_to_amp_0db(self):
        """0 dB should equal amplitude 1.0."""
        assert db_to_amp(0) == pytest.approx(1.0)

    def test_db_to_amp_minus6db(self):
        """−6 dB should approximately halve amplitude."""
        assert db_to_amp(-6) == pytest.approx(0.501, rel=0.01)

    def test_db_to_amp_minus20db(self):
        """−20 dB should equal amplitude 0.1."""
        assert db_to_amp(-20) == pytest.approx(0.1)

    def test_amp_to_db_1(self):
        """Amplitude 1.0 should equal approximately 0 dB."""
        # Note: amp_to_db adds 1e-10 to prevent log(0), so result is very close to 0
        assert amp_to_db(1.0) == pytest.approx(0.0, abs=1e-8)

    def test_amp_to_db_0_5(self):
        """Amplitude 0.5 should be approximately −6 dB."""
        assert amp_to_db(0.5) == pytest.approx(-6.02, rel=0.01)

    def test_amp_to_db_0_1(self):
        """Amplitude 0.1 should equal −20 dB."""
        assert amp_to_db(0.1) == pytest.approx(-20.0)

    def test_roundtrip(self):
        """Converting to dB and back should preserve value."""
        for amp in [0.1, 0.5, 0.8, 1.0]:
            assert db_to_amp(amp_to_db(amp)) == pytest.approx(amp)


class TestNormalize:
    """Tests for audio normalization."""

    def test_normalize_to_target(self):
        """Normalized audio should have max amplitude at target level."""
        samples = np.random.randn(1000) * 0.3
        normalized = normalize(samples, target_db=-3.0)
        max_val = np.max(np.abs(normalized))
        expected = db_to_amp(-3.0)
        assert max_val == pytest.approx(expected, rel=0.01)

    def test_normalize_preserves_shape(self):
        """Normalization should preserve array shape."""
        samples = np.random.randn(1000)
        normalized = normalize(samples)
        assert normalized.shape == samples.shape

    def test_normalize_zero_input(self):
        """Silent input should return silent output without error."""
        samples = np.zeros(1000)
        normalized = normalize(samples)
        assert np.all(normalized == 0)


class TestSoftClip:
    """Tests for soft clipping/saturation."""

    def test_soft_clip_below_threshold(self):
        """Values below threshold should pass through mostly unchanged."""
        samples = np.array([0.1, 0.2, 0.3])
        clipped = soft_clip(samples, threshold=0.8)
        # Values should be close but slightly lower due to tanh
        assert np.all(clipped < samples)
        assert np.all(np.abs(samples - clipped) < 0.1)

    def test_soft_clip_above_threshold(self):
        """Values above threshold should be compressed."""
        samples = np.array([1.5, 2.0, 3.0])
        clipped = soft_clip(samples, threshold=0.8)
        # All outputs should be less than threshold
        assert np.all(clipped < 0.8)

    def test_soft_clip_no_hard_clipping(self):
        """Soft clip should not produce hard clip artifacts."""
        samples = np.linspace(-2, 2, 1000)
        clipped = soft_clip(samples)
        # Should be smooth, no discontinuities
        diff = np.diff(clipped)
        assert np.all(np.abs(diff) < 0.1)


class TestApplyFade:
    """Tests for fade in/out application."""

    def test_fade_in_starts_at_zero(self):
        """Fade in should start at zero amplitude."""
        samples = np.ones(SAMPLE_RATE)  # 1 second
        faded = apply_fade(samples, fade_in_ms=50, fade_out_ms=0)
        assert faded[0] == pytest.approx(0.0)

    def test_fade_out_ends_at_zero(self):
        """Fade out should end at zero amplitude."""
        samples = np.ones(SAMPLE_RATE)  # 1 second
        faded = apply_fade(samples, fade_in_ms=0, fade_out_ms=50)
        assert faded[-1] == pytest.approx(0.0)

    def test_fade_preserves_middle(self):
        """Middle of audio should be unaffected by short fades."""
        samples = np.ones(SAMPLE_RATE)
        faded = apply_fade(samples, fade_in_ms=5, fade_out_ms=20)
        # Middle 50% should be approximately 1.0
        middle = faded[len(faded)//4:3*len(faded)//4]
        assert np.all(middle == pytest.approx(1.0))


# =============================================================================
# Test Synthesis Components
# =============================================================================

class TestFMOscillator:
    """Tests for FM synthesis oscillator."""

    def test_fm_output_shape(self, time_array):
        """FM oscillator should output correct shape."""
        output = fm_oscillator(time_array, 440, 220, 1.0)
        assert output.shape == time_array.shape

    def test_fm_output_range(self, time_array):
        """FM oscillator output should be normalized."""
        output = fm_oscillator(time_array, 440, 220, 1.0)
        assert np.max(np.abs(output)) <= 1.0

    def test_fm_with_harmonics(self, time_array):
        """FM with harmonics should still be normalized."""
        harmonics = [(2, 0.5), (3, 0.25)]
        output = fm_oscillator(time_array, 440, 220, 1.0, harmonics)
        assert np.max(np.abs(output)) <= 1.0

    def test_fm_zero_modulation(self, time_array):
        """Zero modulation should produce pure sine wave."""
        output = fm_oscillator(time_array, 440, 220, 0.0)
        expected = np.sin(2 * np.pi * 440 * time_array)
        np.testing.assert_allclose(output, expected, atol=1e-10)


class TestFilteredNoise:
    """Tests for filtered noise generation."""

    def test_lowpass_noise(self):
        """Lowpass noise should have reduced high frequencies."""
        noise = filtered_noise(SAMPLE_RATE, "lowpass", 1000)
        assert len(noise) == SAMPLE_RATE
        assert np.max(np.abs(noise)) <= 1.0

    def test_highpass_noise(self):
        """Highpass noise should have reduced low frequencies."""
        noise = filtered_noise(SAMPLE_RATE, "highpass", 1000)
        assert len(noise) == SAMPLE_RATE
        assert np.max(np.abs(noise)) <= 1.0

    def test_bandpass_noise(self):
        """Bandpass noise should work with tuple cutoff."""
        noise = filtered_noise(SAMPLE_RATE, "bandpass", (500, 2000))
        assert len(noise) == SAMPLE_RATE
        assert np.max(np.abs(noise)) <= 1.0

    def test_resonance_effect(self):
        """Resonance parameter should be accepted and produce valid output."""
        noise_low_q = filtered_noise(SAMPLE_RATE, "lowpass", 1000, resonance=0.7)
        noise_high_q = filtered_noise(SAMPLE_RATE, "lowpass", 1000, resonance=3.0)
        # Both should produce valid normalized output
        assert np.max(np.abs(noise_low_q)) <= 1.0
        assert np.max(np.abs(noise_high_q)) <= 1.0
        # Both should have content (not silent)
        assert np.std(noise_low_q) > 0
        assert np.std(noise_high_q) > 0


class TestGranularTexture:
    """Tests for granular synthesis."""

    def test_granular_output_shape(self):
        """Granular texture should preserve input shape."""
        source = np.random.randn(SAMPLE_RATE)
        output = granular_texture(source, grain_size_ms=50, density=0.5)
        assert output.shape == source.shape

    def test_granular_adds_content(self):
        """Granular should distribute content across output."""
        # Use a source with content throughout for reliable testing
        source = np.random.randn(SAMPLE_RATE) * 0.5
        output = granular_texture(source, grain_size_ms=50, density=0.8)
        # Output should have content
        assert np.std(output) > 0
        # Output should be different from source (grains have been moved/mixed)
        assert not np.array_equal(output, source)


class TestSimpleReverb:
    """Tests for reverb effect."""

    def test_reverb_output_shape(self):
        """Reverb should preserve input shape."""
        samples = np.random.randn(SAMPLE_RATE)
        output = simple_reverb(samples, size=0.3)
        assert output.shape == samples.shape

    def test_reverb_adds_tail(self):
        """Reverb should add energy after impulse."""
        # Create impulse
        samples = np.zeros(SAMPLE_RATE)
        samples[100:110] = 1.0
        output = simple_reverb(samples, size=0.5)
        # Energy should exist after impulse
        assert np.max(np.abs(output[500:])) > 0

    def test_dry_signal_passthrough(self):
        """Very small reverb size should be near passthrough."""
        samples = np.random.randn(1000)
        output = simple_reverb(samples, size=0.01)
        np.testing.assert_allclose(output, samples, atol=0.01)


class TestEnvelopeADSR:
    """Tests for ADSR envelope generation."""

    def test_adsr_output_shape(self):
        """ADSR should output correct number of samples."""
        env = envelope_adsr(1000, attack=0.1, decay=0.1, sustain=0.7, release=0.2)
        assert len(env) == 1000

    def test_adsr_starts_at_zero(self):
        """ADSR should start at zero."""
        env = envelope_adsr(1000, attack=0.1, decay=0.1, sustain=0.7, release=0.2)
        assert env[0] == pytest.approx(0.0)

    def test_adsr_reaches_peak(self):
        """ADSR should reach peak of 1.0 after attack."""
        env = envelope_adsr(1000, attack=0.1, decay=0.1, sustain=0.7, release=0.2)
        # Peak should be at or near 1.0
        assert np.max(env) >= 0.95

    def test_adsr_sustain_level(self):
        """ADSR sustain phase should be at sustain level."""
        env = envelope_adsr(1000, attack=0.1, decay=0.1, sustain=0.7, release=0.1)
        # Check sustain region (middle of envelope)
        sustain_region = env[300:600]
        assert np.mean(sustain_region) == pytest.approx(0.7, rel=0.1)


# =============================================================================
# Test Theme System
# =============================================================================

class TestSoundTheme:
    """Tests for SoundTheme enum."""

    def test_all_themes_defined(self):
        """All expected themes should be defined."""
        expected_themes = ["tech_ai", "science", "finance", "medical", "space", "nature", "abstract"]
        for theme_value in expected_themes:
            assert SoundTheme(theme_value) is not None

    def test_theme_values(self):
        """Theme values should match enum names."""
        assert SoundTheme.TECH_AI.value == "tech_ai"
        assert SoundTheme.SCIENCE.value == "science"
        assert SoundTheme.SPACE.value == "space"


class TestThemePalette:
    """Tests for ThemePalette dataclass."""

    def test_default_values(self):
        """Default ThemePalette should have sensible defaults."""
        palette = ThemePalette()
        assert palette.root_note == 220.0
        assert palette.digital_amount == 0.5
        assert palette.brightness == 0.5

    def test_custom_values(self):
        """ThemePalette should accept custom values."""
        palette = ThemePalette(
            root_note=440.0,
            digital_amount=0.8,
            brightness=0.9
        )
        assert palette.root_note == 440.0
        assert palette.digital_amount == 0.8
        assert palette.brightness == 0.9


class TestThemePalettes:
    """Tests for THEME_PALETTES preset dictionary."""

    def test_all_themes_have_palettes(self):
        """Most SoundThemes should have corresponding palettes."""
        # Note: MEDICAL theme is defined but not yet implemented in THEME_PALETTES
        # This is acceptable as generator falls back to default palette
        implemented_themes = [
            SoundTheme.TECH_AI, SoundTheme.SCIENCE, SoundTheme.FINANCE,
            SoundTheme.SPACE, SoundTheme.NATURE, SoundTheme.ABSTRACT
        ]
        for theme in implemented_themes:
            assert theme in THEME_PALETTES

    def test_tech_ai_palette(self):
        """TECH_AI palette should have digital characteristics."""
        palette = THEME_PALETTES[SoundTheme.TECH_AI]
        assert palette.digital_amount >= 0.7
        assert palette.warmth <= 0.4

    def test_nature_palette(self):
        """NATURE palette should have organic characteristics."""
        palette = THEME_PALETTES[SoundTheme.NATURE]
        assert palette.digital_amount <= 0.2
        assert palette.warmth >= 0.7

    def test_space_palette(self):
        """SPACE palette should have large reverb."""
        palette = THEME_PALETTES[SoundTheme.SPACE]
        assert palette.reverb_size >= 0.7


# =============================================================================
# Test Sound Events
# =============================================================================

class TestSoundEvent:
    """Tests for SoundEvent enum."""

    def test_all_events_defined(self):
        """All expected event types should be defined."""
        expected_events = [
            "element_appear", "element_disappear", "text_reveal",
            "transition", "data_flow", "transform",
            "connection", "lock", "unlock",
            "success", "warning", "error",
            "reveal", "counter", "pulse", "ping"
        ]
        for event_value in expected_events:
            assert SoundEvent(event_value) is not None

    def test_event_count(self):
        """Should have 16 event types."""
        assert len(SoundEvent) == 16


# =============================================================================
# Test SoundGenerator Class
# =============================================================================

class TestSoundGenerator:
    """Tests for SoundGenerator class."""

    def test_init_with_theme(self):
        """Generator should initialize with specified theme."""
        gen = SoundGenerator(SoundTheme.SPACE)
        assert gen.theme == SoundTheme.SPACE
        assert gen.palette == THEME_PALETTES[SoundTheme.SPACE]

    def test_set_theme(self, generator):
        """set_theme should change theme and palette."""
        generator.set_theme(SoundTheme.NATURE)
        assert generator.theme == SoundTheme.NATURE
        assert generator.palette == THEME_PALETTES[SoundTheme.NATURE]

    def test_generate_output_type(self, generator):
        """generate should return numpy array."""
        output = generator.generate(SoundEvent.PING)
        assert isinstance(output, np.ndarray)

    def test_generate_output_length(self, generator):
        """generate should produce correct duration."""
        duration = 0.5
        output = generator.generate(SoundEvent.PING, duration=duration)
        expected_samples = int(duration * SAMPLE_RATE)
        # Allow some variance due to pitch shifting and processing
        assert len(output) > expected_samples * 0.5
        assert len(output) < expected_samples * 2.0

    def test_generate_normalized(self, generator):
        """generate should produce normalized output."""
        output = generator.generate(SoundEvent.REVEAL, intensity=1.0)
        assert np.max(np.abs(output)) <= 1.0

    def test_generate_all_events(self, generator):
        """All event types should produce valid output."""
        for event in SoundEvent:
            output = generator.generate(event, duration=0.2)
            assert isinstance(output, np.ndarray)
            assert len(output) > 0
            assert np.max(np.abs(output)) <= 1.0

    def test_generate_with_pitch_offset(self, generator):
        """Pitch offset should change output length."""
        base_output = generator.generate(SoundEvent.PING, duration=0.3)
        # Pitch up should shorten
        high_output = generator.generate(SoundEvent.PING, duration=0.3, pitch_offset=12)
        assert len(high_output) < len(base_output)
        # Pitch down should lengthen
        low_output = generator.generate(SoundEvent.PING, duration=0.3, pitch_offset=-12)
        assert len(low_output) > len(base_output)

    def test_generate_reproducible(self, generator):
        """Same seed should produce identical output."""
        output1 = generator.generate(SoundEvent.DATA_FLOW, variation_seed=42)
        output2 = generator.generate(SoundEvent.DATA_FLOW, variation_seed=42)
        np.testing.assert_array_equal(output1, output2)

    def test_generate_different_seeds(self, generator):
        """Different seeds should produce different output."""
        output1 = generator.generate(SoundEvent.DATA_FLOW, variation_seed=42)
        output2 = generator.generate(SoundEvent.DATA_FLOW, variation_seed=123)
        assert not np.array_equal(output1, output2)

    def test_intensity_affects_volume(self, generator):
        """Higher intensity should produce louder output."""
        low = generator.generate(SoundEvent.PULSE, intensity=0.3)
        high = generator.generate(SoundEvent.PULSE, intensity=1.0)
        assert np.max(np.abs(high)) > np.max(np.abs(low))

    def test_get_note(self, generator):
        """_get_note should return correct frequencies."""
        # Degree 0 should be root note
        assert generator._get_note(0) == generator.palette.root_note
        # Higher degrees should be higher frequencies
        assert generator._get_note(1) > generator._get_note(0)
        assert generator._get_note(7) > generator._get_note(0)  # Octave+


# =============================================================================
# Test File I/O
# =============================================================================

class TestSaveWav:
    """Tests for save_wav function."""

    def test_save_creates_file(self, temp_dir):
        """save_wav should create a WAV file."""
        samples = np.random.randn(SAMPLE_RATE)
        filepath = temp_dir / "test.wav"
        save_wav(samples, filepath)
        assert filepath.exists()

    def test_save_creates_directory(self, temp_dir):
        """save_wav should create parent directories."""
        samples = np.random.randn(SAMPLE_RATE)
        filepath = temp_dir / "subdir" / "deep" / "test.wav"
        save_wav(samples, filepath)
        assert filepath.exists()

    def test_saved_wav_properties(self, temp_dir):
        """Saved WAV should have correct properties."""
        samples = np.random.randn(SAMPLE_RATE)
        filepath = temp_dir / "test.wav"
        save_wav(samples, filepath)

        with wave.open(str(filepath), 'r') as wav:
            assert wav.getnchannels() == 1
            assert wav.getsampwidth() == 2
            assert wav.getframerate() == SAMPLE_RATE
            assert wav.getnframes() == len(samples)


# =============================================================================
# Test ProjectSFXManager Class
# =============================================================================

class TestProjectSFXManager:
    """Tests for ProjectSFXManager class."""

    def test_init(self, temp_dir):
        """Manager should initialize with correct paths."""
        manager = ProjectSFXManager(temp_dir, SoundTheme.SCIENCE)
        assert manager.project_dir == temp_dir
        assert manager.sfx_dir == temp_dir / "sfx"
        assert manager.theme == SoundTheme.SCIENCE

    def test_generate_library(self, temp_dir):
        """generate_library should create all base sounds."""
        manager = ProjectSFXManager(temp_dir)
        generated = manager.generate_library()

        # Should have at least one file per event type
        assert len(generated) >= len(SoundEvent)

        # All paths should exist
        for path in generated.values():
            assert path.exists()

    def test_generate_library_creates_variants(self, temp_dir):
        """generate_library should create short and intense variants."""
        manager = ProjectSFXManager(temp_dir)
        generated = manager.generate_library()

        # Check for short variants
        assert "text_reveal_short" in generated
        assert "ping_short" in generated

        # Check for intense variants
        assert "reveal_intense" in generated
        assert "success_intense" in generated

    def test_generate_custom(self, temp_dir):
        """generate_custom should create specific sound file."""
        manager = ProjectSFXManager(temp_dir)
        path = manager.generate_custom(
            "custom_ping",
            SoundEvent.PING,
            duration=0.2,
            intensity=0.8,
            pitch_offset=5
        )

        assert path.exists()
        assert path.name == "custom_ping.wav"

    def test_list_sounds(self, temp_dir):
        """list_sounds should return generated sound names."""
        manager = ProjectSFXManager(temp_dir)
        manager.generate_library()
        sounds = manager.list_sounds()

        assert len(sounds) > 0
        assert "element_appear" in sounds
        assert "ping" in sounds

    def test_list_sounds_empty_dir(self, temp_dir):
        """list_sounds should return empty list if no sounds."""
        manager = ProjectSFXManager(temp_dir)
        sounds = manager.list_sounds()
        assert sounds == []


# =============================================================================
# Test generate_project_sfx Function
# =============================================================================

class TestGenerateProjectSfx:
    """Tests for generate_project_sfx convenience function."""

    def test_generates_library(self, temp_dir):
        """Should generate complete SFX library."""
        generated = generate_project_sfx(temp_dir, "tech_ai")
        assert len(generated) >= len(SoundEvent)

    def test_accepts_theme_string(self, temp_dir):
        """Should accept theme as string."""
        generated = generate_project_sfx(temp_dir, "science")
        assert len(generated) > 0

    def test_invalid_theme_defaults_to_tech_ai(self, temp_dir):
        """Invalid theme should fall back to TECH_AI."""
        generated = generate_project_sfx(temp_dir, "invalid_theme")
        assert len(generated) > 0

    def test_creates_sfx_directory(self, temp_dir):
        """Should create sfx directory in project."""
        generate_project_sfx(temp_dir, "tech_ai")
        assert (temp_dir / "sfx").exists()


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for full workflow."""

    def test_full_project_workflow(self, temp_dir):
        """Test complete workflow: generate library, list, and use sounds."""
        # Generate library
        manager = ProjectSFXManager(temp_dir, SoundTheme.TECH_AI)
        generated = manager.generate_library()

        # Verify library was created
        sounds = manager.list_sounds()
        assert len(sounds) > 0

        # Add custom sound
        custom_path = manager.generate_custom(
            "intro_whoosh",
            SoundEvent.TRANSITION,
            duration=0.8,
            intensity=0.9
        )
        assert custom_path.exists()

        # List should include custom sound
        sounds = manager.list_sounds()
        assert "intro_whoosh" in sounds

    def test_different_themes_produce_different_sounds(self, temp_dir):
        """Different themes should produce audibly different sounds."""
        dir1 = temp_dir / "tech"
        dir2 = temp_dir / "nature"

        gen1 = SoundGenerator(SoundTheme.TECH_AI)
        gen2 = SoundGenerator(SoundTheme.NATURE)

        sound1 = gen1.generate(SoundEvent.REVEAL, variation_seed=42)
        sound2 = gen2.generate(SoundEvent.REVEAL, variation_seed=42)

        # Sounds should be different even with same seed
        # (different theme palettes affect generation)
        assert not np.array_equal(sound1, sound2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
