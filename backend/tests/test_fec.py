"""
test_fec.py – Unit tests for FEC codecs (Viterbi, RS, LDPC, concatenated).
"""
import numpy as np
import pytest

from app.analysis.fec.viterbi import viterbi_decode
from app.analysis.fec.concatenated import concatenated_decode


# ── Viterbi ──────────────────────────────────────────────────────────────────

def test_viterbi_all_zeros():
    """All-zeros codeword should decode to all-zeros."""
    # For K=7 R=1/2, encode 16 bits → 32 + 12 flush symbols = 44 symbols
    # Use hard-decision symbols (perfect reception)
    # All-zeros: every encoded bit is 0 → LLR = +1 (BPSK mapping 0→+1)
    n_info = 16
    # Approximate: send 2*(n_info + K-1) = 2*22 = 44 ones (soft +1.0 = bit 0)
    soft_symbols = np.ones(44, dtype=np.float32)
    bits = viterbi_decode(soft_symbols, soft=True)
    assert len(bits) == 22
    assert np.all(bits == 0)


def test_viterbi_output_dtype():
    symbols = np.ones(20, dtype=np.float32)
    bits = viterbi_decode(symbols, soft=True)
    assert bits.dtype == np.uint8


def test_viterbi_hard_decision():
    symbols = np.array([1, 1, 1, 1, 0, 0, 1, 0], dtype=np.uint8)
    bits = viterbi_decode(symbols, soft=False)
    assert bits.dtype == np.uint8


# ── Concatenated ─────────────────────────────────────────────────────────────

def test_concatenated_decode_returns_tuple():
    """concatenated_decode must return (bytes, info_dict)."""
    symbols = np.ones(520, dtype=np.float32)  # enough for RS block
    try:
        result, info = concatenated_decode(symbols)
        assert isinstance(result, np.ndarray)
        assert "viterbi_bits" in info
        assert "rs_errors_corrected" in info
    except ImportError:
        pytest.skip("reedsolo not installed")


# ── FEC sub-modules importable ────────────────────────────────────────────────

def test_imports():
    from app.analysis.fec import viterbi_decode, rs_decode, ldpc_decode, concatenated_decode  # noqa: F401
