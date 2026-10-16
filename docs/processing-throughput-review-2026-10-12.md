# Processing throughput without weaker quality gates — 2026-10-12

## Decision

There is avoidable mechanical work that can be removed without changing model inputs or editorial decisions. Start with redundant persistence (P1-44). Candidate scheduling (P1-38) and boundary-aware adjudication (P1-45) offer further gains, but their effect on accepted content requires evaluation under P1-34. No runtime optimization, model change, scheduler change, or processing run was performed for this review.

Retain the current model/profile, independent Codex semantic decision, confidence threshold, exact segment-ID checks, contiguous support, complete caption boundaries, 30-second spoken limit, taxonomy checks, quarantine, visual honesty, budget/locking, and publication validators. Do not automatically widen citations or accept an earlier model response that failed deterministic checks.

## Authorized implementation follow-up — 2026-10-12

P1-44 is now implemented and verified: final partial batches write only dirty concept documents and the queue; empty passes and already-checkpointed full batches do not perform a redundant exit save. Tests cover zero/nine/ten/eleven/twenty candidates across acceptance, rejection, deferral, new/restored concepts, and repeated evidence, including unchanged file bytes/mtimes. Existing interruption recovery remains covered. The full release gate passed (127 tests, Ruff, published-artifact validation, zero Astro diagnostics, successful static build). Reviewed YAML hashes were unchanged; published corpus hashes matched after excluding generation time. P1-38/P1-45/P1-46 remain evaluation/planning work.

A bounded local replay used separate temporary copies of the real queue and 597 concept files, the existing normalized cache, the current selected video pool, and ten stubbed model deferrals. The pre-fix function was reconstructed in memory by reversing only the persistence edit; no repository source was replaced. Timed function execution fell from 47.63s to 28.08s, saving 19.55s. Hashes of model inputs, resulting queue (excluding attempt timestamps), and semantic canonical documents were identical. Temporary copies were cleaned up; no model tokens were spent or editorial decisions written to real content. This is a single before-then-after replay with possible cache effects, not a measured production model-cycle speedup.

## Evidence and limits

- Inspected current pipeline, orchestration, boundary assessment, model prompt, configuration, inventory selection, queue rebuild, diagnostics, checkpoint tests, latest manifest, private adjudication metadata, and scheduled-task configuration.
- Latest cycle: October 11, 21:00:08–21:05:00 EEST; completed successfully in approximately 292 seconds. Stages: adjudication 222.1s, queue rebuild 33.1s, summaries 1.9s, publication 18.2s. Remaining time includes orchestration/inventory work; it was not separately profiled.
- Stage summary: ten checked, two accepted, eight deferred, one evidence moment added, no new concepts. Manifest inventory moved from 1,248 to 1,249 accepted proposals, with completion unchanged at 61/752 eligible videos. These counters do not represent two newly added evidence moments.
- Published snapshot: 343 concepts, 206 videos, 1,840 evidence moments; 35 proposed visual windows, zero verified. Raw queue: 6,934 entries, including 1,252 accepted, 5,501 deferred, 106 rejected, 75 pending. Inventory counts 6,930 proposals and 5,500 deferred. Keep raw queue, inventory, and public-corpus metrics separately labeled rather than treating them as interchangeable.
- Read-only serialization measurements on this workstation: safe queue load 4.31s; one in-memory queue dump 14.94s for 14,922,542 characters; round-trip loading 597 concept documents 8.82s; serializing those documents 5.07s. These are single observations without file writes, not an end-to-end benchmark or guaranteed savings.
- The manifest retains only the tail of adjudication output, so it cannot provide all ten model-call durations. No live model benchmark, network ingestion, or paid model call was made.
- Monitor API reported `running=false`, `activeRun=null`; the service is listening on 4322. The scheduled task is ready, last result zero, next invocation October 12 at 21:00 EEST, using the default ten-proposal batch.

## Findings

### P1-44 — Avoid duplicate checkpoint persistence

**Location:** `processors/pipeline.py:565`, `:638`, `:917`.

Every tenth considered item calls `persist_checkpoint()`. At loop exit, `persist_checkpoint(all_concepts=True)` saves the queue again and rewrites every concept, even when the last item just checkpointed and nothing changed. Dirty concept IDs are already tracked, including acceptance/restoration/new-concept paths.

**Smallest safe change:** flush only uncheckpointed queue mutations and dirty concepts at successful exit; retain the ten-item interruption checkpoint and atomic replacement. Avoid loading round-trip documents for unrelated concepts only as a separately measured follow-up, since that requires more restructuring.

**Quality assessment:** no editorial decision or model input needs to change. This is the strongest candidate for output-equivalent optimization. The measured duplicate queue/concept serialization is approximately 20s, or 6.8% of the observed cycle; actual wall-clock savings require an implementation benchmark.

**Acceptance:** compare queue/canonical contents against baseline for zero, nine, ten, eleven, and twenty processed items; cover new concepts, restorations, duplicate evidence, all-deferred passes, and interruption after a checkpoint. Unchanged concept bytes and modification times must remain untouched. Preserve atomic replace/error behavior and recovery semantics.

### P1-38 follow-up — Apply fairness to the actual proposals, not only the video pool

**Location:** `processors/inventory.py:338`, `processors/pipeline.py:681`, `:694`, `scripts/run-cp.py:280`.

Inventory selection fairly constructs a 50-video pool (17/17/16 by source). The CLI passes these IDs as a set. The candidate loop then keeps matching proposals in queue-file order and takes the first ten, discarding the video pool's attempt-aware ordering. `max_adjudication_attempts=2` only annotates review notes; it does not cap or cool down retries.

Using the latest manifest's pool and the current queue, 72 pending proposals are eligible, but six of the next ten slots retry proposals with 13–135 prior checks. The predicted next ten are distributed 2/2/6 across the three sources. This is a current-state selection simulation, not a reconstruction of the previous run.

**Smallest safe change:** choose proposals with pending/least-attempted priority and source rotation at the candidate level. Keep retryable work visible, use bounded retry cooldowns with explicit reactivation, and ensure old deferrals eventually receive service. Do not permanently drop or auto-reject difficult proposals.

**Quality assessment:** validators can stay identical, but reordered adjudication can change the available concept options for later create/merge decisions. Therefore this is not an assertion of identical model output. Evaluate duplicate-topic creation, mapping, source coverage, and starvation before enabling it.

**Acceptance:** a mixed pool must service pending proposals despite early repeated deferrals, preserve source rotation in the actual ten calls, eventually revisit deferred work, survive restart, and record exact selected candidate IDs/reasons. Measure final decisions and evidence moments per call alongside quality, not attempts per day alone.

### P1-45 — Give boundary repair the information required to succeed

**Location:** `processors/pipeline.py:441`, `:727`, `:785`; `processors/codex_engine.py:276`; `processors/boundaries.py:137`.

The prompt includes exact caption context and the 30-second limit, but not the derived caption-unit boundaries that the validator enforces. Context is fixed to two rows either side of candidate citations. A retry sends the original candidate, context, and concept options again, without the queue's previous failure reason. Consequently a model can repeatedly accept semantically valid support that deterministically fails because it starts or ends inside a caption unit. Latest successful audit metadata records model accept decisions even where the stage subsequently deferred them.

The current queue includes 149 boundary-related deferrals and 56 dispersed-support deferrals. Of 5,501 deferred proposals, 3,720 retain the legacy quarantine reason and 1,569 the return-to-automation reason. Most of the backlog still needs adjudication; do not characterize all 5,501 entries as repeated boundary failures. Six deferred items have at least ten recorded attempts; one has 135.

**Smallest safe experiment:** supply the prior deterministic failure, exact original IDs/text, and complete derived caption units around the candidate. Let Codex explicitly select a revised complete span and rewrite its reason/excerpt to that span. Re-run every existing validator. Keep proposed expansion under the spoken-duration limit; defer dispersed, overlong, unsupported, or ambiguous cases. A suggested unit is guidance, not evidence approval.

**Prerequisite:** `build_review_queue` preserves attempts/reasons but omits `adjudication_provenance` (`processors/pipeline.py:413`). The current rebuilt queue has zero such fields. Private hash-named audit files remain, but repair/idempotency must not assume queue provenance survives. Preserve audit references and unchanged-input fingerprints across rebuilds before using them to schedule retries or reuse a failed result.

**Quality assessment:** promising, not proven. Expanded context and changed prompts can change topic interpretation. Version the prompt and compare a fixed stratified sample of short fragments, punctuation-poor captions, dispersed citations, near-30s spans, genuine insufficient evidence, and new/existing concept decisions. Judge entailment, complete boundaries, concept identity, excerpt accuracy, and rejection/defer correctness. Better acceptance counts alone are not a quality result.

**Acceptance:** demonstrate fewer repeated failures without worse judged support/mapping/boundary accuracy; retain all publication invariants and provenance. No automatic snapping, lower threshold, or silent promotion. Stable unchanged failures should wait for a due retry or a relevant input/prompt change, rather than consume identical calls indefinitely; maintain eventual retry coverage.

### P1-46 — Remove unnecessary cycle overhead before increasing capacity

**Location:** `scripts/run-cp.py:219`, `:344`, `:371`; `processors/pipeline.py:362`.

Every cycle rebuilds the queue, even when no candidate files changed. The latest rebuild took 33.1s. This is separate from duplicate checkpoint persistence. Skipping that rebuild is potentially output-equivalent only when a complete extraction/candidate/schema-version fingerprint proves it unnecessary and the adjudicated queue remains durable. Preserve provenance rather than relying on the current rebuild to strip fields.

The current scheduler runs one ten-proposal cycle daily. More cached-only cycles or a larger sequential batch can increase capacity without relaxing gates, but do not repair unproductive retries by themselves. The latest cycle used approximately 187,564 token units according to the ten private audit records, well below the 12M adjudication/30M total daily limits. This is token accounting, not cost. Twenty serial checks at the observed per-cycle rate could increase attempts; it does not establish an increased number of correct final decisions.

**Smallest safe order:** fix repeat selection/repair, remove redundant rebuild only with invalidation tests, then evaluate a bounded cached-only workload at the existing model/thresholds. Preserve checkpoints, locks, budgets, stage timeout, and stop on publication failure. Keep final publication validation even when refreshing the site less often. Do not start more scraping; all 691 incomplete eligible videos are currently in adjudication.

**Acceptance:** measure wall time, calls, token units, supported final decisions, source fairness, and remaining workload on a fixed replay; prove unchanged candidate inputs skip only unnecessary regeneration and changed/new/removed inputs invalidate it. Larger batches must remain bounded under worst-case per-call timeouts and recover at the existing checkpoint interval. Operator chooses the increased compute allowance/schedule after the result is reviewable.

## Recommendation order

1. Implement and verify P1-44 first: mechanical persistence reduction with equivalent content.
2. Finish P1-38 proposal-level fairness and evaluate P1-45 repair under the P1-34 quality benchmark.
3. Address P1-46 no-change rebuild detection; then consider greater cached-only capacity.
4. Leave cheaper models, reduced reasoning, truncated context, batched semantic decisions, concurrent canonical writers, shorter timeouts, lower thresholds, and automatic boundary acceptance out of this pass. None has evidence of lossless quality here.

No reliable total speedup can be promised before implementation. Mechanical work is measurable; semantic throughput remains constrained by the quality benchmark and correct final decisions.

Planning source: [consolidated backlog](prioritized-backlog-2026-07-15.md). Operational context: [operations](operations.md). No changes were made to processing, canonical knowledge, or public corpus data.
