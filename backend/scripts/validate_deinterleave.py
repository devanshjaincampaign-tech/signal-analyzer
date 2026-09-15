import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.analysis.demod import demod_bpsk
from app.analysis.interleaving import block_deinterleave, search_deinterleave
from app.analysis.symbol_rate import estimate_symbol_rate
from app.synth.generate_signals import generate_bpsk_interleaved


np.random.seed(1)
sig, sample_rate, true_bits, true_rows, true_cols = generate_bpsk_interleaved(
    rows=8, cols=8
)
symbol_rate = estimate_symbol_rate(sig, sample_rate)
recovered = demod_bpsk(sig, symbol_rate["samples_per_symbol"])
search = search_deinterleave(recovered)
print("Symbol rate found:", symbol_rate["samples_per_symbol"], "(expected 8)")
print(
    "Search result:",
    search.get("best_params"),
    "(expected:",
    {"rows": true_rows, "cols": true_cols},
    ")",
)
best = search["best_params"]
deinterleaved = block_deinterleave(recovered, best["rows"], best["cols"])
direct = sum(a == b for a, b in zip(true_bits, deinterleaved))
inverted = sum(a == 1 - b for a, b in zip(true_bits, deinterleaved))
print(f"Direct match rate: {direct}/{len(true_bits)} ({100 * direct / len(true_bits):.1f}%)")
print(
    f"Inverted match rate: {inverted}/{len(true_bits)} "
    f"({100 * inverted / len(true_bits):.1f}%)"
)
