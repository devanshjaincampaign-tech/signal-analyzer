"""
iq_reader.py – Robust IQ File Reader and Sampling Rate Extractor.

Detection priority (highest → lowest):
  1. Explicit caller override (--sample-rate flag)
  2. SigMF sidecar (.sigmf-meta)
  3. Sidecar .json / .txt / .info metadata file
  4. Filename regex (e.g. _4MSPS, _4MHz, _4M, _250kHz, _fs48000)
  5. Spectral analysis of the raw IQ data (normalized bandwidth matching)
  6. Fallback: 1.0 MHz (with warning flag in returned metadata)

Spectral Auto-Detection Algorithm
----------------------------------
Since a raw .iq file has no embedded sample-rate header, the algorithm:
  a) Computes the Welch PSD with fs=1.0 (normalised, range -0.5..+0.5)
  b) Locates the occupied channel lobe (excluding DC and Fs/4 hardware spurs)
  c) Measures the 3dB AND 10dB contiguous lobe width in normalised units
  d) For every (standard_SDR_rate × standard_channel_BW) pair, checks
     whether  normalised_bw × candidate_rate  ≈  channel_BW  (within 10%)
  e) Scores each surviving candidate on:
       - Bandwidth match accuracy (lower error → higher score)
       - Oversampling ratio preference (2–32× is realistic; 8× ideal)
       - Protocol/rate priority weight:
           • LoRa 125k/250k/500k chirp BWs get a large bonus
           • Whole-MHz SDR rates (1M, 2M, 4M, 6M …) get a bonus
           • Sub-Hz fractional rates are penalised
  f) Returns the best-scoring (sample_rate, channel_bw, confidence) tuple
"""
from __future__ import annotations

import os
import re
import json
import numpy as np

# ---------------------------------------------------------------------------
# Data-type maps
# ---------------------------------------------------------------------------
DTYPE_MAP = {
    "cs8": np.int8,
    "cu8": np.uint8,
    "ci16_le": np.int16,
    "ci16": np.int16,
    "int16": np.int16,
    "int8": np.int8,
    "uint8": np.uint8,
    "cf32_le": np.float32,
    "float32": np.float32,
}

CANONICAL_NAME_MAP = {
    "cs8": "int8",
    "cu8": "uint8",
    "ci16_le": "int16",
    "ci16": "int16",
    "int16": "int16",
    "int8": "int8",
    "uint8": "uint8",
    "cf32_le": "float32",
    "float32": "float32",
}

# ---------------------------------------------------------------------------
# Standard tables for spectral SR detection
# ---------------------------------------------------------------------------

# (channel_bw_hz, priority_weight)
# Higher weight = preferred when multiple candidates have equal error.
# LoRa chirp BWs: 125k / 250k / 500k  (very common, exact powers of 2 × 125k)
# GSM: 200k, TETRA: 25k, AM: 10k/12.5k, FM: 200k, Satellite: 36MHz…
_STANDARD_CHANNEL_BWS: list[tuple[float, float]] = [
    (12_500, 0.7),        # Narrowband voice, TETRA
    (25_000, 0.8),        # PMR, APRS
    (50_000, 0.8),        # Wide NFM
    (100_000, 0.6),       # Non-standard; low priority
    (125_000, 2.0),       # LoRa BW=125k  ← HIGH PRIORITY
    (200_000, 0.9),       # GSM, EDGE, FM broadcast
    (250_000, 2.0),       # LoRa BW=250k  ← HIGH PRIORITY
    (500_000, 2.0),       # LoRa BW=500k / CDMA one channel ← HIGH PRIORITY
    (1_000_000, 1.0),     # 1 MHz channel (some LTE)
    (1_400_000, 0.8),
    (2_000_000, 1.2),     # LTE 5 MHz resource
    (3_000_000, 0.8),
    (5_000_000, 1.1),     # LTE 10 MHz
    (6_000_000, 0.7),
    (8_000_000, 0.7),
    (10_000_000, 1.0),    # LTE 20 MHz
    (20_000_000, 0.9),    # Wi-Fi HT20
]

# (sdr_rate_hz, priority_weight)
# Whole-MHz rates with large installed base of SDRs get higher weight.
_STANDARD_SDR_RATES: list[tuple[float, float]] = [
    (250_000,   0.5),
    (500_000,   0.7),
    (1_000_000, 1.2),   # RTL-SDR default
    (1_024_000, 0.6),
    (1_400_000, 0.6),
    (1_920_000, 0.7),
    (2_000_000, 1.2),   # HackRF / RTL common
    (2_048_000, 0.7),
    (2_400_000, 1.0),   # RTL-SDR max no-drop
    (2_560_000, 0.6),
    (3_000_000, 0.9),
    (3_200_000, 0.6),
    (4_000_000, 1.3),   # Very common HackRF / USRP rate ← PREFERRED
    (5_000_000, 1.1),
    (6_000_000, 1.1),
    (8_000_000, 1.2),
    (10_000_000, 1.1),
    (12_000_000, 0.8),
    (12_500_000, 0.7),
    (16_000_000, 0.8),
    (20_000_000, 0.9),
    (25_000_000, 0.8),
    (30_720_000, 0.7),
]

# Max number of IQ samples to use for the spectral analysis (trade-off: accuracy vs speed)
_SR_DETECT_MAX_SAMPLES = 500_000
_SR_DETECT_NPERSEG = 4096     # High frequency resolution


# ---------------------------------------------------------------------------
# Public helper
# ---------------------------------------------------------------------------

def parse_sample_rate(val: str | float | int | None) -> float | None:
    """Parse flexible sample-rate inputs into Hz.

    Examples
    --------
    '4M' → 4_000_000.0
    '4MHz' → 4_000_000.0
    '4MSPS' → 4_000_000.0
    '250k' → 250_000.0
    '2.4MSPS' → 2_400_000.0
    4000000 → 4_000_000.0
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val) if float(val) > 0 else None

    s = str(val).strip().lower()
    if not s:
        return None

    m = re.match(
        r'^([0-9]+(?:\.[0-9]+)?(?:e[+\-]?[0-9]+)?)\s*(msps|mhz|m|ksps|khz|k|sps|hz)?$', s
    )
    if m:
        num = float(m.group(1))
        unit = m.group(2) or ""
        if unit.startswith("m"):
            return num * 1_000_000.0
        elif unit.startswith("k"):
            return num * 1_000.0
        elif unit in ("sps", "hz", ""):
            return num

    try:
        return float(s)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Tier 3: Filename regex
# ---------------------------------------------------------------------------

def _extract_sample_rate_from_filename(filename: str) -> float | None:
    """Extract sample rate from common SDR naming conventions in filename."""
    stem = os.path.splitext(os.path.basename(filename))[0]

    unit_patterns = [
        r'(?:^|[_\-\.])(?:fs|rate)?_?([0-9]+(?:\.[0-9]+)?)\s*(msps|mhz|m)\b',
        r'(?:^|[_\-\.])(?:fs|rate)?_?([0-9]+(?:\.[0-9]+)?)\s*(ksps|khz|k)\b',
        r'(?:^|[_\-\.])(?:fs|rate)?_?([0-9]+(?:\.[0-9]+)?)\s*(sps|hz)\b',
    ]

    for pat in unit_patterns:
        m = re.search(pat, stem, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            unit = m.group(2).lower()
            if unit.startswith("m"):
                return val * 1_000_000.0
            elif unit.startswith("k"):
                return val * 1_000.0
            elif unit.startswith("s") or unit.startswith("h"):
                return val

    # Prefix patterns like fs2000000 or rate4000000
    m_prefix = re.search(r'(?:fs|samp_rate|rate|samplerate)[_\-]?([0-9]+)\b', stem, re.IGNORECASE)
    if m_prefix:
        val = float(m_prefix.group(1))
        if val >= 1000:
            return val

    return None


# ---------------------------------------------------------------------------
# Tier 2: Sidecar metadata files
# ---------------------------------------------------------------------------

def _scan_sidecar_metadata(path: str) -> tuple[float | None, str | None]:
    """Scan for .sigmf-meta, .json, or .txt sidecar specifying sample rate."""
    base_dir = os.path.dirname(path) or "."
    stem = os.path.splitext(os.path.basename(path))[0]

    # 1. SigMF
    sigmf_path = os.path.join(base_dir, stem + ".sigmf-meta")
    if os.path.exists(sigmf_path):
        try:
            with open(sigmf_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            global_info = meta.get("global", {})
            sr = float(global_info.get("core:sample_rate", 0))
            dtype_str = global_info.get("core:datatype", "cf32_le")
            dtype_name = CANONICAL_NAME_MAP.get(dtype_str, "float32")
            if sr > 0:
                return sr, dtype_name
        except Exception:
            pass

    # 2. Generic .json / .txt / .info
    for ext in (".json", ".txt", ".info"):
        meta_file = os.path.join(base_dir, stem + ext)
        if os.path.exists(meta_file):
            try:
                with open(meta_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                m = re.search(
                    r'(?:sample[_\s]?rate|samplerate|fs|sampling[_\s]?freq(?:uency)?)'
                    r'\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)\s*(mhz|msps|m|khz|ksps|k|hz|sps)?',
                    content, re.IGNORECASE,
                )
                if m:
                    num = float(m.group(1))
                    unit = (m.group(2) or "").lower()
                    if unit.startswith("m"):
                        return num * 1_000_000.0, None
                    elif unit.startswith("k"):
                        return num * 1_000.0, None
                    return num, None
            except Exception:
                pass

    return None, None


# ---------------------------------------------------------------------------
# Tier 4: Spectral sample-rate estimation from the IQ signal itself
# ---------------------------------------------------------------------------

def _autodetect_sample_rate_from_signal(
    iq: np.ndarray,
) -> tuple[float | None, str]:
    """
    Estimate sampling rate from the normalised PSD of the IQ data.

    Returns
    -------
    (estimated_rate_hz, description_string)
      estimated_rate_hz  – best candidate, or None if confidence too low
      description_string – human-readable explanation
    """
    from scipy import signal as sp_signal  # local import to keep startup fast

    n = min(len(iq), _SR_DETECT_MAX_SAMPLES)
    if n < 256:
        return None, "Signal too short for spectral SR detection"

    seg = iq[:n]

    # Normalised Welch PSD (fs=1.0 → frequencies in [−0.5, +0.5])
    freqs, psd = sp_signal.welch(seg, fs=1.0, nperseg=min(_SR_DETECT_NPERSEG, n),
                                  return_onesided=False)
    freqs = np.fft.fftshift(freqs)
    psd   = np.fft.fftshift(psd)
    psd_db = 10.0 * np.log10(psd + 1e-20)

    # ---------- locate the dominant modulated lobe ----------
    # Mask out common SDR hardware artefacts:
    #   DC spur:          |f| < 0.01
    #   Fs/4 aliasing spur: |f - ±0.25| < 0.02
    mask = (
        (np.abs(freqs) > 0.01)
        & (np.abs(np.abs(freqs) - 0.25) > 0.02)
    )
    if mask.sum() < 8:
        return None, "Spectrum too sparse after masking artefacts"

    noise_floor = float(np.median(psd_db))
    masked_db = np.where(mask, psd_db, noise_floor)
    peak_idx = int(np.argmax(masked_db))

    if masked_db[peak_idx] < noise_floor + 3.0:
        return None, "No prominent signal peak found above noise floor"

    # Measure 3 dB and 10 dB contiguous lobe widths
    def _contiguous_bw(threshold_db: float) -> float:
        l, r = peak_idx, peak_idx
        while l > 0 and psd_db[l - 1] >= threshold_db:
            l -= 1
        while r < len(psd_db) - 1 and psd_db[r + 1] >= threshold_db:
            r += 1
        return float(freqs[r] - freqs[l])

    peak_db   = float(masked_db[peak_idx])
    norm_bw3  = _contiguous_bw(peak_db - 3.0)
    norm_bw10 = _contiguous_bw(peak_db - 10.0)

    if norm_bw10 <= 0.0:
        return None, "Could not measure 10 dB bandwidth"

    # ---------- score all (rate × channel_bw) candidates ----------
    best_score = -1.0
    best_rate: float | None = None
    best_desc = ""

    for fs_cand, fs_weight in _STANDARD_SDR_RATES:
        # Convert normalised BW to Hz at this candidate rate
        implied_bw3  = fs_cand * norm_bw3
        implied_bw10 = fs_cand * norm_bw10

        for chan_bw, bw_weight in _STANDARD_CHANNEL_BWS:
            # Check both 3 dB and 10 dB windows against the standard channel BW
            err3  = abs(chan_bw - implied_bw3)  / chan_bw
            err10 = abs(chan_bw - implied_bw10) / chan_bw
            err   = min(err3, err10)

            if err > 0.10:          # 10% tolerance
                continue

            osr = fs_cand / chan_bw  # oversampling ratio
            if osr < 1.5 or osr > 64.0:
                continue

            # Score components:
            # 1) bandwidth match accuracy (1 at 0% error → 0 at 10% error)
            score_err = 1.0 - err * 10.0

            # 2) OSR preference: ideal ≈ 4–16×, penalise extremes
            ideal_osr = 8.0
            score_osr = 1.0 / (1.0 + 0.03 * abs(osr - ideal_osr))

            # 3) priority weights from the tables
            score = score_err * score_osr * fs_weight * bw_weight

            if score > best_score:
                best_score = score
                best_rate  = float(fs_cand)
                best_desc  = (
                    f"spectral: implied BW = {implied_bw10/1e3:.1f} kHz "
                    f"~= {chan_bw/1e3:.0f} kHz std (err {err*100:.1f}%), "
                    f"Fs = {fs_cand/1e6:.3f} MHz, OSR = {osr:.0f}x"
                )

    if best_rate is None or best_score < 0.05:
        return None, "Spectral SR detection: no confident match found"

    return best_rate, best_desc


# ---------------------------------------------------------------------------
# Format autodetection
# ---------------------------------------------------------------------------

def _autodetect_iq_format(raw_bytes: bytes) -> tuple[str, np.dtype, float]:
    """Statistically detect the binary IQ sample format."""
    n_bytes = len(raw_bytes)
    if n_bytes < 8:
        return "float32", np.dtype(np.float32), 1.0

    if n_bytes % 4 == 0:
        f32_arr = np.frombuffer(raw_bytes[:min(n_bytes, 16384)], dtype=np.float32)
        if np.isfinite(f32_arr).all():
            abs_max = float(np.max(np.abs(f32_arr))) if len(f32_arr) > 0 else 0.0
            if 1e-4 <= abs_max <= 20.0:
                return "float32", np.dtype(np.float32), 1.0

    if n_bytes % 2 == 0:
        i16_arr = np.frombuffer(raw_bytes[:min(n_bytes, 8192)], dtype=np.int16)
        abs_max_16 = float(np.max(np.abs(i16_arr))) if len(i16_arr) > 0 else 0
        std_16 = float(np.std(i16_arr)) if len(i16_arr) > 0 else 0
        if abs_max_16 > 256 and std_16 > 30:
            return "int16", np.dtype(np.int16), 32768.0

    u8_arr = np.frombuffer(raw_bytes[:min(n_bytes, 4096)], dtype=np.uint8)
    mean_u8 = float(np.mean(u8_arr)) if len(u8_arr) > 0 else 0
    if 100 <= mean_u8 <= 155:
        return "uint8", np.dtype(np.uint8), 127.5

    if n_bytes % 4 == 0:
        return "float32", np.dtype(np.float32), 1.0
    return "int8", np.dtype(np.int8), 128.0


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------

def read_iq_samples(
    path: str,
    sample_rate_override: float | str | None = None,
) -> tuple[np.ndarray, float, str]:
    """
    Read a .iq file and return (complex64_array, sample_rate_hz, dtype_name).

    Sample-rate detection priority
    --------------------------------
    1. Explicit override argument
    2. SigMF .sigmf-meta sidecar
    3. Adjacent .json / .txt / .info metadata file
    4. Filename regex (e.g. _4MSPS, _4MHz, _250kHz)
    5. Spectral analysis of the signal data itself
    6. Hardcoded fallback: 1.0 MHz  (sample_rate_was_assumed=True)
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"IQ file not found: {path}")

    # -- Priority 1: explicit override --
    sr_final: float | None = parse_sample_rate(sample_rate_override)
    sr_source = "override" if sr_final else None

    # -- Priority 2 & 3: sidecar metadata --
    if not sr_final:
        sidecar_sr, sidecar_dtype = _scan_sidecar_metadata(path)
        if sidecar_sr:
            sr_final = sidecar_sr
            sr_source = "sidecar_metadata"
    else:
        sidecar_dtype = None

    # -- Priority 4: filename --
    if not sr_final:
        filename_sr = _extract_sample_rate_from_filename(path)
        if filename_sr:
            sr_final = filename_sr
            sr_source = "filename"

    # -- Read raw bytes and detect dtype --
    with open(path, "rb") as f:
        raw_bytes = f.read()

    if len(raw_bytes) == 0:
        raise ValueError(f"IQ file '{path}' is empty.")

    dtype_name = sidecar_dtype if 'sidecar_dtype' in dir() and sidecar_dtype else None
    if not dtype_name:
        dtype_name, np_dtype, scale = _autodetect_iq_format(raw_bytes)
    else:
        np_dtype = DTYPE_MAP.get(dtype_name, np.float32)
        scale = (
            32768.0  if dtype_name == "int16"  else
            128.0    if dtype_name == "int8"   else
            127.5    if dtype_name == "uint8"  else
            1.0
        )

    # Decode interleaved I/Q
    raw_array = np.frombuffer(raw_bytes, dtype=np_dtype)
    if len(raw_array) % 2 != 0:
        raw_array = raw_array[:len(raw_array) - 1]

    if dtype_name == "uint8":
        i_ch = (raw_array[0::2].astype(np.float32) - 127.5) / 127.5
        q_ch = (raw_array[1::2].astype(np.float32) - 127.5) / 127.5
    else:
        i_ch = raw_array[0::2].astype(np.float32) / scale
        q_ch = raw_array[1::2].astype(np.float32) / scale

    iq = (i_ch + 1j * q_ch).astype(np.complex64)

    # -- Priority 5: spectral analysis --
    if not sr_final:
        spectral_sr, spectral_desc = _autodetect_sample_rate_from_signal(iq)
        if spectral_sr:
            sr_final = spectral_sr
            sr_source = f"spectral_analysis ({spectral_desc})"
            print(f"[iq_reader] Auto-detected Fs = {spectral_sr/1e6:.3f} MHz via {spectral_desc}")

    # -- Priority 6: fallback --
    was_assumed = False
    if not sr_final:
        sr_final = 1_000_000.0
        sr_source = "default_fallback_1MHz"
        was_assumed = True
        print(
            f"[iq_reader] WARNING: Could not detect sampling rate for '{os.path.basename(path)}'.\n"
            f"  Defaulting to 1.0 MHz. Pass --sample-rate to override.\n"
            f"  Tip: rename file like 'signal_4MSPS.iq' for automatic detection."
        )

    return iq, float(sr_final), dtype_name


def read_iq(path: str) -> dict:
    """Return an ingestion metadata dict (no sample-rate override)."""
    iq, sr, dtype_name = read_iq_samples(path)
    return {
        "sample_rate": sr,
        "num_samples": len(iq),
        "dtype": dtype_name,
        "source": (
            "sigmf"
            if os.path.exists(path.rsplit(".", 1)[0] + ".sigmf-meta")
            else "autodetected"
        ),
    }