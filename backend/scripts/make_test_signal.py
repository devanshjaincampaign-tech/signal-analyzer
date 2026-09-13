# backend/scripts/make_test_signal.py
# backend/scripts/make_test_signal.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.synth.generate_signals import generate_bpsk, save_iq
os.makedirs("storage_test", exist_ok=True)
iq, sr = generate_bpsk()
save_iq(iq, "storage_test/bpsk_test.iq", sr)
print("Wrote storage_test/bpsk_test.iq")