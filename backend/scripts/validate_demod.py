import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.analysis.demod import demod_bpsk
from app.analysis.symbol_rate import estimate_symbol_rate
from app.synth.generate_signals import generate_bpsk


np.random.seed(42)
sig, sample_rate, true_bits = generate_bpsk(
    num_bits=200, sps=8, sample_rate=200_000
)
symbol_rate = estimate_symbol_rate(sig, sample_rate)
recovered_bits = demod_bpsk(sig, symbol_rate["samples_per_symbol"])

direct = sum(a == b for a, b in zip(true_bits, recovered_bits))
inverted = sum(a == 1 - b for a, b in zip(true_bits, recovered_bits))
print(f"Direct match rate: {direct}/{len(true_bits)} ({100 * direct / len(true_bits):.1f}%)")
print(
    f"Inverted match rate: {inverted}/{len(true_bits)} "
    f"({100 * inverted / len(true_bits):.1f}%)"
)
