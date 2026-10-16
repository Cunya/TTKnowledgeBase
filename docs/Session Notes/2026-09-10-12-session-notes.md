# Session notes — 2026-09-10 12:00

- Distinguish checkpoint interval from the actual automatic adjudication batch size.
- Cap each orchestrated `process-pending` stage at ten candidates so the progress denominator matches the requested batch size.
- Emit an explicit live log entry after each atomic checkpoint is persisted.
