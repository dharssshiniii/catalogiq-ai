# Cost controls

DEMO is offline and deterministic. LIVE requires both `CATALOGIQ_MODE=LIVE` and a server-side `GEMINI_API_KEY`; otherwise the provider is unavailable gracefully. `GEMINI_MODEL` is configurable. No grounding, paid retrieval, queue, vector database or cloud resource is used. LIVE batches default to five rows and never submit all 1,000 rows automatically. Do not activate billing.
