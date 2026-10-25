# Shared published-repair workflow

2026-10-22. P1-51. Implementation and full release verification passed. This does not complete the content audit.

The shared workflow replaces article-specific source, wording, relocation, verification, final source-review, installation and status scripts. It uses the existing finite Codex planner, GPT-6 Luna/high configuration, quota/budget guards, exact proof caches and per-KB locks. Drafting, verification and final editorial source review are separate jobs. Only a complete supported final review can authorize guarded canonical application; publication remains a separate release gate. No new dependency was added.

## Run and resume

From the repository root, using the checked virtual environment:

```powershell
$env:PYTHONUTF8='1'
.\.venv\Scripts\python.exe -m processors.cli continue-published-repairs --kb table-tennis --max-calls 4
```

Repeat this finite command to resume. It prioritizes incomplete current baseline coverage, then rotates fairly through eligible remaining articles using source-fingerprint visit counts, or resumes the current bundle; `--concept-ids ARTICLE_IDS` explicitly selects or retries origins. Its one call allowance covers planning, destination verification and final review together. Exact checkpoints save completed jobs. It installs only a fully reviewed supported bundle and refreshes the complete corpus status. It never publishes or starts an unbounded background loop. Unchanged exceptions are parked by input fingerprint so they cannot starve the remaining queue; changed inputs make them eligible again. The command refuses a configured model/effort other than GPT-6 Luna/high.

The individual planning commands remain available for diagnostics:

```powershell
.\.venv\Scripts\python.exe -m processors.cli plan-published-repairs --kb table-tennis --concept-ids ARTICLE_IDS --repair-confirmed --max-calls 4 --max-articles 1
.\.venv\Scripts\python.exe -m processors.cli plan-published-repair-bundle --kb table-tennis --concept-ids ARTICLE_IDS --max-calls 4
```

Repeat the same finite command to resume its saved checkpoint. `ARTICLE_IDS` is a comma-separated explicit origin selection, not a destination list. The planner proposes existing destinations where evidence is misplaced; destination candidates are retrieval hints, never source proof. Single-article application refuses relocation proposals so a valid instruction cannot be archived without its reviewed destination.

The bundle command handles ordinary repairs and relocations together. It assembles the private after-state, adds changed relation/overlap dependants, checks the whole hypothetical corpus before model calls, and independently verifies every final affected article. Changed wording/source proofs are checked again until the snapshot is stable, with at most three bundle passes. A job allows at most20 calls/20affected articles. Unchanged failures, oversized proofs, rejected destinations and revision limits remain exceptions requiring editorial attention; they never silently exclude an instruction or approve content.

## Review and apply

Private artifacts live under `data/manifests/<kb>/`:

- `published-repair-bundle.json`: original hashes, proposed documents, retention mapping, exact dossiers, independent verification, and final bundle hash.
- `published-repair-bundle-review-template.json`: optional template for an explicitly recorded editorial review.
- `published-repair-bundle-primary.json` and `published-repair-bundle-review.json`: separately prompted Luna/high final source jobs, provenance and complete decisions, bound to the final bundle/configuration/policy. Prior verdicts are not supplied. The final review reads owned captions and surrounding context; source seed IDs select complete citations rather than borrowing conditions. Uncertain findings return to the bounded repair loop. Transport/quota failures preserve checkpoints and block application.
- `published-repair-workflow.json`: coordinator progress and parked exceptions.
- `published-repair-bundle-plans.json`: reusable finite model checkpoints/provenance.
- `published-repair-bundle-transaction.json`: recoverable original/after bytes for every affected file.

The coordinator applies its completed final source review automatically. Manual application of a separately completed review remains available:

```powershell
.\.venv\Scripts\python.exe -m processors.cli apply-published-repair-bundle --kb table-tennis --review-file PATH_TO_COMPLETED_PRIVATE_REVIEW
.\scripts\verify-release.ps1 -Kb table-tennis
```

Application checks the full primary review, policy/hash identity, actual source files, taxonomy/configuration, other canonical articles and each affected file's original bytes. Destinations are written before origin associations are archived. All before/after bytes are journaled before any replacement; a retry accepts only the exact original or proposed bytes. An unrelated edit blocks recovery. Unchanged YAML nodes/comments and original archived records remain intact. No publication runs inside application.

To reverse a prepared/applied transaction whose files still match:

```powershell
.\.venv\Scripts\python.exe -m processors.cli rollback-published-repair-bundle --kb table-tennis
```

Rollback restores originals in reverse write order and refreshes the ledger/status. It refuses unrelated edits. After any application, the full release gate remains required before reporting published output verified.

## Source and visual boundaries

A failed source claim can propose actual neighboring caption rows, at most two on either side, once per evidence item. Only exact known-duration envelopes of 30 seconds or less that retain every original owned ID/bound qualify. Missing IDs, longer windows or unresolved subjects stay exceptions. Existing spoken-context bounds expand consistently; visual windows/status do not change. Fresh independent verification and complete primary review are required. Earlier wording edits survive source completion. Changed failed repairs resume from the previous draft/checks for up to three targeted rounds; unchanged failures park.

Both excerpt and reason are reader-facing prose. The shared drafter/verifier rejects private review scaffolding, unsupported conditions and invented outcomes. Preserving an instruction in a different topic requires independent destination support, not merely a lexical match.

Luna's text workflow always leaves visual units needs_footage. Full-clip footage inspection remains required to approve them; caption context, sparse frames or DOM checks cannot approve footage. Looping remains limited to reviewed visual windows. This automation does not complete the outstanding footage audit or establish that model review catches every semantic error.

## Automatic status

Planning, review recording and application export `published-audit-status.json` and `.md` from the complete ledger, even when the model job selects one article. These include every unfinished article and every actual visual window, including windows in pending articles. The existing `prepare-published-audit --kb ID` command refreshes status without model calls.

README, operations, pipeline, source progress, coverage and backlog opt in with paired `<!-- audit-status:KB:start -->` / `<!-- audit-status:KB:end -->` markers. Only that region is regenerated; editorial notes, release receipts and backlog planning remain separate. Generated counts never imply a release passed or that model proposals are approved.

## Verification

Seventeen bundle regressions cover instruction retention, dependent-target rechecks, finite resume, destination rejection, exact primary review, changed source/target/other files, interrupted writes, unrelated-edit refusal, rollback, YAML comments, CLI application and exhaustive visual status. Existing source-completion, cache, schema, primary-review and single-article tests remain in place. Full release evidence will be added after its final gate completes.

## Verification receipt

2026-10-22 14:43 EEST: full release gate passed: 364 Python tests (303.40s), Ruff, nine monitor tests, reviewed/published validators, zero Astro errors/warnings/hints, and 638 static pages. Private receipt: `media/shared-workflow-release-2026-10-22-14.log`. Twenty-five bundle/coordinator regressions cover finite resumption, separate final-review policy, negative findings, profile invalidation, queue parking, overlap-only work, complete application/status, stale inputs, interruption/recovery, rollback, retained journals and YAML comments. No paid Luna benchmark, article edits or footage inspection occurred during this implementation. Full corpus audit is still incomplete.

Live benchmark follow-up: source-planning jobs rotate between remaining articles after each finite invocation, so large articles cannot consume the queue indefinitely. Pending bundle/transaction recovery retains priority, and explicit origin selection still resumes that origin. Changed source fingerprints reset visit credit. Current-policy checkpoints receive initial visit credit on migration. See the [live benchmark](luna-shared-workflow-live-benchmark-2026-10-22.md).

Final verification at 16:27 EEST: standalone full release gate passed 367 Python tests in233.83s, nine monitor tests, Ruff, reviewed/published validators, zero Astro errors/warnings/hints and 638 pages. Receipt: `media/luna-workflow-live-release-2026-10-22-16.log`. This validates the orchestration code and existing published corpus; the live benchmark did not reach safe new-content application. All35 visual windows remain unverified; normal processing stays paused. No staging/commit/push.

## Spending and blocked-input holds (2026-10-22)

Source repair campaigns retain per-concept spending across resumes and source identities: stop before the next paid call at12 calls or400000 recorded tokens. Existing receipts initialize the account; cached results can still be read. The token threshold can be crossed by one in-flight call. A nonvisual needs_footage verdict holds drafting because text alone cannot clear the article. Coordinator parking records cost exhaustion. Normal processing and the paid audit remain paused after the failed138-call benchmark; do not restart held inputs or delete checkpoints to reset spending. Final bundle review retains its own separate finite/quota controls. See [cost investigation](audit-cost-investigation-2026-10-22.md) for scope, limits and next-step acceptance.


16:49 EEST — Full release passed:372 Python tests (236.50s),nine monitor tests,Ruff,reviewed/published validators,zero Astro diagnostics and638 static pages. Receipt: private media/audit-cost-fix-release-2026-10-22-16.log. No paid audit calls or canonical changes. Final documentation build/backlog HTTP check follows; normal processing and audit remain paused.

## Topic identity preflight

Before spending tokens, source planning runs the per-KB taxonomy topic_identity_rules against article labels and each evidence source's saved title/captions/context. Conflicts persist in topic_identity_holds and park the article. Final source review and single/bundle installation enforce the same hold. Source titles never approve a replacement identity. Run `scan-topic-identity --kb table-tennis` for an exhaustive no-model scan; it writes only a private report and does not reset corpus approvals. See [implementation, findings and limits](topic-identity-workflow-scan-2026-10-22.md).


17:25 EEST — Full release passed379 Python tests (239.78s),nine monitor tests,Ruff,reviewed/published validators,zero Astro diagnostics and638pages. Private receipt: media/topic-identity-release-2026-10-22-17.log. Zero paid model calls. Scan report ignored/private; no canonical changes or new approvals in this pass. Final docs rebuild and local backlog verification next.

Scope-only overlap work: `propose-published-overlaps --kb table-tennis --limit 4` makes at most one configured-model call and saves private, unapproved scope proposals. Same current article fingerprints/profile/policy reuse them. Independent editorial inspection and the existing `record-published-audit` overlap-only importer are required; source/visual decisions remain untouched. See [four-advisory live receipt](overlap-only-audit-continuation-2026-10-23.md).


00:31 EEST — Full release passed384 Python tests (111.95s),nine monitor tests,Ruff,reviewed/published validators,zero Astro diagnostics and638pages. Private receipt: media/overlap-only-release-2026-10-23-00.log. Four overlapadvisories resolved;all380claim/visualdecisionmaps unchanged. Fullaudit remainsincomplete369/380,362pending/17footageunits,0overlapadvisories. Only1Luna/highcall20662tokens. No sourcecampaignlimitreset/footageapproval/canonicalchanges thisturn. Finaldocsrebuild/backlogcheck follows;goal remainsactive(incomplete),freshblocked-auditcount not escalated frompriorblockedrun.
