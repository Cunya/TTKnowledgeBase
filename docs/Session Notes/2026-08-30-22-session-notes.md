# Session notes — 2026-08-30 22:00

- A bounded Codex timeout is an expected per-candidate processing outcome, not a stage-level failure. Convert it to a typed, audited, retryable defer before it reaches the batch orchestrator.
- Keep the timeout's private audit record bounded and source-safe; expose only IDs, counters, status, and elapsed time through monitor progress.
- Keep transport-specific timeout conversion in `processors.codex_engine`; let `processors.pipeline` own queue mutation and batch continuation.
- Verification passed with 78 tests, Ruff, corpus validation/publish checks, and the Astro build. A future scheduled or manually authorized recovery cycle is still needed for live confirmation.
- The combined Windows launcher must not reuse a hidden monitor when fresh UI code is expected. It now owns startup/shutdown, replaces verified project services on start, and cleans both service trees during Ctrl+C cleanup.
