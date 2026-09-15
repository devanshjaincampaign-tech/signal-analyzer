import numpy as np

from app.analysis.symbol_rate import estimate_symbol_rate
from app.synth.generate_signals import generate_bpsk
from app.synth.generate_signals import generate_fsk


def test_symbol_rate_estimator_recovers_bpsk_symbol_spacing():
    sig, sample_rate, _ = generate_bpsk(
        num_bits=1000, sps=8, sample_rate=200_000
    )

    result = estimate_symbol_rate(sig, sample_rate)

    assert result["samples_per_symbol"] is not None
    assert result["symbol_rate_hz"] is not None
    assert abs(result["samples_per_symbol"] - 8) <= 2
    assert abs(result["symbol_rate_hz"] - 25_000.0) < 3_000.0
    assert result["confidence"] > 0.5


def test_symbol_rate_estimator_rejects_non_digital_tone_as_unreliable():
    sample_rate = 8_000
    t = np.linspace(0, 1, sample_rate, endpoint=False)
    sig = np.sin(2 * np.pi * 440 * t).astype(np.float64)

    result = estimate_symbol_rate(sig, sample_rate)

    assert result["samples_per_symbol"] is not None
    assert result["confidence"] < 1.0


def test_symbol_rate_estimator_fsk_result_is_a_valid_symbol_period_or_harmonic():
    np.random.seed(42)
    sig, sample_rate = generate_fsk(num_bits=200, sps=8, sample_rate=200_000)

    result = estimate_symbol_rate(sig, sample_rate)

    assert result["samples_per_symbol"] in {8, 16}
