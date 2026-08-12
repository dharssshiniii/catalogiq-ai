import csv
import json
import os
from datetime import datetime
from time import perf_counter
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import CatalogIQError
from app.database import engine, get_db
from app.models.database import DatasetJob, EnrichedField, EvidenceChunk, ProductRecord, ReviewDecision, SourceRecord
from app.models.schemas import BatchRequest, EnrichmentResult, ProductInput, ReviewAction, SourceRequest
from app.services.csv_utils import profile_frame, read_csv_bytes, sanitize_filename, validate_required_columns
from app.services.enrichment import DemoEnrichmentService
from app.services.providers import GeminiProvider, select_provider
from app.services.retrieval import SafeWebRetriever
from app.services.pdf_extraction import extract_pdf
from app.services.evidence_index import chunk_text
from app.services.workflow import apply_review, export_product, persist_enrichment, product_payload, run_demo_batch, schema_columns

router = APIRouter()
settings = get_settings()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@router.get("/api/v1/status")
def status() -> dict[str, object]:
    database_ok = False
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
        database_ok = True
    except Exception:
        pass
    gemini = GeminiProvider(settings.mode, settings.gemini_api_key, settings.gemini_model)
    return {"mode": settings.mode, "database": {"available": database_ok, "dialect": engine.dialect.name, "persistence": "EPHEMERAL_SERVERLESS" if os.getenv("VERCEL") else "LOCAL_DURABLE"}, "providers": {"demo": True, "gemini": gemini.available, "selected": "gemini" if gemini.available else "demo" if settings.mode == "DEMO" else "unavailable"}, "limits": {"live_batch_cap": settings.live_batch_cap}}


@router.post("/api/v1/datasets/profile")
async def profile_dataset(file: UploadFile = File(...), session: Session = Depends(get_db)) -> dict[str, object]:
    started = perf_counter()
    filename = sanitize_filename(file.filename or "upload.csv")
    if Path(filename).suffix.lower() != ".csv":
        raise CatalogIQError("INVALID_EXTENSION", "Only .csv uploads are accepted.")
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise CatalogIQError("UPLOAD_TOO_LARGE", f"CSV exceeds the {settings.max_upload_bytes} byte limit.", 413)
    frame = read_csv_bytes(content)
    validate_required_columns(frame, settings.required_columns)
    profile = profile_frame(frame)
    duration = int((perf_counter() - started) * 1000)
    session.add(DatasetJob(filename=filename, status="PROFILED", row_count=int(profile["row_count"]), placeholder_count=int(profile["placeholder_count"]), duplicate_count=int(profile["duplicate_count"]), processing_duration_ms=duration))
    session.commit()
    return {"filename": filename, **profile, "processing_duration_ms": duration}


@router.get("/api/v1/schema/output")
def output_schema() -> dict[str, object]:
    schema_path = Path(__file__).parents[1] / "output_schema.csv"
    with schema_path.open(encoding="utf-8-sig", newline="") as handle:
        columns = next(csv.reader(handle))
    return {"column_count": len(columns), "columns": columns}


@router.post("/api/v1/enrich/demo", response_model=EnrichmentResult)
def enrich_demo(product: ProductInput) -> EnrichmentResult:
    return DemoEnrichmentService().enrich(product)


@router.get("/api/v1/demo/products")
def demo_products() -> list[dict[str, str]]:
    path = Path(__file__).parents[3] / "data" / "demo" / "products.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


@router.post("/api/v1/enrich/demo/persist")
def enrich_demo_persist(product: ProductInput, session: Session = Depends(get_db)) -> dict[str, object]:
    record = persist_enrichment(session, DemoEnrichmentService().enrich(product), product)
    return product_payload(record)


@router.post("/api/v1/sources/retrieve")
def retrieve_source(request: SourceRequest, session: Session = Depends(get_db)) -> dict[str, object]:
    cached = session.scalar(select(SourceRecord).where(SourceRecord.url == request.url, SourceRecord.extracted_text.is_not(None)).order_by(SourceRecord.id.desc()))
    if cached:
        return {"ok": True, "url": cached.url, "text": cached.extracted_text, "content_type": cached.content_type, "status": cached.http_status, "content_hash": cached.content_hash, "retrieved_at": cached.retrieved_at.isoformat() if cached.retrieved_at else None, "policy": {"url": cached.url, "domain": cached.domain, "source_type": cached.source_type, "allowed": True, "reason_code": cached.policy_decision, "trust_weight": cached.trust_weight}, "error_code": None, "cached": True}
    result = SafeWebRetriever(timeout=settings.retrieval_timeout_seconds, max_bytes=settings.max_source_bytes).retrieve(request.url, request.manufacturer_domains)
    payload = {key: value for key, value in result.__dict__.items() if key != "metadata"}
    payload["policy"] = result.policy.model_dump() if result.policy else None
    if result.ok and result.content_type == "application/pdf":
        pdf = extract_pdf(result.metadata.get("raw_content", b""), settings.max_source_bytes, settings.max_pdf_pages)
        payload["document"] = pdf.__dict__
        if pdf.ok:
            result.text = "\n".join(str(page["text"]) for page in pdf.pages)
    decision = result.policy
    source = SourceRecord(url=result.url, domain=decision.domain if decision else "", source_type=decision.source_type.value if decision else "UNTRUSTED", policy_decision=decision.reason_code if decision else (result.error_code or "UNKNOWN"), trust_weight=decision.trust_weight if decision else 0, retrieved_at=datetime.fromisoformat(result.retrieved_at) if result.retrieved_at else None, content_type=result.content_type, http_status=result.status, content_hash=result.content_hash, extracted_text=result.text if result.ok else None)
    session.add(source)
    if result.ok and result.text and result.content_hash:
        for chunk in chunk_text(result.text, f"source:{result.content_hash[:12]}", result.url, result.content_hash, decision.trust_weight if decision else 0):
            session.add(EvidenceChunk(source_identifier=chunk.source_identifier, url=chunk.url, page_number=chunk.page_number, heading=chunk.heading, text=chunk.text, source_trust=chunk.source_trust, content_hash=chunk.content_hash))
    session.commit()
    return payload


@router.get("/api/v1/jobs")
def list_jobs(session: Session = Depends(get_db)) -> list[dict[str, object]]:
    jobs = session.scalars(select(DatasetJob).order_by(DatasetJob.created_at.desc())).all()
    return [{"id": job.id, "filename": job.filename, "status": job.status, "row_count": job.row_count, "processed_count": job.processed_count, "failed_count": job.failed_count, "cancelled": job.cancelled} for job in jobs]


@router.post("/api/v1/jobs")
def create_job(request: BatchRequest, session: Session = Depends(get_db)) -> dict[str, object]:
    cap = 1000 if settings.mode == "DEMO" else settings.live_batch_cap
    if request.limit > cap:
        raise CatalogIQError("BATCH_LIMIT_EXCEEDED", f"Mode {settings.mode} permits at most {cap} rows.")
    job = run_demo_batch(session, request.rows, request.limit, cap)
    return {"id": job.id, "status": job.status, "row_count": job.row_count, "processed_count": job.processed_count, "failed_count": job.failed_count}


@router.get("/api/v1/jobs/{job_id}")
def get_job(job_id: int, session: Session = Depends(get_db)) -> dict[str, object]:
    job = session.get(DatasetJob, job_id)
    if not job: raise CatalogIQError("NOT_FOUND", "Job not found.", 404)
    return {"id": job.id, "status": job.status, "row_count": job.row_count, "processed_count": job.processed_count, "failed_count": job.failed_count, "cancelled": job.cancelled, "products": [product.id for product in job.products]}


@router.post("/api/v1/jobs/{job_id}/cancel")
def cancel_job(job_id: int, session: Session = Depends(get_db)) -> dict[str, object]:
    job = session.get(DatasetJob, job_id)
    if not job: raise CatalogIQError("NOT_FOUND", "Job not found.", 404)
    job.cancelled, job.status = True, "CANCELLED"
    session.commit()
    return {"id": job.id, "status": job.status}


@router.get("/api/v1/products/{product_id}")
def get_product(product_id: int, session: Session = Depends(get_db)) -> dict[str, object]:
    product = session.get(ProductRecord, product_id)
    if not product: raise CatalogIQError("NOT_FOUND", "Product not found.", 404)
    return product_payload(product)


@router.post("/api/v1/fields/{field_id}/review")
def review_field(field_id: int, action: ReviewAction, session: Session = Depends(get_db)) -> dict[str, object]:
    field = session.get(EnrichedField, field_id)
    if not field: raise CatalogIQError("NOT_FOUND", "Field not found.", 404)
    try: apply_review(session, field, action.action, action.reviewer, action.value, action.note, action.reason)
    except ValueError as exc: raise CatalogIQError("INVALID_REVIEW_ACTION", str(exc)) from exc
    return product_payload(field.product)


@router.post("/api/v1/products/{product_id}/review")
def review_product(product_id: int, action: ReviewAction, session: Session = Depends(get_db)) -> dict[str, object]:
    product = session.get(ProductRecord, product_id)
    if not product: raise CatalogIQError("NOT_FOUND", "Product not found.", 404)
    normalized = action.action.upper()
    if normalized not in {"APPROVE", "REJECT"}: raise CatalogIQError("INVALID_REVIEW_ACTION", "Product action must be APPROVE or REJECT.")
    product.review_status = "APPROVED" if normalized == "APPROVE" else "REJECTED"
    session.add(ReviewDecision(product_id=product.id, enriched_field_id=product.fields[0].id if product.fields else None, decision=normalized, reviewer=action.reviewer, notes=action.note or action.reason))
    session.commit()
    return product_payload(product)


@router.get("/api/v1/products/{product_id}/export.csv")
def export_csv(product_id: int, session: Session = Depends(get_db)) -> Response:
    product = session.get(ProductRecord, product_id)
    if not product: raise CatalogIQError("NOT_FOUND", "Product not found.", 404)
    csv_text, _ = export_product(product, schema_columns())
    return Response(csv_text, media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="catalogiq-{product_id}.csv"'})


@router.get("/api/v1/products/{product_id}/audit.json")
def export_audit(product_id: int, session: Session = Depends(get_db)) -> dict[str, object]:
    product = session.get(ProductRecord, product_id)
    if not product: raise CatalogIQError("NOT_FOUND", "Product not found.", 404)
    _, audit = export_product(product, schema_columns())
    field_ids = [field.id for field in product.fields]
    decisions = session.scalars(select(ReviewDecision).where((ReviewDecision.product_id == product.id) | (ReviewDecision.enriched_field_id.in_(field_ids)))).all()
    audit["review_history"] = [{"scope": "product" if item.product_id else "field", "decision": item.decision, "reviewer": item.reviewer, "notes": item.notes, "created_at": item.created_at.isoformat()} for item in decisions]
    return audit


@router.get("/api/v1/quality")
def quality(session: Session = Depends(get_db)) -> dict[str, object]:
    fields = session.scalars(select(EnrichedField)).all()
    total = len(fields)
    evidence_count = sum(bool(field.evidence) for field in fields)
    valid = sum(field.validation_status == "VALID" for field in fields)
    validated = sum(field.review_status in {"APPROVED", "AUTO_ACCEPTED"} for field in fields)
    rejected_sources = len(session.scalars(select(SourceRecord).where(SourceRecord.trust_weight == 0)).all())
    latest_profile = session.scalar(select(DatasetJob).where(DatasetJob.status == "PROFILED").order_by(DatasetJob.created_at.desc()))
    return {"field_count": total, "input_row_count": latest_profile.row_count if latest_profile else None, "placeholder_count": latest_profile.placeholder_count if latest_profile else None, "duplicate_count": latest_profile.duplicate_count if latest_profile else None, "processing_duration_ms": latest_profile.processing_duration_ms if latest_profile else None, "evidence_coverage": round(evidence_count / total, 4) if total else None, "schema_valid_percentage": round(valid / total, 4) if total else None, "validated_field_percentage": round(validated / total, 4) if total else None, "conflict_count": sum(field.review_status == "CONFLICT" for field in fields), "human_review_count": sum(field.review_status == "NEEDS_REVIEW" for field in fields), "source_policy_rejection_count": rejected_sources, "automated_test_inventory": ["source policy and retrieval", "PDF and evidence", "normalization and confidence", "review and export integration", "frontend components", "Chromium judge journey"]}
