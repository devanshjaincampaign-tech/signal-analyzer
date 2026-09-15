# app/routers/jobs.py
from fastapi import APIRouter, UploadFile, Depends, HTTPException, File
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid, os
from app.db import get_db
from app.models import Job
from app.ingestion.sniffer import ingest_file

router = APIRouter()
STORAGE_DIR = "storage"


@router.get("/jobs")
async def list_jobs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).order_by(Job.created_at.desc()))
    jobs = result.scalars().all()
    return [
        {
            "job_id": str(job.id),
            "filename": job.original_filename,
            "file_type": job.file_type,
            "status": job.status,
            "error_message": job.error_message,
            "metadata": job.ingestion_metadata,
        }
        for job in jobs
    ]


@router.post("/jobs")
async def create_job(
    file: UploadFile = File(...),
    sidecar: Optional[UploadFile] = File(default=None),
    db: AsyncSession = Depends(get_db),
):
    filename = file.filename or ""
    if not filename.lower().endswith((".wav", ".iq")):
        raise HTTPException(400, "Only .wav or .iq files are supported")

    job_id = uuid.uuid4()
    ext = filename.rsplit(".", 1)[-1].lower()
    path = os.path.join(STORAGE_DIR, f"{job_id}.{ext}")

    os.makedirs(STORAGE_DIR, exist_ok=True)
    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(400, "Uploaded file is empty")
    with open(path, "wb") as output:
        output.write(contents)

    # NEW — save sidecar (if provided) with matching basename so iq_reader.py finds it
    if sidecar is not None and sidecar.filename:
        sidecar_path = os.path.join(STORAGE_DIR, f"{job_id}.sigmf-meta")
        sidecar_contents = await sidecar.read()
        with open(sidecar_path, "wb") as output:
            output.write(sidecar_contents)

    job = Job(id=job_id, original_filename=filename, file_type=ext,
              storage_path=path, status="uploaded")
    db.add(job)
    await db.commit()

    # Run ingestion synchronously in Phase 1 (no worker queue yet)
    try:
        metadata = ingest_file(path, ext)
        job.status = "validated"
        job.ingestion_metadata = metadata
    except Exception as e:
        job.status = "error"
        job.error_message = str(e)
    await db.commit()

    return {"job_id": str(job_id), "status": job.status}


@router.get("/jobs/{job_id}")
async def get_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return {
        "job_id": str(job.id),
        "status": job.status,
        "error_message": job.error_message,
        "metadata": job.ingestion_metadata,
    }