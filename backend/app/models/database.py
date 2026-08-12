from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DatasetJob(Base):
    __tablename__ = "dataset_jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(40), default="PROFILED")
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    cancelled: Mapped[bool] = mapped_column(Boolean, default=False)
    placeholder_count: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0)
    processing_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    products: Mapped[list["ProductRecord"]] = relationship(back_populates="dataset_job")


class ProductRecord(Base):
    __tablename__ = "product_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_job_id: Mapped[int | None] = mapped_column(ForeignKey("dataset_jobs.id"))
    manufacturer_part_number: Mapped[str] = mapped_column(String(255))
    raw_data_json: Mapped[str] = mapped_column(Text)
    review_status: Mapped[str] = mapped_column(String(40), default="NEEDS_REVIEW")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    dataset_job: Mapped[DatasetJob | None] = relationship(back_populates="products")
    fields: Mapped[list["EnrichedField"]] = relationship(back_populates="product")


class EnrichedField(Base):
    __tablename__ = "enriched_fields"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product_records.id"))
    field_name: Mapped[str] = mapped_column(String(255))
    original_value: Mapped[str | None] = mapped_column(Text)
    generated_value: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    validation_status: Mapped[str] = mapped_column(String(40))
    review_status: Mapped[str] = mapped_column(String(40))
    reason_codes_json: Mapped[str] = mapped_column(Text, default="[]")
    candidates_json: Mapped[str] = mapped_column(Text, default="[]")
    product: Mapped[ProductRecord] = relationship(back_populates="fields")
    evidence: Mapped[list["EvidenceRecord"]] = relationship(back_populates="field")
    issues: Mapped[list["ValidationIssue"]] = relationship(back_populates="field")


class EvidenceRecord(Base):
    __tablename__ = "evidence_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    enriched_field_id: Mapped[int] = mapped_column(ForeignKey("enriched_fields.id"))
    excerpt: Mapped[str] = mapped_column(Text)
    source_identifier: Mapped[str] = mapped_column(String(500))
    extraction_method: Mapped[str] = mapped_column(String(80))
    field: Mapped[EnrichedField] = relationship(back_populates="evidence")


class ValidationIssue(Base):
    __tablename__ = "validation_issues"
    id: Mapped[int] = mapped_column(primary_key=True)
    enriched_field_id: Mapped[int | None] = mapped_column(ForeignKey("enriched_fields.id"))
    severity: Mapped[str] = mapped_column(String(30))
    code: Mapped[str] = mapped_column(String(80))
    message: Mapped[str] = mapped_column(Text)
    field: Mapped[EnrichedField | None] = relationship(back_populates="issues")


class ReviewDecision(Base):
    __tablename__ = "review_decisions"
    id: Mapped[int] = mapped_column(primary_key=True)
    enriched_field_id: Mapped[int | None] = mapped_column(ForeignKey("enriched_fields.id"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("product_records.id"))
    decision: Mapped[str] = mapped_column(String(40))
    reviewer: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SourceRecord(Base):
    __tablename__ = "source_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(2048), index=True)
    domain: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(50))
    policy_decision: Mapped[str] = mapped_column(String(80))
    trust_weight: Mapped[float] = mapped_column(Float, default=0)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime)
    content_type: Mapped[str | None] = mapped_column(String(120))
    http_status: Mapped[int | None] = mapped_column(Integer)
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    extracted_text: Mapped[str | None] = mapped_column(Text)


class EvidenceChunk(Base):
    __tablename__ = "evidence_chunks"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_identifier: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(2048))
    page_number: Mapped[int | None] = mapped_column(Integer)
    heading: Mapped[str | None] = mapped_column(String(500))
    text: Mapped[str] = mapped_column(Text)
    source_trust: Mapped[float] = mapped_column(Float)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
