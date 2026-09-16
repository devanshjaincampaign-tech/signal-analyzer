"""
preprocessing.py – Signal preprocessing pipeline.

Provides:
  - DC offset removal
  - Resampling (rational up/down conversion)
  - Hilbert transform (real → analytic signal)
  - Normalisation (unit RMS power)

All functions accept numpy arrays and return numpy arrays.
No side-effects; safe to call from async FastAPI handlers.
"""
from __future__ import annotations

import numpy as np
from scipy import signal as sp_signal


# ── DC offset removal ─────────────────────────────────────────────────────────

def remove_dc(sig: np.ndarray) -> np.ndarray:
    """Subtract the mean (DC component) from the signal.

    Works on both real and complex arrays.

    Args:
        sig: 1-D numpy array.

    Returns:
        DC-free copy of sig.
    """
    return sig - np.mean(sig)


# ── Normalisation ─────────────────────────────────────────────────────────────

def normalize_power(sig: np.ndarray, target_rms: float = 1.0) -> np.ndarray:
    """Scale signal to a target RMS power level.

    Args:
        sig:        Input signal (real or complex).
        target_rms: Desired RMS amplitude (default 1.0).

    Returns:
        Normalised signal.
    """
    rms = np.sqrt(np.mean(np.abs(sig) ** 2))
    if rms < 1e-12:
        return sig  # avoid div-by-zero on zero signal
    return sig * (target_rms / rms)


# ── Resampling ────────────────────────────────────────────────────────────────

def resample(sig: np.ndarray, up: int, down: int) -> np.ndarray:
    """Rational resampling by factor up/down.

    Uses scipy.signal.resample_poly with a Kaiser anti-aliasing window.

    Args:
        sig:  Input signal (real or complex).
        up:   Upsample factor (numerator).
        down: Downsample factor (denominator).

    Returns:
        Resampled signal.

    Example:
        # Resample from 48 kHz to 44.1 kHz
        resample(sig, up=441, down=480)
    """
    if up == down == 1:
        return sig
    return sp_signal.resample_poly(sig, up, down, window=("kaiser", 5.0))


# ── Hilbert transform (real → analytic) ──────────────────────────────────────

def to_analytic(sig: np.ndarray) -> np.ndarray:
    """Convert a real-valued signal to its analytic (complex) representation.

    Applies the Hilbert transform to produce the analytic signal
    z(t) = x(t) + j * H{x(t)}, where the instantaneous amplitude and
    phase are unambiguously defined.

    Args:
        sig: Real-valued 1-D numpy array.

    Returns:
        Complex64 analytic signal of the same length.

    Raises:
        ValueError: if sig is already complex.
    """
    if np.iscomplexobj(sig):
        raise ValueError(
            "Signal is already complex. Hilbert transform applies to real signals only."
        )
    return sp_signal.hilbert(sig).astype(np.complex64)


# ── Convenience pipeline ──────────────────────────────────────────────────────

def preprocess(
    sig: np.ndarray,
    remove_dc_offset: bool = True,
    apply_hilbert: bool = False,
    resample_up: int = 1,
    resample_down: int = 1,
    normalize: bool = True,
) -> np.ndarray:
    """Run the full preprocessing pipeline.

    Steps (in order):
      1. DC offset removal (optional)
      2. Resampling (optional, applied before Hilbert)
      3. Hilbert transform → analytic signal (optional, real input only)
      4. Power normalisation (optional)

    Args:
        sig:             Input signal.
        remove_dc_offset: Remove DC component.
        apply_hilbert:   Convert real to complex analytic signal.
        resample_up:     Resampling numerator (1 = no change).
        resample_down:   Resampling denominator (1 = no change).
        normalize:       Normalise to unit RMS.

    Returns:
        Preprocessed numpy array.
    """
    if remove_dc_offset:
        sig = remove_dc(sig)

    if resample_up != 1 or resample_down != 1:
        sig = resample(sig, resample_up, resample_down)

    if apply_hilbert and not np.iscomplexobj(sig):
        sig = to_analytic(sig)

    if normalize:
        sig = normalize_power(sig)

    return sig
