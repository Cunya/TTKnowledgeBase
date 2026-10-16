# Concept gap and last processing cycle — 2026-09-15 10:00

## Summary

The local `/progress/` page currently publishes 200 concepts. The last committed corpus at `HEAD` (`4a6a231`, 2026-08-05) contains 533 concepts, so the numerical gap is 333 concepts.

This is an intentional safe-public contraction, not silent deletion. The current page counts only approved concepts. Quarantined concepts and legacy evidence remain private and are processed through the Codex-first adjudication path.

## Count comparison

| Snapshot | Concepts | Videos | Evidence moments |
| --- | ---: | ---: | ---: |
| Current generated page, 10:36 EEST | 200 | 120 | 1,420 |
| `HEAD` commit `4a6a231` | 533 | 729 | 5,892 |
| Net difference | **-333** | -609 | -4,472 |

The concept-ID difference decomposes as follows:

- 359 concepts from the committed corpus are absent from the current public snapshot and remain quarantined.
- 26 concepts are new relative to `HEAD`.
- Therefore: `533 - 359 + 26 = 200`.

The current generated progress data separately reports 359 quarantined concepts and 4,775 quarantined evidence moments. These are not included in the public corpus.

## Last completed cycle

The latest completed cycle ran approximately 10:29–10:36 EEST and completed successfully.

- 10 candidate decisions were processed.
- 4 were finally accepted.
- 5 were deferred.
- 1 was rejected.
- 4 evidence moments were added.
- 0 concepts were added.
- 0 quarantined concepts were restored.
- Publication succeeded and remained at 200 concepts.

The accepted decisions targeted existing approved concepts, including `loaded-legs`, `forehand-loop`, `contact-point`, and `forehand-loop-swing-path`. That adds supporting evidence to existing articles; it does not increase the concept count.

The six non-accepted proposals did not reach canonical publication. Their candidate spans were rejected or deferred by semantic and deterministic checks, including sentence-boundary/context failures. One private Codex audit artifact contains a raw `create_new` response, but the selected span failed the deterministic boundary gate before the creation branch ran. This is why the final count was still zero concepts added.

The relevant pipeline order is:

1. Codex proposes `accept_existing`, `create_new`, `reject`, or `defer`.
2. Deterministic validation checks confidence, taxonomy, segment IDs, source bounds, and sentence boundaries.
3. Only a validated accepted decision can add evidence, restore a quarantined concept, or create a new concept.
4. The corpus is published only after validation and navigation checks succeed.

This fail-closed behavior is expected and protects the public corpus from publishing an unsupported or truncated citation.

## How the gap closes

The monitor selects a source-balanced workset of up to 50 videos, but the automatic adjudication stage is capped at 10 candidate decisions per cycle. A concept count increases only when one of those decisions passes all gates and is either:

- a validated `create_new` decision; or
- an `accept_existing` decision targeting a quarantined concept, which restores that concept after fresh evidence is added.

Accepted evidence for already-approved concepts improves article support but does not close the concept-count gap. Deferred candidates return to the retry pool. A failed publish leaves the previous public snapshot unchanged.

At this snapshot the private inventory reports 703 videos with automated work remaining, 94 pending candidates, 5,916 deferred candidates, and 95 accepted-but-unincorporated candidates. The monitor uses a three-minute cooldown; the last successful cycle took about 7.7 minutes. A one-pass drain of the current candidate states would therefore take roughly 4.5 days of continuous processing, before accounting for retries and candidates that remain unsupported.

There is no reliable date for reaching 533 concepts. The process is deliberately evidence-limited: some quarantined concepts may be restored, some may remain deferred, and some may be rejected. The next page change is therefore governed by successful independent adjudications, not by elapsed cycles alone.

## Evidence locations

- [Progress page source](../app/src/pages/progress.astro)
- [Current public corpus](../app/public/data/kbs/table-tennis/corpus.json)
- [Current generated progress](../app/src/data/generated/table-tennis-progress.json)
- [Last-cycle monitor output](../data/manifests/table-tennis/cp.latest.json)
- [Adjudication and creation gate](../processors/pipeline.py)
- [Operational processing rules](operations.md)

## Planning conclusion

No new backlog item is warranted from this observation. The cycle behaved as designed: accepted evidence was incorporated into existing concepts, unsupported or boundary-incomplete proposals were deferred, and publication completed without weakening the evidence gate.
