import numpy as np

from app.analysis.demod import demod_16qam, demod_bpsk, demod_fsk, demodulate
from app.synth.generate_signals import generate_16qam, generate_bpsk, generate_fsk


def test_bpsk_demodulation_recovers_ground_truth_bits():
    np.random.seed(42)
    sig, _, true_bits = generate_bpsk(num_bits=200, sps=8, sample_rate=200_000)

    recovered = demod_bpsk(sig, 8)

    direct = sum(a == b for a, b in zip(true_bits, recovered))
    inverted = sum(a == 1 - b for a, b in zip(true_bits, recovered))
    assert max(direct, inverted) / len(true_bits) > 0.95


def test_fsk_demodulation_recovers_generated_bits():
    np.random.seed(42)
    sig, _ = generate_fsk(num_bits=200, sps=8, sample_rate=200_000)

    recovered = demod_fsk(sig, 8)

    assert len(recovered) == 200
    assert set(recovered) <= {0, 1}


def test_qam_demodulation_returns_normalized_constellation_levels():
    np.random.seed(42)
    sig, _ = generate_16qam(num_symbols=200, sps=8, sample_rate=200_000)

    result = demod_16qam(sig, 8)
    allowed = {-1.0, -1 / 3, 1 / 3, 1.0}

    assert set(result["i_levels"]) <= allowed
    assert set(result["q_levels"]) <= allowed
    assert len(result["i_levels"]) == 200
    assert len(result["q_levels"]) == 200


def test_demodulate_reports_missing_timing_without_throwing():
    result = demodulate(np.ones(8, dtype=np.complex64), None, "PSK")

    assert result == {"success": False, "reason": "No valid symbol timing available"}
