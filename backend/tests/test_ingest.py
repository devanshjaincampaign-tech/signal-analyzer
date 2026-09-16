"""
test_ingest.py – Tests for ingestion pipeline (file loading, preprocessing, spectral).
"""
import numpy as np
import pytest

from app.ingestion.iq_reader import read_iq
from app.ingestion.wav_reader import read_wav
from app.ingestion.sniffer import sniff_format


# ── file-format sniffing ─────────────────────────────────────────────────────

def test_sniff_iq_extension():
    assert sniff_format("signal.iq") == "iq"


def test_sniff_wav_extension():
    assert sniff_format("audio.wav") == "wav"


def test_sniff_sigmf_extension():
    assert sniff_format("capture.sigmf-meta") == "sigmf"


def test_sniff_unknown_raises():
    with pytest.raises(ValueError):
        sniff_format("data.xyz")


# ── IQ reader ────────────────────────────────────────────────────────────────

def test_read_iq_returns_complex(tmp_path):
    """write float32 interleaved I/Q and confirm read_iq returns complex64."""
    iq_file = tmp_path / "test.iq"
    n = 256
    data = np.random.randn(n * 2).astype(np.float32)
    iq_file.write_bytes(data.tobytes())

    signal = read_iq(str(iq_file))
    assert signal.dtype == np.complex64
    assert len(signal) == n


def test_read_iq_values_correct(tmp_path):
    iq_file = tmp_path / "test.iq"
    i_vals = np.ones(4, dtype=np.float32)
    q_vals = np.zeros(4, dtype=np.float32)
    interleaved = np.empty(8, dtype=np.float32)
    interleaved[0::2] = i_vals
    interleaved[1::2] = q_vals
    iq_file.write_bytes(interleaved.tobytes())

    signal = read_iq(str(iq_file))
    np.testing.assert_allclose(signal.real, 1.0)
    np.testing.assert_allclose(signal.imag, 0.0)


# ── WAV reader ───────────────────────────────────────────────────────────────

def test_read_wav_returns_complex(tmp_path):
    import wave, struct
    wav_file = tmp_path / "test.wav"
    n = 128
    samples = [int(np.random.randint(-32768, 32767)) for _ in range(n * 2)]
    with wave.open(str(wav_file), "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        wf.writeframes(struct.pack(f"{n * 2}h", *samples))

    signal = read_wav(str(wav_file))
    assert np.iscomplexobj(signal)
    assert len(signal) == n
