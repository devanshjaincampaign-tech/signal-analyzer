"""
test_correlate.py – Tests for sync-word correlator and Hamming search.
"""
import numpy as np
import pytest

from app.correlate.sync_words import get_sync_word, SYNC_WORDS
from app.correlate.correlator import cross_correlate, hamming_search


# ── sync_words ───────────────────────────────────────────────────────────────

def test_all_sync_words_accessible():
    for name in SYNC_WORDS:
        sw = get_sync_word(name)
        assert isinstance(sw, np.ndarray)
        assert len(sw) > 0


def test_get_sync_word_case_insensitive():
    sw1 = get_sync_word("BARKER_7")
    sw2 = get_sync_word("barker_7")
    np.testing.assert_array_equal(sw1, sw2)


def test_get_sync_word_unknown_raises():
    with pytest.raises(KeyError):
        get_sync_word("nonexistent_pattern")


# ── cross_correlate ──────────────────────────────────────────────────────────

def test_cross_correlate_finds_exact_match():
    sw = get_sync_word("barker_7").astype(float)
    bitstream = np.concatenate([np.zeros(20), sw, np.zeros(10)])
    hits = cross_correlate(bitstream, sw, threshold=len(sw) * 0.99)
    assert len(hits) >= 1
    assert hits[0]["offset"] == 20


def test_cross_correlate_no_match_below_threshold():
    sw = get_sync_word("barker_7").astype(float)
    bitstream = np.random.choice([-1.0, 1.0], size=100)
    hits = cross_correlate(bitstream, sw, threshold=len(sw) * 2.0)  # impossibly high
    assert len(hits) == 0


def test_cross_correlate_returns_sorted():
    sw = get_sync_word("barker_13").astype(float)
    bitstream = np.concatenate([sw, np.zeros(50), sw])
    hits = cross_correlate(bitstream, sw, threshold=10)
    scores = [h["score"] for h in hits]
    assert scores == sorted(scores, reverse=True)


# ── hamming_search ───────────────────────────────────────────────────────────

def test_hamming_search_exact():
    sw = np.array([1, 0, 1, 1, 0, 0, 1], dtype=np.uint8)
    bitstream = np.concatenate([np.zeros(5, dtype=np.uint8), sw, np.zeros(5, dtype=np.uint8)])
    hits = hamming_search(bitstream, sw, max_errors=0)
    assert len(hits) == 1
    assert hits[0]["offset"] == 5
    assert hits[0]["errors"] == 0


def test_hamming_search_one_error():
    sw = np.array([1, 0, 1, 1, 0], dtype=np.uint8)
    corrupted = np.array([1, 1, 1, 1, 0], dtype=np.uint8)  # 1 error at index 1
    bitstream = np.concatenate([np.zeros(3, dtype=np.uint8), corrupted])
    hits = hamming_search(bitstream, sw, max_errors=1)
    assert any(h["offset"] == 3 for h in hits)
