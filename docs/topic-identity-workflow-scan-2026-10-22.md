# Cheap topic identity check — 2026-10-22

The Hook push error exposed a gap: literal translated action words were accepted despite conflicting lesson context. Multiple text-model reviews agreed, but that did not establish the action shown. The workflow now detects a bounded set of these conflicts before spending tokens and prevents unresolved conflicts from reaching installation.

## Workflow change

`processors/topic_identity.py` is a generic local evaluator. Domain action terms live in `config/kbs/table-tennis/taxonomy.yaml`, not shared processors. Current rules flag push/rally-stroke articles sourced from serve-only lessons and serve articles sourced from receive lessons. Article labels establish the topic; action words in a broad multi-source definition do not classify every citation. Explicit receive roles, receive-tutorial titles and locally named rally actions keep legitimate serve-receive/serve-then-attack examples from being treated as contradictions. The ambiguous translated words hook push remain a conflict in a serve-only lesson.

The source-planning campaign records conflicts in private `topic_identity_holds` and parks them before model calls. Final Luna review refuses readiness; single-article and bundle installation reject unresolved conflicts. Luna draft, verification and primary policy versions changed, so previous-policy proposals cannot silently bypass the safeguard. Shared instructions now require checking action identity and incoming/outgoing role against lesson context; titles signal conflict but never supply positive claim support. No automatic relabeling or footage verification follows from a keyword match.

## Exhaustive local scan

Run from the repository root:

```powershell
$env:PYTHONUTF8='1'
.\.venv\Scripts\python.exe -m processors.cli scan-topic-identity --kb table-tennis
```

This uses the existing per-KB lock, reviewed corpus and saved transcripts. It performs no model calls and changes no article, approval or audit ledger. The private report is `data/manifests/table-tennis/topic-identity-scan.json`; it includes counts, exact rule configuration, flagged evidence IDs and all unfinished article IDs.

Scan coverage: **380 articles, 1,816 published evidence associations, all 11 remaining audit articles**. **Zero model calls.** Final rules flag **one article with two evidence records**:

- **Forehand loop swing path and racket angle**: `leQBUn8-4tw-cand-horizontal-backswing-minimal-drop-1` and `-2`. The lesson is *Stop Going for Aces: How to Serve to Set Up Your Next Attack*. Owned/neighboring captions explicitly concern short and long serves, keeping the backswing horizontal, and avoiding a high, slow serve. The public record prose itself calls these serve-path concepts. These are misplaced serve mechanics, not source proof of a forehand loop backswing. They remain held for a retained destination repair; this scan does not invent a replacement or delete valid serving instruction. Both units were already pending in the full audit.

The remaining ten unfinished articles have no match to these configured conflict patterns. This does **not** certify them correct. The corrected Hook-serve page passes because its heading and source now agree.

Inspected negative controls include the actual receive using hook-serve motion, half-long backhand flick/forehand loop recommendations, and lightly looping after a serve. Their local caption roles justify retaining them. The initial broad scan incorrectly linked incidental definition words across unrelated citations; using article labels and local same-action evidence fixes that source of false positives.

## Verification and limits

Seven regressions cover translated Hook push, explicit receive, generic multi-source topics, valid post-serve loops, misplaced serve backswing, zero-call planner holds and zero-call final-review holds. Together with the existing repair/bundle suite,168 focused tests pass; Ruff passes. Full release passed379 Python tests (239.78s),nine monitor tests,Ruff,reviewed/published validators,zero Astro diagnostics and638pages. Private receipt: media/topic-identity-release-2026-10-22-17.log.

This is a cheap targeted conflict detector, not a replacement factual or visual audit. Missing/translated titles, synonyms outside the configured vocabulary, distant context and misleading caption wording can escape it. Do not infer approval from a clean scan. Actual footage is still required for visual verification. No paid audit was restarted, no canonical content was changed and no new approval was granted.

Track follow-up under P1-34/P1-51/P2-12: retain the two valid serving instructions in a defensible destination, then independently verify resulting source ownership and final article coherence before guarded application. Acceptance requires the Hook failure to hold without paid calls while legitimate receive/post-serve cases pass, complete scan coverage and the existing release gates.
