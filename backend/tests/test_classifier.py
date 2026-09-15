import numpy as np

from app.analysis.classifier import (
    classify_modulation,
    extract_classification_features,
)
from app.synth.generate_signals import generate_16qam, generate_bpsk, generate_fsk


def test_generated_modulations_are_classified_by_family():
    np.random.seed(7)
    cases = (
        (generate_bpsk()[:2], "PSK"),
        (generate_fsk(), "FSK"),
        (generate_16qam(), "QAM"),
    )

    for (signal, _), expected in cases:
        result = classify_modulation(extract_classification_features(signal))
        assert result["modulation"] == expected
        assert result["confidence"] > 0
        assert len(result["candidates"]) == 3


def test_real_signal_classification_is_not_applicable():
    features = extract_classification_features(np.ones(32, dtype=np.float32))
    result = classify_modulation(features)

    assert features["applicable"] is False
    assert result["modulation"] is None
    assert result["confidence"] == 0.0
