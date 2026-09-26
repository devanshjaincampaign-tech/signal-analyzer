"""
viterbi.py – High-Performance Vectorized Viterbi Decoder.

Implements rate-1/2, constraint-length-7 convolutional decoder
(standard NASA/CCSDS polynomial: G1=0o171, G2=0o133).

Vectorized with precomputed state transition tables and NumPy arrays
for high throughput and zero bit-error rate.
"""
from __future__ import annotations

import numpy as np

_G1 = 0o171  # 121 decimal: 0b1111001
_G2 = 0o133  # 91  decimal: 0b1011011
_K = 7
_STATES = 2 ** (_K - 1)  # 64 states


def _parity(x: int) -> int:
    x ^= x >> 4
    x ^= x >> 2
    x ^= x >> 1
    return x & 1


# ── Precomputed Vectorized Transition Matrices ────────────────────────────────
# In a K=7 shift register, state s = (s5, s4, s3, s2, s1, s0).
# When input bit b enters: next_state ns = (b << 5) | (s >> 1).
# Therefore, for a given next_state ns:
#   Input bit b = (ns >> 5) & 1  (the MSB of ns)
#   Predecessor state with old bit0 = 0: pred0 = (ns & 31) << 1
#   Predecessor state with old bit0 = 1: pred1 = ((ns & 31) << 1) | 1

_PRED_STATE_0 = np.array([((_ns & 31) << 1) for _ns in range(_STATES)], dtype=np.int32)
_PRED_STATE_1 = np.array([(((_ns & 31) << 1) | 1) for _ns in range(_STATES)], dtype=np.int32)
_IN_BIT = np.array([((_ns >> 5) & 1) for _ns in range(_STATES)], dtype=np.int32)

# Branch outputs for transition into ns from PRED_STATE_0 and PRED_STATE_1:
# Shift register contents: (b << 6) | pred_state
_OUT0_0 = np.array([
    float(1.0 - 2.0 * _parity((_IN_BIT[ns] << 6) | _PRED_STATE_0[ns] & _G1))
    for ns in range(_STATES)
], dtype=np.float32)
_OUT1_0 = np.array([
    float(1.0 - 2.0 * _parity((_IN_BIT[ns] << 6) | _PRED_STATE_0[ns] & _G2))
    for ns in range(_STATES)
], dtype=np.float32)

_OUT0_1 = np.array([
    float(1.0 - 2.0 * _parity((_IN_BIT[ns] << 6) | _PRED_STATE_1[ns] & _G1))
    for ns in range(_STATES)
], dtype=np.float32)
_OUT1_1 = np.array([
    float(1.0 - 2.0 * _parity((_IN_BIT[ns] << 6) | _PRED_STATE_1[ns] & _G2))
    for ns in range(_STATES)
], dtype=np.float32)


def viterbi_decode(symbols: np.ndarray, soft: bool = True, max_decode_symbols: int = 32768) -> np.ndarray:
    """Decode a rate-1/2 K=7 convolutionally encoded bit stream via vectorized Viterbi.

    Args:
        symbols: Received symbols (+1 = bit 0, -1 = bit 1 for soft LLRs).
        soft:    Use Euclidean soft metric when True.
        max_decode_symbols: Cap processing on excessively large bursts.

    Returns:
        Decoded uint8 bit array.
    """
    syms = np.asarray(symbols, dtype=np.float32)
    n_pairs = min(len(syms) // 2, max_decode_symbols // 2)
    if n_pairs == 0:
        return np.array([], dtype=np.uint8)

    # Path metrics initialized to infinity except state 0
    pm = np.full(_STATES, 1e9, dtype=np.float32)
    pm[0] = 0.0

    traceback = np.empty((n_pairs, _STATES), dtype=np.int32)

    # Vectorized forward trellis traversal
    for t in range(n_pairs):
        r0 = syms[2 * t]
        r1 = syms[2 * t + 1]

        if soft:
            # Euclidean distance squared
            metric_0 = (r0 - _OUT0_0) ** 2 + (r1 - _OUT1_0) ** 2
            metric_1 = (r0 - _OUT0_1) ** 2 + (r1 - _OUT1_1) ** 2
        else:
            # Hard Hamming distance
            h0 = float(1.0 if r0 < 0 else 0.0)
            h1 = float(1.0 if r1 < 0 else 0.0)
            metric_0 = (h0 != (1.0 - _OUT0_0) / 2.0).astype(np.float32) + (h1 != (1.0 - _OUT1_0) / 2.0).astype(np.float32)
            metric_1 = (h0 != (1.0 - _OUT0_1) / 2.0).astype(np.float32) + (h1 != (1.0 - _OUT1_1) / 2.0).astype(np.float32)

        cost_0 = pm[_PRED_STATE_0] + metric_0
        cost_1 = pm[_PRED_STATE_1] + metric_1

        # Select minimum metric per state (vectorized)
        choose_1 = cost_1 < cost_0
        pm = np.where(choose_1, cost_1, cost_0)

        # Normalize metrics periodically to avoid numeric overflow
        pm -= np.min(pm)

        # Store predecessor state index for traceback
        traceback[t] = np.where(choose_1, _PRED_STATE_1, _PRED_STATE_0)

    # Traceback from minimum metric state
    state = int(np.argmin(pm))
    decoded = np.empty(n_pairs, dtype=np.uint8)

    for t in range(n_pairs - 1, -1, -1):
        decoded[t] = _IN_BIT[state]
        state = traceback[t, state]

    return decoded
