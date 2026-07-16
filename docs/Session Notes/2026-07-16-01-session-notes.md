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
