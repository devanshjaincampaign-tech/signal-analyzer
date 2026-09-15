import numpy as np
from scipy import signal


def estimate_symbol_rate(sig: np.ndarray, sample_rate: float) -> dict:
    """
    Estimates symbol rate from the dominant periodic structure in the signal.

    For digitally modulated signals, the symbol timing shows up as a repeating
    pattern in a transition-derived feature, even when the carrier envelope is
    constant (as in BPSK). The estimator therefore autocorrelates a transition
    signal derived from the real-valued I/Q stream rather than relying on a
    constant-amplitude envelope alone.
    """
    if len(sig) == 0:
        return _no_result("Signal is empty")
    if sample_rate <= 0:
        return _no_result("Sample rate must be positive")

    base = np.real(sig) if np.iscomplexobj(sig) else np.asarray(sig, dtype=np.float64)
    base = base - np.mean(base)
    if np.allclose(base, 0):
        return _no_result("Signal has no usable variation")

    transition_signal = np.abs(np.diff(np.sign(base)))
    if np.count_nonzero(transition_signal) < 2:
        transition_signal = np.abs(np.diff(base))

    corr = signal.correlate(transition_signal, transition_signal, mode="full", method="fft")
    corr = corr[len(corr) // 2:]
    corr[0] = 0

    min_lag = 2
    max_lag = min(len(corr) - 1, sample_rate // 100)
    if max_lag <= min_lag:
        return _no_result("Signal too short to estimate symbol rate")

    search_region = corr[min_lag:max_lag]
    if search_region.size == 0:
        return _no_result("No valid autocorrelation region")

    local_max = np.zeros_like(search_region, dtype=bool)
    if len(search_region) > 1:
        local_max[1:-1] = (search_region[1:-1] >= search_region[:-2]) & (search_region[1:-1] >= search_region[2:])
        local_max[0] = search_region[0] >= search_region[1]
        local_max[-1] = search_region[-1] >= search_region[-2]

    threshold = np.median(search_region) + 3 * np.std(search_region)
    candidate_idx = np.where(local_max & (search_region >= threshold))[0]
    if candidate_idx.size == 0:
        peak_idx = int(np.argmax(search_region))
    else:
        peak_idx = int(candidate_idx[0])

    samples_per_symbol = peak_idx + min_lag
    peak_value = float(corr[samples_per_symbol])
    if peak_value <= 0:
        return _no_result("No clear periodicity detected in symbol transitions")

    local_mean = float(np.mean(np.abs(search_region)))
    confidence = float(min(1.0, peak_value / (local_mean + 1e-9) / 10))
    symbol_rate = sample_rate / samples_per_symbol

    return {
        "symbol_rate_hz": float(symbol_rate),
        "samples_per_symbol": int(samples_per_symbol),
        "confidence": round(confidence, 3),
        "method": "autocorrelation_transitions",
    }


def _no_result(reason: str) -> dict:
    return {
        "symbol_rate_hz": None,
        "samples_per_symbol": None,
        "confidence": 0.0,
        "method": "autocorrelation_transitions",
        "note": reason,
    }
