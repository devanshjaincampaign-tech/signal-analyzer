# app/analysis/loader.py
import numpy as np
import soundfile as sf

DTYPE_MAP = {
    "int8": np.int8, "uint8": np.uint8,
    "int16": np.int16, "float32": np.float32,
}

def load_signal(job) -> tuple[np.ndarray, float | None, bool]:
    """
    Returns (signal_array, sample_rate, is_complex).
    .wav  -> real-valued float32 array
    .iq   -> complex64 array reconstructed from interleaved I/Q bytes
    sample_rate is None if it was only guessed during ingestion (never verified).
    """
    if job.file_type == "wav":
        data, sr = sf.read(job.storage_path)
        if data.ndim > 1:
            data = data[:, 0]  # take first channel if stereo
        return data.astype(np.float32), sr, False

    elif job.file_type == "iq":
        meta = job.ingestion_metadata or {}
        dtype_name = meta.get("dtype")
        sample_rate = meta.get("sample_rate")
        dtype = DTYPE_MAP.get(dtype_name)
        if dtype is None:
            raise ValueError(f"Cannot load IQ signal: unrecognized dtype '{dtype_name}'")

        raw = np.fromfile(job.storage_path, dtype=dtype)
        iq = raw[0::2].astype(np.float32) + 1j * raw[1::2].astype(np.float32)
        return iq, sample_rate, True

    else:
        raise ValueError(f"Unsupported file_type: {job.file_type}")