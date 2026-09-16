"""
sync_words.py – Known sync-word pattern library.

Contains bit patterns for common framing sync words used in satellite,
aerospace, and military communication standards.
"""
import numpy as np

# Barker codes (used for frame sync, radar)
BARKER_7  = np.array([1, 1, 1, -1, -1, 1, -1], dtype=np.int8)
BARKER_11 = np.array([1, 1, 1, -1, -1, -1, 1, -1, -1, 1, -1], dtype=np.int8)
BARKER_13 = np.array([1, 1, 1, 1, 1, -1, -1, 1, 1, -1, 1, -1, 1], dtype=np.int8)

# CCSDS TM synchronization marker (ASM) – 32 bits
CCSDS_ASM = np.array(
    [0, 1, 0, 1, 1, 0, 1, 1,
     1, 1, 0, 0, 1, 1, 1, 0,
     0, 1, 0, 0, 0, 1, 0, 1,
     1, 0, 0, 0, 1, 1, 0, 0],
    dtype=np.int8,
)

# DVB-S2 SOF (Start of Frame) – 26 bits (pilot-free)
DVB_S2_SOF = np.array(
    [0, 1, 1, 0, 0, 1, 1, 1, 0, 0, 0, 1,
     1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1],
    dtype=np.int8,
)

# Lookup by name
SYNC_WORDS: dict[str, np.ndarray] = {
    "barker_7":  BARKER_7,
    "barker_11": BARKER_11,
    "barker_13": BARKER_13,
    "ccsds_asm": CCSDS_ASM,
    "dvb_s2_sof": DVB_S2_SOF,
}


def get_sync_word(name: str) -> np.ndarray:
    """Return a sync-word array by name.

    Args:
        name: Key from SYNC_WORDS dict (case-insensitive).

    Returns:
        Sync-word as int8 numpy array (+1 / -1 or 0 / 1).

    Raises:
        KeyError: if the name is not found.
    """
    return SYNC_WORDS[name.lower()]
