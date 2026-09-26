"""
classifier.py – Modulation classification via ONNX model (primary) with
rule-based cumulant fallback.

ONNX model contract
-------------------
Input  : float32[1, 2048]  — first 1024 values = I samples,
                              last  1024 values = Q samples (flat, NOT interleaved)
Output : float32[1, N]     — raw logits for N modulation classes

Classes are loaded from  classes.json  (sibling to the model file).
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_HERE = Path(__file__).parent
_MODEL_PATH = _HERE / "best_model.onnx"
_CLASSES_PATH = _HERE / "classes.json"

# ---------------------------------------------------------------------------
# Lazy ONNX session (loaded once, thread-safe)
# ---------------------------------------------------------------------------
_session = None
_classes: list[str] = []
_onnx_lock = threading.Lock()
_onnx_available: bool | None = None   # None = not yet probed


def _try_load_onnx() -> bool:
    """Attempt to initialise the ONNX runtime session. Returns True on success."""
    global _session, _classes, _onnx_available
    with _onnx_lock:
        if _onnx_available is not None:
            return _onnx_available
        try:
            import onnxruntime as ort  # type: ignore
            if not _MODEL_PATH.exists():
                _onnx_available = False
                print("[classifier] ONNX model not found – using rule-based fallback.")
                return False
            # Check for external data file (model weights split across two files)
            _data_path = _MODEL_PATH.parent / (_MODEL_PATH.name + ".data")
            if not _data_path.exists():
                _onnx_available = False
                print(
                    f"[classifier] WARNING: ONNX model weights file missing!\n"
                    f"  Expected : {_data_path}\n"
                    f"  The model was exported with external data. Please place\n"
                    f"  'best_model.onnx.data' alongside 'best_model.onnx' in:\n"
                    f"  {_MODEL_PATH.parent}\n"
                    f"  Falling back to rule-based cumulant classifier."
                )
                return False
            opts = ort.SessionOptions()
            opts.inter_op_num_threads = 1
            opts.intra_op_num_threads = 1
            _session = ort.InferenceSession(
                str(_MODEL_PATH),
                sess_options=opts,
                providers=["CPUExecutionProvider"],
            )
            if _CLASSES_PATH.exists():
                with open(_CLASSES_PATH, "r") as fh:
                    _classes = json.load(fh)
            else:
                # Fallback generic labels
                _classes = [f"MOD_{i}" for i in range(64)]
            _onnx_available = True
            return True
        except Exception:
            _onnx_available = False
            return False


# ---------------------------------------------------------------------------
# Input preparation
# ---------------------------------------------------------------------------
_N_SAMPLES = 1024   # I samples + Q samples = 2048 total


def _prepare_onnx_input(sig: np.ndarray) -> np.ndarray:
    """
    Convert a complex IQ array to float32[1, 2, 1024] expected by the model.

    Model input: (batch=1, channels=2, length=1024)
      channel 0 → I (real)
      channel 1 → Q (imag)

    Steps
    -----
    1. Subsample / zero-pad to exactly 1024 complex samples.
    2. Normalise to unit RMS (prevents amplitude bias).
    3. Stack I and Q as 2-channel tensor → shape (1, 2, 1024) float32.
    """
    n = len(sig)
    if n >= _N_SAMPLES:
        # Uniform decimation keeps spectral structure intact
        step = n // _N_SAMPLES
        seg = sig[::step][:_N_SAMPLES]
    else:
        # Zero-pad (unlikely for real captures, but safe)
        seg = np.zeros(_N_SAMPLES, dtype=np.complex64)
        seg[:n] = sig[:n]

    # Normalise
    rms = np.sqrt(np.mean(np.abs(seg) ** 2)) + 1e-12
    seg = seg / rms

    # Shape: (1, 2, 1024)  —  channel 0 = I, channel 1 = Q
    i_ch = np.real(seg).astype(np.float32)   # (1024,)
    q_ch = np.imag(seg).astype(np.float32)   # (1024,)
    return np.stack([i_ch, q_ch])[np.newaxis, ...]   # (1, 2, 1024)


# ---------------------------------------------------------------------------
# ONNX inference
# ---------------------------------------------------------------------------

def _classify_onnx(sig: np.ndarray) -> dict:
    """Run ONNX inference and return a classification result dict."""
    inp = _prepare_onnx_input(sig)
    input_name = _session.get_inputs()[0].name
    outputs = _session.run(None, {input_name: inp})
    logits = np.array(outputs[0]).flatten()

    # Softmax
    logits -= logits.max()  # numerical stability
    probs = np.exp(logits)
    probs /= probs.sum()

    ranked_idx = np.argsort(probs)[::-1]
    top_idx = int(ranked_idx[0])
    top_label = _classes[top_idx] if top_idx < len(_classes) else f"CLASS_{top_idx}"
    top_conf = float(probs[top_idx])

    candidates = []
    for idx in ranked_idx[:5]:
        lbl = _classes[idx] if idx < len(_classes) else f"CLASS_{idx}"
        candidates.append({"label": lbl, "score": round(float(probs[idx]), 4)})

    return {
        "modulation": top_label,
        "confidence": round(top_conf, 4),
        "candidates": candidates,
        "method": "onnx",
        "model": _MODEL_PATH.name,
    }


# ---------------------------------------------------------------------------
# Rule-based fallback (original cumulant approach)
# ---------------------------------------------------------------------------

def _extract_rule_features(sig: np.ndarray) -> dict:
    envelope = np.abs(sig)
    envelope_norm = envelope / (np.mean(envelope) + 1e-12)
    phase = np.unwrap(np.angle(sig))
    inst_freq = np.diff(phase)

    m2 = np.mean(sig * np.conj(sig))
    m4 = np.mean((sig * np.conj(sig)) ** 2)
    c42 = float(np.abs(m4 - 2 * m2 ** 2))

    return {
        "applicable": True,
        "envelope_variance": round(float(np.var(envelope_norm)), 5),
        "inst_freq_variance": round(float(np.var(inst_freq)), 5),
        "c42_cumulant": round(c42, 5),
    }


def _classify_rule_based(features: dict) -> dict:
    env_var = features["envelope_variance"]
    freq_var = features["inst_freq_variance"]

    if env_var < 0.05:
        if freq_var < 0.3:
            scores = {"2FSK": 0.75, "BPSK": 0.15, "QPSK": 0.10}
        else:
            scores = {"BPSK": 0.60, "QPSK": 0.30, "2FSK": 0.10}
    elif env_var < 0.25:
        scores = {"QPSK": 0.55, "8PSK": 0.30, "16QAM": 0.15}
    else:
        scores = {"16QAM": 0.50, "64QAM": 0.35, "QPSK": 0.15}

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_label, top_conf = ranked[0]
    return {
        "modulation": top_label,
        "confidence": round(top_conf, 3),
        "candidates": [{"label": l, "score": round(s, 3)} for l, s in ranked],
        "method": "rule_based_cumulants",
        "features_used": features,
    }


# ---------------------------------------------------------------------------
# Public API (backward-compatible with existing pipeline calls)
# ---------------------------------------------------------------------------

def extract_classification_features(sig: np.ndarray) -> dict:
    """
    Return features dict for the given IQ signal.

    If ONNX is available, injects 'onnx_ready=True' so that
    classify_modulation() can short-circuit to ONNX inference.
    """
    if not np.iscomplexobj(sig):
        return {
            "applicable": False,
            "reason": (
                "Real-valued signal (e.g. demodulated audio); "
                "modulation classification applies to IQ captures"
            ),
        }
    if len(sig) == 0:
        return {"applicable": False, "reason": "Signal is empty"}

    feat = _extract_rule_features(sig)
    feat["onnx_ready"] = _try_load_onnx()
    feat["_sig_ref"] = sig          # pass-through for classify_modulation
    return feat


def classify_modulation(features: dict) -> dict:
    """
    Classify modulation scheme.

    Preference order:
    1. ONNX model (if available and signal has enough samples)
    2. Rule-based cumulant classifier (fallback)
    """
    if not features.get("applicable", False):
        return {
            "modulation": None,
            "confidence": 0.0,
            "candidates": [],
            "reason": features.get("reason"),
            "features_used": features,
        }

    sig = features.pop("_sig_ref", None)

    if features.get("onnx_ready") and sig is not None and len(sig) >= _N_SAMPLES:
        try:
            result = _classify_onnx(sig)
            result["features_used"] = {
                k: v for k, v in features.items() if k != "onnx_ready"
            }
            return result
        except Exception as exc:
            # ONNX inference failed – fall through to rule-based
            features["onnx_error"] = str(exc)

    # Fallback
    return _classify_rule_based(features)
