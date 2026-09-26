# app/analysis/features.py
from __future__ import annotations

import numpy as np
from scipy import signal

DEFAULT_SAMPLE_RATE_FALLBACK = 1_000_000.0  # 1 MHz — only used if sample_rate is truly unknown


def _normalize_frequency_axis(freqs: np.ndarray, spectrum: np.ndarray, is_complex: bool) -> tuple[np.ndarray, np.ndarray]:
    if is_complex:
        freqs = np.fft.fftshift(freqs)
        spectrum = np.fft.fftshift(spectrum, axes=0)
    return freqs, spectrum


def extract_spectral_features(sig: np.ndarray, sample_rate: float | None) -> dict:
    """
    Extract spectral characteristics from real or complex baseband signals.

    Features extracted:
      - center_frequency_hz / baseband_offset_hz : Frequency of highest channel energy
      - bandwidth_hz                             : Contiguous 3dB channel bandwidth
      - bandwidth_10db_hz                        : Contiguous 10dB channel bandwidth
      - noise_floor_db                           : Median spectral noise power
      - peak_power_db                            : Peak channel power (dBFS)
    """
    if len(sig) == 0:
        raise ValueError("Signal is empty")

    used_fallback_rate = False
    if sample_rate is None or sample_rate <= 0:
        sample_rate = DEFAULT_SAMPLE_RATE_FALLBACK
        used_fallback_rate = True

    is_complex = np.iscomplexobj(sig)
    
    # Use Welch's method with nperseg=2048 for high frequency resolution
    nperseg = min(2048, len(sig))
    freqs, psd = signal.welch(
        sig, fs=sample_rate, nperseg=nperseg,
        return_onesided=not is_complex,
    )
    freqs, psd = _normalize_frequency_axis(freqs, psd, is_complex)

    psd_db = 10 * np.log10(psd + 1e-20)
    noise_floor_db = float(np.median(psd_db))

    # Candidate peaks above noise floor
    min_height = noise_floor_db + 4.0
    peaks, _ = signal.find_peaks(psd_db, height=min_height, prominence=1.5)

    if len(peaks) == 0:
        best_peak = int(np.argmax(psd_db))
    else:
        # Rank peaks by integrated channel energy (band power)
        # to filter out zero-bandwidth CW hardware spurs (e.g. at -Fs/4 or DC)
        candidates = []
        for p in peaks:
            th = psd_db[p] - 3.0
            l, r = p, p
            while l > 0 and psd_db[l - 1] >= th:
                l -= 1
            while r < len(psd_db) - 1 and psd_db[r + 1] >= th:
                r += 1
            bw = float(freqs[r] - freqs[l])
            bins = r - l + 1
            band_pwr = float(np.sum(psd[l:r + 1]))
            candidates.append({
                "peak_idx": p,
                "freq": float(freqs[p]),
                "power_db": float(psd_db[p]),
                "bw_3db": bw,
                "bins": bins,
                "band_pwr": band_pwr,
            })

        # Prefer modulated channels spanning multiple bins over single-bin spurs
        modulated = [c for c in candidates if c["bins"] > 1]
        if modulated:
            best_cand = max(modulated, key=lambda c: c["band_pwr"])
        else:
            best_cand = max(candidates, key=lambda c: c["power_db"])
        best_peak = best_cand["peak_idx"]

    center_frequency = float(freqs[best_peak])

    # Contiguous 3dB bandwidth around selected peak
    th3 = psd_db[best_peak] - 3.0
    left3, right3 = best_peak, best_peak
    while left3 > 0 and psd_db[left3 - 1] >= th3:
        left3 -= 1
    while right3 < len(psd_db) - 1 and psd_db[right3 + 1] >= th3:
        right3 += 1
    bandwidth_3db = float(freqs[right3] - freqs[left3])

    # Contiguous 10dB bandwidth around selected peak
    th10 = psd_db[best_peak] - 10.0
    left10, right10 = best_peak, best_peak
    while left10 > 0 and psd_db[left10 - 1] >= th10:
        left10 -= 1
    while right10 < len(psd_db) - 1 and psd_db[right10 + 1] >= th10:
        right10 += 1
    bandwidth_10db = float(freqs[right10] - freqs[left10])

    bin_resolution = float(freqs[1] - freqs[0]) if len(freqs) > 1 else 1.0

    return {
        "center_frequency_hz": center_frequency,
        "baseband_offset_hz": center_frequency,
        "bandwidth_hz": bandwidth_3db if bandwidth_3db > 0 else bin_resolution,
        "bandwidth_10db_hz": bandwidth_10db if bandwidth_10db > 0 else (bandwidth_3db or bin_resolution),
        "noise_floor_db": noise_floor_db,
        "peak_power_db": float(psd_db[best_peak]),
        "sample_rate_used": sample_rate,
        "sample_rate_was_assumed": used_fallback_rate,
    }


def compute_spectrogram(sig: np.ndarray, sample_rate: float, nperseg: int = 256) -> dict:
    if len(sig) == 0:
        raise ValueError("Signal is empty")

    is_complex = np.iscomplexobj(sig)
    freqs, times, Sxx = signal.spectrogram(
        sig, fs=sample_rate, nperseg=min(nperseg, len(sig)),
        return_onesided=not is_complex,
    )
    if is_complex:
        freqs = np.fft.fftshift(freqs)
        Sxx = np.fft.fftshift(Sxx, axes=0)
    Sxx_db = 10 * np.log10(Sxx + 1e-20)

    f_step = int(max(1, len(freqs) // 64))
    t_step = int(max(1, len(times) // 64))
    return {
        "freq_bins": freqs[::f_step].tolist(),
        "time_bins": times[::t_step].tolist(),
        "power_db_matrix": Sxx_db[::f_step, ::t_step].tolist(),
    }