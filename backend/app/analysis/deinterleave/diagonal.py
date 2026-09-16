"""
diagonal.py – Diagonal (helical) de-interleaver.

Used in some satellite standards (e.g., DVB-S) where the interleaver writes
bits diagonally across a matrix then reads column-by-column.
"""
import numpy as np


def diagonal_deinterleave(bits: np.ndarray, rows: int, cols: int) -> np.ndarray:
    """Reverse a diagonal (helical scan) interleaver.

    Args:
        bits: Flat bit array of length rows * cols.
        rows: Matrix row count used during interleaving.
        cols: Matrix column count.

    Returns:
        De-interleaved bit array.
    """
    if len(bits) != rows * cols:
        raise ValueError(
            f"bit array length {len(bits)} != rows({rows}) * cols({cols})"
        )
    matrix = np.zeros((rows, cols), dtype=bits.dtype)
    for idx, b in enumerate(bits):
        r = idx % rows
        c = (idx // rows + r) % cols
        matrix[r, c] = b
    # Read column-by-column
    return matrix.T.flatten()
