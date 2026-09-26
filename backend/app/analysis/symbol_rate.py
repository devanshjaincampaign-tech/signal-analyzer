"""
symbol_rate.py – Robust Symbol Rate and Timing Estimator.

Estimates symbol rate using cyclostationary timing analysis, transition
autocorrelation, and envelope cyclostationarity across both real and complex
baseband signals.
"""
from __future__ import annotations

import numpy as np
from scipy import signal


def estimate_symbol_rate(sig: np.ndarray, sample_rate: float) -> dict:
    """Estimates symbol rate from the dominant periodic timing structure in the signal.

    Args:
        sig:         Input signal (real or complex).
        sample_rate: Sampling frequency in Hz.

    Returns:
        dict with keys: 'symbol_rate_hz', 'samples_per_symbol', 'confidence', 'method'
    """
    if len(sig) == 0:
        return _no_result("Signal is empty")
    if sample_rate <= 0:
        return _no_result("Sample rate must be positive")

    # Use max 65536 samples for fast, reliable timing estimation
    sub_sig = sig[:min(len(sig), 65536)]

    if np.iscomplexobj(sub_sig):
        # 1. Complex baseband: extract both phase/frequency transitions and envelope variations
        phase = np.unwrap(np.angle(sub_sig))
        freq_dev = np.diff(phase)
        freq_dev = freq_dev - np.mean(freq_dev)
        env = np.abs(sub_sig)
        env_dev = np.abs(np.diff(env))
        
        # Combined transition feature
        norm_freq = freq_dev / (np.std(freq_dev) + 1e-9)
        norm_env = env_dev / (np.std(env_dev) + 1e-9)
        trans = np.abs(norm_freq) + np.abs(norm_env)
    else:
        # 2. Real signal: zero-crossing transitions and envelope
        base = np.asarray(sub_sig, dtype=np.float64)
        base = base - np.mean(base)
        trans = np.abs(np.diff(np.sign(base)))
        if np.count_nonzero(trans) < 2:
            trans = np.abs(np.diff(base))

    # Fast FFT-based autocorrelation of transition profile
    corr = signal.correlate(trans, trans, mode="full", method="fft")
    corr = corr[len(corr) // 2:]
    corr[0] = 0.0

    min_lag = 2
    max_lag = int(min(len(corr) - 1, int(sample_rate) // 50))
    if max_lag <= min_lag:
        max_lag = min(len(corr) - 1, 1024)

    search_region = corr[min_lag:max_lag]
    if search_region.size == 0:
        return _no_result("No valid autocorrelation region")

    # Detect peaks in autocorrelation
    peaks, props = signal.find_peaks(search_region, distance=2, prominence=np.std(search_region) * 0.5)

    if len(peaks) > 0:
        # Choose most prominent candidate
        best_p = peaks[np.argmax(props.get("prominences", search_region[peaks]))]
        peak_idx = best_p
    else:
        peak_idx = int(np.argmax(search_region))

    samples_per_symbol = peak_idx + min_lag
    peak_value = float(corr[samples_per_symbol])

    local_mean = float(np.mean(np.abs(search_region))) + 1e-9
    confidence = float(min(1.0, peak_value / (local_mean * 5.0)))
    symbol_rate = sample_rate / samples_per_symbol

    return {
        "symbol_rate_hz": float(symbol_rate),
        "samples_per_symbol": int(samples_per_symbol),
        "confidence": round(confidence, 3),
        "method": "cyclostationary_timing_autocorrelation",
    }


def _no_result(reason: str) -> dict:
    return {
        "symbol_rate_hz": None,
        "samples_per_symbol": None,
        "confidence": 0.0,
        "method": "cyclostationary_timing_autocorrelation",
        "note": reason,
    }
