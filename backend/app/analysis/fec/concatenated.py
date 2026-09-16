"""
concatenated.py – Concatenated FEC pipeline (RS-after-Viterbi).

Implements the classic inner Viterbi + outer Reed-Solomon scheme
used in CCSDS and many legacy satellite links.
"""
from __future__ import annotations

import numpy as np

from .viterbi import viterbi_decode
from .reed_solomon import rs_decode


def concatenated_decode(
    symbols: np.ndarray,
    rs_nsym: int = 32,
    viterbi_soft: bool = True,
) -> tuple[np.ndarray, dict]:
    """Run the full concatenated FEC decoding pipeline.

    Pipeline::

        received symbols
            └─► Viterbi decoder  (inner, convolutional K=7 R=1/2)
                    └─► RS decoder    (outer, (255,223) CCSDS)
                            └─► decoded bytes

    Args:
        symbols:      Received (possibly soft) symbols from the demodulator.
        rs_nsym:      Number of RS parity symbols.
        viterbi_soft: Use soft-decision Viterbi when True.

    Returns:
        (decoded_bytes, info_dict)
        info_dict contains 'viterbi_bits', 'rs_errors_corrected'.
    """
    viterbi_bits = viterbi_decode(symbols, soft=viterbi_soft)

    # Pack bits → bytes for RS decoder
    n_bytes = len(viterbi_bits) // 8
    byte_array = np.packbits(viterbi_bits[: n_bytes * 8])

    decoded_bytes, n_errors = rs_decode(byte_array, nsym=rs_nsym)

    info = {
        "viterbi_bits": viterbi_bits,
        "rs_errors_corrected": n_errors,
    }
    return decoded_bytes, info
