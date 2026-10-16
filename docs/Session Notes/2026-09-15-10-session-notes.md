# Session notes — 2026-09-15 10:00

- Investigating readable monitor logs and periods with no output.
- Backlog link: P1-40 observability and progress reporting.
- Keep stage markers machine-readable while adding operator-facing explanations and elapsed durations.
- Verified the live child output after the next scheduled cycle started: stage purpose, 15-second idle heartbeat, and the correct video ID were present. The existing monitor process was intentionally not restarted mid-cycle.
- Recorded the concept-gap review: the latest completed cycle added evidence to existing approved concepts, while a raw `create_new` proposal was deferred by deterministic boundary validation before canonical mutation. No backlog item was warranted.
- The failed 07:39–07:47 UTC cycle exposed an ordering bug: automatic navigation placement ran before generated evidence summaries, so an approved Codex concept could be left unplaced and abort publish. Placement now also uses aliases, facets, evidence excerpts, and evidence reasons; the follow-up 07:50–07:58 UTC cycle completed successfully.
- Release gate passed after the fix: 90 tests, Ruff, Astro diagnostics/build, reviewed-corpus validation, sanitized publish, and published-artifact validation.
- Added allowlisted failure summaries to the monitor lifecycle log; syntax and diff checks pass. The monitor remains stopped and will load this change on its next start.
- Final release gate passed again after the monitor change, including 90 tests, Ruff, Astro diagnostics/build, and published-artifact validation.
- Rebuilt the Astro app after the final backlog timestamp update; 352 pages generated with no diagnostics.
- The idle monitor process could not be replaced because the local execution policy blocked that process operation; no overlapping service was started, and the source change is ready for the next normal restart.
- Clarified the live decision cards and chart group to say `concept proposals`; restarted the idle monitor and verified the new API labels and descriptions while leaving the processing loop stopped.

- Split adjudication progress into three scopes: current ten-candidate pass, eligible retry candidates in the selected source-balanced video pool, and the full retryable queue. The monitor now renders the full backlog as emaining/starting-total, making the cross-run decrease visible without treating the selected-video pool as work processed in one pass.
- Updated P1-40 and P1-28 backlog evidence plus README/pipeline documentation. Focused pipeline/CLI tests (27), Ruff, and Node syntax checks passed; the active monitor loop was not restarted.


- The first live cycle with the new counters resolved 4 candidates, deferred 4, rejected 2, and reduced the full retry backlog from 5883 to 5878 during adjudication; the queue snapshot now reports 5876 deferred proposals after rebuild.
- That cycle exposed one unrelated publish validation failure for an unplaced approved concept. Added concept-stiff-arm-motion-limits-power-generation under power-and-coordination; validate, publish (213 concepts), validate-published, 90 tests, Ruff, and the Astro build (370 pages, zero diagnostics) now pass.
- Stopped the loop while idle and restarted the monitor service so the new progress parser is loaded; it is reachable on port 4322 with the loop stopped.


- Corrected the full-backlog scope after observing a pending proposal move to deferred: retry passes admit pending, deferred, and human-advice decisions, so the monotonic full counter now includes all three. Final validate/publish/published validation, 90 tests, Ruff, and Node syntax checks pass; the monitor is restarted idle with its loop stopped.


- Restarted the loop and confirmed the live run uses the three explicit scopes: x/10 current pass, selected-video pool 423, and full adjudication backlog 5963/5963 decreasing to 5959/5963. The ten-candidate cycle completed successfully and published 213 concepts; monitor loop is active between cycles with no active child.


- Rebuilt Astro after the final backlog wording update; diagnostics reported zero errors, warnings, or hints and the static build completed 371 pages.


- Added one shared stage-count calculation and reused it for runner output, private stage manifests, current-stage UI labels, and whole-cycle progress; no separate per-UI counter was introduced.

- Live verification after restarting the monitor showed `Stage 1/4` in the stage header, current-stage API, progress label, and heartbeat. The latest cycle passed the previously missing navigation placement and is still processing its ten-candidate retry stage.

- Final checks after the navigation repair: 90 tests passed, Ruff passed, Node syntax passed, Astro diagnostics were zero, and the static build generated 384 pages. The monitor loop was restarted with the 15-minute cooldown and the next cycle uses the numbered stage runner.
- Post-cycle `validate-published` confirmed 225 concepts and 133 videos.

- Latest log review found a Stage 4 publish failure caused by two missing navigation placements. Both were repaired, the full verification suite passed, and a fresh monitor cycle completed successfully with the retry counter reset.
- Backlog view rebuilt after recording the recurring navigation-placement finding. Monitor is idle between scheduled cycles with `lastOutcome: completed`, `retryCount: 0`, and 257 published concepts.
