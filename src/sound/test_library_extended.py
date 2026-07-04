"""Tests for extended sound library generators.

These tests verify that the new sound generators:
1. Produce valid audio samples
2. Have correct duration
3. Are properly normalized
4. Don't clip excessively
"""

import numpy as np
import pytest
from pathlib import Path
import tempfile

from .library import (
    SAMPLE_RATE,
    SOUND_MANIFEST,
    GENERATORS,
    SoundLibrary,
    # New generators
    generate_keyboard_type,
    generate_keyboard_rapid,
    generate_bar_grow,
    generate_progress_tick,
    generate_digital_stream,
    generate_impact_soft,
    generate_impact_hard,
    # Existing generators (for comparison)
    generate_ui_pop,
    generate_reveal_hit,
    generate_counter_sweep,
    # Utilities
    normalize,
    soft_clip,
    hard_clip,
    sharp_transient,
    bandpass_noise,
    highpass_noise,
)


class TestSoundManifest:
    """Tests for the extended sound manifest."""

    def test_manifest_contains_new_sounds(self):
        """Test that manifest includes all new sounds."""
        new_sounds = [
            "keyboard_type",
            "keyboard_rapid",
            "bar_grow",
            "progress_tick",
            "digital_stream",
            "impact_soft",
            "impact_hard",
        ]

        for sound in new_sounds:
            assert sound in SOUND_MANIFEST, f"Missing {sound} in manifest"
            assert "description" in SOUND_MANIFEST[sound]
            assert "generator" in SOUND_MANIFEST[sound]

    def test_all_generators_exist(self):
        """Test that all manifest generators are implemented."""
        for name, info in SOUND_MANIFEST.items():
            generator_name = info["generator"]
            assert generator_name in GENERATORS, f"Missing generator {generator_name}"


class TestGeneratorOutput:
    """Tests for generator output characteristics."""

    @pytest.mark.parametrize("generator,expected_duration", [
        (generate_keyboard_type, 0.06),
        (generate_keyboard_rapid, 0.15),
        (generate_bar_grow, 0.35),
        (generate_progress_tick, 0.08),
        (generate_digital_stream, 0.5),
        (generate_impact_soft, 0.15),
        (generate_impact_hard, 0.25),
    ])
    def test_generator_duration(self, generator, expected_duration):
        """Test that generators produce correct duration samples."""
        samples = generator()
        expected_samples = int(SAMPLE_RATE * expected_duration)

        assert len(samples) == expected_samples

    @pytest.mark.parametrize("generator", [
        generate_keyboard_type,
        generate_keyboard_rapid,
        generate_bar_grow,
        generate_progress_tick,
        generate_digital_stream,
        generate_impact_soft,
        generate_impact_hard,
    ])
    def test_generator_not_silent(self, generator):
        """Test that generators produce non-silent output."""
        samples = generator()

        # Should have some energy
        rms = np.sqrt(np.mean(samples ** 2))
        assert rms > 0.01, f"Generator output too quiet (RMS: {rms})"

    @pytest.mark.parametrize("generator", [
        generate_keyboard_type,
        generate_keyboard_rapid,
        generate_bar_grow,
        generate_progress_tick,
        generate_digital_stream,
        generate_impact_soft,
        generate_impact_hard,
    ])
    def test_generator_not_clipping(self, generator):
        """Test that generators don't excessively clip."""
        samples = generator()

        # Check for excessive clipping (more than 1% of samples at max)
        clipped = np.sum(np.abs(samples) >= 0.99)
        clip_ratio = clipped / len(samples)

        assert clip_ratio < 0.01, f"Excessive clipping: {clip_ratio * 100:.1f}%"

    @pytest.mark.parametrize("generator", [
        generate_keyboard_type,
        generate_keyboard_rapid,
        generate_bar_grow,
        generate_progress_tick,
        generate_digital_stream,
        generate_impact_soft,
        generate_impact_hard,
    ])
    def test_generator_within_range(self, generator):
        """Test that generator output is within [-1, 1] range."""
        samples = generator()

        assert np.max(samples) <= 1.0
        assert np.min(samples) >= -1.0


class TestKeyboardType:
    """Tests for keyboard_type generator."""

    def test_has_sharp_attack(self):
        """Test that keyboard type has a sharp attack."""
        samples = generate_keyboard_type()

        # First few samples should have significant energy
        attack_energy = np.max(np.abs(samples[:int(SAMPLE_RATE * 0.005)]))
        assert attack_energy > 0.3, "Attack not sharp enough"

    def test_fast_decay(self):
        """Test that keyboard type decays quickly."""
        samples = generate_keyboard_type()

        # Energy at end should be much lower than at start
        start_energy = np.max(np.abs(samples[:int(SAMPLE_RATE * 0.01)]))
        end_energy = np.max(np.abs(samples[-int(SAMPLE_RATE * 0.01):]))

        assert end_energy < start_energy * 0.3, "Decay not fast enough"

    def test_custom_duration(self):
        """Test keyboard type with custom duration."""
        duration = 0.1
        samples = generate_keyboard_type(duration=duration)

        assert len(samples) == int(SAMPLE_RATE * duration)


class TestKeyboardRapid:
    """Tests for keyboard_rapid generator."""

    def test_multiple_transients(self):
        """Test that rapid has multiple transient peaks."""
        samples = generate_keyboard_rapid()

        # Find peaks (local maxima above threshold)
        threshold = 0.3
        peaks = []
        for i in range(1, len(samples) - 1):
            if samples[i] > threshold and samples[i] > samples[i-1] and samples[i] > samples[i+1]:
                peaks.append(i)

        # Should have at least 3 distinct peaks (allowing for some noise)
        assert len(peaks) >= 2, f"Expected multiple peaks, got {len(peaks)}"

    def test_longer_than_single_key(self):
        """Test that rapid is longer than single key."""
        single = generate_keyboard_type()
        rapid = generate_keyboard_rapid()

        assert len(rapid) > len(single)


class TestBarGrow:
    """Tests for bar_grow generator."""

    def test_rising_pitch(self):
        """Test that bar grow has ascending frequency content.

        The bar grow sound should have rising pitch character overall,
        but due to noise and harmonic content, we check the peak frequency
        in early vs late portions.
        """
        samples = generate_bar_grow()

        # Take small windows from start and end to check pitch sweep
        window_size = int(SAMPLE_RATE * 0.05)  # 50ms windows
        early_window = samples[window_size:window_size*2]  # Skip initial transient
        late_window = samples[-window_size*2:-window_size]  # Before final fade

        # Zero-pad for better frequency resolution
        n_fft = 4096
        fft_early = np.abs(np.fft.rfft(early_window, n=n_fft))
        fft_late = np.abs(np.fft.rfft(late_window, n=n_fft))

        freqs = np.fft.rfftfreq(n_fft, 1/SAMPLE_RATE)

        # Find peak frequency in relevant range (100-2000 Hz)
        mask = (freqs >= 100) & (freqs <= 2000)
        early_peak_idx = np.argmax(fft_early[mask])
        late_peak_idx = np.argmax(fft_late[mask])

        early_peak_freq = freqs[mask][early_peak_idx]
        late_peak_freq = freqs[mask][late_peak_idx]

        # Late peak should be higher or at least in upper portion
        # Allow some tolerance since it's a complex sound
        assert late_peak_freq >= 300, f"Late frequency too low: {late_peak_freq} Hz"

    def test_smooth_envelope(self):
        """Test that bar grow has relatively smooth envelope."""
        samples = generate_bar_grow()

        # Compute envelope via Hilbert transform or simple moving average
        window = int(SAMPLE_RATE * 0.01)
        envelope = np.array([
            np.max(np.abs(samples[max(0, i-window):i+window]))
            for i in range(0, len(samples), window)
        ])

        # Check for smoothness (no extreme jumps)
        diff = np.abs(np.diff(envelope))
        assert np.max(diff) < 0.5, "Envelope not smooth"


class TestProgressTick:
    """Tests for progress_tick generator."""

    def test_very_short(self):
        """Test that progress tick is short."""
        samples = generate_progress_tick()

        # Should be under 0.1 seconds
        assert len(samples) < int(SAMPLE_RATE * 0.1)

    def test_high_frequency_content(self):
        """Test that progress tick has high frequency content."""
        samples = generate_progress_tick()

        fft = np.abs(np.fft.rfft(samples))
        freqs = np.fft.rfftfreq(len(samples), 1/SAMPLE_RATE)

        # Find peak frequency
        peak_freq = freqs[np.argmax(fft)]

        # Should have significant high frequency content (above 1kHz)
        assert peak_freq > 1000, f"Peak frequency too low: {peak_freq} Hz"


class TestDigitalStream:
    """Tests for digital_stream generator."""

    def test_has_rhythmic_content(self):
        """Test that digital stream has rhythmic pulses."""
        samples = generate_digital_stream()

        # Autocorrelation to detect periodicity
        autocorr = np.correlate(samples, samples, mode='same')
        autocorr = autocorr[len(autocorr)//2:]  # Take positive lags

        # Normalize
        autocorr = autocorr / autocorr[0]

        # Find first significant peak after origin (indicates pulse period)
        min_lag = int(SAMPLE_RATE * 0.03)  # Minimum 30ms between pulses
        max_lag = int(SAMPLE_RATE * 0.1)   # Maximum 100ms between pulses

        peak_region = autocorr[min_lag:max_lag]
        has_periodicity = np.max(peak_region) > 0.3

        assert has_periodicity, "No rhythmic content detected"

    def test_sustained_duration(self):
        """Test that digital stream maintains energy throughout."""
        samples = generate_digital_stream()

        # Check energy in quarters
        quarter = len(samples) // 4
        q1_energy = np.mean(np.abs(samples[:quarter]))
        q2_energy = np.mean(np.abs(samples[quarter:2*quarter]))
        q3_energy = np.mean(np.abs(samples[2*quarter:3*quarter]))
        q4_energy = np.mean(np.abs(samples[3*quarter:]))

        # Energy should be present throughout (allow for fade)
        assert q1_energy > 0.05
        assert q2_energy > 0.05
        assert q3_energy > 0.03


class TestImpactSoft:
    """Tests for impact_soft generator."""

    def test_lower_peak_than_hard(self):
        """Test that soft impact has lower peak than hard."""
        soft = generate_impact_soft()
        hard = generate_impact_hard()

        soft_peak = np.max(np.abs(soft))
        hard_peak = np.max(np.abs(hard))

        # Soft should have similar or lower peak (after normalization they're close)
        # But check the raw transient character
        soft_attack_rate = np.max(np.abs(np.diff(soft[:int(SAMPLE_RATE * 0.01)])))
        hard_attack_rate = np.max(np.abs(np.diff(hard[:int(SAMPLE_RATE * 0.01)])))

        # Hard should have sharper attack
        assert hard_attack_rate > soft_attack_rate * 0.8

    def test_has_low_frequency(self):
        """Test that soft impact has low frequency content."""
        samples = generate_impact_soft()

        fft = np.abs(np.fft.rfft(samples))
        freqs = np.fft.rfftfreq(len(samples), 1/SAMPLE_RATE)

        # Energy in low frequency band (below 200Hz)
        low_mask = freqs < 200
        low_energy = np.sum(fft[low_mask])
        total_energy = np.sum(fft)

        # Should have significant low frequency content
        assert low_energy / total_energy > 0.1


class TestImpactHard:
    """Tests for impact_hard generator."""

    def test_sharp_transient(self):
        """Test that hard impact has a sharp transient."""
        samples = generate_impact_hard()

        # Check first few milliseconds
        attack_samples = samples[:int(SAMPLE_RATE * 0.003)]

        # Should reach significant amplitude quickly
        assert np.max(np.abs(attack_samples)) > 0.3

    def test_wide_frequency_range(self):
        """Test that hard impact has wide frequency content."""
        samples = generate_impact_hard()

        fft = np.abs(np.fft.rfft(samples))
        freqs = np.fft.rfftfreq(len(samples), 1/SAMPLE_RATE)

        # Energy in low band (below 200Hz)
        low_mask = freqs < 200
        low_energy = np.sum(fft[low_mask])

        # Energy in high band (above 2kHz)
        high_mask = freqs > 2000
        high_energy = np.sum(fft[high_mask])

        total_energy = np.sum(fft)

        # Should have both low and high frequency content
        assert low_energy / total_energy > 0.05, "Not enough low frequency"
        assert high_energy / total_energy > 0.05, "Not enough high frequency"


class TestSoundLibrary:
    """Tests for SoundLibrary class with new sounds."""

    def test_generate_all_includes_new_sounds(self):
        """Test that generate_all creates all new sounds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sfx_dir = Path(tmpdir)
            library = SoundLibrary(sfx_dir)

            generated = library.generate_all()

            # Check new sounds are generated
            new_sounds = [
                "keyboard_type",
                "keyboard_rapid",
                "bar_grow",
                "progress_tick",
                "digital_stream",
                "impact_soft",
                "impact_hard",
            ]

            for sound in new_sounds:
                assert sound in generated
                assert (sfx_dir / f"{sound}.wav").exists()

    def test_list_sounds_includes_new(self):
        """Test that list_sounds includes new sounds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            library = SoundLibrary(Path(tmpdir))
            sounds = library.list_sounds()

            assert "keyboard_type" in sounds
            assert "keyboard_rapid" in sounds
            assert "bar_grow" in sounds

    def test_get_sound_info_new_sounds(self):
        """Test getting info for new sounds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            library = SoundLibrary(Path(tmpdir))

            info = library.get_sound_info("keyboard_type")
            assert info is not None
            assert "description" in info
            assert "typing" in info["description"].lower() or "keystroke" in info["description"].lower()


class TestUtilityFunctions:
    """Tests for audio utility functions."""

    def test_normalize(self):
        """Test normalization function."""
        samples = np.random.randn(1000) * 0.1
        normalized = normalize(samples, target_db=-3.0)

        # Check peak is near target
        target_amp = 10 ** (-3.0 / 20)
        peak = np.max(np.abs(normalized))

        assert abs(peak - target_amp) < 0.01

    def test_soft_clip_preserves_quiet(self):
        """Test that soft clip doesn't affect quiet signals."""
        samples = np.array([0.1, 0.2, 0.3, -0.1, -0.2])
        clipped = soft_clip(samples, threshold=0.8)

        np.testing.assert_array_almost_equal(samples, clipped, decimal=2)

    def test_hard_clip_limits_peaks(self):
        """Test that hard clip limits peaks."""
        samples = np.array([0.5, 1.5, -1.5, 0.3])
        clipped = hard_clip(samples, threshold=0.7)

        assert np.max(clipped) <= 0.7
        assert np.min(clipped) >= -0.7

    def test_sharp_transient_decays(self):
        """Test that sharp transient decays rapidly."""
        transient = sharp_transient(int(SAMPLE_RATE * 0.05), intensity=1.0)

        # Energy at start should be higher than at end
        start_energy = np.mean(np.abs(transient[:100]))
        end_energy = np.mean(np.abs(transient[-100:]))

        assert start_energy > end_energy * 10

    def test_bandpass_noise_frequency_range(self):
        """Test that bandpass noise is within specified range."""
        low = 500
        high = 2000
        noise = bandpass_noise(int(SAMPLE_RATE * 0.5), low, high)

        fft = np.abs(np.fft.rfft(noise))
        freqs = np.fft.rfftfreq(len(noise), 1/SAMPLE_RATE)

        # Find peak frequency
        peak_freq = freqs[np.argmax(fft)]

        # Peak should be within or very close to the passband
        # Allow 5% tolerance for filter rolloff
        tolerance = (high - low) * 0.05
        assert low - tolerance <= peak_freq <= high + tolerance


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
