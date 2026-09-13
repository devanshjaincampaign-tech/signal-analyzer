# app/ingestion/iq_reader.py
import os, json
import numpy as np

# dtype object used to actually read the bytes
DTYPE_MAP = {
    "cs8": np.int8, "cu8": np.uint8,
    "ci16_le": np.int16, "cf32_le": np.float32,
}

# canonical name stored in metadata — MUST match the names _guess_format
# produces ("int8", "uint8", "int16", "float32"), so loader.py's DTYPE_MAP
# understands a dtype string regardless of which path (sidecar vs guessed)
# produced it.
CANONICAL_NAME_MAP = {
    "cs8": "int8", "cu8": "uint8",
    "ci16_le": "int16", "cf32_le": "float32",
}

def read_iq(path: str) -> dict:
    sidecar = path.rsplit(".", 1)[0] + ".sigmf-meta"
    if os.path.exists(sidecar):
        return _read_with_sigmf(path, sidecar)
    return _guess_format(path)

def _read_with_sigmf(path: str, sidecar: str) -> dict:
    with open(sidecar, encoding="utf-8") as f:
        meta = json.load(f)
    try:
        global_info = meta["global"]
        dtype_str = global_info["core:datatype"]
        sample_rate = global_info["core:sample_rate"]
    except (KeyError, TypeError) as exc:
        raise ValueError("SigMF sidecar is missing required global metadata") from exc

    dtype = DTYPE_MAP.get(dtype_str)
    canonical_name = CANONICAL_NAME_MAP.get(dtype_str)
    if dtype is None or canonical_name is None:
        raise ValueError(f"Unsupported SigMF datatype: {dtype_str}")

    raw = np.fromfile(path, dtype=dtype)
    if len(raw) == 0 or len(raw) % 2:
        raise ValueError("IQ file must contain a non-empty even number of interleaved samples")
    iq = raw[0::2].astype(np.float32) + 1j * raw[1::2].astype(np.float32)
    return {
        "sample_rate": sample_rate,
        "num_samples": len(iq),
        "dtype": canonical_name,   # <-- "float32", not "cf32_le"
        "source": "sigmf",
    }

def _guess_format(path: str) -> dict:
    file_size = os.path.getsize(path)
    if file_size == 0:
        raise ValueError("IQ file is empty")
    candidates = [("int16", 2), ("float32", 4), ("int8", 1)]
    for name, itemsize in candidates:
        if file_size % (itemsize * 2) == 0:
            dtype = np.dtype(name)
            raw = np.fromfile(path, dtype=dtype)
            iq = raw[0::2].astype(np.float32) + 1j * raw[1::2].astype(np.float32)
            if np.isfinite(iq).all():
                return {
                    "sample_rate": None,
                    "num_samples": len(iq),
                    "dtype": name,
                    "source": "guessed",
                    "warning": "No SigMF sidecar found; sample_rate unknown, format guessed",
                }
    raise ValueError("Could not determine a valid IQ format for this file")