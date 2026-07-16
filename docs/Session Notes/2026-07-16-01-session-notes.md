# Session notes — 2026-07-16 00:10 EEST

## Current state

- Published table-tennis corpus: 73 concepts, 121 videos, 1,814 evidence moments.
- Review queue: 1,060 accepted, 139 deferred, and 1 rejected; no candidates remain pending.
- Source progress: TT SpinMaster has 99 configured/eligible/extracted videos and 98 published; GlobalTTStudio has 23 eligible and published videos plus 8 members-only configured entries.
- Visual evidence remains conservative: 35 proposed visual intervals and 0 manually verified demonstrations.
- The 00:15 review is a historical snapshot: it found 403 repeated-excerpt groups covering 936 moments, six concepts without outgoing relations, seven empty navigation leaves, and three single-source concepts.
- The backlog now includes project-qualified Pages URL verification (P1-10) and UTF-8 mojibake cleanup with a CI guard (P1-11). A dated review is recorded in `docs/project-review-2026-07-16-00.md`.
- The controlled continuation batches processed fourteen public GlobalTTStudio videos in total, added 112 focused evidence moments, and left 36 candidates deferred. Six members-only videos were excluded without retrying across those batches.
- Visible evidence titles now remove transcript-reporting scaffolding. For example, “The transcript explicitly defines acceleration as a slow-soft backswing followed by a fast release” renders as “Acceleration: a slow-soft backswing followed by a fast release.” Canonical excerpts and provenance remain unchanged.
- Controlled batch 15 added two public GlobalTTStudio videos and four confirmed members-only entries. The public pair added 23 accepted candidates and 30 evidence moments; 5 candidates were deferred.
- Current published state: 73 concepts, 121 videos, and 1,814 evidence moments. The cached queue is fully resolved; review the 139 deferred candidates and 35 proposed visual intervals before another expansion batch.
- Added `docs/moment-boundary-analysis-study-2026-07-16.md` after reviewing the span resolver, caption timing, optional local ASR, prosody, and semantic-boundary options. The study recommends caption-only sentence snapping and short-window flags before any audio alignment; no processing behavior changed.
- Extended the boundary study with an automation split: scripts own timing, alignment, validation, metrics, and links; the configured LLM may classify ambiguous same-topic/meaningfulness cases and draft editorial wording, but cannot invent timestamps or approve publication.
- The study's staged plan now repeats that split directly in Phases 1-5, so each phase states whether LLM use is absent, optional, targeted, or prohibited at its publication gate.
- Implemented P1-15: `processors.llm_budget` now enforces configurable daily/per-task token reservations across extraction, rephrasing, and benchmarks; exhausted tasks defer before Codex execution and the local `llm-budget` command reports usage.
- Added a local-only LLM budget view to `/progress/`: daily and per-task progress bars, usage/remaining tokens, call and deferral counts, ledger state, and the configured timezone. Production builds continue to omit the progress page and therefore cannot expose private budget data.
- Refreshed documentation after the GlobalTTStudio metric audit. The source state is 31 configured entries, 23 eligible/public entries, and 8 members-only entries; the local progress page now labels these stages separately.
- Reworked `README.md` around the MomentGraph name and documented the current architecture, pipeline, LLM budget, public/private boundaries, GitHub Pages deployment, multi-KB workflow, future offline scope, and release checks.
- Added denominator-aware percentages in parentheses to the progress summary's workflow-stage counts and documented the calculation in the table note.
- Reviewed daily timer operation in `docs/daily-pipeline-automation-review-2026-07-16.md`. The individual Python stages and Codex CLI calls are usable without the ChatGPT app, but a timer-safe orchestrator is still missing. The review records the extraction idempotency gap, workset/lock/run-manifest needs, scheduler environment requirements, and the boundary around human review and public deployment.
- Added a README section for the table-tennis KB: source channels and availability, forehand-loop-centered scope, shot hierarchy, evidence types, per-video TOCs, and editorial safeguards.
- Reconciled recent studies into `docs/prioritized-backlog-2026-07-15.md`: added a study mapping table, expanded deterministic TOC follow-up, and added P1-17 for excerpt classification and overlap-regression protection. The recommended sequence now includes P1-14, P1-16, and P1-17.
- Added the local-only `/backlog/` operator page. It parses the consolidated Markdown backlog into priority lanes, counts, status pills, expandable rationale/work/dependency/acceptance sections, and a production exclusion notice. Local and production-flagged Astro builds both pass; production omits the route.
- Resolved the reported local `/backlog/` 404: port 4321 was serving Astro preview from the prior production artifact. Rebuilt the local artifact; the route now returns HTTP 200 and includes the backlog content.
- Consolidated operator navigation into one local-only `/dashboard/` link. The dashboard links to Progress, Backlog, Pipeline, and Recent while the focused routes remain available directly. Production builds remove the dashboard and all operator pages.
- Reworked the local-only `/backlog/` page around feature outcomes rather than separate P0/P1/P2 lanes. Four workstreams now group the related items, while every row keeps its priority and status badge; section spacing was tightened to reduce the gap between a feature and its subitems.
- Added a study-to-backlog documentation contract to `AGENTS.md`, `docs/pipeline.md`, `docs/operations.md`, and `README.md`: studies must update the canonical Markdown backlog, rebuild/verify the generated local HTML backlog, and update relevant docs plus the session log/notes.
- Added published and local table-tennis KB links to the README for easier discovery.
- Updated the backlog hierarchy to feature area → feature → P0/P1/P2 item, with nested progress summaries and responsive indentation.
- `cp` drained the cached queue with no eligible candidates remaining; another scrape was deferred because the open P0 trust gates still prohibit expansion.
- After clarifying that `cp` should continue with a controlled batch when local work is empty, ingested and processed `D1cBF0nsjKo` and `Kg4hLYnEbAs`. The batch added 12 accepted evidence moments and deferred 6 weaker candidates; source progress and P1-02 were refreshed.
- Synchronized the local progress page with batch 16 so its totals, latest-batch note, backlog counts, and source inventory no longer show the previous 121-video/1,814-moment snapshot.

## Maintained planning sources

- `docs/prioritized-backlog-2026-07-15.md` remains the consolidated backlog.
- `docs/source-video-progress.md` remains the source-state snapshot.
- `docs/lessons-learned.md` and `docs/refactorings.md` remain the process-improvement notes.

## Next safe work

1. Review deferred candidates and visual proposals before broadening acquisition.
2. Keep public/private and source-removal safeguards ahead of large-scale publishing.
3. Prefer generated progress metrics over hand-maintained snapshots as P1-04 is implemented.
4. Fix deployment URL/encoding findings before treating the static site as release-clean.
5. Review the 139 deferred candidates and 35 proposed visual intervals before another expansion batch.
6. Treat P1-14 as the next boundary-quality implementation item: measure mid-sentence and non-meaningful short moments before changing defaults.
7. Review the new LLM budget defaults before the next extraction batch; adjust `config/processors.yaml` intentionally rather than bypassing the guard.
8. Implement P1-16 in dry-run mode before registering any Windows Task Scheduler job; do not start unattended acquisition until the lock, workset, exit classes, and private run manifest exist.

## 2026-07-16 16:35

- P1-14 Phase 1 is now script-only: caption units, boundary flags, snapped proposals, and corpus metrics share one module.
- `process-pending` defers flagged new candidates; public reviewed evidence is not widened automatically.
- Baseline report: 1,826 non-demo records evaluated; starts mid-sentence 16.4%, ends mid-sentence 17.5%, under four seconds 3.5%, needs context 31.9%.
- Next boundary work is review/gold-set calibration and a second measured pass; audio/prosody and LLM semantic suggestions remain optional later phases.

## 2026-07-16 16:38

- P1-14 verification passed: publish/validate-published, 34 tests, Ruff, Astro diagnostics/build, local backlog/progress HTTP checks, and diff hygiene.
- Boundary JSON is private and now ignored; the Markdown report is the durable baseline. No commit or staging was performed.
- Re-ran the final 207-page Astro build after publishing; diagnostics remained clean.

## 2026-07-16 16:42

- Backlog rows now use status colors and active-first ordering inside each feature; completed items are grouped at the end.
- Fixed the parser precedence bug where a planned item's explanatory text containing “complete” could mark it complete.
- Local route, build, Ruff, and diff checks passed. No commit or staging was performed.

## 2026-07-16 16:55

- Project counts must be generated by the processor, not edited by an LLM or copied into page templates. `processors.progress` centralizes this calculation and `publish` refreshes the JSON snapshot.
- Keep source IDs aligned with `config/kbs/<kb>/sources.yaml`; display names are not stable identifiers. The page initially used display-like IDs and correctly fell back, which hid the generated values until the IDs were corrected.

## 2026-07-16 16:58

- Updated the session record after the progress-count implementation. Current totals remain processor-generated; do not hand-edit page or documentation counts.
- Verification remains complete: published artifacts valid, 34 tests passed, Ruff passed, Astro build passed, and local management routes respond successfully.

## 2026-07-16 17:05

- P1-14 now has a deterministic, stratified 24-item gold-set worksheet and a validator. It contains no transcript text and leaves all actions pending until a reviewer inspects the source intervals.
- Do not mark P1-14 complete or claim boundary-rate reduction until the worksheet decisions are recorded and a second report is generated.
- Final verification passed at 17:09: 35 tests, Ruff, published validation, Astro diagnostics/build, and diff hygiene.

## 2026-07-16 17:12

- The dashboard’s management links were compressed into one row because the shared global `nav` rule applies `display: flex`. Added `display: grid` and `width: 100%` to `.dashboard-index`; the child links now form four full-width rows while retaining the existing responsive link grid.
- Verified `/dashboard/` at the local server: four links have distinct vertical positions and equal full-width bounds. Astro diagnostics/build passed (0 diagnostics, 207 pages). No commit or staging was performed.

## 2026-07-16 17:17

- Per-video TOCs now begin with reviewed concept summaries, ordered by the first timestamp where each concept appears. Each summary links to the concept overview and its first evidence moment; the existing chronological moment list remains below it.
- Summary copy is sourced only from the published concept definitions (`short_definition` and optional `detailed_definition`), so this UI change does not invent or re-quote transcript text.
- Representative local route rendered 6 summaries and 14 moments. Astro diagnostics/build passed with 0 diagnostics and 207 pages. No commit or staging was performed.

## 2026-07-16 20:49

- Smoke-tested the concept-summary presentation on `counter-loop` and on video `G7eiadOxN8E`.
- The multi-concept route rendered 12 summaries and 34 moments. All summary rows contained text plus valid concept-overview and first-moment links; the local route returned HTTP 200.
- No code changes, commit, or staging were performed during this test.

## 2026-07-16 21:06

- The per-video summary implementation did not make the concept article itself visibly labeled as a summary. Added a `Summary` Contents link and section to concept pages, using only reviewed definition fields.
- Counter-loop now exposes the Summary heading and definition before its separate three-moment evidence library. Build passed with 0 diagnostics and 207 pages; local route returned HTTP 200.
- No commit or staging was performed.

## 2026-07-16 21:10

- Clarified that a concept Summary should be an essay synthesizing the information across its moments, not only a general definition. Added optional reviewed `evidence_summary` support across the model, published data type, and concept article UI.
- Counter-loop now has a source-grounded essay covering its patient topspin exchange, pause/rotation/power timing, physical endurance, and rhythm cues. The core concept remains separately labeled.
- Other concepts fall back transparently to their reviewed definition until a moment synthesis is authored; no unsupported prose is generated by the UI.
- Fixed YAML quoting with a folded scalar. Validation/publish, 35 tests, Ruff, Astro diagnostics/build, local HTTP route, and browser checks all passed. No commit or staging.

## 2026-07-16 21:13

- The requested essay-style summary should exist for every concept, not only Counter-loop. Inventory: 73 concepts have approved evidence reasons; only one currently has `evidence_summary`.
- Plan: add a deterministic, non-LLM builder that synthesizes approved reason fields into concise paragraphs, populate missing canonical summaries, and leave the hand-reviewed Counter-loop essay unchanged.

## 2026-07-16 21:19

- Implemented the deterministic `build-evidence-summaries` command and populated the 72 concepts that were missing moment-based essays. The existing Counter-loop summary was left unchanged.
- The generated paragraphs use only approved evidence reasons, avoid raw transcript quotation, and can be regenerated for future missing concepts without spending the LLM budget.
- Full validation, publish, tests (38), Ruff, Astro build (207 pages), and local Active block route verification passed. No commit or staging.

## 2026-07-16 21:22

- Removed remaining transcript-framing phrases and quotation marks from generated summary blocks, preserving the approved evidence records.
- Added a regression assertion that all 73 reviewed concepts have an evidence summary. Focused tests pass (4); the full validation/build cycle remains green.

## 2026-07-16 21:41

- Completed incremental summary maintenance. Generated essays now store a hash of the approved evidence inputs, and publishing refreshes only stale generated essays.
- Hand-authored summaries are identified by the absence of that hash and are preserved. The standalone CLI supports an explicit `--refresh-generated` operation.
- Fixed orphan-hash insertion handling and added stale-refresh tests. Full validation/publish, 40 tests, Ruff, and the 207-page Astro build passed. No commit or staging.

## 2026-07-16 21:49

- Updated generated summary wording to present ideas directly, without source-reporting leads. The format version forces a controlled refresh of all generated essays while preserving Counter-loop’s hand-authored text.
- Added a corpus regression check for attribution terms. Full validation/publish, 41 tests, Ruff, and the 207-page Astro build passed. No commit or staging.

## 2026-07-16 21:50

- Repaired the remaining coordinated-clause wording in generated summaries and refreshed the corpus. The push-technique essay now directly states the racket-angle, compact-force, brushing, timing, and placement ideas without source attribution.
- Final validation/publish, 41 tests, Ruff, and the 207-page Astro build passed. No commit or staging.

## 2026-07-16 22:14

- Replaced fragment-joining as the quality path with batched Codex synthesis over approved evidence reasons. The single- and batch-call prompts require coherent 2–4 sentence paragraphs without source attribution or transcript quotation.
- Added `summary` budget configuration, private audit provenance, generator metadata, and a validation gate. All 72 generated essays were rewritten; the Codex ledger recorded 19 summary calls and 296,102 actual tokens. No commit or staging.
