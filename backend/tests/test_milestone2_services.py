import io

import fitz
import httpx
import pytest

from app.services.confidence import assess_confidence
from app.services.descriptions import build_descriptions
from app.services.evidence_index import Chunk, EvidenceIndex, chunk_text
from app.services.normalization import decimal_to_fraction, deduplicate_features, normalize_dimensions, normalize_measurement
from app.services.pdf_extraction import extract_pdf
from app.services.providers import ExtractedFacts, GeminiProvider, UnavailableProvider
from app.services.retrieval import SafeWebRetriever, extract_html_text
from app.services.source_policy import SourcePolicy, SourceType


@pytest.mark.parametrize("url", ["file:///etc/passwd", "http://localhost/admin", "http://127.0.0.1/x", "http://169.254.169.254/latest", "http://10.0.0.1/x", "http://[::1]/x"])
def test_ssrf_protection(url):
    result = SourcePolicy().evaluate(url)
    assert result.allowed is False


@pytest.mark.parametrize("url", ["https://amazon.com/p/1", "https://www.ebay.com/item/1", "https://shop.amazon.in/x"])
def test_marketplaces_blocked(url):
    result = SourcePolicy().evaluate(url, resolve_dns=False)
    assert result.source_type == SourceType.PROHIBITED_MARKETPLACE
    assert not result.allowed


def test_manufacturer_classification():
    policy = SourcePolicy()
    page = policy.evaluate("https://docs.aster.example/product", ["aster.example"], resolve_dns=False)
    document = policy.evaluate("https://aster.example/spec.pdf", ["aster.example"], resolve_dns=False)
    assert page.source_type == SourceType.MANUFACTURER_PAGE and page.trust_weight == 1
    assert document.source_type == SourceType.MANUFACTURER_DOCUMENT


def test_unsafe_redirect_is_stopped():
    def handler(request):
        return httpx.Response(302, headers={"location": "http://127.0.0.1/private"})
    result = SafeWebRetriever(transport=httpx.MockTransport(handler)).retrieve("https://manufacturer.example/start", ["manufacturer.example"])
    assert not result.ok and result.error_code == "UNSAFE_REDIRECT"


def test_retrieval_size_content_and_html_extraction():
    html = b"<html><nav>Menu</nav><h1>Dishwasher</h1><script>bad()</script><table><tr><th>Voltage</th><td>120 V</td></tr></table></html>"
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=html, headers={"content-type": "text/html"}))
    result = SafeWebRetriever(max_bytes=1000, transport=transport).retrieve("https://manufacturer.example/product", ["manufacturer.example"])
    assert result.ok and "Dishwasher" in result.text and "120 V" in result.text and "bad" not in result.text and "Menu" not in result.text
    limited = SafeWebRetriever(max_bytes=2, transport=transport).retrieve("https://manufacturer.example/product")
    assert limited.error_code == "RESPONSE_TOO_LARGE"


def test_transient_get_retries_once():
    calls = 0
    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(503) if calls == 1 else httpx.Response(200, content=b"<p>Recovered specification</p>", headers={"content-type":"text/html"})
    result = SafeWebRetriever(transport=httpx.MockTransport(handler)).retrieve("https://manufacturer.example/product")
    assert result.ok and calls == 2


def test_timeout_is_structured():
    def handler(request): raise httpx.ReadTimeout("slow", request=request)
    result = SafeWebRetriever(transport=httpx.MockTransport(handler)).retrieve("https://manufacturer.example/product")
    assert result.error_code == "TIMEOUT"


def make_pdf(text: str = "Verified dishwasher specification voltage 120 V") -> bytes:
    doc = fitz.open(); page = doc.new_page()
    if text: page.insert_text((72, 72), text)
    return doc.tobytes()


def test_pdf_extraction_preserves_pages_and_detects_low_text():
    result = extract_pdf(make_pdf())
    assert result.ok and result.pages[0]["page_number"] == 1 and "120 V" in result.pages[0]["text"]
    empty = extract_pdf(make_pdf(""))
    assert not empty.ok and empty.requires_ocr and empty.error_code == "OCR_REQUIRED"


def test_evidence_index_relevance():
    index = EvidenceIndex()
    for chunk in chunk_text("Voltage rating 120 V\nSound level 44 dBA", "s1", "https://m.example", "abc", 1): index.add(chunk)
    index.add(Chunk("s2", "https://x.example", "Warranty one year", .6, "def"))
    assert index.search("voltage")[0].source_identifier == "s1"


def test_provider_validation_and_unavailable_fallback():
    assert ExtractedFacts.model_validate({"values": {"voltage": None}}).values["voltage"] is None
    assert not UnavailableProvider().extract([], []).available
    assert GeminiProvider("DEMO", "secret", "model").extract([], []).error_code == "LIVE_NOT_CONFIGURED"
    assert GeminiProvider("LIVE", None, "model").available is False


def test_normalization_and_fraction_boundaries():
    assert decimal_to_fraction(50.25) == "50-1/4"
    assert decimal_to_fraction(0.015625) == "1/64"
    assert normalize_measurement("120", "v") == "120 V"
    assert normalize_measurement("44", "dba") == "44 dBA"
    assert normalize_measurement("2", "unsupported") is None
    assert normalize_dimensions(24, 24.25) == "24 in W x 24-1/4 in D"
    assert deduplicate_features(["Quiet wash", " quiet  wash ", "Steel tub"]) == ["Quiet wash", "Steel tub"]


def test_conflicts_and_confidence_boundaries():
    missing = assess_confidence([], .7)
    assert missing.score == 0 and missing.review_status == "NEEDS_REVIEW"
    agreed = assess_confidence([{"value": "120 V", "evidence": ["x"], "source_trust": 1, "directness": 1, "method": "deterministic", "valid": True}], .7)
    assert agreed.score >= .7 and agreed.review_status == "AUTO_ACCEPTED"
    boundary = assess_confidence([{"value": "x", "evidence": ["x"], "source_trust": .4, "directness": .4, "method": "ai", "valid": True}], .7)
    assert boundary.score < .7 and "BELOW_CONFIDENCE_THRESHOLD" in boundary.reason_codes
    conflict = assess_confidence([{"value": "120 V", "evidence": ["x"], "source_trust": 1}, {"value": "240 V", "evidence": ["y"], "source_trust": 1}])
    assert conflict.conflict and conflict.review_status == "CONFLICT" and "CREDIBLE_SOURCE_CONFLICT" in conflict.reason_codes


def test_description_stability_and_unsupported_claim_absence():
    attrs = {"brand": "Aster", "product_name": "Dishwasher", "size": "24 in", "colour": "White", "features": "Steel tub|Quiet wash"}
    first = build_descriptions(attrs)
    assert first == build_descriptions(attrs)
    assert "best" not in first.long.lower()
