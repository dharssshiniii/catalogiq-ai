from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ReviewStatus(str, Enum):
    AUTO_ACCEPTED = "AUTO_ACCEPTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    CONFLICT = "CONFLICT"
    REJECTED = "REJECTED"
    APPROVED = "APPROVED"


class ValidationStatus(str, Enum):
    VALID = "VALID"
    WARNING = "WARNING"
    INVALID = "INVALID"


class Evidence(BaseModel):
    excerpt: str
    source_identifier: str
    extraction_method: str
    url: str | None = None
    page_number: int | None = None
    heading: str | None = None
    source_trust: float = Field(default=0.5, ge=0, le=1)


class EnrichedFieldResult(BaseModel):
    field_name: str
    original_value: str | None = None
    generated_value: str | None = None
    evidence: list[Evidence] = []
    confidence: float = Field(ge=0, le=1)
    validation_status: ValidationStatus
    review_status: ReviewStatus
    reason_codes: list[str] = []
    candidates: list[dict[str, Any]] = []


class ValidationIssueResult(BaseModel):
    field_name: str | None = None
    severity: str
    code: str
    message: str


class ProductInput(BaseModel):
    Mfg_Part_Num: str = Field(min_length=1, max_length=255)
    Part_Desc: str = Field(min_length=1, max_length=2000)
    E1_Brand: str = ""
    Unilog_Brand: str = ""
    DIB_Brand: str = ""
    Part_Manuf: str = ""

    @field_validator("Mfg_Part_Num", "Part_Desc")
    @classmethod
    def strip_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value.strip()


class EnrichmentResult(BaseModel):
    product_key: str
    mode: str
    fields: list[EnrichedFieldResult]
    validation_issues: list[ValidationIssueResult]
    review_status: ReviewStatus
    commerce_record: dict[str, Any]


class ReviewAction(BaseModel):
    action: str
    reviewer: str = "prototype-reviewer"
    value: str | None = None
    note: str | None = None
    reason: str | None = None


class SourceRequest(BaseModel):
    url: str
    manufacturer_domains: list[str] = []


class BatchRequest(BaseModel):
    rows: list[ProductInput]
    limit: int = Field(default=5, ge=1, le=1000)
