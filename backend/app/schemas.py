"""
schemas.py – Pydantic models for API requests, responses, and signal data contracts.
"""
from __future__ import annotations

from typing import Any, Optional, List, Dict
from pydantic import BaseModel, Field
import uuid


# ── Job Schemas ───────────────────────────────────────────────────────────────

class JobResponse(BaseModel):
    job_id: str
    filename: Optional[str] = None
    file_type: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# ── Direct Analysis Request/Response Schemas ──────────────────────────────────

class DirectAnalysisRequest(BaseModel):
    file_path: Optional[str] = None
    sample_rate_override: Optional[float] = None
    modulation_override: Optional[str] = None
    symbol_rate_override: Optional[float] = None
    fec_override: Optional[str] = None
    interleave_override: Optional[int] = None


class SpectralFeatures(BaseModel):
    center_frequency_hz: float
    bandwidth_hz: float
    noise_floor_db: float
    peak_power_db: float
    sample_rate_used: float
    sample_rate_was_assumed: bool


class SpectrogramData(BaseModel):
    freq_bins: List[float]
    time_bins: List[float]
    power_db_matrix: List[List[float]]


class SymbolRateResult(BaseModel):
    symbol_rate_hz: Optional[float] = None
    samples_per_symbol: Optional[int] = None
    confidence: float = 0.0
    method: str = "autocorrelation_transitions"
    note: Optional[str] = None


class ClassificationCandidate(BaseModel):
    label: str
    score: float


class ClassificationResult(BaseModel):
    modulation: Optional[str] = None
    confidence: float = 0.0
    candidates: List[ClassificationCandidate] = Field(default_factory=list)
    reason: Optional[str] = None


class DemodResult(BaseModel):
    success: bool
    type: Optional[str] = None
    bits: Optional[List[int]] = None
    num_bits: Optional[int] = None
    modulation: Optional[str] = None
    i_levels: Optional[List[float]] = None
    q_levels: Optional[List[float]] = None
    reason: Optional[str] = None


class InterleavingResult(BaseModel):
    success: bool
    pattern: Optional[str] = None
    best_params: Optional[Dict[str, Any]] = None
    best_entropy: Optional[float] = None
    baseline_entropy: Optional[float] = None
    entropy_improvement: Optional[float] = None
    confidence: float = 0.0
    reason: Optional[str] = None


class FecResult(BaseModel):
    success: bool
    method: Optional[str] = None
    input_bits: Optional[int] = None
    decoded_bits: Optional[List[int]] = None
    decoded_count: Optional[int] = None
    errors_corrected: Optional[int] = None
    reason: Optional[str] = None


class CorrelationHit(BaseModel):
    offset: int
    errors: Optional[int] = None
    score: Optional[float] = None


class CorrelationResult(BaseModel):
    success: bool
    sync_words_searched: List[str] = Field(default_factory=list)
    hits: Dict[str, List[CorrelationHit]] = Field(default_factory=dict)
    total_hits: int = 0
    reason: Optional[str] = None


class AnalysisResponse(BaseModel):
    job_id: Optional[str] = None
    status: str = "success"
    features: Optional[Dict[str, Any]] = None
    spectrogram: Optional[Dict[str, Any]] = None
    symbol_rate: Optional[Dict[str, Any]] = None
    classification: Optional[Dict[str, Any]] = None
    demod: Optional[Dict[str, Any]] = None
    interleaving: Optional[Dict[str, Any]] = None
    fec: Optional[Dict[str, Any]] = None
    correlation: Optional[Dict[str, Any]] = None
    psd: Optional[List[float]] = None
    freqs: Optional[List[float]] = None
    iq_samples: Optional[Dict[str, List[float]]] = None
