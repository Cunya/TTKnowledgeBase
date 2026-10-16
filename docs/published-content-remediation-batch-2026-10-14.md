# Published-content remediation — first bounded batch

Reviewed 2026-10-14, 12:18–12:22 EEST. Follow-up to [the earlier audit](affected-content-spot-check-2026-10-14.md), tracked under P1-14 and P1-34 in [the backlog](prioritized-backlog-2026-07-15.md).

## Selection and findings

Selected the eight shortest `too_short` citations in the prior boundary report's 50-row sample. This sample is truncated and ordered by corpus traversal; it is not representative of all 381 context flags or of the whole corpus. Checked exact selected caption rows and surrounding context for each. Reviewed related sibling rows when repairing fragments to avoid retaining redundant or contradictory descriptions.

The recurring issue was a broad proposal excerpt/reason repeated on individually split citation fragments. Examples: `hDXIuFwtrHE:00136` says only “spin”; `:00120` begins a question about the arm's power source. Neither supports the published combined forearm/elbow/grip description alone. `xWrDKGnqmBs:00133` says “Brush first” and does not support wrist-error or hard-hitting corrections. `q9c2_hCwlhs:00141` gives a sound cue, not the full loose-release exercise. These are established selected-span support failures, rather than merely short-duration flags.

## Recorded decisions

Twelve evidence actions across five concept files: eight amended citations, three consolidations, one quarantine. Original evidence and summary fields are preserved in [the editorial archive](../content/kbs/table-tennis/annotations/published-repair-batch-2026-10-14.yaml). No IDs, timestamps, quotes, or visual confirmation were invented.

| Topic | Repair |
|---|---|
| Backhand rip practice progression | Complete brushing-first progression with `xWrDKGnqmBs:00131–00137`; consolidate its single-line fragment. Complete the loose-whip practice cue with `q9c2_hCwlhs:00139–00141`. Cite the full wrist-isolation drill in `:00172–00179`, consolidate its fragment, and retain a separate backspin variation in `:00180–00183`. |
| Backhand rip backswing | `xWrDKGnqmBs:00071–00072` supports the local drive-versus-rip comparison. Remove uncited abdomen-height and near-table claims from this evidence row. |
| Backhand rip | Quarantine the `:00053–00054` label-only “Rip / Drive” demonstration proposal; a mechanics comparison needs footage inspection. Preserve it as unreviewed. |
| Backhand serve | Complete the forearm/racket-head explanation with `hDXIuFwtrHE:00120–00126`; complete the power/grip explanation with `:00134–00141` and consolidate the “spin” fragment. Remove the uncited anchored-elbow claim from these rows. |
| Backhand spacing | `q9c2_hCwlhs:00094–00099` supports the close-ball instruction and overextension consequence. Remove the uncited reassurance about jammed-looking contact. |

Rewrote four affected summaries to reflect the reviewed instructions, retaining manual prose rather than regenerating broad repeated reasons. Existing visual classifications remain unchanged; no footage was watched and no demonstration was verified. All amended spoken windows are contiguous, caption-derived, and at most 30 seconds.

## Unflagged controls

Three deterministic unflagged, at-least-ten-second Codex-reviewed citations from different videos were also checked. Their selected captions support the published excerpts:

- `concept-acceleration-without-force`: `CD09LNI2fYk:00150–00159`, constant pressure and increased motion frequency.
- `concept-accurate-foot-placement-and-balance`: `2DXviJQOA5M:00058–00060`, stance stability, shoulder-width feet, and hip use.
- `concept-adapt-racket-angle-to-the-incoming-ball`: `tFXmtu4Egw8:00048–00049`, racket-head direction for topspin/backspin loops.

These controls do not establish corpus-wide accuracy. More source-balanced samples, especially repeated broad excerpts on split moments and caption-origin risks, remain under P1-34. Boundary flags alone do not justify automatic removal or expansion.

## Verification

The active processing cycle finished normally before the monitor loop was paused. Canonical changes were applied under the per-KB lock. Release verification and affected route checks are recorded below after completion.

At 12:25 EEST the complete release gate passed: reviewed validation, sanitized publication, published-artifact validation, 142 Python tests, nine monitor tests, Ruff, and Astro diagnostics/build with zero errors/warnings/hints (625 pages). The public snapshot contains 371 concepts, 224 videos, and 1,884 evidence moments after the operator's intervening processing cycles and this repair. Public checks confirm all amended citations are present, consolidated fragments and the quarantined label-only clip are excluded, and each repaired window stays within 30 seconds. Five affected live concept routes return HTTP 200 with transcript-only looping disabled. Live and built backlog views show the first batch under P1-34; broader work remains in progress. No Git staging, commit, push, or remote deployment was performed.
