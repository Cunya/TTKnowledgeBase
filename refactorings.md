# Refactorings

## 2026-09-15

- Reused the existing streamed stage runner for operator-readable purpose, heartbeat, and duration messages instead of adding a second logging pipeline; the existing machine-readable stage markers remain unchanged.
- Reused the existing navigation scoring path and expanded its input context instead of adding a second placement pass after summary generation.
- Reused the monitor's existing bounded child-output buffer for allowlisted failure summaries instead of storing or streaming raw tracebacks.

## 2026-09-08

- Reused one adjudication persistence helper for final writes and ten-candidate checkpoints, avoiding separate queue/concept serialization paths.

## 2026-07-20

- Replaced whole-stage subprocess capture in `scripts/run-cp.py` with one bounded streaming reader. This keeps the monitor live during long ingest and extraction stages while retaining the existing final stage report contract.

## 2026-07-21

- Extracted shared local-ASR transcription from the temporary audio fallback so the retained-media ASR route and normal fallback use the same segment construction and explicit `local_asr` provenance.

- 2026-09-15: Reused the run manifest stage list as the source for `Stage x/y` numbering so the runner and monitor do not maintain separate counters.

## 2026-09-16

- Reused the existing review-queue item and validator instead of adding a second reconciliation pass; accepted adjudications now carry their exact selected segment IDs through the current rebuild path.
- Reused the existing navigation scorer and added one configured editorial holding node for ambiguous generated concepts, avoiding a second publish-only reconciliation pass.
