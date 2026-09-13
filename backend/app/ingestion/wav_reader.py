# app/ingestion/wav_reader.py
import soundfile as sf

def read_wav(path: str) -> dict:
    info = sf.info(path)
    data, sample_rate = sf.read(path)
    return {
        "sample_rate": sample_rate,
        "num_samples": len(data),
        "channels": info.channels,
        "subtype": info.subtype,      # e.g. 'PCM_16'
        "duration_sec": info.duration,
    }