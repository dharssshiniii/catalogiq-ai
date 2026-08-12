# Testing strategy

Backend unit tests cover placeholder variants, required headers, malformed/empty CSVs, duplicate profiling, confidence boundaries, missing/conflicting evidence, description checks, filename sanitization, and formula-injection escaping. API tests exercise health, status, schema parsing, upload profiling, extension rejection, deterministic enrichment, and review flags.

Frontend component tests cover shell state/navigation and the asynchronous evidence review. The production build acts as a TypeScript and bundling gate. Playwright provides a local two-server smoke test when Chromium is installed.

CI runs backend tests, frontend tests, and frontend production build on every push and pull request. No organizer data or external provider is required.

Milestone 2 should add contract tests for LIVE providers, a curated representative evaluation set, batch/export round trips, persistence integration tests, and accessibility/browser coverage.

Implemented Milestone 2 categories include SSRF and marketplace policy, redirects, limits and timeouts, HTML/PDF extraction, local evidence retrieval, provider fallback, normalization, confidence conflicts, stable descriptions, review history, batch controls, exact 252-column export and an enrichment-review-export integration flow.
