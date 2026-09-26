"""
analysis.py – FastAPI router for signal processing and analysis endpoints.
"""
from __future__ import annotations

import os
import uuid
import numpy as np
import soundfile as sf
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from scipy import signal as sp_signal

from app.db import get_db
from app.models import Job, AnalysisResult
from app.schemas import DirectAnalysisRequest, AnalysisResponse
from app.analysis.loader import load_signal, DTYPE_MAP
from app.analysis.features import extract_spectral_features, compute_spectrogram, _normalize_frequency_axis
from app.analysis.symbol_rate import estimate_symbol_rate
from app.analysis.classifier import classify_modulation, extract_classification_features
from app.analysis.demod import demodulate
from app.analysis.deinterleave.detector import detect_and_deinterleave
from app.analysis.interleaving import search_deinterleave
from app.analysis.fec.viterbi import viterbi_decode
from app.analysis.fec.reed_solomon import rs_decode
from app.analysis.fec.ldpc import ldpc_decode
from app.analysis.fec.concatenated import concatenated_decode
from app.correlate.correlator import cross_correlate, hamming_search
from app.correlate.sync_words import SYNC_WORDS
from app.ingestion.preprocessing import preprocess

router = APIRouter()


def _load_raw_file(path: str, sample_rate_override: float | None = None) -> tuple[np.ndarray, float, bool]:
    """Helper to directly load a .wav or .iq file by path."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    
    ext = path.rsplit(".", 1)[-1].lower()
    if ext == "wav":
        data, sr = sf.read(path)
        if data.ndim > 1:
            data = data[:, 0]
        final_sr = float(sample_rate_override if sample_rate_override and sample_rate_override > 0 else sr)
        return data.astype(np.float32), final_sr, False

    elif ext in ("iq", "sigmf-meta"):
        iq_path = path if ext == "iq" else path.rsplit(".", 1)[0] + ".iq"
        from app.ingestion.iq_reader import read_iq_samples
        iq, sr, _ = read_iq_samples(iq_path, sample_rate_override=sample_rate_override)
        return iq, sr, True

    else:
        raise ValueError(f"Unsupported extension: {ext}")


def _execute_full_pipeline(
    sig: np.ndarray,
    sample_rate: float | None,
    req: DirectAnalysisRequest | None = None,
) -> dict:
    """Execute the full end-to-end signal analysis pipeline."""
    # Preprocessing
    sig = preprocess(sig, remove_dc_offset=True, normalize=True)
    
    sr = (req.sample_rate_override if req and req.sample_rate_override else None) or sample_rate or 1_000_000.0
    is_complex = np.iscomplexobj(sig)

    # 1. Spectral Features & Raw PSD
    spectral = extract_spectral_features(sig, sr)
    spectrogram = compute_spectrogram(sig, sr)

    freqs, psd = sp_signal.welch(
        sig, fs=sr, nperseg=min(2048, len(sig)),
        return_onesided=not is_complex,
    )
    freqs, psd = _normalize_frequency_axis(freqs, psd, is_complex)
    psd_db = (10 * np.log10(psd + 1e-20)).tolist()

    # 2. Baseband Frequency Translation (DDC to 0 Hz DC)
    fc = float(spectral.get("center_frequency_hz", 0.0))
    if is_complex and abs(fc) > 1.0:
        n_pts = len(sig)
        n_arr = np.arange(n_pts, dtype=np.float64)
        sig_bb = (sig * np.exp(-1j * 2.0 * np.pi * (fc / sr) * n_arr)).astype(np.complex64)
    else:
        sig_bb = sig

    # 3. Symbol Rate
    symbol_rate_res = estimate_symbol_rate(sig_bb, sr)
    if req and req.symbol_rate_override:
        sps = max(1, int(round(sr / req.symbol_rate_override)))
        symbol_rate_res["symbol_rate_hz"] = req.symbol_rate_override
        symbol_rate_res["samples_per_symbol"] = sps
        symbol_rate_res["confidence"] = 1.0

    # 4. Modulation Classification
    classification_feat = extract_classification_features(sig_bb)
    classification_res = classify_modulation(classification_feat)
    if req and req.modulation_override and req.modulation_override != "Auto":
        classification_res["modulation"] = req.modulation_override
        classification_res["confidence"] = 1.0

    # 5. Demodulation
    mod_target = classification_res.get("modulation") or "PSK"
    sps_target = symbol_rate_res.get("samples_per_symbol") or 4
    demod_res = demodulate(sig_bb, sps_target, mod_target)

    # 6. De-interleaving
    interleaving_res: dict = {"success": False, "reason": "No demodulated bits available"}
    bits_stream = demod_res.get("bits") if demod_res.get("success") else None
    
    if bits_stream and len(bits_stream) >= 16:
        arr_bits = np.array(bits_stream, dtype=np.uint8)
        det_res = detect_and_deinterleave(arr_bits)
        if det_res.get("type"):
            interleaving_res = {
                "success": True,
                "pattern": det_res["type"],
                "best_params": {"depth": det_res["depth"], "width": det_res["width"]},
                "confidence": round(min(1.0, det_res["score"] / 5.0), 3),
                "bits": det_res["bits"].tolist() if isinstance(det_res["bits"], np.ndarray) else det_res["bits"],
            }
        else:
            interleaving_res = search_deinterleave(bits_stream)

    # 7. Forward Error Correction (FEC)
    fec_res: dict = {"success": False, "reason": "No bitstream available for FEC"}
    active_bits = (
        interleaving_res.get("bits")
        if interleaving_res.get("success") and interleaving_res.get("bits")
        else bits_stream
    )
    
    if active_bits and len(active_bits) >= 8:
        try:
            arr_bits = np.array(active_bits, dtype=np.uint8)
            fec_choice = (req.fec_override if req and req.fec_override else "Viterbi").lower()
            
            if "rs" in fec_choice or "reed" in fec_choice:
                # Reed-Solomon
                n_bytes = len(arr_bits) // 8
                byte_arr = np.packbits(arr_bits[:n_bytes * 8])
                dec_bytes, n_err = rs_decode(byte_arr)
                dec_bits = np.unpackbits(dec_bytes).tolist()
                fec_res = {
                    "success": True,
                    "method": "reed_solomon",
                    "input_bits": len(arr_bits),
                    "decoded_bits": dec_bits,
                    "decoded_count": len(dec_bits),
                    "errors_corrected": n_err,
                }
            elif "ldpc" in fec_choice:
                # LDPC
                soft = 1.0 - 2.0 * arr_bits.astype(np.float64)
                dec_bits = ldpc_decode(soft)
                fec_res = {
                    "success": True,
                    "method": "ldpc_min_sum",
                    "input_bits": len(arr_bits),
                    "decoded_bits": dec_bits.tolist(),
                    "decoded_count": len(dec_bits),
                }
            elif "concat" in fec_choice:
                # Concatenated RS + Viterbi
                soft = 1.0 - 2.0 * arr_bits.astype(np.float32)
                dec_bytes, info = concatenated_decode(soft)
                dec_bits = np.unpackbits(dec_bytes).tolist()
                fec_res = {
                    "success": True,
                    "method": "concatenated_rs_viterbi",
                    "input_bits": len(arr_bits),
                    "decoded_bits": dec_bits,
                    "decoded_count": len(dec_bits),
                    "errors_corrected": info.get("rs_errors_corrected", 0),
                }
            else:
                # Standard NASA/CCSDS Viterbi K=7 R=1/2
                soft = 1.0 - 2.0 * arr_bits.astype(np.float32)
                dec_bits = viterbi_decode(soft, soft=True)
                fec_res = {
                    "success": True,
                    "method": "viterbi_r12_k7",
                    "input_bits": len(arr_bits),
                    "decoded_bits": dec_bits.tolist(),
                    "decoded_count": len(dec_bits),
                }
        except Exception as exc:
            fec_res = {"success": False, "reason": str(exc)}

    # 8. Bit Stream Correlation & Sync Search
    corr_res: dict = {"success": False, "reason": "No bits available for correlation"}
    final_bits = (
        fec_res.get("decoded_bits")
        or active_bits
    )
    if final_bits and len(final_bits) >= 8:
        bitstream = np.array(final_bits, dtype=np.uint8)
        hits: dict[str, list] = {}
        for sw_name, sw_pattern in SYNC_WORDS.items():
            sw = ((sw_pattern + 1) // 2).astype(np.uint8)
            found = hamming_search(bitstream, sw, max_errors=1)
            if found:
                hits[sw_name] = found[:5]
        corr_res = {
            "success": True,
            "sync_words_searched": list(SYNC_WORDS.keys()),
            "hits": hits,
            "total_hits": sum(len(v) for v in hits.values()),
        }

    # 9. Subsample baseband I/Q at symbol centers for clean UI constellation plot
    sps = int(symbol_rate_res.get("samples_per_symbol") or 4)
    if is_complex and len(sig_bb) >= sps * 8:
        sym_pts = sig_bb[sps // 2 :: sps]
        decim = max(1, len(sym_pts) // 2048)
        sub_sig = sym_pts[::decim][:2048]
    else:
        decim = max(1, len(sig) // 2048)
        sub_sig = sig[::decim][:2048]

    return {
        "features": spectral,
        "spectrogram": spectrogram,
        "symbol_rate": symbol_rate_res,
        "classification": classification_res,
        "demod": demod_res,
        "interleaving": interleaving_res,
        "fec": fec_res,
        "correlation": corr_res,
        "psd": psd_db,
        "freqs": freqs.tolist(),
        "iq_samples": {
            "i": np.real(sub_sig).tolist(),
            "q": np.imag(sub_sig).tolist(),
        },
    }


# ── Direct Endpoints for GUI & Scripting ──────────────────────────────────────

@router.post("/analyze")
async def direct_analyze(req: DirectAnalysisRequest):
    """Direct analysis endpoint for GUI without database requirements."""
    if not req.file_path:
        raise HTTPException(400, "file_path is required")
    try:
        sig, sample_rate, _ = _load_raw_file(req.file_path)
        res = _execute_full_pipeline(sig, sample_rate, req)
        return {"status": "success", **res}
    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {e}")


# ── Database-Backed Job Analysis Endpoints ─────────────────────────────────────

@router.post("/jobs/{job_id}/analyze")
async def analyze_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Run pipeline on an ingested database Job."""
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != "validated":
        raise HTTPException(400, f"Job is not ready for analysis (status: {job.status})")

    try:
        sig, sample_rate, is_complex = load_signal(job)
    except Exception as e:
        raise HTTPException(500, f"Failed to load signal for analysis: {e}")

    results = _execute_full_pipeline(sig, sample_rate)

    rows = [
        AnalysisResult(job_id=job.id, stage="features",
                       result_data={**results["features"], "spectrogram": results["spectrogram"]}),
        AnalysisResult(job_id=job.id, stage="symbol_rate",    result_data=results["symbol_rate"]),
        AnalysisResult(job_id=job.id, stage="classification", result_data=results["classification"]),
        AnalysisResult(job_id=job.id, stage="demod",          result_data=results["demod"]),
        AnalysisResult(job_id=job.id, stage="interleaving",   result_data=results["interleaving"]),
        AnalysisResult(job_id=job.id, stage="fec",            result_data=results["fec"]),
        AnalysisResult(job_id=job.id, stage="correlation",    result_data=results["correlation"]),
    ]
    db.add_all(rows)
    await db.commit()

    return {"job_id": str(job.id), **results}


@router.get("/jobs/{job_id}/results")
async def get_results(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AnalysisResult)
        .where(AnalysisResult.job_id == job_id)
        .order_by(AnalysisResult.created_at)
    )
    rows = result.scalars().all()
    if not rows:
        raise HTTPException(404, "No analysis results found for this job")
    return [
        {"stage": r.stage, "result_data": r.result_data, "created_at": str(r.created_at)}
        for r in rows
    ]