# Session notes — 2026-10-14 21:00 EEST

- Latest task: implement P1-51. Code paths are present; finish live calibration and the required full release gate. No scheduler/model/profile/budget changes.
- Duration exclusions are mechanical and reversible, not false-content judgments or semantic completion. Original baseline379 remains in history; current public-eligible378,4 cleared/374 pending.
- Preserve quotes and check YAML through the same safe reader used by the pipeline before replacing canonical/archived files. Raw flow-list colon scalars can parse differently through round-trip and C readers. Explicit rollback restores only known before/after bytes and rejects unrelated editor changes.
- Code changed normal acceptance: a separate source verification stage must pass; quarantined topic restoration also reviews existing fields and defers approved relations needing whole-article review. Pause flag prevents normal processing until deliberately released.
