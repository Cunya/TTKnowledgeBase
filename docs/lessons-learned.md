# Lessons learned

## Evidence and editorial state

- A queue decision is not trustworthy unless it can be derived from canonical evidence. Validate every accepted candidate against exact segment IDs in the referenced concept and video.
- Semantic similarity is useful for suggesting a destination, but it is not proof that a candidate was incorporated. Leave unmatched candidates pending rather than calling them accepted duplicates.
- LLMs often select sparse transcript segments spread across a long discussion. Before publication, split these into contiguous semantic moments instead of playing everything between the first and last citation.
- Enforce evidence-window rules in validation. Editorial conventions alone drift during large processing batches.
- Keep the spoken claim window separate from the visual demonstration window. Transcript-inferred evidence must never silently become a loopable visual example.
- Treat candidate uncertainty literally. One candidate admitted that it inferred segment numbering and produced nonexistent IDs; exclude those IDs and publish only independently present transcript segments.

## Batch processing

- Treat requested batch sizes as upper bounds. Report the actual number of available candidates rather than padding the batch.
- Process extraction jobs one video at a time when provenance and failure isolation matter. This makes retries and audits clearer.
- Preserve prior queue decisions when adding new extraction results. Rebuilding the entire generated queue can erase editorial work.
- Consolidate candidates into durable mechanics, timing, spacing, selection, error, and drill concepts instead of creating one article per LLM label.

## YouTube ingestion

- After an IP block, make only one controlled probe. Stop immediately on HTTP 429 and honor the retry record.
- A genuine network-state change, such as the operator enabling a VPN, justifies a new controlled probe before resuming a paced batch.
- Cache-first ingestion and sequential requests prevent already completed work from being lost when a later request fails.
- Keep downloaded or normalized transcripts private even when the sanitized derived knowledge is public.

## Tooling and verification

- A successful static build does not substitute for visual browser inspection. When browser automation is unavailable, state that limitation explicitly.
- PowerShell piping can corrupt typographic punctuation in generated YAML. Use UTF-8 mode and prefer ASCII apostrophes in mechanically generated editorial text.
- Round-trip YAML can emit trailing spaces and unquoted flow-style segment IDs. Run parsing, validation, and `git diff --check` after bulk content transformations.
- Always cap caption-derived end times to the video duration because the final caption can slightly exceed container metadata.
- Do not translate “not fast” into an explicit `flex` override without checking endpoint support. For the current Codex extraction path, omitting the service-tier setting is the compatible normal/default behavior.
