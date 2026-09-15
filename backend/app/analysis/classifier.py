import numpy as np


def extract_classification_features(sig: np.ndarray) -> dict:
    """
    Compute rule-based features for complex IQ modulation classification.

    Real-valued input is treated as demodulated audio and is not classified.
    """
    if not np.iscomplexobj(sig):
        return {
            "applicable": False,
            "reason": (
                "Real-valued signal (e.g. demodulated audio); modulation "
                "classification applies to IQ captures"
            ),
        }
    if len(sig) == 0:
        return {"applicable": False, "reason": "Signal is empty"}

    envelope = np.abs(sig)
    envelope_norm = envelope / (np.mean(envelope) + 1e-12)
    phase = np.unwrap(np.angle(sig))
    inst_freq = np.diff(phase)

    m2 = np.mean(sig * np.conj(sig))
    m4 = np.mean((sig * np.conj(sig)) ** 2)
    c42 = np.abs(m4 - 2 * m2**2)

    return {
        "applicable": True,
        "envelope_variance": round(float(np.var(envelope_norm)), 5),
        "inst_freq_variance": round(float(np.var(inst_freq)), 5),
        "c42_cumulant": round(float(c42), 5),
    }


def classify_modulation(features: dict) -> dict:
    if not features.get("applicable", False):
        return {
            "modulation": None,
            "confidence": 0.0,
            "candidates": [],
            "reason": features.get("reason"),
            "features_used": features,
        }

    env_var = features["envelope_variance"]
    freq_var = features["inst_freq_variance"]

    if env_var < 0.05:
        # BPSK phase reversals create a much larger instantaneous-phase
        # variance than the small frequency steps in the generated 2-FSK.
        if freq_var < 0.3:
            scores = {"FSK": 0.75, "PSK": 0.20, "QAM": 0.05}
        else:
            scores = {"PSK": 0.75, "FSK": 0.20, "QAM": 0.05}
    else:
        scores = {"QAM": 0.70, "PSK": 0.20, "FSK": 0.10}

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    top_label, top_confidence = ranked[0]
    return {
        "modulation": top_label,
        "confidence": round(top_confidence, 3),
        "candidates": [
            {"label": label, "score": round(score, 3)}
            for label, score in ranked
        ],
        "features_used": features,
    }
