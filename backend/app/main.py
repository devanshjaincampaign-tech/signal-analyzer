from fastapi import FastAPI
from app.routers import jobs, analysis

app = FastAPI(title="Signal Analyzer API")
app.include_router(jobs.router)
app.include_router(analysis.router)

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {
        "name": app.title,
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
    }