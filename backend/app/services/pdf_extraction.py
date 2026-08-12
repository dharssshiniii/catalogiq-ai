from dataclasses import dataclass, field

import fitz


@dataclass
class PdfExtractionResult:
    ok: bool
    pages: list[dict[str, object]] = field(default_factory=list)
    page_count: int = 0
    requires_ocr: bool = False
    error_code: str | None = None


def extract_pdf(content: bytes, max_bytes: int = 5_242_880, max_pages: int = 100, minimum_text: int = 20) -> PdfExtractionResult:
    if len(content) > max_bytes:
        return PdfExtractionResult(False, error_code="PDF_TOO_LARGE")
    try:
        document = fitz.open(stream=content, filetype="pdf")
    except Exception:
        return PdfExtractionResult(False, error_code="INVALID_PDF")
    if document.page_count > max_pages:
        return PdfExtractionResult(False, page_count=document.page_count, error_code="PDF_PAGE_LIMIT")
    pages = [{"page_number": index + 1, "text": document[index].get_text("text").strip()} for index in range(document.page_count)]
    text_size = sum(len(str(page["text"])) for page in pages)
    low_text = text_size < minimum_text * max(1, document.page_count)
    return PdfExtractionResult(not low_text, pages, document.page_count, low_text, "OCR_REQUIRED" if low_text else None)
