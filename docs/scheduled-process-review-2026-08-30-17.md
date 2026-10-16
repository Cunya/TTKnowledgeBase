# Scheduled processing review — 2026-08-30 17:00

## Verdict

The registered 21:00 task is correctly targeted and will reach the deferred Codex recovery path, provided the workstation is on AC power and the task is not missed. It will process a bounded, source-balanced batch and publish only after validation. It is not yet fully robust against overlap or retry starvation.

## What the scheduled call executes

The live Task Scheduler registration is enabled as `\\MomentGraph Table Tennis Daily Processing` and runs:

```text
D:\Code\AIAssistedProjects\TTKnowledgeBase\.venv\Scripts\python.exe scripts/run-cp.py --kb table-tennis
```

Its working directory is the repository root. The task runs daily at 21:00 Europe/Helsinki, uses `MultipleInstances=IgnoreNew`, and runs with an `InteractiveToken` principal, so the configured user session must be available. It last returned exit code `1` on 2026-08-29 because of the now-fixed Codex response-schema error. The next scheduled run is 2026-08-30 at 21:00.

`run-cp.py` rebuilds the private inventory, selects up to 50 source-balanced videos in `needs_adjudication`, and runs `process-pending --retry-deferred --video-ids ...`. It then rebuilds the review queue, refreshes summaries, and publishes only approved, validated content. The new item-level schema-error handler allows that batch to continue when one model response is malformed.

## Findings and resolution

1. The registered task bypassed `scripts/run-daily-processing.ps1`, so the wrapper's per-KB lock and `daily-processing.latest.json` were not involved. This is resolved in code by a shared OS-level lock inside `run-cp.py`; Task Scheduler, the monitor, the wrapper, and manual invocations now contend on the same lock. This was tracked as P1-37.
2. The selector was fair across the three sources, but had no temporal rotation. It now carries per-video adjudication history in the private ledger and prioritizes untouched/less-attempted work before repeated retries. This was tracked as P1-38.
3. The task does not start when the machine is on battery, does not catch up after a missed trigger, and requires the interactive user session. This is an explicit current scheduler policy, not a data-integrity failure, but it can delay recovery.

## Safe operating conclusion

At the next run, keep the interactive monitor loop stopped. The scheduled task should process the first 50-video adjudication workset, defer any still-unsafe candidates, continue through the batch, and publish the unchanged safe snapshot if no candidate is accepted. A successful publish may update the snapshot timestamp without increasing counts; only newly accepted evidence/concepts should increase public counts.

No scheduled run was started during this review. The new behavior is covered by a cross-process lock test and a workset-rotation test; live observation remains for the next scheduled run.
