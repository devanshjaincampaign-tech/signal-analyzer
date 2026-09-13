# app/synth/generate_signals.py
import numpy as np

def generate_bpsk(num_bits=1000, sps=8, sample_rate=200_000):
    bits = np.random.randint(0, 2, num_bits)
    symbols = 2 * bits - 1  # map {0,1} -> {-1,+1}
    signal = np.repeat(symbols, sps).astype(np.complex64)
    noise = (np.random.randn(len(signal)) + 1j*np.random.randn(len(signal))) * 0.05
    return (signal + noise), sample_rate

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