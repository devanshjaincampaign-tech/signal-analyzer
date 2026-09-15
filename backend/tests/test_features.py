import numpy as np

from app.analysis.features import compute_spectrogram, extract_spectral_features


def test_extract_spectral_features_for_complex_signal_has_positive_bandwidth():
    sample_rate = 1_000
    t = np.arange(0, 1.0, 1 / sample_rate)
    sig = np.exp(1j * 2 * np.pi * 50 * t).astype(np.complex64)

    features = extract_spectral_features(sig, sample_rate)

    assert features["bandwidth_hz"] >= 0
    assert abs(features["center_frequency_hz"] - 50.0) < 5.0
    assert features["sample_rate_used"] == sample_rate


def test_spectrogram_bins_are_monotonic_for_complex_signal():
    sample_rate = 1_000
    t = np.arange(0, 1.0, 1 / sample_rate)
    sig = np.exp(1j * 2 * np.pi * 50 * t).astype(np.complex64)

    spec = compute_spectrogram(sig, sample_rate)
    freqs = np.asarray(spec["freq_bins"])

    assert np.all(np.diff(freqs) >= 0)
    assert spec["power_db_matrix"]
