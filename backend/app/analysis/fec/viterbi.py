"""
viterbi.py – High-Performance Vectorized Viterbi Decoder.

Implements rate-1/2, constraint-length-7 convolutional decoder
(standard NASA/CCSDS polynomial: G1=0o171, G2=0o133).

Vectorized with precomputed state transition tables and NumPy arrays
for high throughput on large bitstreams.
"""
from __future__ import annotations

import numpy as np

_G1 = 0o171  # 121 decimal
_G2 = 0o133  # 91  decimal
_K = 7
_STATES = 2 ** (_K - 1)  # 64 states


def _parity(x: int) -> int:
    x ^= x >> 4
    x ^= x >> 2
    x ^= x >> 1
    return x & 1


# ── Precomputed Vectorized Transition Matrices ────────────────────────────────
# For each state s (0..63) and input bit b (0..1):
#   next_state = (s >> 1) | (b << 5)
#   out0 = parity(reg & G1), out1 = parity(reg & G2) where reg = (b << 6) | (s >> 1)
_PREV_STATE = np.zeros((_STATES, 2), dtype=np.int32)
_PREV_BIT = np.zeros((_STATES, 2), dtype=np.int32)
_BRANCH_OUT0 = np.zeros((_STATES, 2), dtype=np.float32)
_BRANCH_OUT1 = np.zeros((_STATES, 2), dtype=np.float32)

for _s in range(_STATES):
    for _b in range(2):
        _reg = (_b << (_K - 1)) | (_s >> 1)
        _o0 = _parity(_reg & _G1)
        _o1 = _parity(_reg & _G2)
        _ns = (_s >> 1) | (_b << (_K - 2))
        
        # Backward pointer: from next_state, who was the predecessor state and input bit?
        # A state ns has two predecessor candidates: s0 = (ns << 1) & 63 and s1 = ((ns << 1) | 1) & 63
        _PREV_STATE[_ns, _b] = _s
        _PREV_BIT[_ns, _b] = _b
        _BRANCH_OUT0[_ns, _b] = float(1.0 - 2.0 * _o0)  # +1 for bit 0, -1 for bit 1
        _BRANCH_OUT1[_ns, _b] = float(1.0 - 2.0 * _o1)

# Direct predecessor indices for every next_state ns:
_PRED_STATE_0 = np.array([(_ns << 1) & 63 for _ns in range(_STATES)], dtype=np.int32)
_PRED_STATE_1 = np.array([((_ns << 1) | 1) & 63 for _ns in range(_STATES)], dtype=np.int32)

_OUT0_0 = np.array([_BRANCH_OUT0[ns, 0] for ns in range(_STATES)], dtype=np.float32)
_OUT1_0 = np.array([_BRANCH_OUT1[ns, 0] for ns in range(_STATES)], dtype=np.float32)
_OUT0_1 = np.array([_BRANCH_OUT0[ns, 1] for ns in range(_STATES)], dtype=np.float32)
_OUT1_1 = np.array([_BRANCH_OUT1[ns, 1] for ns in range(_STATES)], dtype=np.float32)


def viterbi_decode(symbols: np.ndarray, soft: bool = True, max_decode_symbols: int = 16384) -> np.ndarray:
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
            # Branch metrics (Euclidean distance squared)
            metric_0 = (r0 - _OUT0_0) ** 2 + (r1 - _OUT1_0) ** 2
            metric_1 = (r0 - _OUT0_1) ** 2 + (r1 - _OUT1_1) ** 2
        else:
            # Hard Hamming distance
            h0 = int(r0 < 0)
            h1 = int(r1 < 0)
            metric_0 = (h0 != (1 - _OUT0_0) / 2).astype(np.float32) + (h1 != (1 - _OUT1_0) / 2).astype(np.float32)
            metric_1 = (h0 != (1 - _OUT0_1) / 2).astype(np.float32) + (h1 != (1 - _OUT1_1) / 2).astype(np.float32)

        cost_0 = pm[_PRED_STATE_0] + metric_0
        cost_1 = pm[_PRED_STATE_1] + metric_1

        # Select minimum metric per state (vectorized)
        choose_1 = cost_1 < cost_0
        pm = np.where(choose_1, cost_1, cost_0)

        # Normalize metrics periodically to avoid numeric drift
        pm -= np.min(pm)

        # Store predecessor state index for traceback
        traceback[t] = np.where(choose_1, _PRED_STATE_1, _PRED_STATE_0)

    # Traceback from minimum metric state
    state = int(np.argmin(pm))
    decoded = np.empty(n_pairs, dtype=np.uint8)

    for t in range(n_pairs - 1, -1, -1):
        prev_state = traceback[t, state]
        # Bit is MSB of the state in our convention
        decoded[t] = (state >> (_K - 2)) & 1
        state = prev_state

    return decoded
