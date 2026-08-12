import csv
import io
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.database import DatasetJob, EnrichedField, EvidenceRecord, ProductRecord, ReviewDecision, ValidationIssue
from app.models.schemas import EnrichmentResult, ProductInput
from app.services.csv_utils import escape_csv_formula
from app.services.descriptions import build_descriptions
from app.services.enrichment import DemoEnrichmentService


def persist_enrichment(session: Session, result: EnrichmentResult, raw: ProductInput, job: DatasetJob | None = None) -> ProductRecord:
    product = ProductRecord(dataset_job=job, manufacturer_part_number=result.product_key, raw_data_json=raw.model_dump_json(), review_status=result.review_status.value)
    session.add(product)
    session.flush()
    for item in result.fields:
        field = EnrichedField(product=product, field_name=item.field_name, original_value=item.original_value, generated_value=item.generated_value, confidence=item.confidence, validation_status=item.validation_status.value, review_status=item.review_status.value, reason_codes_json=json.dumps(item.reason_codes), candidates_json=json.dumps(item.candidates))
        session.add(field)
        session.flush()
        for evidence in item.evidence:
            session.add(EvidenceRecord(field=field, excerpt=evidence.excerpt, source_identifier=evidence.source_identifier, extraction_method=evidence.extraction_method))
    fields_by_name = {field.field_name: field for field in product.fields}
    for issue in result.validation_issues:
        session.add(ValidationIssue(field=fields_by_name.get(issue.field_name or ""), severity=issue.severity, code=issue.code, message=issue.message))
    session.commit()
    session.refresh(product)
    return product


def product_payload(product: ProductRecord) -> dict[str, object]:
    return {"id": product.id, "manufacturer_part_number": product.manufacturer_part_number, "review_status": product.review_status, "fields": [{"id": field.id, "field_name": field.field_name, "original_value": field.original_value, "generated_value": field.generated_value, "confidence": field.confidence, "validation_status": field.validation_status, "review_status": field.review_status, "reason_codes": json.loads(field.reason_codes_json or "[]"), "candidates": json.loads(field.candidates_json or "[]"), "evidence": [{"excerpt": ev.excerpt, "source_identifier": ev.source_identifier, "extraction_method": ev.extraction_method} for ev in field.evidence], "validation_issues": [{"severity": issue.severity, "code": issue.code, "message": issue.message} for issue in field.issues]} for field in product.fields]}


def rebuild_product_descriptions(product: ProductRecord) -> None:
    mapping = {
        field.field_name: field.generated_value
        for field in product.fields
        if field.generated_value and field.review_status != "REJECTED"
    }
    attrs = {
        "brand": mapping.get("MANUFACTURER_NAME", mapping.get("BRAND_NAME", "")),
        "series": mapping.get("TRADE_NAME", ""),
        "product_name": mapping.get("Product Name", ""),
        "size": mapping.get("ATTRIBUTE_VALUE 6", ""),
        "colour": mapping.get("ATTRIBUTE_VALUE 2", ""),
        "sound_level": mapping.get("ATTRIBUTE_VALUE 10", ""),
        "features": "|".join(
            value for name, value in sorted(mapping.items()) if name.startswith("ITEM_FEATURES_")
        ),
    }
    descriptions = build_descriptions(attrs)
    names = {
        "MOBILE_DESC": descriptions.mobile,
        "INVOICE_DESC": descriptions.invoice,
        "SHORT_DESC": descriptions.short,
        "RETAIL_DESC": descriptions.retail,
        "MARKETING_DESCRIPTION": descriptions.long,
    }
    for field in product.fields:
        if field.field_name.startswith("LONG_DESC"):
            field.generated_value = descriptions.long
        elif field.field_name in names:
            field.generated_value = names[field.field_name]


def apply_review(session: Session, field: EnrichedField, action: str, reviewer: str, value: str | None, note: str | None, reason: str | None) -> None:
    normalized = action.upper()
    if normalized == "APPROVE":
        field.review_status = "APPROVED"
    elif normalized == "CORRECT":
        if value is None:
            raise ValueError("Correction value is required")
        field.generated_value, field.review_status = value, "APPROVED"
        rebuild_product_descriptions(field.product)
    elif normalized == "REJECT":
        field.review_status = "REJECTED"
    else:
        raise ValueError("Unsupported review action")
    session.add(ReviewDecision(enriched_field_id=field.id, decision=normalized, reviewer=reviewer, notes=note or reason))
    session.commit()


def export_product(product: ProductRecord, columns: list[str]) -> tuple[str, dict[str, object]]:
    values = {field.field_name: field.generated_value for field in product.fields if field.review_status != "REJECTED" and field.generated_value is not None}
    values.setdefault("Mfg_Part_Num", product.manufacturer_part_number)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerow({column: escape_csv_formula(values.get(column, "")) for column in columns})
    field_payload = product_payload(product)["fields"]
    audit = {"product_id": product.id, "review_status": product.review_status, "supported_populated_fields": sorted(values), "fields": field_payload, "conflicts": [field for field in field_payload if field["review_status"] == "CONFLICT"], "validation_issues": [issue for field in field_payload for issue in field["validation_issues"]], "exported_at": datetime.utcnow().isoformat() + "Z"}
    return buffer.getvalue(), audit


def run_demo_batch(session: Session, rows: list[ProductInput], limit: int, cap: int) -> DatasetJob:
    bounded = rows[: min(limit, cap)]
    job = DatasetJob(filename="api-batch", status="RUNNING", row_count=len(bounded))
    session.add(job)
    session.commit()
    service = DemoEnrichmentService()
    for row in bounded:
        if job.cancelled:
            job.status = "CANCELLED"
            break
        try:
            persist_enrichment(session, service.enrich(row), row, job)
            job.processed_count += 1
        except Exception:
            job.failed_count += 1
        session.commit()
    if not job.cancelled:
        job.status = "COMPLETED"
    session.commit()
    session.refresh(job)
    return job


def schema_columns() -> list[str]:
    with (Path(__file__).parents[1] / "output_schema.csv").open(encoding="utf-8-sig", newline="") as handle:
        return next(csv.reader(handle))
