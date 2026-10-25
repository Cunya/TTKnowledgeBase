# Audit cost investigation and spending fix — 2026-10-22

The last continuation spent **5,003,915 processor tokens in 138 Luna/high calls**, across 22 finite invocations, and installed **zero articles**. It did complete private baseline checks for 357 remaining units. That was an unsuccessful throughput benchmark; it should not have been scaled to the quota limit. Normal processing and paid audit work remain paused.

## Why it was expensive

- Source-context completion changed the article planning identity. The next pass repeated baseline verification and field-proof authoring. Preserving whole-job receipts did not make changed batches reusable.
- The individual verification cache included unrelated grouped captions. One source change could invalidate proof for a different citation. Only one individual verdict was reused in the 138-call run, despite 59 whole-job cache hits.
- Per-invocation limits reset on each continuation. There was no durable article spending ceiling across retries and source identities; the three-revision limit also belonged to an identity.
- Nonvisual claims marked `needs_footage` blocked whole-article installation, but the workflow still drafted other text. Repeating text work could not clear that blocker. Uncertainty also correctly prevented approval.
- Individual CLI calls were expensive: a saved caption-free proposal assembly used 27,226 input tokens. The transport already uses an ephemeral temporary directory, read-only sandbox, disabled apps and a strict schema. The exact split between CLI instructions, schema and payload is **not established**. Small overlap previews do not explain the cost. We have not removed instructions, schema constraints or source context on that assumption.

Saved report: private `media/luna-workflow-live-final-2026-10-22-16.json`. A separate receipt census is in private `media/audit-cost-receipts-2026-10-22-16.json`. Its historical totals are larger because it includes earlier jobs; do not present that census as this run's consumption.

## Changes

1. Verification payloads retain each unit's complete owned-source neighboring-context IDs. Cache fingerprints and pending requests use those rows, rather than unrelated rows from the batch. Same-source negative context remains mandatory. Article semantics, source metadata, boundary findings, targets, overlap, model, effort and policy still invalidate proof conservatively. The internal ID map is removed from the model prompt.
2. Source-planning campaigns now stop before another paid call once an article has used **12 calls or 400,000 recorded tokens**. This is cumulative by concept ID, survives identity/config/policy changes and resumes, and counts authoring plus verification. A call already underway can cross the token threshold; the call ceiling remains hard. Attempts reserve their call before execution so interruption cannot reset the allowance. Quota denial refunds that unstarted call.
3. Existing successful receipts are deduplicated across current and historical source identities to initialize the allowance. Cached jobs remain readable without spending. Errors without usage still consume a call. Missing old receipts cannot reconstruct unknown historical consumption.
4. The coordinator parks an article on the cumulative spending hold. Changing the source fingerprint cannot reset its spending account. This limit applies to each repair campaign checkpoint; bundle preparation/final review still has its own finite/checkpoint/quota controls. It is not an account-wide token limit or a guaranteed total campaign price.
5. After baseline verification, any nonvisual `needs_footage` claim holds the article before text drafting. The saved unit verdicts/notes identify the missing evidence. Visual-only holds retain the existing behavior: they cannot approve footage, but do not unnecessarily block valid text repair.

Existing saved work is retained. These holds do not approve claims, erase proposals, publish partial articles or clear footage requirements. Further spending on held articles needs a concrete editorial decision and fresh evidence; deleting checkpoints or repeatedly restarting is not the solution. Keep the audit paused until a bounded benchmark can demonstrate an applied, independently reviewed outcome rather than another cycle of proposals.

## Verification

Offline regressions exercise unrelated-source cache reuse, retained neighboring negative context, both spending limits across resumes/identity changes, historical receipt deduplication, and zero drafting for a footage-blocked article. Focused suite: 161 tests passed; Ruff passed. Full release passed:372 Python tests (236.50s),nine monitor tests,Ruff,reviewed/published validators,zero Astro diagnostics and638 static pages. Receipt: private media/audit-cost-fix-release-2026-10-22-16.log. No paid model job, canonical content change, footage approval or new article approval was performed during this fix.

Performance limit: this is deterministic correctness/reuse evidence, not a measured live token reduction. Remaining costs include conservative article-wide semantic invalidation, large field proofs and CLI overhead. Track these under P1-51/P2-12, without spending more on the same held inputs.
