# Normal processing reviewed against the full audit

Reviewed on 16 October 2026. Scope: extraction, candidate adjudication, independent verification, canonical promotion, summaries, excerpt rephrasing, taxonomy and pause boundaries. The initial review changed no production behavior. The user subsequently authorized the P1-53 fixes; implementation and verification are recorded below. No model calls ran and processing remains paused.

## Findings

### 1. P1 — Deterministic summary cleanup can invent causality

Location: `processors/evidence_summaries.py:68`.

The cleanup replaces “with the coach noting that” with “because.” A controlled example transforms “Keep the racket close to the body, with the coach noting that the ball is fast” into “Keep the racket close to the body, because the ball is fast.” The original reports two observations; the result asserts why the instruction applies. The full audit has already rejected invented causal bridges between nearby observations.

This runs in the default deterministic summary producer, including normal publication refreshes. It is not made safe by avoiding an LLM. Smallest fix: remove the causal substitution and preserve a neutral separation, with a regression asserting that cleanup does not introduce a causal relationship. Avoid broad automatic grammar rewriting of reviewed knowledge.

### 2. P1 — Final excerpt and Codex-summary rewrites bypass source verification

Locations: `processors/pipeline.py:222`, `processors/pipeline.py:240`, `processors/evidence_summaries.py:277`.

Excerpt rephrasing checks length, quotation marks and remaining transcript overlap, then replaces the canonical excerpt while retaining approval. It does not verify the new wording against its owned rows. A controlled rephrase response containing unrelated universal forehand advice passed those checks and remained approved with the original ready-position citation. This proves a missing gate, not that a real model necessarily returns that example.

The optional Codex summary writer similarly checks formatting and reporting words before writing generated prose; it does not independently verify the final summary against selected transcript support. Its inputs are sampled reasons and labels, not actual owned captions. Normal `run-cp.py` uses deterministic summaries, so the Codex-summary branch is an optional command, while excerpt rewriting is reachable through publication's opt-in automatic rephrase stage.

Smallest fix: treat semantic rewrites as proposals and use the existing shared verifier on their final values and exact source IDs before canonical replacement. Retain the original on unsupported, uncertain, budget or transport failure. An unavailable verifier must not silently downgrade to formatting checks. Mechanical summary cleanup should preserve meaning rather than create new claims.

### 3. P1 — Direct summary writes bypass the audit pause and KB lock

Location: `processors/cli.py:324`.

`build-evidence-summaries --write` reaches both canonical writers without checking the published-audit pause or acquiring the per-KB run lock. Normal `run-cp.py` and automatic publication refresh are paused, but this direct command remains a bypass. A CLI test with the real pause marker present reached a mocked writer and returned success. No actual canonical write occurred in the test.

This can change the fixed audit target or race another KB writer. Smallest fix: enforce the existing pause and shared lock around both summary-write engines, leaving preview read-only. Test paused writes and lock contention for both engines. The underlying summary writer also uses direct `write_text`; reuse the existing atomic replacement pattern when touching that path.

Coordinate lock ownership with `scripts/run-cp.py:229`, which holds the KB lock while invoking child CLI stages. Simply adding a second lock acquisition inside the summary child would reject the normal runner's own stage. The fix must protect direct commands while retaining safe runner ownership, with an integration test for the complete cycle. Do not add an unverified “skip lock” switch.

### 4. P2 — New concept type is saved without independent verification

Locations: `processors/pipeline.py:817`, `processors/pipeline.py:890`.

New-concept verification requests excerpt/reason, label, definition and facets. It omits `concept_type`, although the accepted producer value is written into approved canonical YAML. A temporary fixture supplied `processing_novelty` as the type; the pipeline saved it as approved without including a type unit in the verifier request. The full audit has already encountered processing-oriented topic classifications that should not be public instructional metadata.

Smallest fix: include the proposed type in the existing verifier's unit coverage and article payload. Judge its editorial fit rather than requiring a literal taxonomy word in the transcript. Do not introduce table-tennis-only type rules into shared processors. Also supply domain-owned facet meanings to the producer/verifier: the current taxonomy gives allowed values but does not explain that `distance: close` means player-to-table distance, rather than racket-to-body proximity. This semantic-vocabulary gap is already tracked under P1-51.

## Safeguards already present

- Normal candidate processing already calls the shared independent verifier on final selected rows; it does not rely only on producer confidence.
- Per-citation source ownership, incoming/outgoing roles, necessary qualifiers, causal inference and public review scaffolding are covered by the shared verifier rules.
- Invalid IDs, dispersed spans, boundary problems and out-of-vocabulary new facets are rejected or deferred.
- New concepts do not receive an inferred difficulty rating or aliases by default.
- Transcript-based processing does not mark footage verified or enable a visual loop.
- The normal runner and candidate command respect the current audit pause; the gap above concerns direct summary writes.

These safeguards reduce recurrence, but the audit's real false acceptances and excessive rejections show that two model passes alone are not a general accuracy guarantee. Retain the existing P1-34 frozen source controls and final source review until the ordinary workflow demonstrates acceptable accuracy. No recommendation here requires a more expensive model or another whole-corpus rerun.

## Recommended order

1. Remove the causal cleanup and close the summary pause/lock bypass.
2. Require exact-source verification for final semantic rewrites.
3. Complete new-concept metadata coverage and domain-owned facet meanings.
4. Replay the audit's actual negative and positive controls before resuming normal generation.

Work is tracked under P1-53, with P1-33/P1-34/P1-51 dependencies in the [consolidated backlog](prioritized-backlog-2026-07-15.md). The full audit remains at 116/377 supported articles and 261 pending; these review findings add no coverage or approvals.

## Verification and limits

### Authorized P1-53 implementation

Implemented all four reviewed fixes: neutral summary cleanup rather than invented causality; shared exact-source verification before final excerpt/Codex-summary replacement; pause/KB-lock protection for direct summary writes plus atomic summary persistence; new/restored concept type in verifier coverage. Added domain-owned facet meanings to the normal candidate producer/verifier inputs. Removed the runner's redundant summary child stage, relying on its existing publish stage to fill missing summaries under the parent lock. This avoids nested child lock acquisition without a bypass option. Read-only summary preview remains available. Focused rejection/pause/lock tests and Ruff passed; full idle release result is recorded in the session/backlog checkpoint. No corpus audit decisions or visual attestations were added.

Full idle release passed at 18:05 EEST: 281 Python tests in 246.17 seconds, nine Node tests, Ruff, reviewed/published validation, zero Astro errors/warnings and 635 pages (`media/p1-53-release.log`). Seven new tests cover causal cleanup, both summary engines' pause/lock protection, rejected Codex-summary preservation and rejected excerpt preservation; the existing creation/restoration test verifier now requires type coverage. Live model accuracy replay and a live normal processing cycle were not run: quota protection and the audit pause remain active. Oversized complete summary proofs stop at the existing verifier cap without truncating rows. These limits do not reopen normal processing or clear the remaining 261 articles.

Controlled reproductions used temporary fixtures, injected responses or mocked writers. All temporary fixture directories were cleaned up. Private evidence: `media/normal-processing-audit-review-2026-10-16-17-reproductions.json`. All 86 existing focused pipeline/summary tests passed; these passing tests do not cover the reproduced gaps. Test log: `media/normal-processing-audit-review-2026-10-16-17-tests.log`. Documentation build and local backlog verification are recorded in the session checkpoint. No live model accuracy test, scrape, publication, monitor restart or production fix was performed.

Final documentation/site verification passed: zero Astro errors/warnings, 635 pages; local HTTP confirmed P1-53 as Open in the Moment quality group with findings and acceptance visible. Only the new planning item's explicit group mapping changed in the site. Evidence: `media/normal-processing-audit-review-2026-10-16-17-build.log` and corresponding `live.json`. The full release gate was not repeated because no Python/model/content behavior changed.
