# Whole-project content and moment-accuracy review — 2026-08-12 11:00 EEST

## Executive conclusion

The repository has a strong provenance skeleton, but the current published corpus should not be treated as editorially trustworthy yet. Structural validation passes: source IDs exist, timestamps are bounded, public data excludes transcripts, and inferred visuals do not loop. The semantic publication gate is the weak point. Automatic promotion expanded the corpus from the earlier 73-editorial-concept baseline to 533 concepts without a human decision for each proposal, and the evidence-localization step can silently discard most of the segments used to justify a claim.

The immediate recommendation was to pause the unsafe heuristic promotion path while P0-08 through P0-10 were implemented. The implementation direction was subsequently clarified: human decisions are optional augmentation/advice, while schema-constrained Codex CLI is the default semantic gate.

## Implementation addendum — 2026-08-12 12:05 EEST

P0-08 through P0-10 are now implemented as a Codex-first gate. Extraction uses bounded overlapping jobs; candidate resolution is schema-constrained Codex adjudication; deterministic code enforces exact supplied segment IDs, one contiguous supported span, controlled facets, complete timestamp envelopes, and auditable model provenance. Deferrals remain automated work rather than becoming a mandatory human queue.

The former heuristic output is preserved for audit but excluded from publication: 4,775 evidence moments and 460 generated concepts were marked unreviewed. Safe timestamp envelopes were repaired, while three overlong legacy spans remain quarantined for new adjudication. One live Codex CLI call completed successfully and added an exact supported moment to `concept-ready-position`. The safe public corpus is therefore intentionally smaller: 73 concepts, 51 videos, and 1,119 evidence moments. The queue has 6,470 Codex decisions remaining; human advice/override is optional.

## Scope and method

The review traced the project from configuration and normalized captions through Codex extraction, queue adjudication, canonical YAML, validation, publishing, Astro rendering, tests, operational manifests, and project documentation. It used the current private cached corpus without making network requests or starting the processor monitor.

Checks included:

- required architecture, pipeline, operations, backlog, session, and lessons documentation;
- source, taxonomy, prompt, model, adjudication, boundary, validation, publishing, review-UI, ranking, and TOC code;
- the current queue, canonical YAML, sanitized public corpus, latest processor manifest, and representative exact caption rows;
- deterministic counts for concept provenance, resolution consistency, segment retention, source bounds, navigation, taxonomy, aliases, summaries, relations, visual status, and transcript provenance;
- repository validation and the current quality-report command.

This was a source-grounding audit, not an independent table-tennis coaching endorsement. It checks whether the project says only what its cited moments support and whether the system preserves the right topic and time.

## Current baseline

| Signal | Current result |
|---|---:|
| Approved concepts | 533 |
| Concepts created by `automatic_candidate_review` | 460 |
| Published videos | 729 |
| Eligible normalized videos in local validation | 752 |
| Published evidence moments | 5,892 |
| Queue items | 6,934 |
| Accepted / human review / rejected / pending | 5,117 / 1,807 / 9 / 1 |
| Fully complete eligible videos in latest run manifest | 176 of 752 |
| Videos assigned to human review | 575 |
| Verified visual demonstrations | 0 |
| Proposed `visual_source` windows | 35 |
| Caption-boundary items needing context | 582 of 5,892 (9.88%) |

The current `validate --kb table-tennis` and `report-quality --kb table-tennis` commands pass/run successfully, but their checks do not cover the highest-risk semantic failures below.

## Findings

### P0 — automatic promotion bypasses the stated editorial contract

`process_pending_candidates` can create an approved canonical concept from a high-confidence `new` candidate and can add approved evidence to an existing concept without a tracked human decision. The current public corpus contains 460 concepts whose `generated_by.processor` is `automatic_candidate_review`; all 460 lack reviewed relations. This conflicts with the repository rule that LLM output is a proposal and never becomes approved public knowledge without review.

Model confidence is being treated as if it were calibrated editorial confidence. The extraction prompt supplies no independent entailment check, and the processor verifies that cited segment IDs exist, not that their words support the definition or mapping.

### P0 — dispersed citations are silently collapsed into the wrong moment

The extractor currently receives the entire video transcript. Although `config/processors.yaml` declares `max_segments_per_job: 80` and `overlap_segments: 8`, neither setting is used. Of 753 cached transcript records including the fixture, 733 contain more than 80 segments and 230 contain more than 200; the largest has 637.

The model therefore often cites several locations across a lesson for one evidence rationale. `_candidate_source_span` calls `assess_boundary`, which chooses the largest allowed contiguous group and discards the other cited groups. The definition and reason are copied unchanged, so they can continue to summarize discarded segments.

Measured against accepted queue items:

- 4,663 automatic canonical evidence records could be matched to their source candidate;
- 3,346 (71.8%) published fewer segment IDs than the candidate evidence used to justify the claim;
- 1,253 retained less than half of the candidate segment IDs;
- 287 retained only one segment.

Representative failures found by comparing the exact surviving caption rows:

- `Distance-dependent stroke size` points one published moment at a caption whose complete text is “important thing,” while the reason claims advice about fast balls, smaller strokes, and rhythm.
- `Backhand block angle adjustment` keeps captions about watching an opponent and a change of pace after discarding the cited block-position instructions.
- `Bounce-phase shot timing` keeps a caption about anticipating a heavy return after discarding the cited on-the-rise and bounce-peak instructions.
- `Footwork foundation` keeps captions about brushing and playing soft/strong after discarding the cited footwork rows.
- `Use placement to move the opponent and lower return quality` keeps a disconnected three-caption cluster about aggressive style after discarding the placement and reaction-time rows.

Every surviving ID is real, so the current structural validator accepts these records. The project needs a no-silent-discard rule: split a multi-location rationale into separately supported moments or defer it.

### P0 — concept resolution can accept internally contradictory model output

The schema allows `resolution: new` together with a non-null `matched_concept_id`. `_best_existing_concept_for_candidate` assigns a score of 100 whenever that ID exists, regardless of label or definition similarity. The later `new` check therefore treats the model-provided ID as a strong match.

The accepted queue contains 142 `new` candidates with a non-null matched ID. Examples include a half-long forehand/step-around concept mapped into the broad `Attack first over conservative play` article and a cross-court defensive-positioning concept mapped into `Use placement to move the opponent and lower return quality`. Across accepted items, 257 candidate-to-canonical mappings have a best label/alias token-set score below 60. Low lexical similarity is not proof of error, but at this scale it is a strong review-risk signal and cannot be overridden solely by the model's target ID.

`ConceptCandidate` needs a consistency validator, and publication needs an independent semantic mapping gate or a human decision.

### P0 — some source windows end before their cited caption segment ends

Validation confirms that segment IDs exist but does not require `source.start_ms` and `source.end_ms` to enclose the complete cited segments. In the current canonical corpus:

- 36 evidence windows end before the last cited caption ends;
- 12 truncate more than the UI's 1.2-second playback tail;
- the worst truncation is 9.5 seconds.

This is a timestamp-accuracy defect even when the underlying segment provenance is correct. Source bounds should equal the cited segment envelope. Extra listening context belongs only in the separate spoken-context fields.

### P1 — topic identity and taxonomy have drifted into a flat micro-concept collection

The configured taxonomy defines five category values and a small controlled facet vocabulary, but the model accepts arbitrary strings. The corpus now has 42 distinct `concept_type` values. Forty-one concepts contain out-of-vocabulary facet values, including category values such as `mechanics`, `receive`, `timing`, `power`, and `strategy`, plus `spin: against-backspin` and `distance: neutral`.

There are 43 normalized label/alias strings assigned to more than one concept, spanning 93 concept memberships. Some are legitimate contextual phrases, but others expose unresolved identity overlap, such as the three braking-motion articles, three crossover/step-across articles, two rhythm/tempo articles, and overlapping wrist, flick, spacing, and borrowing-power concepts.

The current corpus also has:

- 466 concepts without outgoing relations, including all 460 automatically created concepts;
- 156 single-video concepts;
- 153 concepts with exactly one evidence moment;
- one approved automatic concept not placed anywhere in navigation, because `validate_navigation` exempts automatically generated concepts from the otherwise documented placement requirement.

This is not yet the intended wiki-style knowledge graph. A corpus-level merge/split/alias/relationship pass is required before more concept creation.

### P1 — deterministic summaries are visible but frequently not editorial prose

All 533 concept pages have a summary string, but provenance is 460 deterministic fallbacks, 72 Codex summaries, and one hand-authored summary. The deterministic builder concatenates cleaned evidence reasons between generic opening and closing sentences. With many moments, the result often contains fragments such as “Swing size and body mechanics to distance from the table” and “About close, medium, or larger spacing.”

Summary presence is therefore being counted as content completeness even when readability and synthesis quality are poor. Deterministic fallback text should be a private draft or a concise structured outline, not an approved public essay without editorial review.

### P1 — moment ranking rewards uncalibrated confidence, not verified support

`evidenceRelevance` assigns 70% of its score to model confidence, 20% to label-word overlap, and 10% to a verified visual. No verified visuals currently exist, and automatic evidence commonly carries confidence around 0.95. The ranking can therefore put a semantically wrong but highly confident clip above a better-supported moment.

Ranking should use review state, exact support/boundary checks, source diversity, and representative-moment decisions. Model confidence may remain a diagnostic but should not dominate public ordering.

### P1 — the human-review tool does not yet support high-quality editorial correction

The five-item workflow is a useful safety improvement, but it shows only the highest-confidence evidence proposal, not every candidate evidence cluster. Accepting copies the model's label, definition, aliases, facets, reason, and evidence type without an edit step. The source link opens the video root rather than the cited timestamp, and there is no embedded playback window.

For topic and time accuracy, the reviewer needs to inspect all proposed support clusters, open/play the exact cited interval, edit the canonical wording/taxonomy before acceptance, and see duplicate/alias/relationship context. The current 1,807-item human queue should not be processed as a simple yes/no throughput exercise.

### P1 — transcript provenance is internally inconsistent

The cached corpus has 181 tracks with `is_generated: true`, but only 18 have `transcript_origin: youtube_generated`; 163 load as `youtube_manual` through the model default. This is legacy-data drift, not evidence that the captions are manual. Generated/manual provenance matters because caption text and timing reliability differ and because quality sampling should be stratified by origin.

A migration should derive or re-ingest this field from durable acquisition metadata and validation should reject contradictory values.

### P1 — quality and operator documentation are stale or too shallow

The local pipeline page still reports 107 videos, 73 concepts, and 1,686 moments while the current public corpus has 729 videos, 533 concepts, and 5,892 moments. The canonical backlog's previous baseline also described the earlier 73-concept corpus. `report-quality` currently reports counts, repetition, graph isolation, source coverage, visuals, and pending candidates, but not segment loss, resolution contradictions, exact source bounds, taxonomy vocabulary, summary provenance, or the human-review backlog.

Generated quality data must become the one source for operator pages and documentation, with semantic-risk metrics added before “valid” is interpreted as “accurate.”

The planning surface itself also has integrity drift: the Markdown contains duplicate IDs `P1-03`, `P1-12`, and `P1-16`; the local page's curated feature map omitted `P1-27` and `P1-28`; and the first post-study build silently omitted every newly added review item until the map was updated. Backlog parsing should reject duplicate IDs and surface every unmapped item instead of dropping work from the HTML view.

### P1 — tracked private operational/audit metadata violates repository policy

Twenty-seven files under `data/manifests/table-tennis/` are tracked, including summary-audit records and historical LLM-budget ledgers. They do not contain raw responses in the sampled files, but repository instructions classify Codex audit data and private processor state as uncommittable. Move retained provenance to an explicitly sanitized tracked report or keep it ignored; do not leave private runtime ledgers in the public Git history.

## What is working well

- Segment IDs and YouTube URLs are generated deterministically rather than invented by the LLM.
- The public corpus strips transcript segments and the public/private copy parity check passes.
- Spoken evidence and `visual_source` are separate; inferred visuals cannot become loopable verified demos.
- The current corpus honestly reports zero verified visual demonstrations.
- Caption-only boundary checks have reduced the old baseline substantially: 5.09% start mid-sentence, 5.43% end mid-sentence, 1.09% are under four seconds, and 9.88% need context review.
- Source-balanced processing, bounded human-review batches, process locks, budget controls, and monitor idleness checks are good operational foundations.
- Validation, tests, lint, Astro diagnostics, and the static build are deterministic and network-independent; the missing layer is semantic quality coverage, not basic reproducibility.

## Recommended recovery sequence

The sequence below records the audit's original recovery proposal. Where it called for mandatory human promotion or review, the implementation addendum above supersedes it with Codex semantic adjudication plus deterministic validation and optional human advice.

1. Freeze automatic canonical creation/evidence acceptance and public expansion. Extraction may continue privately only if it does not publish or overwrite reviewed decisions.
2. Implement real 80-segment overlapping extraction jobs and a per-evidence contiguous-support contract. Reject or split multi-location rationales; never silently choose one cluster while retaining a multi-cluster reason.
3. Add exact source-envelope validation, resolution/matched-ID consistency, controlled taxonomy validation, and support-aware quality metrics/tests.
4. Generate a private published-content remediation queue, prioritizing the 3,346 segment-loss records, 142 contradictory resolutions, 36 truncated source bounds, low-similarity mappings, generated-caption tracks, and highest-traffic concepts.
5. Audit the 460 automatically created concepts as a corpus: merge duplicates, correct aliases/facets/navigation, add or remove relations, and require a tracked human editorial status.
6. Replace or review the 460 deterministic public summaries and rank moments only after support checks pass.
7. Upgrade the human-review workspace with exact timestamp playback, all evidence clusters, editable canonical fields, duplicate/relationship context, and a named reviewer/audit identity.
8. Build a stratified gold set across all three sources, manual/generated caption origins, languages, concept types, and automatic/editorial content. Measure claim support, topic mapping, boundary completeness, and exact playback accuracy before resuming expansion.
9. Begin visual verification only after spoken evidence is trustworthy. Review the 35 proposed windows and establish at least a small verified core before advertising loopable demonstrations.

## Verification performed

- `processors.cli validate --kb table-tennis`: passed with 533 concepts, 752 videos, and 5,892 non-demo evidence records.
- `processors.cli report-quality --kb table-tennis`: completed; 533 concepts, 729 published videos, 5,892 moments, 460 isolated concepts, 156 single-source concepts, and zero verified visuals.
- Deterministic boundary analysis over the non-demo corpus: 5,892/5,892 evaluated; 582 need context review.
- Private artifact and queue analyses described above were read-only.

The backlog items created or expanded by this review are P0-08, P0-09, P0-10, P1-04, P1-32, P1-33, P1-34, and P1-35.

Post-remediation verification passed. The release gate validated 533 canonical files while publishing only 73 approved concepts and 51 videos, validated the sanitized artifacts, passed all 74 tests and Ruff, reported zero Astro diagnostics, and built 146 static pages. Representative live routes for pipeline, progress, optional advice, backlog, the restored concept, and its source video all returned HTTP 200.
