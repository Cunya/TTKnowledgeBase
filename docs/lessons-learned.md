# Lessons learned

## Evidence and editorial state

- A queue decision is not trustworthy unless it can be derived from canonical evidence. Validate every accepted candidate against exact segment IDs in the referenced concept and video.
- Semantic similarity is useful for suggesting a destination, but it is not proof that a candidate was incorporated. Leave unmatched candidates pending rather than calling them accepted duplicates.
- LLMs often select sparse transcript segments spread across a long discussion. Before publication, split these into contiguous semantic moments instead of playing everything between the first and last citation.
- Enforce evidence-window rules in validation. Editorial conventions alone drift during large processing batches.
- Keep the spoken claim window separate from the visual demonstration window. Transcript-inferred evidence must never silently become a loopable visual example.
- Treat candidate uncertainty literally. One candidate admitted that it inferred segment numbering and produced nonexistent IDs; exclude those IDs and publish only independently present transcript segments.
- Audit public excerpts against their cited transcript segments before broad publication. Exact and near-verbatim matches need rephrasing or explicit, short quotation treatment, while the surrounding editorial reason should remain original.
- When rephrasing audited excerpts, change only the public editorial wording and preserve segment IDs, timestamps, evidence type, confidence, visual status, reasons, and provenance so every claim remains traceable.
- Automatic LLM editorial transforms should be explicitly gated at publish time, schema-constrained, overlap-checked after generation, and fail closed; this keeps CI deterministic while making the local operator workflow repeatable.
- Keep the prioritized backlog as the planning source of truth. Dated review reports explain findings, but actionable work also needs a priority, status, dependency, and acceptance criterion in `docs/prioritized-backlog-2026-07-15.md`.

## Batch processing

- Preserve editorial queue state during deterministic rebuilds, but require a content fingerprint as well as video and candidate ID. Reused IDs with changed definitions or evidence must return to pending review.
- Treat requested batch sizes as upper bounds. Report the actual number of available candidates rather than padding the batch.
- Process extraction jobs one video at a time when provenance and failure isolation matter. This makes retries and audits clearer.
- Preserve prior queue decisions when adding new extraction results. Rebuilding the entire generated queue can erase editorial work.
- Consolidate candidates into durable mechanics, timing, spacing, selection, error, and drill concepts instead of creating one article per LLM label.
- Track extracted, fully reviewed, and published as independent states. A video can be published through one approved evidence moment while other candidates from that video remain pending.
- A large candidate may cite useful segments scattered across several minutes. Incorporate only a focused contiguous cluster that independently supports the canonical wording; do not stretch one playback window across the complete candidate evidence list.
- Long-running extraction loops may buffer child-process output until completion. Check subprocess start times and candidate-file timestamps before treating a quiet batch as stalled, while retaining the configured per-call timeout.
- A daily LLM allowance must reserve an estimate before spawning Codex, then reconcile with reported usage. Keeping the ledger private and per knowledge base lets exhausted work defer cleanly without creating partial candidates or mixing domains.

## YouTube ingestion

- After an IP block, make only one controlled probe. Stop immediately on HTTP 429 and honor the retry record.
- A genuine network-state change, such as the operator enabling a VPN, justifies a new controlled probe before resuming a paced batch.
- Cache-first ingestion and sequential requests prevent already completed work from being lost when a later request fails.
- Keep downloaded or normalized transcripts private even when the sanitized derived knowledge is public.
- A private, non-sharing offline copy is a different risk category from public redistribution, but it does not authorize bypassing technical restrictions or silently disregard YouTube/platform terms. Keep public and private storage boundaries explicit.

## Tooling and verification

- A successful static build does not substitute for visual browser inspection. When browser automation is unavailable, state that limitation explicitly.
- Never call a transcript-inferred visual window reviewed or loopable. A proposed clip becomes a verified demonstration only after someone watches the complete interval and records manual review.
- CI cannot use ignored private transcripts. Validate the sanitized public corpus, manifest, queue overlap, and publish-copy equality in CI, while retaining transcript-backed validation as a required local publishing step.
- PowerShell piping can corrupt typographic punctuation in generated YAML. Use UTF-8 mode and prefer ASCII apostrophes in mechanically generated editorial text.
- Round-trip YAML can emit trailing spaces and unquoted flow-style segment IDs. Run parsing, validation, and `git diff --check` after bulk content transformations.
- Always cap caption-derived end times to the video duration because the final caption can slightly exceed container metadata.
- Do not translate “not fast” into an explicit `flex` override without checking endpoint support. For the current Codex extraction path, omitting the service-tier setting is the compatible normal/default behavior.
- Treat public-project precedent research as two separate checks: copyright outcomes for similar uses and the source platform’s contract/API rules. A favorable indexing case does not authorize scraping or public full-copy storage.
- Conservative pending-candidate triage needs deterministic evidence-ID suffixes when one candidate appears in multiple distinct moments, and inferred citation ends must be capped to the source video duration before validation.
- Responsive rules for nested evidence layouts should use the manuscript/container width as well as viewport breakpoints; browser zoom and split panels can make a wide viewport contain a narrow content column.
- Start a new dated session log when the calendar date changes, and append events in actual completion order so processing history remains auditable.
