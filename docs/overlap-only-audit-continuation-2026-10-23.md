# Overlap-only audit continuation — 2026-10-23

The full audit had four advisory scope checks pending in addition to its factual and footage holds. The general repair coordinator treated overlap work as a reason to recheck every article claim. A scope-only path now avoids that repeated source audit.

Run `python -m processors.cli propose-published-overlaps --kb table-tennis --limit 4` with the repository virtual environment. It makes at most one configured-model call, uses only exact current topic definitions and overlap candidates, validates complete unique article coverage and saves private proposals with blank reviewer fields. It does not alter the audit ledger. Identical current input/profile/policy proposals are reused without another call. A reviewer must inspect the proposals, supply provenance and use the existing `record-published-audit` overlap-only importer; stale fingerprints and any claim decisions are rejected.

Live result: **one GPT-6 Luna/high call,20,662 tokens** (19,884input +778output). Reasoning tokens are included in output, not added twice. Private provenance: data/manifests/table-tennis/published-audit-overlap-proposals.json. No escalation, source-campaign spending reset or footage review occurred.

Independent editorial scope review accepted these distinctions:

- Forehand loop is the general stroke. Compact acceleration, backspin application, path/angle, timing, forward-brushing cues and spin/power comparisons have narrower distinct scopes.
- Forehand loop against backspin is a situational application; general looping, path mechanics, lunge stance and shot-choice comparison retain distinct editorial purposes.
- Forehand loop swing path addresses path/angle; Brush around the ball is a particular cue, general looping is broader, and backspin looping is situational.
- Post-serve recovery concerns the sequence and timing after serving. Ready position is general posture/readiness, and Control before power is a general power/rhythm principle.

All four scope advisories were recorded with exact fresh fingerprints and independent reviewer provenance. An exhaustive before/after assertion confirms **all380article claim/visual decision maps are exactly equal**. Only advisory flags/review history changed. This does not verify that every claim in these still-pending articles is true.

Current audit:369/380articles supported,3804/4183units supported,362pending and17classifiedneeds_footage;**overlap reviews pending:0**. All35actualvisualwindows remain unverified. The audit is incomplete. Source-planning cumulative spending limits and all other holds remain intact.

Tests cover exact/partial/duplicate response coverage, blank-reviewer import refusal,no pending work/no model call, no claim-state mutation and CLI cache reuse. Focused18tests/Ruff pass. Full release passed384 Python tests (111.95s),nine monitor tests,Ruff,reviewed/published validators,zero Astro diagnostics and638pages. Private receipt: media/overlap-only-release-2026-10-23-00.log.

Remaining blockers require complete footage observation and source-preserving editorial resolution, not repeated advisory or full-source model voting. Normal processing stays paused. P1-34/P1-51/P2-12 track the complete scope; the four cleared advisories are actual progress, not whole-article approval.
