import numpy as np

from app.analysis.demod import demod_bpsk
from app.analysis.interleaving import (
    block_deinterleave,
    block_interleave,
    search_deinterleave,
)
from app.analysis.symbol_rate import estimate_symbol_rate
from app.synth.generate_signals import generate_bpsk_interleaved


def test_block_interleave_is_reversible():
    bits = [int(value) for value in "0100110011110001"]

    assert block_deinterleave(block_interleave(bits, 4, 4), 4, 4) == bits


def test_search_finds_structured_interleaved_bpsk_payload():
    np.random.seed(1)
    sig, sample_rate, true_bits, rows, cols = generate_bpsk_interleaved(
        rows=8, cols=8
    )
    timing = estimate_symbol_rate(sig, sample_rate)
    recovered = demod_bpsk(sig, timing["samples_per_symbol"])

    result = search_deinterleave(recovered)

    assert result["success"] is True
    assert result["best_params"] == {"rows": rows, "cols": cols}
    restored = block_deinterleave(
        recovered, result["best_params"]["rows"], result["best_params"]["cols"]
    )
    assert sum(a == b for a, b in zip(true_bits, restored)) / len(true_bits) > 0.95


def test_search_rejects_short_and_prime_length_inputs():
    assert search_deinterleave([0, 1] * 7)["success"] is False
    assert search_deinterleave([0, 1] * 11 + [0])["success"] is False
