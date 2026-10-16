# Refactoring notes

## Owned-source application gap — 2026-10-16

Implemented at22:41: reused source validation/dossiers, existing archive and prepared transaction; added exact corrected-proof identity and reused the CLI's fresh eligible snapshot instead of reloading an incompatible unfiltered corpus. Post-application mapping now matches the verified corrected source. Normal plans stay compatible. Thirteen new source-boundary/archive/recovery/CLI tests and the full297-test release passed.

P1-51 source corrections should reuse `validate_source_span`, fresh `audit_dossier`, exact primary/verification binding, `write_repair_archive` and the existing prepared-transaction writer. Avoid an ad hoc canonical writer. The current repair edit whitelist excludes source dictionaries; `apply-published-repairs` also maps post-application decisions by equality with the old source. Both proof validation and post-application mapping must use the verified corrected source while canonical freshness/record matching use the original source. Preserve visual fields and do not reset unrelated cleared audit decisions.

## Repair heading/ID policy — 2026-10-16

Fixed the shared model-call instructions instead of writing article-specific quarantine exceptions. Draft, verifier and reducer receive the same opaque-ID rule; the reducer preserves proposed heading corrections without source adjudication. Reused policy version invalidation, existing review/application guards and finite CLI workflow. Test fixtures now use actual stage constants instead of duplicating policy strings. No new abstraction or dependency.

## Normal-processing audit review — 2026-10-16

P1-53 implemented: reused the shared exact-source verifier for final excerpt/summary proposals and metadata coverage, KB pause/lock for direct summary commands and atomic replacement for summary persistence. Removed redundant runner summary child instead of adding parent-lock bypass machinery. Full release passed; broader live accuracy controls remain open. Evidence: [review and implementation](normal-processing-audit-review-2026-10-16.md).

## Specification review — 2026-09-19

- Completed: shared citation-span validation for evidence and relations and shared candidate/adjudicated citation-ID accounting for queue validation and inventory.
- Follow-up under P1-43: unify canonical/extraction relation vocabulary after editorial migration decisions; do not duplicate incompatible allowlists.

- 2026-09-10: Keep automatic adjudication selection separate from persistence checkpoints. The orchestrator now caps each `process-pending` retry stage at the existing ten-item batch size while retaining the ten-item atomic checkpoint.

## Candidate promotion workflow

- Consider a first-class `import-candidate-batch` command with explicit added/changed/removed candidate reporting. Queue rebuilding now fingerprints candidate content and resets changed candidates to pending safely.
- Move exact accepted-candidate reconciliation into a reusable typed queue model rather than validating untyped dictionaries.
- Add a processor that proposes contiguous evidence clusters from candidate segment IDs using the same 30-second and 20-second-gap rules as validation.
- Provide an editorial promotion helper that creates canonical evidence records from reviewed candidate clusters without hand-written one-off transformation code.
- Validate every candidate segment ID against the normalized transcript immediately after Codex extraction so invented or mistyped IDs never reach the editorial queue.
- Add a review-batch report that groups pending candidates by video, matched canonical concept, contiguous evidence cluster, and publication impact so partial review does not require ad hoc inspection scripts.

## Validation

- Extract source-span validation into a shared function and apply it consistently to concept evidence and relation sources.
- Keep daily LLM budget reservation, reconciliation, and status reporting in the shared `processors.llm_budget` service rather than duplicating token checks in extraction, rephrase, and benchmark commands.
- Add explicit validation that source bounds enclose their cited segments, allowing only the documented final-caption/video-duration clamp.
- Return structured validation findings with severity and item identifiers instead of plain strings.
- Add navigation diagnostics that distinguish missing placement, valid cross-listing, and accidental duplication.
- Share the Codex subprocess runner between extraction and excerpt-rephrasing stages if additional structured editorial transforms are added; both currently preserve isolated, schema-constrained execution.

## Ingestion

- Share ordered source-caption language matching between transcript adapters so exact configured codes remain preferred while regional fallback behavior stays deterministic and testable.
- Generate `source-video-progress.md` from source-specific discovery manifests and pipeline artifacts instead of maintaining its snapshot tables manually.
- Add a shared daily-run orchestrator around the CLI phases rather than duplicating scheduling policy in PowerShell, Task Scheduler, or future CI jobs. It should own locking, missing-artifact workset selection, run manifests, and machine-readable exit classes.
- Make extraction workset selection hash-aware and idempotent so the timer never re-invokes Codex for an unchanged normalized transcript merely because `extract-concepts` was called without `--video-id`.
- Keep retry-cooldown enforcement covered by CLI tests as ingestion options evolve; the command now enforces `next_retry_at` and permits an explicit override only after a route change.
- Add an explicit single-video `probe-ingestion` command that does not imply a full batch restart.
- Normalize video-title encoding when source metadata enters the pipeline so mojibake cannot persist in configuration.
- Preserve separate discovery manifests per source. The current command overwrites `discovered-videos.json`, and some channel handles resolve only to invalid tab placeholders rather than video entries.

## Site

- Add a visible badge for single-source concepts. Transcript-inferred visual moments are now labeled as proposed and cannot loop until verified.
- Add a generated “Recently added” view based on reviewed content provenance or an editorial publication date.
- Add browser-level tests for primary/cross-listed topic paths, base-path routing, and non-looping transcript-only evidence.

## Concept synthesis

- Keep evidence-summary construction in `processors/evidence_summaries.py` and reuse it for future knowledge bases instead of duplicating prose assembly in Astro pages. The deterministic path remains a no-cost fallback; the explicit batched Codex path handles coherent prose, with attribution/paragraph validation shared by both.
# Review-queue YAML stability

- The review-queue writer rebuilt plain dictionaries with ruamel.yaml's default narrow line width, creating thousands of formatting-only changes on a no-op queue refresh. Keep a wide output width so generated candidates remain readable and diffs stay focused on actual candidate changes.
- Reuse the existing round-trip YAML candidate node when its fingerprint is unchanged; reconstructing it discarded quoting and reviewed presentation-only corrections even though the candidate itself had not changed.

## Site TOC

- Extract the deterministic per-video TOC join, sorting, de-duplication, and anchor validation into a shared helper if more site views need the same index; do not add an LLM call to the build path.

## Progress reporting

- Reuse `select_source_balanced` for extraction, automatic review, acquisition, and human-review ordering; do not reintroduce independent source-sorted slices that can starve later catalogs.

- Derive the monitor's adjudication completed/total/remaining display from the existing bounded progress stream; do not add a second counter protocol or duplicate queue scans.

- Keep project/source count aggregation in `processors/progress.py` and expose one generated snapshot to local operator pages. Avoid duplicating count logic in Astro templates or documentation; a later quality report should consume the same snapshot.
- Keep the Recent snapshot explicitly metadata-only. Normalized `Video` models include private transcript segments, so serializing them directly can fail the Pages artifact scan and leak raw transcripts into generated HTML.
- Keep Pages credential scans specific to known secret prefixes; a broad `sk-` pattern falsely classified legitimate concept slugs as API keys.
- Keep system resource telemetry separate from the detailed process list: total CPU/memory percentages and rolling browser history make the monitor actionable, while cumulative process CPU time remains a diagnostic detail.
- Keep bucket history owned by durable inventory writes, with the monitor reading it on every refresh. Reuse the already-built ledger summary rather than adding another inventory scan; unchanged observations make flat periods visible without browser polling.

## Generated-file replacement

- Centralize the bounded Windows atomic-replacement retry in `processors.utils.replace_with_retry`; JSON ledgers and round-trip YAML writers previously duplicated or bypassed this handling, which made a transient file lock disproportionately likely to fail a full processing cycle.

## Codex timeout isolation — 2026-08-30

- Keep subprocess timeout translation in `processors.codex_engine` and batch continuation in `processors.pipeline`; this preserves a transport-specific audit/provenance boundary while preventing one slow model call from aborting unrelated candidates.

## Moment boundaries

- Keep caption-unit derivation and boundary assessment in one shared module (`processors/boundaries.py`) so candidate triage and corpus reporting use identical gap, duration, and flag rules.
- Keep proposed snapped playback bounds separate from cited segment IDs; publishing a wider interval without an explicit review would blur the claim-support boundary.
- Scheduled processing now has a reusable PowerShell wrapper for locking and run manifests; the eventual full daily-run orchestrator should reuse those concerns instead of duplicating them.

## Semantic content quality — 2026-08-12

- Completed: replaced the promotion-time `_largest_contiguous_group` shortcut with shared boundary assessment that reports discarded clusters and makes Codex selection defer rather than silently dropping support.
- Completed: centralized extraction resolution invariants in the Pydantic candidate model and added a safe migration for contradictory legacy candidate artifacts.
- Completed: extracted a schema-constrained Codex semantic-adjudication function with the same model, timeout, budget, ephemeral workspace, audit, and fail-closed conventions as extraction.
- Follow-up: move repeated concept restoration/new-concept provenance construction into one helper if another adjudication path is added.
- Generate semantic-quality metrics alongside `progress.json` instead of reimplementing corpus counts in Astro pages or dated documentation. Include human provenance, segment retention, source-envelope accuracy, taxonomy vocabulary, alias collisions, summary provenance, and graph isolation.
- Add a reusable transcript-track quality classifier and legacy provenance migration so generated/manual status and fragmentary/mixed-language warnings reach extraction and review consistently.
- Keep representative-evidence selection in a shared reviewed-support scorer; model confidence should be a tiebreaker only after support, boundary completeness, redundancy, and source diversity.

## Processing throughput — 2026-10-12

- P1-44 implemented: final partial batches reuse dirty-concept persistence; empty/full-checkpointed passes skip the duplicate final save. Loading unrelated round-trip documents remains a separate, unimplemented optimization.
- P1-38: apply attempt-aware source rotation to actual proposals; the current queue slice loses video-pool ordering.
- P1-45: reuse shared caption-unit derivation in repair context and preserve existing adjudication provenance during queue rebuild; do not create a second boundary rule set.
- P1-46: skip a no-change queue rebuild only after candidate/schema fingerprints establish safe invalidation. Evidence and acceptance criteria: `docs/processing-throughput-review-2026-10-12.md`.

## Whole-process entry points — 2026-09-10

- Reuse the shared `run-cp.py` continuation path for configured-source discovery and its per-KB lock; remove the obsolete local catalog and configured-video selectors so the manifest cannot report a different workset from the ledger.
- Reuse one bounded monitor request-body reader across start and review-task endpoints instead of maintaining separate stream loops; add another endpoint only when it needs a different limit or content type.
- Keep Windows scheduling policy in one utility used by the CLI callback and orchestrator; process creation flags then cover each orchestrator stage without lowering the monitor UI.

## 2026-10-13 — Monitor page duplication

- `scripts/processor-monitor.mjs` retains unused legacy page templates alongside the served dashboard. Remove them in a separate cleanup after checking template dependencies; this control fix changes only the active dashboard.

## 2026-10-14 — Citation identity and summary text

- Exact spoken-citation identity is used by incorporation and validation; keep the two short local checks until a third caller needs a shared helper. Validation additionally preserves distinct visual windows.
- Legacy deterministic reason rewriting has many substitutions. Consider replacing that path with explicit reader-facing reason inputs once P1-33/P1-34 quality evaluation is complete; do not add more domain-specific regex transformations.

- Published-content filtering is now repeated between the publisher and the private exhaustive-audit input loader. When publication eligibility changes, extract one shared selection helper and verify output equivalence; do not let audit coverage and public eligibility diverge.

- Adjudication and exhaustive audit now share the schema-constrained CLI transport, preserving timeout/budget/provenance handling. Extraction/rephrase/summary transports still duplicate some execution scaffolding; consider consolidating them only when another contract change needs it, with output-equivalence/error-path tests.

- Summary YAML writing now handles complete scalar boundaries rather than physical lines. If more editable fields or unusual top-level formatting need support, move this writer to the repository's round-trip YAML approach; avoid accumulating format-specific regex branches. Current scope is definitions, summaries and summary metadata with regression coverage.

- Implemented 2026-10-14: span assessment, envelope repair and source validation share the raw caption-duration conflict check. Preserve metadata precision uncertainty; defer unknown timing rather than inventing a shared tolerance.
- Implemented 2026-10-14: P1-51 reuses the audit dossiers, schema-constrained transport, budget and locks for typed article plans and separate verification. No canonical claim-graph migration or additional dependency.
- Reviewed batch application reloads the entire audit before and after every article. A future throughput change can load the corpus once and update affected fingerprints under the existing KB lock; retain fresh source/target checks and per-article recovery checkpoints. Current finite batches are correct but slow.
- Large-article proposal assembly and caption adjudication share the existing transport but require different prompts. Keep that distinction in the shared call boundary; do not add a second reducer pipeline or skip actual source verification when a draft is uncertain.
- Implemented 2026-10-15: independent evidence verification omits old confidence/approval once at the shared transport boundary used by both repair and new-candidate acceptance. Keep the complete canonical/proposed record for deterministic validation; avoid separate metadata-filtering implementations in each caller.
- Implemented P1-51 efficiency phase 1 (2026-10-15, contract 1.1.0): separate stage policy identities, reuse exact dependency-matched verifier units/provenance, revise failed units only, compact source spans and park unchanged exceptions inside the existing checkpoint/transport. All-corpus draft request characters shrink 49.5%. Batching and token/runtime gains remain unmeasured; known false acceptance persists on GPT-6 Luna controls. Keep primary approval and P1-34 evaluation.

- Verifier policy 1.1.1 uses the existing shared verifier prompt to require incomplete-clause referent grounding. Keep the rule domain-neutral; avoid hard-coded transcript exceptions or a duplicate acceptance path. Fixed Luna high effort flows through existing transport/config/provenance; no task-profile framework added.

- Full audit taxonomy finding (2026-10-15 15:34): reuse configured per-KB facet vocabulary in shared repair draft/verification schema/input, rather than letting models propose free-form tags that application later rejects. Existing application guard stays mandatory. Implement after active campaign idle and invalidate only affected stage/unit dependencies; no hard-coded table-tennis vocabulary.

- Implemented full-audit failure guard (2026-10-15 18:28): align per-unit edit representation once in the existing schema builder and keep the transport-failure counter inside the existing call/checkpoint loop. No separate retry framework, model change or broad cache invalidation; inspect and resume failed jobs only after actual recovery.

- Implemented 2026-10-15 19:27: all five source-only child command paths opt out of Apps and record it in provenance, without a new transport framework. Legacy extraction/summary/rephrase still duplicate command construction; any later consolidation should reuse the shared constrained transport while preserving stage hashes, schema versions, audit/timeout/budget behavior. Defer that broader cleanup until full-audit runtime is idle.

- Throughput review2026-10-15 (P1-51): existing article-field hash in every verifier cache context rechecks unchanged citation support for unrelated rating/alias edits; derive minimal true dependencies, retaining topic/source/target/context invalidation and regression tests. Existing source-row chunking also splits citations and repeats fields; pack complete proof units inside the existing scheduler, without a new service or claim-graph migration. See audit-throughput-redesign-2026-10-15.md for measured costs and bounded acceptance.

- Implemented2026-10-15 P1-51: coverage-first/targeted scheduler removes active reducer/revision calls, full article-field cache hash removed from citation checks, and batch application reuses immutable video inputs under the existing lock. Canonical/source/topic freshness checks and archives remain; measured pilot/release evidence is in audit-throughput-redesign-2026-10-15.md.

- 2026-10-16 12:24: Profile growing apply-published-repairs latency (four reviewed articles several minutes). Reuse immutable work where safe; retain per-article canonical/source/target freshness and archive/transaction guards. Evidence media/audit-rating6-apply-2026-10-16-12.log; P1-51.

- 2026-10-16 13:Measured P1-51 study:shared full corpus rebuild before/after every article plus full YAML archive round-trip. Prioritize exact reviewed optional-null removals andlarger release batches; thenprofile whole scratchtransaction andlimit fresh dependency work without weakening validation/archive safety. See audit-throughput-diagnosis-2026-10-16.md.

- 2026-10-16 P1-51: Batch application now reuses checked post-application corpus state; safe plain archive serialization replaces expensive round-trip archive handling with equality validation. Further per-dependency incremental dossier rebuilding is deferred until whole real-batch measurements justify complexity. Existing full post-application audit rebuild remains once per article.

- 2026-10-16 P1-51 real20benchmark: investigate shared long-lived processor sessions after observed repeated CLI import/corpus-loading delays; preserve source/file freshness and per-KB locking across every operation. Actual profile includes graph/ingestion and rich/Typer-help startup; environmental cause of sudden delays remains unproven. Do not replace a dependency or bypass validation based on import timing alone. Existing correction flow also cannot redraft rejected quarantined units; add a typed, explicitly reviewed restoration path rather than automatically restoring records.

- 2026-10-16 P1-51: replace operational interactive audit REPL usage with existing finiteCLI jobs;do not introduce another worker framework merely to avoid imports. If app-restart survival is later required,use an explicitly designed OS-managed runner with ownedlogs/checkpoints and process identity. Client thread-routing failure is external;do not patch installedapp orbypass KB locks.
