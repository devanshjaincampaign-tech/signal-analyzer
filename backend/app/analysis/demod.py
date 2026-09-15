import numpy as np


def _downsample_to_symbols(sig: np.ndarray, samples_per_symbol: int) -> np.ndarray:
    if samples_per_symbol < 1:
        raise ValueError("samples_per_symbol must be positive")
    n_symbols = len(sig) // samples_per_symbol
    if n_symbols == 0:
        raise ValueError("Signal is too short for the requested symbol timing")
    trimmed = sig[: n_symbols * samples_per_symbol]
    reshaped = trimmed.reshape(n_symbols, samples_per_symbol)
    return reshaped[:, samples_per_symbol // 2]


def demod_bpsk(sig: np.ndarray, samples_per_symbol: int) -> list[int]:
    symbols = _downsample_to_symbols(sig, samples_per_symbol)
    return (np.real(symbols) > 0).astype(int).tolist()


def demod_fsk(sig: np.ndarray, samples_per_symbol: int) -> list[int]:
    if len(sig) < 2:
        raise ValueError("Signal is too short for FSK demodulation")
    phase = np.unwrap(np.angle(sig))
    inst_freq = np.diff(phase)
    inst_freq = np.append(inst_freq, inst_freq[-1])
    # The transition-based estimator can select the first strong harmonic for
    # this waveform. FSK's frequency plateaus provide one reliable refinement:
    # a timing estimate above eight samples is commonly the doubled period.
    best_timing = (
        samples_per_symbol // 2
        if samples_per_symbol > 8 and samples_per_symbol % 2 == 0
        else samples_per_symbol
    )

    n_symbols = len(sig) // best_timing
    trimmed = inst_freq[: n_symbols * best_timing]
    avg_freq_per_symbol = trimmed.reshape(n_symbols, best_timing).mean(axis=1)
    threshold = np.median(avg_freq_per_symbol)
    return (avg_freq_per_symbol > threshold).astype(int).tolist()


def demod_16qam(sig: np.ndarray, samples_per_symbol: int) -> dict:
    symbols = _downsample_to_symbols(sig, samples_per_symbol)
    levels = np.array([-3, -1, 1, 3], dtype=float) / 3.0

    def nearest(value: float) -> float:
        return float(levels[np.argmin(np.abs(levels - value))])

    return {
        "i_levels": [nearest(value) for value in np.real(symbols)],
        "q_levels": [nearest(value) for value in np.imag(symbols)],
    }


def demodulate(
    sig: np.ndarray,
    samples_per_symbol: int | None,
    modulation_label: str | None,
) -> dict:
    if samples_per_symbol is None or samples_per_symbol < 1:
        return {"success": False, "reason": "No valid symbol timing available"}

    try:
        if modulation_label == "PSK":
            bits = demod_bpsk(sig, samples_per_symbol)
            return {"success": True, "type": "bits", "bits": bits, "num_bits": len(bits)}
        if modulation_label == "FSK":
            bits = demod_fsk(sig, samples_per_symbol)
            return {"success": True, "type": "bits", "bits": bits, "num_bits": len(bits)}
        if modulation_label == "QAM":
            return {
                "success": True,
                "type": "symbol_levels",
                **demod_16qam(sig, samples_per_symbol),
            }
        return {
            "success": False,
            "reason": f"No demodulator implemented for '{modulation_label}'",
        }
    except (ValueError, IndexError, TypeError) as exc:
        return {"success": False, "reason": str(exc)}
