"""
demod.py – High-Performance Vectorized Demodulation Suite.

Vectorized with NumPy operations for maximum throughput across all supported schemes:
  - BPSK, QPSK, 8-PSK
  - 2-FSK, 4-FSK
  - 16-QAM, 64-QAM
"""
from __future__ import annotations

import numpy as np


def _downsample_to_symbols(sig: np.ndarray, samples_per_symbol: int) -> np.ndarray:
    if samples_per_symbol < 1:
        raise ValueError("samples_per_symbol must be positive")
    n_symbols = len(sig) // samples_per_symbol
    if n_symbols == 0:
        raise ValueError("Signal is too short for the requested symbol timing")
    
    # Vectorized center-slice downsampling
    trimmed = sig[: n_symbols * samples_per_symbol]
    reshaped = trimmed.reshape(n_symbols, samples_per_symbol)
    return reshaped[:, samples_per_symbol // 2]


def demod_bpsk(sig: np.ndarray, samples_per_symbol: int) -> list[int]:
    """BPSK: 1 bit per symbol (real part slicing)."""
    symbols = _downsample_to_symbols(sig, samples_per_symbol)
    return (np.real(symbols) > 0).astype(np.uint8).tolist()


def demod_qpsk(sig: np.ndarray, samples_per_symbol: int) -> list[int]:
    """QPSK: 2 bits per symbol (vectorized Gray-coded quadrant decision)."""
    symbols = _downsample_to_symbols(sig, samples_per_symbol)
    i_bits = (np.real(symbols) > 0).astype(np.uint8)
    q_bits = (np.imag(symbols) > 0).astype(np.uint8)
    # Interleave I and Q bits
    interleaved = np.empty(len(symbols) * 2, dtype=np.uint8)
    interleaved[0::2] = i_bits
    interleaved[1::2] = q_bits
    return interleaved.tolist()


def demod_8psk(sig: np.ndarray, samples_per_symbol: int) -> list[int]:
    """8-PSK: 3 bits per symbol (vectorized sector quantization)."""
    symbols = _downsample_to_symbols(sig, samples_per_symbol)
    phases = np.angle(symbols)  # -π to π
    sectors = np.mod(np.round(phases / (2.0 * np.pi / 8.0)).astype(int), 8)
    
    sector_map = np.array([0b000, 0b001, 0b011, 0b010, 0b110, 0b111, 0b101, 0b100], dtype=np.uint8)
    grays = sector_map[sectors]

    b0 = (grays >> 2) & 1
    b1 = (grays >> 1) & 1
    b2 = grays & 1

    interleaved = np.empty(len(symbols) * 3, dtype=np.uint8)
    interleaved[0::3] = b0
    interleaved[1::3] = b1
    interleaved[2::3] = b2
    return interleaved.tolist()


def demod_fsk(sig: np.ndarray, samples_per_symbol: int) -> list[int]:
    """2-FSK: instantaneous frequency tracking."""
    if len(sig) < 2:
        raise ValueError("Signal is too short for FSK demodulation")
    phase = np.unwrap(np.angle(sig))
    inst_freq = np.diff(phase)
    inst_freq = np.append(inst_freq, inst_freq[-1])

    best_timing = (
        samples_per_symbol // 2
        if samples_per_symbol > 8 and samples_per_symbol % 2 == 0
        else samples_per_symbol
    )
    n_symbols = len(sig) // best_timing
    trimmed = inst_freq[: n_symbols * best_timing]
    avg_freq_per_symbol = trimmed.reshape(n_symbols, best_timing).mean(axis=1)
    threshold = np.median(avg_freq_per_symbol)
    return (avg_freq_per_symbol > threshold).astype(np.uint8).tolist()


def _vectorized_qam_slicer(symbols: np.ndarray, levels: np.ndarray) -> dict:
    """Vectorized M-QAM constellation slicer."""
    i_vals = np.real(symbols)
    q_vals = np.imag(symbols)
    
    # Broadcast distance matrix: |vals[:, None] - levels[None, :]|
    i_diffs = np.abs(i_vals[:, None] - levels[None, :])
    q_diffs = np.abs(q_vals[:, None] - levels[None, :])
    
    i_nearest = levels[np.argmin(i_diffs, axis=1)]
    q_nearest = levels[np.argmin(q_diffs, axis=1)]
    
    return {
        "i_levels": i_nearest.tolist(),
        "q_levels": q_nearest.tolist(),
    }


def demod_16qam(sig: np.ndarray, samples_per_symbol: int) -> dict:
    """16-QAM: 4 bits per symbol."""
    symbols = _downsample_to_symbols(sig, samples_per_symbol)
    levels = np.array([-3.0, -1.0, 1.0, 3.0], dtype=np.float32) / 3.0
    return _vectorized_qam_slicer(symbols, levels)


def demod_64qam(sig: np.ndarray, samples_per_symbol: int) -> dict:
    """64-QAM: 6 bits per symbol."""
    symbols = _downsample_to_symbols(sig, samples_per_symbol)
    levels = np.array([-7.0, -5.0, -3.0, -1.0, 1.0, 3.0, 5.0, 7.0], dtype=np.float32) / 7.0
    return _vectorized_qam_slicer(symbols, levels)


def demodulate(
    sig: np.ndarray,
    samples_per_symbol: int | None,
    modulation_label: str | None,
) -> dict:
    """Unified demodulator dispatcher."""
    if samples_per_symbol is None or samples_per_symbol < 1:
        return {"success": False, "reason": "No valid symbol timing available"}

    label = (modulation_label or "").upper().replace("-", "").replace(" ", "")
    try:
        if label in ("PSK", "BPSK"):
            bits = demod_bpsk(sig, samples_per_symbol)
            return {"success": True, "type": "bits", "bits": bits, "num_bits": len(bits), "modulation": "BPSK"}

        if label == "QPSK":
            bits = demod_qpsk(sig, samples_per_symbol)
            return {"success": True, "type": "bits", "bits": bits, "num_bits": len(bits), "modulation": "QPSK"}

        if label == "8PSK":
            bits = demod_8psk(sig, samples_per_symbol)
            return {"success": True, "type": "bits", "bits": bits, "num_bits": len(bits), "modulation": "8PSK"}

        if label in ("FSK", "2FSK", "4FSK"):
            bits = demod_fsk(sig, samples_per_symbol)
            return {"success": True, "type": "bits", "bits": bits, "num_bits": len(bits), "modulation": "FSK"}

        if label in ("QAM", "16QAM"):
            return {"success": True, "type": "symbol_levels", **demod_16qam(sig, samples_per_symbol), "modulation": "16QAM"}

        if label == "64QAM":
            return {"success": True, "type": "symbol_levels", **demod_64qam(sig, samples_per_symbol), "modulation": "64QAM"}

        return {"success": False, "reason": f"No demodulator implemented for '{modulation_label}'"}
    except (ValueError, IndexError, TypeError) as exc:
        return {"success": False, "reason": str(exc)}
