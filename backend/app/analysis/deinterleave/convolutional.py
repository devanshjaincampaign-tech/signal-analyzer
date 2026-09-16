"""
convolutional.py – Convolutional de-interleaver (Ramsey Type-III / CCSDS).

Implements the shift-register bank that is the inverse of a convolutional
interleaver with N branches and delay increment M.
"""
import numpy as np
from collections import deque


class ConvolutionalDeinterleaver:
    """Inverse of a convolutional (Forney) interleaver.

    Args:
        n_branches: Number of parallel branches (rows).
        delay_inc:  Delay increment between branches (in symbols).
    """

    def __init__(self, n_branches: int = 8, delay_inc: int = 17):
        self.n = n_branches
        self.m = delay_inc
        # Branch k has delay (n_branches - 1 - k) * delay_inc
        self._buffers: list[deque] = [
            deque([0] * ((n_branches - 1 - k) * delay_inc), maxlen=(n_branches - 1 - k) * delay_inc or 1)
            for k in range(n_branches)
        ]

    def process(self, symbols: np.ndarray) -> np.ndarray:
        """De-interleave a flat symbol array.

        The input must be a multiple of n_branches in length.
        """
        if len(symbols) % self.n != 0:
            raise ValueError("Input length must be a multiple of n_branches.")
        out = []
        for i, sym in enumerate(symbols):
            buf = self._buffers[i % self.n]
            buf.append(sym)
            out.append(buf[0] if len(buf) == buf.maxlen else 0)
        return np.array(out, dtype=symbols.dtype)
