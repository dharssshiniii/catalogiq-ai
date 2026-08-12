# Data privacy and security

- Organizer datasets live only in ignored `data/raw/`; synthetic fixtures are public-safe.
- Uploads are processed in memory, bounded to 5 MiB by default, and not retained by the profiling endpoint.
- Filenames are reduced to a basename and restricted character set. CSV structure, UTF-8 encoding, required columns, and extensions are validated.
- Future exports must call `escape_csv_formula` for cells beginning with spreadsheet formula prefixes.
- Secrets belong in the backend `.env`, which is ignored. The frontend contains no provider credentials.
- Structured output validation uses Pydantic. Central errors avoid leaking traces to clients.
- Source URLs and every redirect are policy checked. Original PDFs are not retained by default; only permitted extracted text, hashes and metadata may be cached.
- Gemini is server-side and opt-in, receives bounded evidence rather than whole datasets, and prompts or keys are not logged.
- Vercel DEMO uses ephemeral `/tmp` SQLite only; no organizer upload or reviewer state is intentionally retained across cold starts.

For production, add authentication, authorization, malware scanning, encryption/retention controls, rate limiting, audit access policies, and an approved privacy impact assessment.
