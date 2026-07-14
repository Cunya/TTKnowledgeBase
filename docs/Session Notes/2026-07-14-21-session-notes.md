# Session notes — 2026-07-14 21:00 EEST

## Current state

- Knowledge base: `table-tennis`
- Canonical concepts: 65 approved
- Source videos in published corpus: 27
- Published evidence moments: 687 excluding demo evidence
- Review queue: 284 accepted, 7 pending, 1 rejected
- Queue-integrity errors: 0
- Python tests: 17 passing
- Static pages: 52
- Codex extraction service tier: normal/default (no `fast` or `flex` override)

## Newly covered areas

- Push: compact action, racket angle, contact, and spin generation.
- Block: forearm angle, trajectory, placement, spin reading, on-the-rise timing, active block, and defensive rhythm changes.
- Backhand rip: distinction from the drive, backswing, and practice progression.
- Backhand loop: general mechanics, swing path, contact, spacing, body coordination, and backspin adjustment.
- Footwork and consistency: economical movement, body-height adjustment, direction reading, and control before power.
- Point construction: post-serve recovery, third-ball adjustment, match phases, opponent targeting, and serve planning.
- Serve receive: rhythm matching, sidespin control, compact responses, and short-versus-long decisions.
- Backlog consolidation: counter-loop, forehand drive, racket-contact drill, sidespin-backspin serve, and rubber-friction differences.

## Important limitations

- The 107 pending candidates still require editorial resolution.
- New evidence is transcript-reviewed but does not yet have manually verified visual demonstration windows.
- Visual status remains honest: transcript-inferred citations do not loop without a separate `visual_source`.
- Eleven concepts were single-source before the latest batch; source-diversity statistics should be recalculated before prioritizing the next ingestion round.
- Browser automation was unavailable during the last UI verification attempt, although Astro diagnostics and production rendering passed.

## Recommended next actions

1. Review pending candidates by source video and consolidate only evidence that improves an existing article or supports a durable new concept.
2. Select and manually verify visual demonstration windows for the new push, block, and backhand concepts.
3. Add a Recently added page so users can find newly processed material.
4. Implement retry-time enforcement before the next large YouTube ingestion batch.
5. Run a local visual QA pass for the table-tennis hierarchy and representative new concept pages.
