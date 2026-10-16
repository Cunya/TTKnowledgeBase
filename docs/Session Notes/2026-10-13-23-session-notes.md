# Session notes — 2026-10-13 23:00 EEST

- Root cause is identity collision, not changing source content. Match video + candidate ID + hash; preserve changed-content reset and legacy hash handling.
- Preserve `adjudication_provenance` as well as decisions/attempts; original rebuild omits it.
- Deferred proposals must remain retryable. Least-attempted selection avoids exhausting the same ten rows in a selected video pool.
- Production loop was enabled with two-minute cooldown; resume after verification.
