# Vercel deployment

CatalogIQ uses one Vercel project and one public origin. Static Vite assets are served from `frontend/dist`; `/api/*` and `/health` rewrite to the FastAPI function in `api/index.py`; other paths rewrite to `index.html` for SPA refreshes.

Required environment variable: `CATALOGIQ_MODE=DEMO`. Optional non-secret limits can retain defaults. `GEMINI_API_KEY` is not required and should remain unset for the public synthetic demo.

## Persistence boundary

Vercel functions cannot provide durable local SQLite. The function selects `sqlite:////tmp/catalogiq.db`, which supports a warm-instance judge sequence but can reset on cold start and is not shared between concurrent instances. This is suitable only for a synthetic hackathon demonstration. A durable production review ledger would require an external database, intentionally not added here because the project is constrained to free Vercel-only resources.
