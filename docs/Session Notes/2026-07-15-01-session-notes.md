# Session notes — 2026-07-15 13:04 EEST

## Current state refresh - 2026-07-15 13:04 EEST

- Canonical concepts: 73 approved; published corpus: 68 videos and 1,321 evidence moments.
- Review queue: 653 accepted, 41 explicitly deferred, 1 rejected, and 0 pending decisions.
- P1-02 processing is complete for the cached candidate queue; the controlled follow-up batch accepted 57 high-confidence candidates and added 57 focused evidence moments.
- Eight of the nine previously one-concept videos gained additional concept links. `hDXIuFwtrHE` remains one-concept because no pending candidate safely mapped to an existing concept.
- Quality report: 851 distinct excerpts, 0 isolated concepts, 9 single-source concepts, 35 proposed visual intervals, and 0 manually verified visuals.
- Verification: 26 Python tests passed, Astro diagnostics passed with 0 errors/warnings/hints, the static build produced 150 pages, and `git diff --check` passed.
- Reusable command: `.venv\Scripts\python.exe -m processors.cli process-pending --kb table-tennis`; it currently returns zero remaining candidates to process.

## Historical state refresh - 2026-07-15 11:40 EEST

- Canonical concepts: 73 approved.
- Published corpus: 50 videos and 1,118 evidence moments.
- Private normalized area: 60 real videos plus the demo fixture; this is not the same as the published count.
- Review queue: 450 accepted, 174 pending, 1 rejected.
- Visual evidence: 0 `verified_visual_demo`, 485 `transcript_inferred`, 633 `not_visual`.
- Python tests: 25 passing; Astro diagnostics: 24 files with 0 errors/warnings/hints; static build: 132 pages.
- Codex extraction profile: `gpt-5.4-mini`, low reasoning, normal/default service tier; no automatic escalation.
- Maintained backlog: `docs/prioritized-backlog-2026-07-15.md`.
- Highest-priority work is quotation rephrasing, acquisition-policy documentation, canonical publish freshness, quarantine controls, visual verification, and pending-candidate review before another large scrape.

## Current state refresh - 2026-07-15 11:55 EEST

- P0-01 rephrasing pass completed across the audited high-overlap evidence excerpts.
- Source segment IDs, timestamps, evidence types, reasons, and provenance were preserved; only public excerpt wording changed.
- Post-pass quotation screen: 0 complete normalized matches, 0 high-ratio matches, and 28 lower-ratio partial overlaps to monitor.
- Canonical validation and publish completed: 73 concepts, 1,118 evidence items.
- Verification: 25 Python tests passed, Ruff passed, Astro check passed with 0 diagnostics, and the 132-page static build passed.
- Remaining follow-up: add `excerpt_kind` schema/validator and keep the quotation screen in the pre-publication checks.
- Automatic guard now available: `rephrase-excerpts` or `publish --auto-rephrase-high-overlap` runs the configured low-cost Codex rewrite only for flagged excerpts and persists excerpt-only changes.

## Historical state snapshot

- Knowledge base: `table-tennis`
- Canonical concepts: 73 approved
- Eligible, ingested, and extracted videos: 50
- Videos represented in the published corpus: 50
- Fully reviewed videos: 42
- Published evidence moments: 1,118 excluding demo evidence
- Review queue: 450 accepted, 68 pending, 1 rejected
- Proposed visual intervals: 35; manually verified intervals: 0
- Python tests: 23 passing
- Static pages: 80
- Codex extraction profile: `gpt-5.4-mini`, low reasoning, normal/default service tier; no automatic escalation

## Latest batch

- A route change cleared the earlier YouTube IP block. One probe and seven conservatively paced requests ingested eight videos without another HTTP 429.
- All eight cached transcripts completed schema-constrained Codex extraction without model escalation, producing 76 candidates.
- One focused, exact-segment-backed addition from every new video was incorporated into canonical content and published.
- The remaining 68 proposals are pending. They must be consolidated, split, or rejected individually; they were not bulk-promoted.
- New approved coverage includes backhand-loop timing and contact height, backhand-serve wrist position, short-ball receive options and spacing, backhand-loop preparation shape, forehand brush-before-power sequencing, and backhand opening adjustments against backspin.

## Ingestion safeguards now active

- Cache-first behavior and sequential requests.
- Default 20-second delay plus up to 20 seconds of jitter.
- Maximum eight uncached videos per invocation.
- Retry cooldown enforcement and an explicit `--retry-blocked` route-change override.
- Circuit breaking on a detected IP block.

## Important limitations

- Published does not mean fully reviewed: 11 videos have approved public evidence but retain explicitly deferred proposals.
- Candidate extraction analyzes transcripts, not video frames. `transcript_inferred` moments remain non-looping until a separate visual interval is watched and verified.
- The review queue currently has a large formatting diff because it was regenerated after new candidate files were added; the widened round-trip writer should keep future unchanged candidates stable.
- The working tree also contains the earlier progress-page, workflow-name, ingestion-hardening, and queue-stability changes; preserve them together during review.

## Historical recommended next actions (superseded by the maintained backlog)

1. Review the 68 pending candidates video by video, prioritizing clean matches that add a second source or materially improve an existing article.
2. Reject duplicate labels and weak fragments explicitly rather than accepting them as semantic matches.
3. Create durable new concepts only where the material does not fit the existing hierarchy, especially push-flick mechanics and serve deception.
4. Manually inspect high-value visual intervals before enabling loops.
5. Review the complete working-tree diff before preparing the next commit message.

## Current next actions

1. Follow `docs/prioritized-backlog-2026-07-15.md` as the maintained planning source of truth.
2. Add excerpt-kind schema/validator and keep the quotation screen in CI; the P0-01 rephrasing pass and automatic guard are complete.
3. Document the lawful transcript-acquisition basis and add public source/removal handling.
4. Add canonical-to-publish freshness and TOC/anchor validation to CI.
5. Review the 28 deferred candidates and visually verify high-value loop windows before processing another large batch.
6. Implement public/private publication controls and a project-owned local export when the P0/P1 safeguards are ready.

## Video index navigation note

- The video index should expose a compact, per-video contents list rather than only concept chips. Contents links should resolve to the matching concept article and its timestamped evidence row, so the destination remains the source of truth for the moment.
- Grouped evidence rows may represent several citation IDs. Keep hidden anchors for the additional citation IDs so every timestamp listed in a video contents index remains a valid target.
- TOC review: concept/moment joins, timestamp ordering, de-duplication, labels, and link validation are deterministic; only optional semantic section naming would need an LLM proposal.
- The full TOC now lives on one static detail route per video; the library index keeps only a compact preview to avoid a monster page.
- Detailed video contents are intentionally linear by source timestamp; concept labels remain attached to each row instead of becoming the primary grouping.
- Evidence rows now use a flexible content column plus a separate action column; the evidence type sits inside the content block so excerpts cannot be squeezed by citation buttons.
