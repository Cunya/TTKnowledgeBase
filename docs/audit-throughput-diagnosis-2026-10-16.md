# Audit throughput diagnosis — 2026-10-16

Observed 2026-10-16 13:10 Helsinki time. Read-only investigation; no model calls or canonical changes.

## Finding

The remaining audit is slow mainly because the workflow repeatedly revalidates, serializes, reviews and publishes small groups. Initial machine coverage is already complete; it is not the same as source-reviewed clearance. The previous 55–60 hour estimate was a linear extrapolation of mixed initial-coverage and repair work, not a measured forecast of remaining work. Do not use it as a reliable completion estimate.

## Measured evidence

- Six saved coverage batches:120 calls,2,903,654 processor tokens,3,020.54 seconds (50.3 minutes),113 article visits (not necessarily unique or completed). These calls produce private dispositions, not public clearance.
- Ten saved full release gates today:1,721.42 seconds (28.7 minutes) in Python tests alone, excluding validation,publishing,monitor tests,Astro and observation latency. Four recent repair releases alone used782.72 seconds in Python tests. These totals cover the explicitly collected logs, not every operation in the thread.
- Two explicit difficulty-only repair batches used16 model calls/306,505 processor tokens for six applied articles. This is unnecessary generative work for deleting a reviewed unsupported optional rating.
- Read-only cProfile of `_published_audit_inputs`:7.855 seconds; canonical loader3.824s,full audit rebuild3.485s,377 dossiers3.138s. Instrumentation adds overhead. Application calls this before and after EACH article and also reloads all reviewed concepts for collision checks.
- Shared reviewed YAML archive2.18MB/168 repairs:5.29s round-trip load,4.39s in-memory rendering. Real application additionally safe-parses and checks the entire rendered archive before replacement. Repair-plan JSON36.8MB:0.42s load,0.96s in-memory serialization. Rewriting history scales with accumulated history.
- Source reviewer/model disagreement and partial repairs create repeat work. Known examples: optional difficulty returned uncertain/no edit; full selected serve context missed by verifier; mandatory full application waits for advisory model exceptions. Actual polarity errors also exist,so removing source review would be unsafe.
- Related brushing definition changed,causing entire friction-vs-impact review to reopen via advisory topic-overlap context,although its claims and selected captions were unchanged. Fresh full source review restored it at zero model cost.
- Frequent small progress turns,duplicated documentation and separate backlog builds add parent-chat/token/interaction overhead. Processor token logs do not measure that cost.

## Recommended sequence (P1-51)

1. Implement zero-model typed removal of optional difficulty ONLY when exact-current complete primary review explicitly rejects that rating. Preserve all other fields,archive originals,validate final delta and keep source/final-review guards. No blanket metadata wipe.
2. Assemble 20–30 reviewed corrections and release once per batch,with targeted checks while editing and the complete mandated release gate at batch end. Do not run the entire suite for every one or two content articles. Keep detailed evidence private; consolidate logs/docs/backlog at meaningful batch/study checkpoints.
3. Reuse immutable caption/corpus indexes within the held lock; compute changed article/source/target dependencies instead of rebuilding all377 dossiers twice per application. Retain fresh file/source/target checks,collision detection,transaction recovery and archive-before-write. Profile a whole scratch transaction before changing it; current read-only timings do not fully attribute earlier multi-minute application latency. Avoid a new storage framework unless measurement justifies it.
4. Separate source-claim fingerprints from advisory duplicate/topic-overlap context. A related wording change should reopen duplicate/overlap judgment only; actual topic,relation-target or owned-caption changes must reopen their affected claim reviews.
5. Queue text repair,citation/context repair and footage review separately. Target Luna high at unresolved semantic edits,not deletions or already-reviewed unchanged fields. Model verdicts stay proposals; explicitly resolve source-proven false model rejections without erasing missing-proof or footage requirements.
6. Benchmark one representative 20-article batch including difficult cases:elapsed time,processor tokens,parent review effort,applied/pending/quarantined counts and frozen false-acceptance controls. Estimate remaining duration only after this. No claimed speedup or shortened completion guarantee yet.

Evidence: `media/audit-throughput-diagnosis-2026-10-16-13.json`, `media/audit-throughput-profile-2026-10-16-13.log`. Code: `processors/cli.py:apply_published_repairs`, `processors/published_repair.py:apply_reviewed_plan/write_repair_archive`, `processors/published_audit.py:build_published_audit`. Operations: [operations](operations.md); planning: [P1-51](prioritized-backlog-2026-07-15.md).

## Implemented throughput safeguards — 2026-10-16 14:27 EEST

Implemented exact-current complete-primary difficulty removal with zero model calls, checked post-application snapshot reuse, safe plain YAML archive serialization with complete equality validation, separate advisory-overlap pending review, and private text/citation/footage work queues. Batch reuse regression requires three corpus reads for two articles (formerly four) and rejects a detected external write before the next article changes. Actual source/target changes still reopen claims; legacy decisions migrate only on exact original full-fingerprint equality. Full post-application corpus rebuild remains once per article rather than introducing an unmeasured dependency-cache framework.

Scratch benchmark evidence: `media/throughput-benchmark-2026-10-16-14.json` and reproducible private fixture script of the same stem. With the actual 2,183,519-byte/168-record archive, two previous round-trip load/render/reparse/write trials took10.10s and12.19s; safe plain trials took3.66s and3.69s (approximately3× archive-path improvement). Twenty complete scratch transactions, each independently seeded with that archive, took78.02s total/3.90s mean and preserved all prior archive values plus the original rating. These transactions include canonical validation, archive-before-write and journaling; fixture setup and explicit history assertions are outside the reported transaction timer. No production article changed and no model call ran. Benchmark and release validation briefly overlapped on this workstation; timings are local observations, not a controlled end-to-end speed guarantee.

Focused tests:87 passed. Representative real20article semantic/quality benchmarking, frozen false-acceptance controls and full corpus clearance remain open. No new remaining-hours estimate is justified by these application measurements. Follow the [batch procedure](operations.md#throughput-implementation--2026-10-16-1426-eest) and retain final-primary/source/footage/quota safeguards.

Release evidence: `media/throughput-release-2026-10-16-14.log` passed the idle full gate:274 Python tests in150.65s,nine monitor tests,Ruff,zero Astro errors/warnings and635 pages. Current-ledger bootstrap preserved92/377articles and683/4465units supported;285articles/3782units pending. Zero structural/source-metadata findings and no pending overlap reviews at this checkpoint. Implementation used zero model calls and did not change canonical production articles. Full corpus clearance remains incomplete.
