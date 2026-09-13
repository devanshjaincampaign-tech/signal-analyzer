# app/analysis/features.py
import numpy as np
from scipy import signal

DEFAULT_SAMPLE_RATE_FALLBACK = 1_000_000  # 1 MHz — only used if sample_rate is truly unknown

def extract_spectral_features(sig: np.ndarray, sample_rate: float | None) -> dict:
    used_fallback_rate = False
    if sample_rate is None:
        sample_rate = DEFAULT_SAMPLE_RATE_FALLBACK
        used_fallback_rate = True

    # Welch's method: averages multiple overlapping FFT segments -> much less
    # noisy than a single raw FFT, at the cost of some frequency resolution.
    freqs, psd = signal.welch(
        sig, fs=sample_rate, nperseg=min(1024, len(sig)),
        return_onesided=not np.iscomplexobj(sig),
    )

    psd_db = 10 * np.log10(psd + 1e-20)  # +epsilon avoids log(0)
    peak_idx = np.argmax(psd_db)
    center_frequency = float(freqs[peak_idx])

    # Occupied bandwidth: width of the region within 3dB of peak power
    threshold = psd_db[peak_idx] - 3
    above = np.where(psd_db >= threshold)[0]
    bandwidth = float(freqs[above[-1]] - freqs[above[0]]) if len(above) > 1 else 0.0

    return {
        "center_frequency_hz": center_frequency,
        "bandwidth_hz": bandwidth,
        "noise_floor_db": float(np.median(psd_db)),
        "peak_power_db": float(psd_db[peak_idx]),
        "sample_rate_used": sample_rate,
        "sample_rate_was_assumed": used_fallback_rate,
    }


def compute_spectrogram(sig: np.ndarray, sample_rate: float, nperseg: int = 256) -> dict:
    freqs, times, Sxx = signal.spectrogram(
        sig, fs=sample_rate, nperseg=min(nperseg, len(sig)),
        return_onesided=not np.iscomplexobj(sig),
    )
    Sxx_db = 10 * np.log10(Sxx + 1e-20)

    # Downsample before storing — a full-resolution spectrogram matrix is far
    # too large for a JSONB column; 64x64 is plenty for a UI heatmap in Phase 3.
    f_step = max(1, len(freqs) // 64)
    t_step = max(1, len(times) // 64)
    return {
        "freq_bins": freqs[::f_step].tolist(),
        "time_bins": times[::t_step].tolist(),
        "power_db_matrix": Sxx_db[::f_step, ::t_step].tolist(),
    }