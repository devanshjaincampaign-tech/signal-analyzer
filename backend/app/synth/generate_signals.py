# app/synth/generate_signals.py
import numpy as np
from app.analysis.interleaving import block_interleave

def generate_bpsk(num_bits=1000, sps=8, sample_rate=200_000):
    bits = np.random.randint(0, 2, num_bits)
    symbols = 2 * bits - 1  # map {0,1} -> {-1,+1}
    signal = np.repeat(symbols, sps).astype(np.complex64)
    noise = (np.random.randn(len(signal)) + 1j*np.random.randn(len(signal))) * 0.05
    return (signal + noise), sample_rate, bits.tolist()


def generate_fsk(num_bits=1000, sps=8, sample_rate=200_000, freq_dev=5000):
    bits = np.random.randint(0, 2, num_bits)
    t = np.arange(sps) / sample_rate
    signal = np.concatenate([
        np.exp(1j * 2 * np.pi * (freq_dev if bit else -freq_dev) * t)
        for bit in bits
    ]).astype(np.complex64)
    noise = (np.random.randn(len(signal)) + 1j * np.random.randn(len(signal))) * 0.05
    return signal + noise, sample_rate


def generate_16qam(num_symbols=1000, sps=8, sample_rate=200_000):
    levels = np.array([-3, -1, 1, 3])
    i_vals = np.random.choice(levels, num_symbols)
    q_vals = np.random.choice(levels, num_symbols)
    symbols = (i_vals + 1j * q_vals) / 3.0
    signal = np.repeat(symbols, sps).astype(np.complex64)
    noise = (np.random.randn(len(signal)) + 1j * np.random.randn(len(signal))) * 0.05
    return signal + noise, sample_rate


def generate_bpsk_interleaved(
    message="HELLO WORLD! " * 8,
    sps=8,
    sample_rate=200_000,
    rows=8,
    cols=8,
):
    bits = []
    for char in message:
        bits.extend(int(bit) for bit in format(ord(char), "08b"))
    bits = bits[: rows * cols]
    interleaved_bits = block_interleave(bits, rows, cols)
    symbols = [2 * bit - 1 for bit in interleaved_bits]
    signal = np.repeat(symbols, sps).astype(np.complex64)
    noise = (np.random.randn(len(signal)) + 1j * np.random.randn(len(signal))) * 0.03
    return signal + noise, sample_rate, bits, rows, cols


def save_iq(iq: np.ndarray, path: str, sample_rate: int):
    interleaved = np.empty(len(iq) * 2, dtype=np.float32)
    interleaved[0::2] = iq.real
    interleaved[1::2] = iq.imag
    interleaved.tofile(path)
    # write matching SigMF sidecar
    import json
    meta = {"global": {"core:datatype": "cf32_le", "core:sample_rate": sample_rate}}
    with open(path.rsplit(".", 1)[0] + ".sigmf-meta", "w") as f:
        json.dump(meta, f)