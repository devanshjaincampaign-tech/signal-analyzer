# app/routers/analysis.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from app.db import get_db
from app.models import Job, AnalysisResult
from app.analysis.loader import load_signal
from app.analysis.features import extract_spectral_features, compute_spectrogram

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

    result = AnalysisResult(
        job_id=job.id,
        stage="features",
        result_data={**spectral, "spectrogram": spectrogram},
    )
    db.add(result)
    await db.commit()

    return {"job_id": str(job.id), "stage": "features", "result": spectral}


@router.get("/jobs/{job_id}/results")
async def get_results(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AnalysisResult).where(AnalysisResult.job_id == job_id).order_by(AnalysisResult.created_at)
    )
    rows = result.scalars().all()
    if not rows:
        raise HTTPException(404, "No analysis results found for this job")
    return [{"stage": r.stage, "result_data": r.result_data, "created_at": str(r.created_at)} for r in rows]