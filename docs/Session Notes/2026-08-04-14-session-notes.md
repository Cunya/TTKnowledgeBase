# Session notes — 2026-08-04 14:20

- Current issue is not that `en` is globally wrong: the existing default succeeds for many videos.
- The safe fix is ordered fallback selection: try exact configured codes first, then a regional variant such as `en-US` only when no exact requested track exists.
- Do not treat YouTube's translation-language list as proof that an original `en` track exists.
- Keep the monitor's active `run-cp.py` cycle isolated while changing the ingest implementation.
- Implemented shared exact-then-regional source-caption selection and covered it with offline tests; the full test suite and Ruff pass.
- Stable validation, publish, published-artifact validation, Astro build, and local backlog verification passed before restarting the 15-minute monitor loop.
- Resource monitor improvement is implemented as a Windows total CPU/memory snapshot with rolling percentage bars/sparklines; the detailed process list remains available.
- Live verification passed after a safe monitor restart; the loop is active again.
- Final Astro build and monitor health check passed; no active processor child was running at the final check moment.
- Operational audit confirmed 85 persisted member-only retry records, all with matching classification/availability and exact 72-hour future cooldowns; the latest cp discovered batch had no cooldown overlap and selected no videos.
- Restored the monitor's next-process countdown: the Run State panel now updates every second with remaining time and the exact local start time, while active cycles show their start time. The 15-minute loop remains running.
- Renamed the monitor control to “Cooldown between runs (minutes)” and aligned the internal scheduling terminology; the existing start request remains backward-compatible.
