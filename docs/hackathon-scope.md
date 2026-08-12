# Hackathon scope

## Milestone 1

This milestone proves the foundation: observed schemas, safe profiling, deterministic evidence-aware enrichment, review-oriented UI, audit-ready persistence models, automated checks, and zero-cost local operation.

It intentionally does not claim enrichment accuracy. Two supplied golden rows are examples, not an evaluation dataset. It also excludes deployment, billing, external resources, live web retrieval, Gemini calls, batch jobs, queues, vector search, and presentation edits.

The organizer explainer clarifies future retrieval policy: manufacturer websites and manufacturer-provided manuals, videos, catalogs, and technical sources are preferred; shopping/e-commerce sites such as Amazon and eBay must not be used. Source URLs must accompany extracted data, and the solution should remain generic across industrial segments. The stated judging dimensions are innovation, accuracy, quality, and scalability with equal weight. Milestone 1 therefore emphasizes provenance and a provider-neutral architecture while avoiding unsupported evaluation claims.

## Milestone 2

Next work should implement source/document provider adapters, opt-in Gemini structured extraction, persisted jobs and review decisions, batch enrichment, safe delivery-format export, source conflict resolution, and an independently reviewed evaluation corpus. LIVE mode must retain conservative confidence gates and work only when explicitly configured.

Milestone 2 now implements those MVP boundaries. Milestone 3 remains authentication, schema migrations, durable workers, approved-domain governance, OCR, JavaScript rendering, category authoring, production controls and a representative reviewed evaluation corpus.
