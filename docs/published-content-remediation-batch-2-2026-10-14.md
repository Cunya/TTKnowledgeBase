# Published-content remediation — second bounded batch

Reviewed 2026-10-14, 12:27–12:34 EEST. Continues [batch one](published-content-remediation-batch-2026-10-14.md); planning IDs P1-14 (boundaries/timing) and P1-34 (semantic support/topic mapping).

## Selection

Screened the complete current public corpus with the existing caption-only boundary assessor. Selected eight short citations, one per video, excluding the three videos repaired in batch one and other previously repaired sources. This is deliberate risk selection, not a random prevalence estimate. Exact selected captions and surrounding context were read before any canonical writes. The opponent-specific serve-selection sentence in `leQBUn8-4tw:00041` is meaningful despite its short duration and was kept.

## Findings and actions

Fifty archived evidence actions across seven concept files: fourteen amendments, four consolidations, thirty-two quarantines. Seven summaries revised. Original records and previous summaries are in [the editorial archive](../content/kbs/table-tennis/annotations/published-repair-batch-2-2026-10-14.yaml).

| Topic | Decision and evidence |
|---|---|
| Post-serve recovery | Complete delayed-backswing instruction in `m93pWt9MIZE:00231–00240`; consolidate the generic introduction. Keep the short-return condition in `:00241–00245`. Quarantine the final foot/hand coordination fragment: the complete sentence ends at 671,519ms, beyond cached video duration 671,000ms. No invented truncation or metadata change. |
| Push technique | Distinguish the opening flat-angle problem (`p3hweUir1Mg:00001–00002`) from the regular-backspin correction (`:00009–00017`) and the upright-angle/net contrast (`:00019–00020`). Each description now stays within its own selected rows. |
| Forehand loop | `I99BjizeWeE:00191–00193` supports the slight post-contact rise and complete arm closure, not the full preceding backswing sequence. |
| Body/hand synchronization | Combine the forward C-shape posture and stomach-out correction in `Cq6MbP6TEdc:00056–00058`; consolidate the separate fragment. |
| Serve receive principles | Complete three distinct heavy-spin instructions in `bUCFpvTlaMU:00192–00197`, `:00198–00205`, and `:00208–00217`; remove broad repeated descriptions from incomplete fragments. |
| Contact point | Separate soft-ball timing (`uag7n7hq3bM:00207–00217`), waiting/closer contact (`:00218–00227`), and the fast/slow practice example (`:00228–00230`). Do not attach the whole soft-ball instruction to “then slow.” |
| Contact zone on the ball | Reviewed all 41 approved citations after discovering object/topic confusion. Quarantined 31 misplaced rows: racket-surface contact and spacing (`G7eiadOxN8E`, 11), approach/racket contact (`dWZw3A0X-4A`, 4), ball height/shot selection (`JmOI0L7SiG8`, 3), hand orientation/finger mechanics (`V__nqiNHeKE`, 8), force/rotation (`bUCFpvTlaMU`, 2), finger-driven friction (`t3HX8AEujWw`, 3). Retained supported ball-surface evidence from four other videos. Consolidated two driving/follow-through fragments into the complete region instruction in `leQBUn8-4tw:00169–00173`; omitted the spin label spoken outside this window. Eight approved topic citations remain. |

The contact-zone summary previously treated upper racket contact as higher contact on the ball and generalized its result. It now describes the supported ball-surface serve examples, with ball/racket/spatial distinctions explicit. No misplaced record was silently promoted into a different topic. Quarantine preserves recoverable history for separately reviewed remapping. Remaining ball-surface citations have varying caption boundaries; keeping their supported topic mapping is not a claim of perfect playback boundaries.

Adjudication prompt **1.1.2** explicitly preserves the object described and separates ball-surface region, racket-surface region, spatial position, and hand/force mechanics. The existing captured-call test checks this instruction reaches Codex and that failure provenance records the current prompt version. Model, profile, schema, confidence thresholds, and budgets are unchanged. This instruction is prevention guidance, not measured proof of semantic accuracy.

## Controls and limits

Three additional unflagged citations were supported by their exact selected captions: rhythm practice (`9WPYbE6DoTo:00013–00016`), fast-backspin positioning (`2LkVpDM69vo:00151–00153`), and adapting technique/rhythm (`b3bRD1hQpe8:00185–00190`). These cover two channel labels, including GlobalTTStudio. Metadata labels remain provisional attribution; no coach identities were inferred.

No footage was watched, no visual status was upgraded, and no full-corpus accuracy certification is claimed. Broader source-balanced auditing and recovery/remapping of quarantined useful proposals remain under P1-34. Cached end-of-video caption/duration reconciliation remains under P1-14; the quarantined fragment must not be restored by guessing an endpoint.

## Verification

The active cycle completed normally and the monitor paused between runs. Repairs were applied under the KB lock. Serialized YAML was checked with the repository's safe loader before replacement. Reviewed validation and focused Codex-engine tests passed; complete release and route verification are recorded after completion below.

At 12:37 EEST the full idle/locked release gate passed: reviewed validation, sanitized publication, published-artifact validation, 142 Python tests, nine monitor tests, Ruff, and Astro diagnostics/build with zero errors/warnings/hints (632 pages). The public snapshot contains 377 concepts, 225 videos, and 1,855 evidence moments after the intervening processing cycle and this repair. Artifact checks confirm all fourteen amended records are published and all thirty-two quarantined/four consolidated records are excluded. All seven affected live concept routes return HTTP 200 with transcript-only looping disabled; live and built backlog show both batches. The operator's enabled loop was restored with its saved two-minute cooldown. No staging, commit, push, deployment, or model escalation.
