"""
iq_reader.py – Robust IQ File Reader and Sampling Rate Extractor.

Supports:
  - SigMF Metadata (.sigmf-meta) parsing
  - Filename sample rate extraction regex (e.g. _2MSPS, _250kHz, _fs48000)
  - Accurate statistical data format autodetection (float32, int16, int8, uint8)
  - Unit normalization to standard float32 baseband I/Q (-1.0 to +1.0)
"""
from __future__ import annotations

import os
import re
import json
import numpy as np

# Canonical data types
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


def _extract_sample_rate_from_filename(filename: str) -> float | None:
    """Extract sample rate from common SDR naming conventions in filename.
    
    Examples:
      'capture_2.4MSPS.iq' -> 2,400,000.0 Hz
      'signal_fs250k.iq'   -> 250,000.0 Hz
      'lora_125kHz.iq'     -> 125,000.0 Hz
      'sat_48000Hz.iq'     -> 48,000.0 Hz
      'test_1M.iq'         -> 1,000,000.0 Hz
    """
    stem = os.path.splitext(os.path.basename(filename))[0]

    # Pattern for numbers followed by frequency/rate unit
    patterns = [
        r'(?:fs|rate|samp)?_?(\d+(?:\.\d+)?)\s*(m|k)?(?:sps|hz|samples|sample_rate)?(?:\b|_|$)',
        r'(\d+(?:\.\d+)?)\s*(msps|ksps|sps|mhz|khz|hz)\b',
    ]

    for pat in patterns:
        m = re.search(pat, stem, re.IGNORECASE)
        if m:
            val_str = m.group(1)
            unit_str = (m.group(2) if len(m.groups()) >= 2 and m.group(2) else "").lower()
            try:
                val = float(val_str)
                if "m" in unit_str:
                    return val * 1_000_000.0
                elif "k" in unit_str:
                    return val * 1_000.0
                elif val >= 1000:
                    return val
            except ValueError:
                pass
    return None


def _autodetect_iq_format(raw_bytes: bytes) -> tuple[str, np.dtype, float]:
    """Statistically detect the binary IQ format from raw byte samples.
    
    Returns:
        (canonical_name, np_dtype, normalization_scale)
    """
    n_bytes = len(raw_bytes)
    if n_bytes < 8:
        return "float32", np.dtype(np.float32), 1.0

    # 1. Test Float32
    if n_bytes % 4 == 0:
        f32_arr = np.frombuffer(raw_bytes[:min(n_bytes, 16384)], dtype=np.float32)
        if np.isfinite(f32_arr).all():
            abs_max = float(np.max(np.abs(f32_arr))) if len(f32_arr) > 0 else 0.0
            # Standard SDR floating point IQ samples typically reside in [-10.0, 10.0]
            if 1e-4 <= abs_max <= 20.0:
                return "float32", np.dtype(np.float32), 1.0

    # 2. Test Int16 (ci16_le)
    if n_bytes % 2 == 0:
        i16_arr = np.frombuffer(raw_bytes[:min(n_bytes, 8192)], dtype=np.int16)
        abs_max_16 = float(np.max(np.abs(i16_arr))) if len(i16_arr) > 0 else 0
        std_16 = float(np.std(i16_arr)) if len(i16_arr) > 0 else 0
        # If values span well beyond 8-bit range (> 256), it's int16
        if abs_max_16 > 256 and std_16 > 30:
            return "int16", np.dtype(np.int16), 32768.0

    # 3. Test Unsigned 8-bit (cu8 - RTL-SDR standard centered at 127.5)
    u8_arr = np.frombuffer(raw_bytes[:min(n_bytes, 4096)], dtype=np.uint8)
    mean_u8 = float(np.mean(u8_arr)) if len(u8_arr) > 0 else 0
    if 100 <= mean_u8 <= 155:
        return "uint8", np.dtype(np.uint8), 127.5

    # 4. Default to signed 8-bit (cs8 - HackRF standard) or float32
    if n_bytes % 4 == 0:
        return "float32", np.dtype(np.float32), 1.0
    return "int8", np.dtype(np.int8), 128.0


def read_iq_samples(
    path: str,
    sample_rate_override: float | None = None,
) -> tuple[np.ndarray, float, str]:
    """Read a .iq file and return normalized complex64 array, sample rate, and detected dtype.
    
    Returns:
        (iq_complex64_array, sample_rate_hz, dtype_name)
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"IQ file not found: {path}")

    sidecar = path.rsplit(".", 1)[0] + ".sigmf-meta"
    sr_detected = sample_rate_override or _extract_sample_rate_from_filename(path)
    dtype_name = None

    # 1. Read SigMF sidecar if present
    if os.path.exists(sidecar):
        try:
            with open(sidecar, "r", encoding="utf-8") as f:
                meta = json.load(f)
            global_info = meta.get("global", {})
            if not sr_detected:
                sr_detected = float(global_info.get("core:sample_rate", 1_000_000.0))
            dtype_str = global_info.get("core:datatype", "cf32_le")
            dtype_name = CANONICAL_NAME_MAP.get(dtype_str, "float32")
        except Exception:
            pass

    # Read binary bytes
    with open(path, "rb") as f:
        raw_bytes = f.read()

    if len(raw_bytes) == 0:
        raise ValueError(f"IQ file '{path}' is empty.")

    # 2. Autodetect format if not determined by SigMF
    if not dtype_name:
        dtype_name, np_dtype, scale = _autodetect_iq_format(raw_bytes)
    else:
        np_dtype = DTYPE_MAP.get(dtype_name, np.float32)
        scale = 32768.0 if dtype_name == "int16" else (128.0 if dtype_name == "int8" else (127.5 if dtype_name == "uint8" else 1.0))

    # Parse interleaved I/Q
    raw_array = np.frombuffer(raw_bytes, dtype=np_dtype)
    if len(raw_array) % 2 != 0:
        raw_array = raw_array[:len(raw_array) - 1]

    if dtype_name == "uint8":
        # Unsigned 8-bit (RTL-SDR): convert [0, 255] -> [-1.0, 1.0]
        i_ch = (raw_array[0::2].astype(np.float32) - 127.5) / 127.5
        q_ch = (raw_array[1::2].astype(np.float32) - 127.5) / 127.5
    else:
        i_ch = raw_array[0::2].astype(np.float32) / scale
        q_ch = raw_array[1::2].astype(np.float32) / scale

    iq = i_ch + 1j * q_ch

    # Default fallback rate if completely unspecified
    final_sr = float(sr_detected if sr_detected and sr_detected > 0 else 1_000_000.0)

    return iq.astype(np.complex64), final_sr, dtype_name


def read_iq(path: str) -> dict:
    """Ingestion metadata dictionary."""
    iq, sr, dtype_name = read_iq_samples(path)
    return {
        "sample_rate": sr,
        "num_samples": len(iq),
        "dtype": dtype_name,
        "source": "sigmf" if os.path.exists(path.rsplit(".", 1)[0] + ".sigmf-meta") else "autodetected",
    }