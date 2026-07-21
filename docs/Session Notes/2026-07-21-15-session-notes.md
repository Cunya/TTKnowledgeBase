# Session notes — 2026-07-21 15:25 EEST

## Navigation audit

- Reviewed all 371 approved concept placements.
- Corrected eight clear semantic parent mismatches in the table-tennis navigation.
- Kept intentional cross-listings and ambiguous placements where the reviewed evidence supported them.
- Recorded the audit in `docs/concept-navigation-audit-2026-07-21.md` and completed backlog item P1-18.
- Verified navigation coverage, publish validation, 48 tests, Ruff, and Astro build through `scripts/verify-release.ps1 -Kb table-tennis`.

## ASR boundary follow-up

- Compared the one-video ASR and YouTube caption tracks and found approximately 3% word-level disagreement with near-identical duration coverage.
- Proposed using private ASR word timings/confidence for audio-boundary triage only; caption segment IDs remain authoritative and reviewers decide topic/context changes.
- Recorded the design in `docs/asr-audio-boundary-verification-2026-07-21.md` under backlog item P1-14.
