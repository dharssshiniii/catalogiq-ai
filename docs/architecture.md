# Architecture

CatalogIQ is a local-first modular monolith: a React/TypeScript client and a typed FastAPI service backed by SQLite. This keeps the ₹0 milestone easy to inspect and operate while preserving seams for future providers.

The upload route reads a bounded byte stream, validates the sanitized extension, rejects binary/corrupt/empty input, checks the six observed input columns, and profiles with Pandas. It does not persist the upload. The schema route reads a header-only artifact derived from the supplied 252-column delivery format; supplied product rows are never exposed.

The demo enrichment service resolves the first non-placeholder manufacturer, recognizes a small verified dishwasher vocabulary, normalizes place-setting units, builds a conservative description, and attaches the input field as evidence. Missing or conflicting evidence produces low confidence and `NEEDS_REVIEW`.

Provider contracts separate source retrieval, document extraction, AI extraction, validation, and description building. `GeminiProvider` currently reports configuration availability only. Future LIVE code should implement these contracts without changing API response models.

SQLite tables form the future audit graph: dataset job → product record → enriched field → evidence/issue, with review decisions linked to fields.

Milestone 2 gates HTTPX retrieval and redirects through source policy, cleans HTML with BeautifulSoup, extracts numbered PDF pages with PyMuPDF, and flags OCR needs. A BM25-compatible local index ranks chunks without vectors. Provider selection is deterministic DEMO, explicitly configured Gemini, or unavailable fallback. Review and export operate on persisted fields.
