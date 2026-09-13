# app/ingestion/sniffer.py
from app.ingestion.wav_reader import read_wav
from app.ingestion.iq_reader import read_iq

def ingest_file(path: str, ext: str) -> dict:
    if ext == "wav":
        return read_wav(path)
    elif ext == "iq":
        return read_iq(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")