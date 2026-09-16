"""
loader.py – Unified Signal Loader for IQ and WAV files.
"""
from __future__ import annotations

import os
import numpy as np
from app.ingestion.iq_reader import read_iq_samples, DTYPE_MAP


def load_signal(job) -> tuple[np.ndarray, float | None, bool]:
    """Returns (signal_array, sample_rate, is_complex)."""
    if job.file_type == "wav":
        data, sr = sf.read(job.storage_path)
        if data.ndim > 1:
            data = data[:, 0]
        return data.astype(np.float32), float(sr), False

    elif job.file_type == "iq":
        meta = job.ingestion_metadata or {}
        sr_hint = meta.get("sample_rate")
        iq, sr, _ = read_iq_samples(job.storage_path, sample_rate_override=sr_hint)
        return iq, sr, True

    else:
        raise ValueError(f"Unsupported file_type: {job.file_type}")