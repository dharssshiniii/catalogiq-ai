# Resume and interview guide

## Resume line

Built CatalogIQ AI, a React/FastAPI evidence-first catalog enrichment MVP that profiles industrial CSVs, retrieves policy-approved HTML/PDF evidence, detects conflicting facts, persists human review and exports an audit-backed 252-column delivery format entirely in a ₹0 offline demo mode.

## Full-Stack interview

Discuss the typed React-to-FastAPI contract, upload states, persisted review forms, SQLite relationships, exact-order streaming downloads, error handling, responsive navigation and Playwright journey. The key trade-off was a modular monolith: fastest to understand and demo, with provider and job boundaries ready to separate later.

## Applied AI interview

Emphasize evidence-bounded extraction rather than free-form generation. Confidence combines trust, directness, agreement, method and validation. Conflicts preserve all candidates. Gemini is optional, server-side and instructed to return null when evidence is absent. The honest benchmark excludes manufacturer/marketing targets not supported by source input.

## HPE SQA interview

Frame the system as a traceable quality pipeline: deterministic normalization, boundary-value confidence tests, SSRF/redirect security cases, synthetic PDFs, exact schema assertions, rejected-value export tests, component tests and seven Chromium journeys. Explain why the two-row golden set cannot support general accuracy and how a representative reviewed corpus would be designed.

## Likely questions

- Why no vector database? Local lexical retrieval is inspectable, sufficient for the MVP and has zero operating cost.
- Why not auto-resolve conflicts? Silent choice would undermine provenance; review is safer.
- What would you productionize first? Authentication, formal migrations, domain governance, durable jobs, rate limits and a representative evaluation corpus.
- What failed during development? The original benchmark counted unsupported dealer/manufacturer and marketing comparisons; the fix was honest support classification, not hardcoded answers.
