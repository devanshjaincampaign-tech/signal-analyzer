# app/routers/analysis.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from app.db import get_db
from app.models import Job, AnalysisResult
from app.analysis.loader import load_signal
from app.analysis.features import extract_spectral_features, compute_spectrogram
from app.analysis.symbol_rate import estimate_symbol_rate
from app.analysis.classifier import (
    classify_modulation,
    extract_classification_features,
)
from app.analysis.demod import demodulate
from app.analysis.interleaving import search_deinterleave

router = APIRouter()

@router.post("/jobs/{job_id}/analyze")
async def analyze_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != "validated":
        raise HTTPException(400, f"Job is not ready for analysis (status: {job.status})")

    try:
        sig, sample_rate, is_complex = load_signal(job)
    except Exception as e:
        raise HTTPException(500, f"Failed to load signal for analysis: {e}")

    spectral = extract_spectral_features(sig, sample_rate)
    spectrogram = compute_spectrogram(sig, spectral["sample_rate_used"])
    symbol_rate_result = estimate_symbol_rate(sig, spectral["sample_rate_used"])
    classification_features = extract_classification_features(sig)
    classification_result = classify_modulation(classification_features)
    demod_result = demodulate(
        sig,
        symbol_rate_result.get("samples_per_symbol"),
        classification_result.get("modulation"),
    )
    interleaving_result = {
        "success": False,
        "reason": "No bit-type demod output available",
    }
    if demod_result.get("success") and demod_result.get("type") == "bits":
        interleaving_result = search_deinterleave(demod_result["bits"])

    features_result = AnalysisResult(
        job_id=job.id,
        stage="features",
        result_data={**spectral, "spectrogram": spectrogram},
    )
    symbol_rate_row = AnalysisResult(
        job_id=job.id,
        stage="symbol_rate",
        result_data=symbol_rate_result,
    )
    classification_row = AnalysisResult(
        job_id=job.id,
        stage="classification",
        result_data=classification_result,
    )
    demod_row = AnalysisResult(
        job_id=job.id,
        stage="demod",
        result_data=demod_result,
    )
    interleaving_row = AnalysisResult(
        job_id=job.id,
        stage="interleaving",
        result_data=interleaving_result,
    )
    db.add_all(
        [
            features_result,
            symbol_rate_row,
            classification_row,
            demod_row,
            interleaving_row,
        ]
    )
    await db.commit()

    return {
        "job_id": str(job.id),
        "features": spectral,
        "symbol_rate": symbol_rate_result,
        "classification": classification_result,
        "demod": demod_result,
        "interleaving": interleaving_result,
    }


@router.get("/jobs/{job_id}/results")
async def get_results(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AnalysisResult).where(AnalysisResult.job_id == job_id).order_by(AnalysisResult.created_at)
    )
    rows = result.scalars().all()
    if not rows:
        raise HTTPException(404, "No analysis results found for this job")
    return [{"stage": r.stage, "result_data": r.result_data, "created_at": str(r.created_at)} for r in rows]