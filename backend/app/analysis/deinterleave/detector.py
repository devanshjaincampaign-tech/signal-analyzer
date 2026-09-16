"""
detector.py – Fast Parameter Detector for De-interleaving.

Optimized with two-tier parameter evaluation:
  1. Fast evaluation tier on representative signal chunk (<= 4096 bits)
  2. Full-stream execution on the single winning parameter configuration
"""
from __future__ import annotations

import numpy as np

from .block import block_deinterleave
from .convolutional import ConvolutionalDeinterleaver
from .diagonal import diagonal_deinterleave
from .pseudo_random import pn_deinterleave, PRESETS


SUPPORTED_TYPES = ("block", "convolutional", "diagonal", "pseudo_random")


def _validity_score(bits: np.ndarray) -> float:
    """Higher score = more likely to be a structured de-interleaved bit stream.

    Uses run-length statistics: natural de-interleaved streams display longer
    runs of identical bits compared to pseudo-random scrambled bit streams.
    """
    if len(bits) == 0:
        return 0.0
    changes = np.diff(bits) != 0
    change_indices = np.where(changes)[0]
    if len(change_indices) == 0:
        return float(len(bits))
    runs = np.diff(np.concatenate(([-1], change_indices, [len(bits) - 1])))
    return float(np.mean(runs))


def _apply_deinterleaver(kind: str, bits: np.ndarray, depth: int, width: int) -> np.ndarray:
    """Apply a specified de-interleaver to a bit array."""
    trimmed = bits[: depth * width] if depth * width <= len(bits) else bits
    if kind == "block":
        return block_deinterleave(trimmed, depth, width)
    elif kind == "convolutional":
        di = ConvolutionalDeinterleaver(n_branches=depth, delay_inc=max(1, width // depth))
        return di.process(trimmed)
    elif kind == "diagonal":
        return diagonal_deinterleave(trimmed, depth, width)
    elif kind.startswith("pseudo_random:"):
        preset = kind.split(":", 1)[1]
        kwargs = PRESETS.get(preset, {"degree": 8, "taps": (7, 3, 2, 1), "seed": 0xFF})
        return pn_deinterleave(trimmed, **kwargs)
    return bits


def detect_and_deinterleave(
    bits: np.ndarray,
    depth_range: range = range(2, 33),
    sync_word: np.ndarray | None = None,
    max_search_bits: int = 4096,
) -> dict:
    """Fast search for best de-interleaving scheme, followed by full-stream transformation.

    Args:
        bits:            Input (interleaved) bit array.
        depth_range:     Depths / branch counts to test.
        sync_word:       Optional known sync pattern for correlation scoring.
        max_search_bits: Maximum bits to use during parameter search.

    Returns:
        dict with keys: 'type', 'depth', 'width', 'bits', 'score'
    """
    bits = np.asarray(bits, dtype=np.uint8)
    n_total = len(bits)
    if n_total < 8:
        return {"score": 0.0, "type": None, "depth": None, "width": None, "bits": bits}

    # Use fast search chunk to evaluate configurations
    search_bits = bits[:min(n_total, max_search_bits)]
    best: dict = {"score": -1.0, "type": None, "depth": None, "width": None}

    for depth in depth_range:
        search_width = len(search_bits) // depth
        if search_width < 1:
            continue
        trimmed_search = search_bits[: depth * search_width]

        candidates: list[tuple[str, np.ndarray]] = []

        # 1. Block
        try:
            candidates.append(("block", block_deinterleave(trimmed_search, depth, search_width)))
        except ValueError:
            pass

        # 2. Convolutional
        try:
            di = ConvolutionalDeinterleaver(n_branches=depth, delay_inc=max(1, search_width // depth))
            candidates.append(("convolutional", di.process(trimmed_search)))
        except Exception:
            pass

        # 3. Diagonal
        try:
            candidates.append(("diagonal", diagonal_deinterleave(trimmed_search, depth, search_width)))
        except ValueError:
            pass

        # 4. Pseudo-random LFSR presets
        for preset_name, preset_kwargs in PRESETS.items():
            try:
                cand = pn_deinterleave(trimmed_search, **preset_kwargs)
                candidates.append((f"pseudo_random:{preset_name}", cand))
            except Exception:
                pass

        for kind, res in candidates:
            if sync_word is not None:
                corr = np.correlate(res.astype(np.float32), sync_word.astype(np.float32), mode="valid")
                score = float(np.max(corr)) if len(corr) > 0 else 0.0
            else:
                score = _validity_score(res)

            if score > best["score"]:
                best = {"score": score, "type": kind, "depth": depth, "width": search_width}

    # Apply winning configuration to the full bitstream
    if best["type"] is not None and best["depth"] is not None:
        full_width = n_total // best["depth"]
        if full_width >= 1:
            try:
                full_result = _apply_deinterleaver(best["type"], bits, best["depth"], full_width)
                best["width"] = full_width
                best["bits"] = full_result
                return best
            except Exception:
                pass

    best["bits"] = bits
    return best
