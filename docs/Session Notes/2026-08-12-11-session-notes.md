# Session notes — 2026-08-12 11:00

- Treat automation coverage and editorial completion as separate metrics; 99.9% automation-triaged does not imply content is review-complete.
- Audit topic accuracy at three boundaries: extraction labels, canonical concept resolution/navigation, and moment-level excerpt/reason relevance.
- Audit time accuracy separately for transcript provenance, spoken playback boundaries, and visually verified demonstrations.
- Preserve the existing dirty worktree and avoid starting a processing cycle during the review.
- Highest-risk defect: canonical promotion silently keeps the largest contiguous citation cluster while retaining a rationale synthesized from all candidate clusters; valid IDs therefore mask unsupported public claims.
- Freeze canonical/public automation under P0-08 through P0-10. Private proposal extraction may continue only when it cannot publish or mutate canonical decisions.
- Recovery order: restore the human gate; implement bounded overlapping extraction and no-silent-loss support; enforce complete source envelopes; build a published-content remediation gold set; reconcile the 460 automatic concepts; then rewrite summaries and ranking.
- Do not use automated-triage coverage as a content-quality KPI. Report human approval, semantic support, topic mapping, playback accuracy, and visual verification independently.
- A successful Astro build does not prove the local planning view includes every Markdown item when the page uses a curated ID map. Verify the rendered backlog for each newly created ID.
- Operator correction: human review is advisory/augmentative. Default semantic decisions should use Codex CLI under the same schema, transcript-ID, read-only, budget, audit, and fail-closed controls as extraction; deterministic validators remain authoritative for mechanical invariants.
- Implemented that correction: Codex now makes the semantic decision, while deterministic code owns segment membership, contiguity, duration, boundary, taxonomy, timestamp, and publication checks.
- The public contraction from 533 concepts/729 videos/5,892 moments to 73/51/1,119 is intentional quarantine, not data loss. Legacy YAML and queue history remain available for bounded re-adjudication.
- Restore a quarantined concept only after Codex accepts its topic independently. Do not restore its old heuristic evidence; add only the newly selected exact span.
- Queue drain is intentionally incomplete: 6,470 decisions require bounded, budgeted Codex passes. Do not hide this as human work or run an unbounded batch during release verification.
- Final release evidence: 74 tests, clean Ruff, zero Astro diagnostics, 146 pages, 73 approved public concepts, 51 public videos, and six representative HTTP 200 route checks.
