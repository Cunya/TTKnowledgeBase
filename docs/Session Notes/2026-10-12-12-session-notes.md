# Processing throughput review notes — 2026-10-12 12:00

- Distinguish exact mechanical savings from prompt/selection changes requiring quality evaluation.
- Candidate selection slices queue order after a fair video pool; video ordering may be discarded.
- Boundary validator has complete-unit knowledge absent from the adjudication prompt. Retries do not receive the previous boundary failure.
- Final checkpoint rewrites every concept after the tenth-item checkpoint, including unchanged documents.
- Read-only measurement only; no live Codex experiment or runtime changes authorized by this review.

- Measurement: one queue dump 14.94s; all-concept dump 5.07s; latest cycle about 292s. First change should eliminate redundant successful-exit persistence while keeping interruption checkpoints.
- Most deferrals remain legacy unreviewed work (3,720 quarantine + 1,569 return-to-automation reasons); only 149 currently record boundary failures. Avoid overstating repeated-failure scope.
- P1-44/P1-45/P1-46 added; P1-38 follow-up reopened; report and operations updated. Astro build and live/built backlog coverage passed.
- Monitor service exists and loop is stopped; verify API instead of relying solely on process-regex matching.

- P1-44 implemented after user authorization. Existing dirty set plus partial-batch remainder suffices; no new state machine/model/prompt/threshold changes.
- Full release gate passed: 127 tests, Ruff, all validation stages, Astro diagnostics/build. Real reviewed YAML and published knowledge hashes matched before/after verification.
- Temporary-copy ten-defer replay: 47.63s -> 28.08s; saved 19.55s with identical inputs/semantic outputs. Model calls stubbed; before-then-after cache effects possible. Live production speedup remains unmeasured.

- Monitor-history bug: page polling owns history writes; scheduled runs without a viewer leave no observations. Use ledger generation as the durable writer and the monitor as a reader to avoid cross-runtime lost updates.
- Recover only real counts/timestamps from latest manifest. Do not backfill missing days from present counts. Time axis must use elapsed time, preserve a boundary observation, and label missing history.
- P1-47 complete: 133 Python tests and five Node chart tests plus full release gate passed. Restarted idle service renders 11 actual line paths; observed coverage begins October 11, 21:00 EEST. Browser polling no longer writes private history.
