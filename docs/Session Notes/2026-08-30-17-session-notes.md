# Session notes — 2026-08-30 17:00

- The scheduled task reaches deferred quarantine recovery through `run-cp.py` and `process-pending --retry-deferred`; it does not need a separate “quarantine release” command.
- A scheduler’s same-task `IgnoreNew` policy does not protect against a separately launched monitor process. A shared per-KB lock must be acquired by the common orchestrator or every entry point must use the same wrapper.
- Source-balanced selection is fair across sources but not across time: without an attempt cursor, cooldown, or rotation state, unresolved top-ranked videos can monopolize future 50-video batches.
- The live task has `StartWhenAvailable=false` and battery execution disabled; these are explicit scheduler policies that can delay a run after sleep, shutdown, or unplugging.
- The task uses `InteractiveToken`, so it is not a fully logged-out/background service; the configured user session must be available for the scheduled action to run.
- The shared lock now belongs to `run-cp.py`, eliminating the previous direct-task/wrapper lock mismatch. Selection now uses ledger-backed attempt history so source fairness is preserved across time as well as within a batch.
- The 17:23 and 17:45 retry cycles both failed while atomically replacing the private `llm-budget.json` ledger on Windows; the second cycle was stopped by the operator. The fix centralizes bounded replacement retries and uses per-process temporary JSON filenames to avoid stale cross-process `.tmp` collisions.
- Live monitor visualizations should read the existing private inventory/queue snapshot and active-stage output, keep labels tied to named units, and avoid adding writes while a processor cycle is active.
- For long captured Codex calls, emit privacy-safe flushed heartbeats from the subprocess boundary. A phase header alone cannot distinguish normal model latency from a hang; never stream prompt, transcript, or raw model output to the operator monitor.
