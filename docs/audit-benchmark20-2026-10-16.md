# Frozen 20-article audit benchmark — 2026-10-16

This was an operational benchmark of a deliberately mixed remaining batch, not a random sample or a matched before/after semantic trial. Twenty articles and187 original review units were frozen before calls; every outcome is included. Model: GPT-6 Luna, high effort, no escalation. Normal processing/expansion stayed paused; source/final-primary/transaction/quota guards remained enabled.

## Results

- Eleven articles applied after complete final primary/source review; nine remain blocked or disputed. No uninspected footage was approved.
- Audit ledger increased from92 to103 supported articles out of377;274 pending. Supported units increased from683 to762;3695 pending out of4457 current units. Eight optional difficulty fields were removed; the unit-count decrease is not extra semantic clearance.
- First semantic pass:37 calls,798308 processor tokens,811.03s. One bounded targeted follow-up:6 calls,137214 tokens,184.89s. Two frozen controls:2 calls,38646 tokens,26.17s. Total45 calls/974168 tokens/1022.09s (17.03min) in model phases. The controls rejected the frozen unsupported referent and retained the complete-clause control. This pair is not a corpus-wide accuracy estimate.
- Typed difficulty-only planning used zero model calls for the heavy-spin-serve article. Other applied edits also retained previously reviewed proposals; do not attribute every resulting correction to new calls.
- Eleven complete applications took160.04s total (14.55s mean), including fresh full post-application audits and history/journaling. This is distinct from the earlier3.90s scratch transaction benchmark, which excluded whole-corpus CLI audit work.
- Actual end-to-end walltime, release status and unchanged machine provenance are in the private result artifact. Parent-chat token usage was not measured. Processor tokens are not account quota percentages.
- Repeated local command startup/corpus loading added substantial walltime after the first pass. A zero-call primary import took roughly14minutes. A read-only import profile includes rich/Typer help, networkx and ingestion imports with repeated roughly0.5second module delays. Low process CPU and available memory were observed; the environmental cause remains unproven. Reusing a checked Python session avoided subsequent repeated imports while calling the same lock/freshness-protected functions. Do not blame model calls for all walltime or bypass freshness checks.

## All frozen outcomes

| Article ID suffix | Result | Remaining action |
|---|---|---|
| heavy-spin-serve-disrupts-step-around | Applied | Optional unsupported rating removed through typed zero-model path. |
| backhand-attack | Applied | Direct source-scoped body/backhand instruction and reviewed metadata. |
| backhand-pressure-management | Applied after follow-up | Separate racket-proximity/jamming from C-shape/core roles. |
| banana-flick-arm-shape | Applied | Keep complete elbow/wrist practice cue; no undefined-angle geometry. |
| defense-as-interception-and-redirection | Applied | Direct source-grounded principle. |
| diagonal-step-in-for-forehand | Applied | Preserve slightly-deeper-ball condition. |
| downward-pressure-and-friction-on-serve | Applied | Preserve sideways/underspin preparation and contact-pressure scope. |
| finger-engagement-for-power-and-feel | Applied | Preserve feel/power and stable-arm/quickness clauses separately. |
| firm-forearm-at-impact | Applied after follow-up | Preserve reduced-spin tradeoff without invented acceleration causation. |
| flick-push | Applied | Attribute numerical coaching comparison rather than claim calibrated performance. |
| grip-selection-for-left-sidespin-serve | Applied | Numbered grip explicitly lesson-local; no invented geometry. |
| curved-serve-trajectory | Blocked/disputed | Primary approved reversible handpath/ballflight-mapping quarantine; verifier still rejects it. No forced application. |
| forearm-led-serve-acceleration | Blocked | Explicitly own/review actual serving-context IDs; context is not already citation proof. |
| forehand-loop-common-errors | Blocked | Source-clause/prose/metadata correction and actual full-clip review remain. |
| forehand-loop-down-the-line | Blocked | Restore valid related placement drill; explicitly own actual forehand relation context. |
| forward-brushing-on-topspin | Blocked | Produced-spin reason corrected privately; incoming-topspin topic condition still unowned. |
| functional-phases-of-the-stroke | Blocked | Reject invented generic phase scheme and exclusion of actual backspin brush/drive/stop source. |
| half-long-ball | Blocked | Optional rating removed privately; quarantined citation still needs a direct reason/restoration decision. |
| high-quality-attacks-use-explosive-power-and-a-low-arc | Blocked/disputed | Qualified example accepted by primary, still rejected by verifier; no forced application. |
| horizontal-force-for-hooking | Blocked | Whole sideways-then-up/down sequence corrected privately; immutable processing-novelty topic type still needs reviewed metadata correction. |

## What to improve next

Continue bounded source-reviewed batches, excluding unchanged parked cases. Do not run another unrestricted campaign. P1-51 retains three generic workflow gaps: typed reviewed metadata edits, owned source-context changes with actual validated IDs/timing, and explicitly reviewed restoration of rejected quarantines. Current targeting excludes already-quarantined units, preventing some legitimate corrections. Retain the actual false-exclusion proposals as P1-34 controls. Optional partial metadata transformations must preserve all other negative decisions and never imply article approval.

This batch does not establish a reliable remaining-hours forecast: it was mixed, included previous proposals, encountered unexplained local startup delays and left nine hard cases unresolved. Source/footage closure and the full-audit gate remain incomplete.

Private evidence: media/audit-benchmark20-2026-10-16-14-baseline.json; first-pass-final-plans; dossiers; primary-part1/part2/followup; round1/round2/targeted-followup logs; frozen-controls; apply-metrics; results-2026-10-16-15.json; CLI import profile. Release evidence: media/audit-benchmark20-release-2026-10-16-15.log. Planning: [P1-51 and P1-34](prioritized-backlog-2026-07-15.md); [operations](operations.md); [session](Session%20Logs/2026-10-16-15.md).

## Verified release and route checkpoint

The single full idle release gate passed:274 Python tests in107.31s,nine monitor tests,Ruff,zero Astro errors/warnings,635 pages. Three live corrected routes (pressure management,firm forearm,lesson-local grip) returnedHTTP200 with expected instruction text,nonlooping spoken controls and disabled visual looping. Built and live /backlog/ reflect the current P1-51 benchmark status. Full elapsed time through release:54.15minutes,including root/source review,local startup delays,application and validation;model phases were17.03minutes. This is a measured mixed batch,not a reliable completion forecast. Private final metrics mark release_verified:true. Next bounded batch is prepared separately;the nine blocked benchmark cases are excluded from unchanged retries.
