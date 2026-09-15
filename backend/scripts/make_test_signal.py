# backend/scripts/make_test_signal.py
# backend/scripts/make_test_signal.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.synth.generate_signals import (
    generate_16qam,
    generate_bpsk,
    generate_bpsk_interleaved,
    generate_fsk,
    save_iq,
)
os.makedirs("storage_test", exist_ok=True)

for name, generator in (
    ("bpsk", generate_bpsk),
    ("fsk", generate_fsk),
    ("16qam", generate_16qam),
):
    generated = generator()
    iq, sr = generated[:2]
    path = f"storage_test/{name}_test.iq"
    save_iq(iq, path, sr)
    print(f"Wrote {path}")

iq, sr, _, _, _ = generate_bpsk_interleaved()
save_iq(iq, "storage_test/bpsk_interleaved_test.iq", sr)
print("Wrote storage_test/bpsk_interleaved_test.iq")