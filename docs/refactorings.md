# Refactoring notes

## Candidate promotion workflow

- Consider a first-class `import-candidate-batch` command with explicit added/changed/removed candidate reporting. Queue rebuilding now fingerprints candidate content and resets changed candidates to pending safely.
- Move exact accepted-candidate reconciliation into a reusable typed queue model rather than validating untyped dictionaries.
- Add a processor that proposes contiguous evidence clusters from candidate segment IDs using the same 30-second and 20-second-gap rules as validation.
- Provide an editorial promotion helper that creates canonical evidence records from reviewed candidate clusters without hand-written one-off transformation code.
- Validate every candidate segment ID against the normalized transcript immediately after Codex extraction so invented or mistyped IDs never reach the editorial queue.
- Add a review-batch report that groups pending candidates by video, matched canonical concept, contiguous evidence cluster, and publication impact so partial review does not require ad hoc inspection scripts.

## Validation

- Extract source-span validation into a shared function and apply it consistently to concept evidence and relation sources.
- Keep daily LLM budget reservation, reconciliation, and status reporting in the shared `processors.llm_budget` service rather than duplicating token checks in extraction, rephrase, and benchmark commands.
- Add explicit validation that source bounds enclose their cited segments, allowing only the documented final-caption/video-duration clamp.
- Return structured validation findings with severity and item identifiers instead of plain strings.
- Add navigation diagnostics that distinguish missing placement, valid cross-listing, and accidental duplication.
- Share the Codex subprocess runner between extraction and excerpt-rephrasing stages if additional structured editorial transforms are added; both currently preserve isolated, schema-constrained execution.

## Ingestion

- Generate `source-video-progress.md` from source-specific discovery manifests and pipeline artifacts instead of maintaining its snapshot tables manually.
- Add a shared daily-run orchestrator around the CLI phases rather than duplicating scheduling policy in PowerShell, Task Scheduler, or future CI jobs. It should own locking, missing-artifact workset selection, run manifests, and machine-readable exit classes.
- Make extraction workset selection hash-aware and idempotent so the timer never re-invokes Codex for an unchanged normalized transcript merely because `extract-concepts` was called without `--video-id`.
- Keep retry-cooldown enforcement covered by CLI tests as ingestion options evolve; the command now enforces `next_retry_at` and permits an explicit override only after a route change.
- Add an explicit single-video `probe-ingestion` command that does not imply a full batch restart.
- Normalize video-title encoding when source metadata enters the pipeline so mojibake cannot persist in configuration.
- Preserve separate discovery manifests per source. The current command overwrites `discovered-videos.json`, and some channel handles resolve only to invalid tab placeholders rather than video entries.

## Site

- Add a visible badge for single-source concepts. Transcript-inferred visual moments are now labeled as proposed and cannot loop until verified.
- Add a generated “Recently added” view based on reviewed content provenance or an editorial publication date.
- Add browser-level tests for primary/cross-listed topic paths, base-path routing, and non-looping transcript-only evidence.
# Review-queue YAML stability

- The review-queue writer rebuilt plain dictionaries with ruamel.yaml's default narrow line width, creating thousands of formatting-only changes on a no-op queue refresh. Keep a wide output width so generated candidates remain readable and diffs stay focused on actual candidate changes.
- Reuse the existing round-trip YAML candidate node when its fingerprint is unchanged; reconstructing it discarded quoting and reviewed presentation-only corrections even though the candidate itself had not changed.

## Site TOC

- Extract the deterministic per-video TOC join, sorting, de-duplication, and anchor validation into a shared helper if more site views need the same index; do not add an LLM call to the build path.
