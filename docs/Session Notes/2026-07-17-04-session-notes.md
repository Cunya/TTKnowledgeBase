# Session notes - 2026-07-17

## 10:59

- `cp` stopped at the cached-work gate because normalized transcripts still await extraction.
- Extraction is deferred by the configured task cap; do not ingest another controlled batch until the next budget window or an explicit budget-policy change.
- Deterministic queue rebuild, validation, and publication passed.
