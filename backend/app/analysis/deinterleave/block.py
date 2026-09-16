"""
block.py – Block de-interleaver.

Reverses a block interleaver of given depth and width:
    interleaved[row * width + col] -> original[col * depth + row]
"""
import numpy as np


def block_deinterleave(bits: np.ndarray, depth: int, width: int) -> np.ndarray:
    """De-interleave a 1-D bit array using a (depth x width) block matrix.

    Args:
        bits:  Flat bit array of length depth * width.
        depth: Number of rows written during interleaving.
        width: Number of columns (= interleave span).

    Returns:
        De-interleaved bit array of the same length.
    """
    if len(bits) != depth * width:
        raise ValueError(
            f"bit array length {len(bits)} != depth({depth}) * width({width})"
        )
    matrix = bits.reshape(depth, width)
    return matrix.T.flatten()
