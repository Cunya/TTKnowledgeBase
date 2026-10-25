# Live shared-workflow benchmark — 2026-10-22

P1-51 / P2-12. First-article benchmark completed with unresolved findings; full-audit continuation is in progress. This is not corpus clearance.

The new `continue-published-repairs` coordinator automatically selected the remaining Forehand loop article. No article-specific content script or parent-agent source adjudication was used. Normal processing stays paused.

At 14:45 EEST the account showed 15% five-hour usage and 77% weekly usage. Both were below the configured 80%/95% stops. The CLI independently checked its connected account before model work; a later read showed 16%/77% with no block. No reset credits or account switch were used.

## First finite invocation

Command: `python -m processors.cli continue-published-repairs --kb table-tennis --max-calls 4` through the checked virtual environment.

| Measurement | Result |
|---|---|
| Exit | 0, stopped at the four-call limit |
| Wall time | 149.59 seconds |
| Campaign time | 138.81 seconds |
| Model calls | 4 |
| Exact cached jobs reused | 3 |
| Recorded processor tokens | 170,037 |
| Model / effort | `gpt-6-luna` / `high`, confirmed in saved provenance |
| Content outcome | Pending; no canonical article installed |

Three targeted draft jobs and the first bounded article-field proof job completed and were saved. The next invocation resumed the second field-proof job, rather than repeating the completed drafts. Full source ownership and context caps remain enforced. These figures measure a partial large-article repair, not articles per hour or the end-to-end final-review/application cost.

Private receipts: `media/luna-workflow-benchmark-2026-10-22-14.log`, its `-result.json`, the repair-plan checkpoint and model provenance under `data/manifests/table-tennis/`. Raw model/source data remain private.

## Continuation

The second four-call invocation completed at the call limit: four cached jobs reused, 148,519 tokens and 121.84 campaign seconds. A third invocation completed three independent verification calls (eight cached jobs reused), 100,359 tokens and 89.70 campaign seconds. Combined: 11 new calls and 418,915 processor tokens; no article installed yet. Source review retained 39 supported units, nine needing repairs and 11 needing footage. These findings are proposals, not new canonical approval.

The live run exposed premature coordinator parking after a progressing repair pass. The coordinator now parks only when the repair engine actually reports exhausted work, and invalidates legacy premature parking entries. A regression covers both resumption and migration; all 26 bundle/coordinator tests and Ruff pass. Full release verification will run again after live continuation is idle.

A fourth finite invocation is now using the existing bounded source-context completion stage. It automatically selected seven evidence records for context completion; no parent-agent caption editing or content judgment was used. Final source-review/application and release outcomes remain to be measured. The corpus baseline remains 370/380 supported articles, ten unfinished articles, 35 unverified visual windows and four pending overlap reviews. Footage requires actual full-clip inspection; a text-model result cannot clear that hold.

Dependencies and implementation: [shared workflow](shared-published-repair-workflow-2026-10-22.md), [consolidated backlog](prioritized-backlog-2026-07-15.md), [14h session](Session%20Logs/2026-10-22-14.md).

## First-article terminal outcome — 15:10 EEST

Seven finite invocations completed:36 new Luna/high calls,1,244,514 processor tokens,1,158.40 campaign seconds (19m18s; excludes coordinator startup/documentation time),20 exact job-cache hits across resumes and one reused verification unit. The original39 evidence records remain intact; no canonical application occurred. The final private proposal has41 supported units,16 footage holds (11 visual units plus five evidence claims), and two uncertain units. This is a blocked quality outcome, not a successful end-to-end installation benchmark or a demonstrated throughput improvement.

Nine evidence source-context completions were proposed automatically and independently checked. The coordinator will park the exhausted proposal and advance to other eligible articles; no parent-agent content decision overrides the unresolved findings. Fresh quota at 15:10 was31% five-hour/79% weekly, so another finite continuation group is authorized. Broader cost/replay acceptance under P2-12 remains open.

## Exhaustive remaining baseline coverage — 2026-10-22T16:06:20.396112+03:00

All five remaining written articles have complete private baseline unit-key coverage: Forehand loop59, Forehand loop against backspin64, Forehand loop spacing39, Forehand loop swing path139, Post-serve recovery56; total 357/357 units. These review the current source/repair proposals and do not approve canonical text.

Live continuation exposed selection starvation as well as premature parking. The coordinator now prioritizes incomplete current baseline coverage, then rotates by source-fingerprint visit count. It preserves explicit-origin and pending-bundle/transaction priority.28 focused regressions and Ruff pass; full release rerun remains pending until jobs idle. Live evidence: it advanced from Backspin to Spacing, Swing path and Post-serve recovery, then resumed Swing path at audit8 to finish its large baseline. No parent-agent content scripts or source adjudication were used.

## Saved quota-stop checkpoint — 16:21 EEST

The five-hour quota guard stopped further model calls at 80% usage; weekly usage was87%, below its95% stop. Current window reset:19:27 Helsinki, ten-minute grace starts19:17. Resume only after a fresh guard check permits it; no reset credits/account changes were used.

Across22 finite invocations:138 new GPT-6 Luna/high calls,5,003,915 processor tokens,5,007.20 campaign seconds (83m27s; excludes coordinator/documentation time),59 exact job-cache hits and one reused verification unit. All five remaining articles have complete private baseline coverage of 357/357 units. Repairs and independent verification remain incomplete. No canonical article changed or was newly approved/published. The public approval ledger remains370/380 supported articles,3811/4185 supported units, ten unfinished articles and 35 actual visual windows unverified. No footage was watched.

| Article | Baseline units | Saved private stage |
|---|---:|---|
| Forehand loop |59/59|Exhausted exceptions:41 supported proposal units,16 footage holds, two uncertain|
| Forehand loop against backspin |64/64|Repair verification pending; nine automatic source completions|
| Forehand loop spacing |39/39|Exceptions:27 supported proposal units, six needing fixes, two uncertain, four footage holds|
| Forehand loop swing path |139/139|Targeted repair drafting checkpointed|
| Post-serve recovery |56/56|Field-proof assembly deferred by quota guard|

The next coordinator invocation resumes the saved work with coverage-first fair rotation. Do not repeat the benchmark from scratch, hand-edit captions, stamp private support verdicts into public approvals, or promote unresolved proposals. Full release verification of the three orchestration fixes is running; result to follow. The benchmark did not establish lower end-to-end token cost or successful live application. P2-12 performance acceptance remains open.

Private exhaustive receipt: `media/luna-workflow-live-final-2026-10-22-16.json`; per-job logs/checkpoints/provenance remain ignored.

Final verification at 16:27 EEST: standalone full release gate passed 367 Python tests in233.83s, nine monitor tests, Ruff, reviewed/published validators, zero Astro errors/warnings/hints and 638 pages. Receipt: `media/luna-workflow-live-release-2026-10-22-16.log`. This validates the orchestration code and existing published corpus; the live benchmark did not reach safe new-content application. All35 visual windows remain unverified; normal processing stays paused. No staging/commit/push.
