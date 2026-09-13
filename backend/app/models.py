# app/models.py
import uuid
from sqlalchemy import String, Text, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from sqlalchemy import ForeignKey

class Base(DeclarativeBase):
    pass

class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_filename: Mapped[str] = mapped_column(Text)
    file_type: Mapped[str] = mapped_column(String)
    storage_path: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="uploaded")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    ingestion_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[str] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[str] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"))
    stage: Mapped[str] = mapped_column(String)
    result_data: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[str] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())