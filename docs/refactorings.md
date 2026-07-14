# Refactoring notes

## Candidate promotion workflow

- Consider a first-class `import-candidate-batch` command with explicit added/changed/removed candidate reporting. Queue rebuilding now fingerprints candidate content and resets changed candidates to pending safely.
- Move exact accepted-candidate reconciliation into a reusable typed queue model rather than validating untyped dictionaries.
- Add a processor that proposes contiguous evidence clusters from candidate segment IDs using the same 30-second and 20-second-gap rules as validation.
- Provide an editorial promotion helper that creates canonical evidence records from reviewed candidate clusters without hand-written one-off transformation code.
- Validate every candidate segment ID against the normalized transcript immediately after Codex extraction so invented or mistyped IDs never reach the editorial queue.

## Validation

- Extract source-span validation into a shared function and apply it consistently to concept evidence and relation sources.
- Add explicit validation that source bounds enclose their cited segments, allowing only the documented final-caption/video-duration clamp.
- Return structured validation findings with severity and item identifiers instead of plain strings.
- Add navigation diagnostics that distinguish missing placement, valid cross-listing, and accidental duplication.

## Ingestion

- Generate `source-video-progress.md` from source-specific discovery manifests and pipeline artifacts instead of maintaining its snapshot tables manually.
- Enforce `next_retry_at` inside the ingest command. The retry manifest currently records backoff state, but the command relies on operator discipline to honor it.
- Add an explicit single-video `probe-ingestion` command that does not imply a full batch restart.
- Normalize video-title encoding when source metadata enters the pipeline so mojibake cannot persist in configuration.
- Preserve separate discovery manifests per source. The current command overwrites `discovered-videos.json`, and some channel handles resolve only to invalid tab placeholders rather than video entries.

## Site

- Add a visible badge for single-source concepts. Transcript-inferred visual moments are now labeled as proposed and cannot loop until verified.
- Add a generated “Recently added” view based on reviewed content provenance or an editorial publication date.
- Add browser-level tests for primary/cross-listed topic paths, base-path routing, and non-looping transcript-only evidence.
