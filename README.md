# CatalogIQ AI — Milestone 2

CatalogIQ AI is an explainable product-intelligence foundation for turning incomplete industrial catalogue rows into structured, validated, commerce-ready records. Every generated field carries its original value, evidence, source identifier, extraction method, confidence, validation state, and review state.

> Turn incomplete catalog rows into defensible product intelligence—with an Evidence Ledger for every supported value and explicit conflict handling when sources disagree.

## Problem solved

Industrial distributors receive sparse rows while useful specifications live across manufacturer pages and documents. CatalogIQ profiles input quality, retrieves policy-approved evidence, structures supported facts, normalizes units, preserves competing candidates, routes uncertainty to review and exports the exact 252-column delivery shape plus a separate audit report.

The unique Evidence Ledger links every supported field to source excerpts, extraction method, confidence reasons, validation and human decisions. Credible conflicts are never silently discarded.

## Complete demo flow

1. Upload the source CSV and inspect derived placeholders and duplicate categories.
2. Select a public-safe synthetic record and run offline DEMO enrichment.
3. Inspect attributes, evidence, confidence reasons and a conflict/needs-review example.
4. Approve, correct with a note, or reject a field; observe regenerated descriptions.
5. Approve/reject the product and display audit history.
6. Download the exact-order 252-column CSV and evidence/audit JSON.
7. Inspect persisted state-derived metrics in Quality Centre.

## Screenshots

Add final submission captures here: Overview · 1,000-row profile · Evidence Ledger conflict · persisted review/audit · Quality Centre.

## ₹0 architecture

React/Vite/Tailwind communicates with FastAPI/Pydantic services and local SQLite. Pandas profiles CSVs, HTTPX/BeautifulSoup/PyMuPDF handle bounded evidence, and deterministic local retrieval avoids paid infrastructure. DEMO needs no network or key; optional LIVE Gemini is server-side and explicitly enabled without search grounding.

## What is included

- A FastAPI API for health/status, safe CSV profiling, the 252-column delivery schema, and deterministic demo enrichment.
- SQLAlchemy models for dataset jobs, product records, enriched fields, evidence, validation issues, and review decisions.
- A responsive React dashboard for overview, dataset profiling, field-level enrichment review, and quality controls.
- Two public-safe synthetic dishwasher fixtures in `data/demo/`; organizer datasets stay ignored in `data/raw/`.
- Pytest, Vitest/Testing Library, a Playwright smoke configuration, and GitHub Actions CI.

## Architecture

```text
React/Vite dashboard ──HTTP──> FastAPI routes
                                  │
                         profiling/enrichment services
                           │                  │
                       Pandas            provider contracts
                           │                  │
                       SQLite          DEMO (active)
                                         LIVE/Gemini (boundary only)
```

See [architecture](docs/architecture.md) for decisions and data flow.

## Windows local setup

Prerequisites: Python 3.11+ and Node.js 20+.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m uvicorn app.main:app --reload
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`; API docs are at `http://localhost:8000/docs`.

## Vercel deployment

The repository includes a single-project Vercel layout: Vite builds to `frontend/dist`, `api/index.py` exposes the existing FastAPI app, and same-origin rewrites keep frontend requests on relative `/api` paths. Set `CATALOGIQ_MODE=DEMO`; no API key is required. Do not add `GEMINI_API_KEY` unless intentionally enabling optional LIVE mode.

Vercel serverless provides only an ephemeral writable `/tmp` filesystem. CatalogIQ therefore uses `/tmp/catalogiq.db` on Vercel so the full review journey can be demonstrated within a warm serverless session, but review decisions, jobs, source cache and quality history may reset on a cold start or be inconsistent across parallel instances. This deployment does not claim durable persistence. Local SQLite remains durable during local development.

```powershell
vercel.cmd
vercel.cmd --prod
```

The free demo requires no purchased domain, database, or paid service.

## Tests and build

```powershell
cd backend
python -m pytest

cd ..\frontend
npm test
npm run build
```

Playwright is configured but browser binaries are optional: `npx playwright install chromium`, then `npm run e2e`.

## DEMO versus LIVE

`APP_MODE=DEMO` is the default and needs no key, internet, paid service, or cloud resource. Its rules are deterministic and deliberately conservative. A `GeminiProvider` availability boundary and extraction protocol prepare LIVE mode, but no Gemini request is implemented or required in this milestone. Keep all future provider keys in the backend `.env`; never expose them to Vite.

## Milestone status

Milestone 1 delivers the full local foundation and evidence-first demo flow. Known limitations: no live source retrieval, document parsing, AI call, batch enrichment/export, authentication, or persisted review UI. The demo parser recognizes a deliberately narrow attribute set and marks absent evidence for review.

Only two expected-output examples were supplied. They define the output shape but cannot support a general accuracy claim; none is made here.

Milestone 2 adds source policy, bounded HTML/PDF retrieval, local evidence ranking, optional server-side Gemini extraction, deterministic conflicts, persisted review, bounded jobs, exact-order export and state-derived quality metrics. `CATALOGIQ_MODE=DEMO` remains offline by default; LIVE requires explicit configuration plus `GEMINI_API_KEY` and configurable `GEMINI_MODEL`. No grounding or billing-dependent feature is enabled.

References: [source policy](docs/source-policy.md), [review workflow](docs/review-workflow.md), [cost controls](docs/cost-controls.md), and [evaluation method](docs/evaluation-method.md). Optional benchmark: `cd backend; python evaluate_golden.py`.

## Data handling

Organizer files are never changed and are excluded by `.gitignore`. Put local copies in `data/raw/`. Committed tests use only synthetic records. See [data privacy](docs/data-privacy.md).
