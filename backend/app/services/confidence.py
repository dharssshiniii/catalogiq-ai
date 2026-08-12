from dataclasses import dataclass


@dataclass
class ConfidenceResult:
    score: float
    review_status: str
    reason_codes: list[str]
    conflict: bool


def assess_confidence(candidates: list[dict[str, object]], threshold: float = 0.70) -> ConfidenceResult:
    supported = [item for item in candidates if item.get("value") is not None and item.get("evidence")]
    if not supported:
        return ConfidenceResult(0, "NEEDS_REVIEW", ["MISSING_EVIDENCE"], False)
    values = {str(item["value"]).strip().casefold() for item in supported}
    conflict = len(values) > 1
    trust = sum(float(item.get("source_trust", 0.5)) for item in supported) / len(supported)
    directness = sum(float(item.get("directness", 0.8)) for item in supported) / len(supported)
    validation = 1.0 if all(item.get("valid", True) for item in supported) else 0.4
    agreement = 0.25 if conflict else min(1.0, 0.75 + 0.1 * (len(supported) - 1))
    method = sum(1.0 if item.get("method") == "deterministic" else 0.8 for item in supported) / len(supported)
    score = round(0.35 * trust + 0.2 * directness + 0.2 * agreement + 0.15 * validation + 0.1 * method, 3)
    reasons = []
    if conflict:
        reasons.append("CREDIBLE_SOURCE_CONFLICT")
    if not all(item.get("valid", True) for item in supported):
        reasons.append("VALIDATION_FAILED")
    if score < threshold:
        reasons.append("BELOW_CONFIDENCE_THRESHOLD")
    status = "CONFLICT" if conflict else "NEEDS_REVIEW" if score < threshold else "AUTO_ACCEPTED"
    return ConfidenceResult(score, status, reasons or ["EVIDENCE_AGREES"], conflict)
