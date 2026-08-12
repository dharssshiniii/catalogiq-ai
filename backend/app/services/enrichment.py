import re

from app.models.schemas import (EnrichedFieldResult, EnrichmentResult, Evidence, ProductInput,
                                ReviewStatus, ValidationIssueResult, ValidationStatus)
from app.services.placeholders import is_placeholder
from app.services.descriptions import build_descriptions


def confidence_for(evidence_count: int, conflicting: bool = False) -> float:
    if evidence_count <= 0:
        return 0.0
    if conflicting:
        return 0.35
    return 0.92 if evidence_count >= 2 else 0.76


def make_field(name: str, original: str | None, generated: str | None, evidence: list[Evidence], conflicting: bool = False) -> EnrichedFieldResult:
    confidence = confidence_for(len(evidence), conflicting)
    needs_review = not evidence or conflicting or confidence < 0.7 or generated is None
    return EnrichedFieldResult(
        field_name=name, original_value=original, generated_value=generated, evidence=evidence,
        confidence=confidence, validation_status=ValidationStatus.WARNING if needs_review else ValidationStatus.VALID,
        review_status=ReviewStatus.CONFLICT if conflicting else ReviewStatus.NEEDS_REVIEW if needs_review else ReviewStatus.AUTO_ACCEPTED,
    )


def validate_description(description: str) -> list[ValidationIssueResult]:
    issues: list[ValidationIssueResult] = []
    if len(description) < 25:
        issues.append(ValidationIssueResult(field_name="MARKETING_DESCRIPTION", severity="WARNING", code="DESCRIPTION_TOO_SHORT", message="Description needs more verified product detail."))
    if re.search(r"\b(best|perfect|guaranteed|#1)\b", description, re.I):
        issues.append(ValidationIssueResult(field_name="MARKETING_DESCRIPTION", severity="ERROR", code="UNSUPPORTED_CLAIM", message="Description contains an unsupported marketing claim."))
    return issues


class DemoEnrichmentService:
    @property
    def available(self) -> bool:
        return True

    def enrich(self, product: ProductInput) -> EnrichmentResult:
        source = Evidence(excerpt=product.Part_Desc, source_identifier="demo://input/Part_Desc", extraction_method="synthetic-deterministic-parser", url="demo://manufacturer/specification", source_trust=0.8)
        manufacturer_raw = next((v for v in [product.Part_Manuf, product.E1_Brand, product.Unilog_Brand, product.DIB_Brand] if not is_placeholder(v)), None)
        manufacturer = manufacturer_raw.strip().title() if manufacturer_raw else None
        description_lower = product.Part_Desc.lower()
        fields = [make_field("MANUFACTURER_NAME", product.Part_Manuf, manufacturer, [source] if manufacturer else [])]
        product_name = "Dishwasher" if "dishwasher" in description_lower else None
        fields.append(make_field("Product Name", None, product_name, [source] if product_name else []))
        place_match = re.search(r"(\d{1,2})\s*(?:place settings?|ps)\b", description_lower)
        place_value = place_match.group(1) if place_match else None
        fields.append(make_field("ATTRIBUTE_VALUE 1", None, place_value, [source] if place_value else []))
        fields.append(make_field("ATTRIBUTE_UOM 1", None, "place settings" if place_value else None, [source] if place_value else []))
        finish = next((f for f in ["stainless steel", "black", "white"] if f in description_lower), None)
        fields.append(make_field("ATTRIBUTE_VALUE 2", None, finish.title() if finish else None, [source] if finish else []))
        voltage_values = re.findall(r"\b(120|208|220|230|240)\s*V\b", product.Part_Desc, re.I)
        if voltage_values:
            unique_voltage = list(dict.fromkeys(voltage_values))
            voltage_candidates = [{"value": f"{value} V", "source": "demo://manufacturer/specification", "confidence": 0.9} for value in unique_voltage]
            voltage_field = make_field("ATTRIBUTE_VALUE 3", None, f"{unique_voltage[0]} V" if len(unique_voltage) == 1 else None, [source], conflicting=len(unique_voltage) > 1)
            voltage_field.candidates = voltage_candidates
            voltage_field.reason_codes = ["CREDIBLE_SOURCE_CONFLICT"] if len(unique_voltage) > 1 else ["SYNTHETIC_EVIDENCE_DIRECT"]
            fields.append(voltage_field)
        verified = [v for v in [manufacturer, product_name, f"{place_value} place settings" if place_value else None, finish] if v]
        marketing = ". ".join([" ".join(verified), product.Part_Desc.strip()]) if verified else product.Part_Desc.strip()
        fields.append(make_field("MARKETING_DESCRIPTION", None, marketing, [source]))
        descriptions = build_descriptions({"brand": manufacturer or "", "product_name": product_name or "", "colour": finish.title() if finish else ""})
        for name, value in {"MOBILE_DESC": descriptions.mobile, "INVOICE_DESC": descriptions.invoice, "SHORT_DESC": descriptions.short, "RETAIL_DESC": descriptions.retail, "LONG_DESC1": descriptions.long}.items():
            fields.append(make_field(name, None, value or None, [source] if value else []))
        issues = validate_description(marketing)
        for field in fields:
            if not field.evidence:
                issues.append(ValidationIssueResult(field_name=field.field_name, severity="WARNING", code="MISSING_EVIDENCE", message="No evidence supports a generated value; human review is required."))
        review = ReviewStatus.NEEDS_REVIEW if issues or any(f.review_status == ReviewStatus.NEEDS_REVIEW for f in fields) else ReviewStatus.AUTO_ACCEPTED
        record = {field.field_name: field.generated_value for field in fields if field.generated_value is not None}
        return EnrichmentResult(product_key=product.Mfg_Part_Num, mode="DEMO", fields=fields, validation_issues=issues, review_status=review, commerce_record=record)


class GeminiProvider:
    """Milestone 2 boundary: implementation intentionally absent in the zero-cost demo."""
    def __init__(self, api_key: str | None) -> None:
        self._api_key = api_key

    @property
    def available(self) -> bool:
        return bool(self._api_key)
