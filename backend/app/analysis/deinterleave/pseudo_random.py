"""
pseudo_random.py – Pseudo-random (PN-sequence) de-interleaver.

Many military and satellite standards use a PN-sequence (LFSR-based) to
scramble bit positions before transmission. This module:
  1. Generates an LFSR PN sequence of the required length.
  2. Applies the inverse permutation to recover the original bit order.

Supported LFSR polynomials (tap sets):
  - CCSDS   : degree 8,  taps (7,3,2,1)  → period 255
  - GSM A5/1: degree 19, taps (18,17,16,13)
  - Custom  : user-supplied tap positions and degree
"""
from __future__ import annotations

import numpy as np


# ── LFSR generator ────────────────────────────────────────────────────────────

def generate_pn_sequence(
    length: int,
    degree: int = 8,
    taps: tuple[int, ...] = (7, 3, 2, 1),
    seed: int = 0xFF,
) -> np.ndarray:
    """Generate a binary PN (LFSR) sequence.

    Args:
        length: Number of bits to generate.
        degree: LFSR register length in bits.
        taps:   Feedback tap positions (0-indexed from MSB).
        seed:   Initial register state (must be non-zero).

    Returns:
        Binary numpy array of length ``length`` (dtype uint8).
    """
    if seed == 0:
        raise ValueError("LFSR seed must be non-zero.")
    reg = seed & ((1 << degree) - 1)
    out = np.empty(length, dtype=np.uint8)
    mask = (1 << degree) - 1

    for i in range(length):
        out[i] = (reg >> (degree - 1)) & 1   # output MSB
        feedback = 0
        for t in taps:
            feedback ^= (reg >> (degree - 1 - t)) & 1
        reg = ((reg << 1) | feedback) & mask

    return out


# ── permutation helpers ───────────────────────────────────────────────────────

def _pn_permutation(length: int, degree: int, taps: tuple[int, ...], seed: int) -> np.ndarray:
    """Return the index permutation produced by the PN sequence."""
    pn = generate_pn_sequence(length, degree=degree, taps=taps, seed=seed)
    # Build a shuffle permutation: sort by cumulative XOR value
    # (deterministic mapping from PN bits to index order)
    cumulative = np.cumsum(pn) % length
    # Ensure unique indices via argsort of the cumulative PN values
    return np.argsort(cumulative, kind="stable")


# ── public API ────────────────────────────────────────────────────────────────

def pn_deinterleave(
    bits: np.ndarray,
    degree: int = 8,
    taps: tuple[int, ...] = (7, 3, 2, 1),
    seed: int = 0xFF,
) -> np.ndarray:
    """De-interleave bits that were shuffled by a PN-sequence interleaver.

    The inverse of ``pn_interleave``: applies the reverse permutation so that
    output[perm[i]] = input[i].

    Args:
        bits:   Interleaved bit array (uint8, 0/1).
        degree: LFSR degree used during interleaving.
        taps:   LFSR tap positions used during interleaving.
        seed:   LFSR seed used during interleaving.

    Returns:
        De-interleaved bit array of the same length.
    """
    bits = np.asarray(bits, dtype=np.uint8)
    n = len(bits)
    perm = _pn_permutation(n, degree, taps, seed)
    inverse_perm = np.empty_like(perm)
    inverse_perm[perm] = np.arange(n)
    return bits[inverse_perm]


def pn_interleave(
    bits: np.ndarray,
    degree: int = 8,
    taps: tuple[int, ...] = (7, 3, 2, 1),
    seed: int = 0xFF,
) -> np.ndarray:
    """Interleave bits using a PN-sequence permutation (for testing / synth)."""
    bits = np.asarray(bits, dtype=np.uint8)
    perm = _pn_permutation(len(bits), degree, taps, seed)
    return bits[perm]


# ── LFSR preset library ───────────────────────────────────────────────────────

PRESETS: dict[str, dict] = {
    "ccsds": {"degree": 8,  "taps": (7, 3, 2, 1), "seed": 0xFF},
    "gsm":   {"degree": 19, "taps": (18, 17, 16, 13), "seed": 0x7FFFF},
    "dvb":   {"degree": 15, "taps": (14, 13), "seed": 0x4A80},
}
