# Review of recent concept, moment, and video count decrease — 2026-08-30 13:00 EEST

## Conclusion

The sharp decrease is intentional quarantine, not deletion or loss of the source corpus. The current working-tree public snapshot is the safe post-remediation view: 73 approved concepts, 51 videos with approved evidence, and 1,119 non-demo evidence moments. Before the 2026-08-12 Codex-first remediation, the published snapshot contained 533 concepts, 729 videos, and 5,892 moments, but 460 concepts and 4,775 evidence moments came from the retired heuristic promotion path and were marked `unreviewed`.

Recovery has not yet replenished the public snapshot. The latest processor cycle on 2026-08-29 failed during Codex adjudication before publication, so the safe counts stayed unchanged. The canonical YAML still contains all 533 concept files and the private queue still contains the quarantined work.

## Evidence

| Layer | Current result | Interpretation |
| --- | ---: | --- |
| Canonical concept YAML files | 533 | No concept files were deleted. |
| Approved canonical concepts | 73 | Only these are eligible for public publication. |
| Unreviewed/quarantined concepts | 460 | Legacy heuristic output awaiting independent Codex adjudication. |
| Current public corpus | 73 concepts / 51 videos / 1,119 moments | Safe working-tree snapshot. |
| `HEAD` public corpus | 533 concepts / 729 videos / 5,892 moments | Pre-quarantine snapshot. |
| Eligible inventory | 752 of 838 | 709 still need automated adjudication; 43 are complete; 86 are excluded. |
| Queue | 6,934 items | 454 accepted, 6,470 deferred, 9 rejected, 1 pending. |
| Latest processor run | `stage_failed` | Stopped in Codex adjudication; no publish stage completed. |

The 1,119 public moments exclude three synthetic demo records from the 1,122 approved evidence records in canonical YAML. The 51 published videos are therefore not the same metric as the 752 eligible normalized videos or the 838-video inventory.

## Root cause timeline

1. The earlier heuristic path promoted 460 generated concepts and thousands of evidence records into the public snapshot.
2. On 2026-08-12, the project correctly quarantined that output after finding unsupported semantic mappings, silent citation-cluster loss, and incomplete source envelopes.
3. Publication was rebuilt from approved concepts/evidence only, producing 73 / 51 / 1,119.
4. Subsequent processing has been aimed at bounded Codex re-adjudication, but the 2026-08-29 run stopped on a response-schema validation error: a `create_new` decision included a non-null canonical concept ID. Because the failure aborts the stage, the 6,470 deferred decisions remain deferred and no new safe content reaches publication.

## Assessment

This behavior is safe but operationally incomplete. Restoring the old 533 / 729 / 5,892 snapshot would hide the exact trust problem that caused the quarantine. The recovery path needs to fix the adjudication failure, then publish only newly accepted, exact, contiguous, source-enclosed evidence. The operator UI should also make the safe-public, quarantined-history, and inventory counts visibly distinct so the contraction cannot look like silent data loss.

No network acquisition or content restoration was performed during this review. The monitor was confirmed idle before documentation changes.

## Implementation follow-up — 2026-08-30

- P0-11 was implemented in `processors/codex_engine.py` and `processors/pipeline.py`: response-schema validation now writes a private failure artifact, defers the affected queue item with retryable provenance, and allows the rest of the bounded batch to continue. Systemic Codex/CLI failures still stop the stage.
- P1-36 was implemented in generated progress data and `/progress/`: the UI now separates the safe public snapshot, quarantined history, and full inventory, and displays the last successful publication time.
- A live controlled retry was intentionally not started during this fix; it would invoke Codex and mutate the recovery queue. The next controlled run should verify the new defer-and-continue path against the previously failing item.

## Recommended next actions

- Observe the next controlled retry for P0-11 and confirm the malformed item is deferred while later items continue.
- Continue P1-34 in small, source-balanced Codex passes after the failure is fixed; do not bulk-promote quarantined YAML or legacy evidence.
- Keep the P1-36 count-layer implementation aligned with future inventory/recovery runs.
- Keep P1-04 open for broader operational observability beyond the count-layer timestamp now shown on `/progress/`.

## Files and checks reviewed

- `app/public/data/kbs/table-tennis/corpus.json` and `manifest.json`
- `content/kbs/table-tennis/concepts/`
- `content/kbs/table-tennis/annotations/review-queue.yaml`
- `data/manifests/table-tennis/inventory-ledger.json` and `cp.latest.json`
- local monitor `/api/status` and representative `/pipeline/`, `/progress/`, and KB routes
- `docs/Session Logs/2026-08-12-11.md` and the current backlog/lessons documentation

## Verification

- `npm run build`: passed; Astro diagnostics 0 errors / 0 warnings / 0 hints; 146 pages built.
- Local `/backlog/`, `/pipeline/`, `/progress/`, and `/kb/table-tennis/` routes: HTTP 200.
- Final monitor check: idle, with no active run; public corpus and manifest agree at 73 concepts, 51 videos, and 1,119 moments.

## Fix verification

- Targeted pipeline/model tests: 21 passed.
- Full test suite: 75 passed.
- `validate --kb table-tennis`, `publish --kb table-tennis`, and `validate-published --kb table-tennis`: passed.
- Ruff: passed.
- `npm run build`: passed; Astro diagnostics 0 errors / 0 warnings / 0 hints; 146 pages built.
- Generated progress snapshot: 73 public concepts, 51 videos, 1,119 moments; 460 quarantined concepts and 4,775 quarantined evidence moments; last successful publish `2026-08-30T16:58:01`.
