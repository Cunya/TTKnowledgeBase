# Refactorings

## 2026-07-20

- Replaced whole-stage subprocess capture in `scripts/run-cp.py` with one bounded streaming reader. This keeps the monitor live during long ingest and extraction stages while retaining the existing final stage report contract.

## 2026-07-21

- Extracted shared local-ASR transcription from the temporary audio fallback so the retained-media ASR route and normal fallback use the same segment construction and explicit `local_asr` provenance.
