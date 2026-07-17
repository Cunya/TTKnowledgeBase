# Study: better start and end boundaries for evidence moments

**Date:** 2026-07-16  
**Status:** Phase 1 caption-only baseline and the first Phase 2 review pass are implemented; 9 safe context merges and 4 short-window keeps were recorded, while 11 ambiguous cases remain deferred for source/audio inspection.
**Scope:** Transcript-backed moments, optional authorized local audio analysis, and separately reviewed visual demonstrations

## Executive summary

The current pipeline derives a spoken evidence window from the first and last cited caption segments. That is deterministic and source-grounded, but caption cues do not necessarily align with sentence boundaries. A candidate can therefore begin or end in the middle of a sentence. Very short windows, such as a three-second fragment, can also be technically accurate while being too thin to teach a useful idea.

The safest improvement is a layered boundary policy:

1. Merge caption cues into sentence-like units while retaining every original segment ID.
2. Snap the spoken window to a complete utterance and a nearby pause where evidence permits.
3. Expand only within a small context budget and never across a topic transition.
4. Flag very short windows for merge, context expansion, or review instead of treating them as normal moments.
5. Keep the claim-supporting citation separate from optional playback context, so a nicer listening window does not silently widen the source claim.
6. Use word timestamps, voice activity, and prosody only for authorized local/private media; they are an enhancement, not a reason to bypass source restrictions.

## What the pipeline does today

The current implementation is intentionally conservative:

- Caption ingestion creates timed `Segment` records. The original segment IDs remain the citation anchors.
- Candidate extraction cites segment IDs and does not invent timestamps.
- `processors/pipeline.py::_candidate_source_span` sorts the cited segments, groups them by a configured gap, selects the largest contiguous group, and uses the first selected start and last selected end.
- A spoken source is capped by `MAX_SPOKEN_SOURCE_MS` (currently 30 seconds). Large gaps split a candidate rather than being silently bridged.
- `spoken_context_end_ms` is available for a wider spoken playback context, but it is not currently populated automatically.
- Visual windows are a separate evidence type. A transcript citation should not be presented as proof that a visual demonstration occurs at exactly the same time.

This gives excellent traceability, but it treats caption cue boundaries as if they were linguistic boundaries. That assumption is the source of the mid-sentence problem.

## Boundary signals to combine

No single signal is reliable enough for every video. The recommended design combines deterministic signals first, then uses more expensive or rights-sensitive signals only when needed.

### 1. Caption and punctuation signals

Caption cues can be merged into sentence-like units without losing provenance:

- Merge adjacent cues when the first does not end in terminal punctuation, the next cue begins with a lowercase word or a continuation such as `and`, `but`, or `because`, and the gap is small.
- Treat a cue ending in `.`, `?`, `!`, a colon followed by a new list, or a clear speaker turn as a likely boundary.
- Preserve all source segment IDs in the merged unit; the merge is a derived index, not a replacement transcript.
- Keep a conservative maximum merged-unit duration (for example 12-15 seconds) so a captioning error cannot create an oversized sentence.
- Use a sentence-boundary helper such as `pysbd` only as an aid. The timed source segments remain authoritative because a text-only splitter cannot know the exact spoken time.

This phase works with captions already present in the private normalized data and does not require downloading media.

### 2. Word timestamps from authorized local ASR

When a user has the right to process a local copy of the audio, a word-timestamp ASR pass (for example, the existing optional `faster-whisper` path) can refine boundaries:

- Align the cited words to the caption-derived interval.
- Snap the start to the first complete word and the end to the last complete word.
- Keep the original caption IDs as citation provenance and record the ASR model/version as a derived alignment source.
- Mark low-confidence words and fall back to caption boundaries when alignment is uncertain.

This is appropriate for user-supplied or otherwise authorized local media. It should not become a block-evasion or default public acquisition step.

### 3. Silence, voice activity, and prosody

Pauses are useful because a cut immediately after a word often sounds more natural than a cut at an arbitrary caption edge. A practical first pass can classify pauses rather than relying on one hard threshold:

- A short pause around 250-500 ms is a soft boundary.
- A pause around 700-1,000 ms is a stronger utterance boundary.
- Longer silence, a speaker change, or a clear restart is strong evidence for a boundary.

These values must be calibrated against the sources. Breaths, room noise, music, and automatic gain changes can create false pauses, so pause detection should support caption and punctuation evidence rather than override it.

### 4. Semantic topic transitions

A moment should not expand into the next lesson point merely to avoid a short duration. Build sentence-like units, then detect a topic shift using a cheap deterministic method:

- cosine distance between neighboring sentence embeddings;
- TextTiling-style lexical cohesion; or
- a change-point library such as `ruptures` over sentence features.

The output should be a proposed transition with a confidence score. An LLM can label or explain a proposed boundary, but it must not invent a timestamp. If one candidate crosses a strong transition, split it into separate moments and link both to the concept when appropriate.

### 5. Visual and scene signals

Shot changes, camera motion, and visible demonstrations are valuable for `visual_source` windows, but they are not a substitute for spoken sentence boundaries. A visual action can begin before the explanation, continue after it, or repeat later. Keep visual start/end selection as a separate reviewed task with its own evidence type and confidence.

## Proposed boundary algorithm

The following algorithm keeps the current source-grounded model while making playback more natural.

### Step A: Build derived utterance units

1. Start with normalized caption segments and their IDs.
2. Merge adjacent segments using punctuation, lexical continuation, speaker continuity, and a small gap limit.
3. Store each unit's first/last segment IDs, start/end time, text, and merge reasons.

### Step B: Resolve the candidate's claim span

1. Take the candidate's cited segment IDs as the non-negotiable claim support.
2. Map them to utterance units.
3. If the IDs cover more than one topic unit, split the candidate or retain only the focused contiguous cluster.
4. Set the canonical source span to the smallest set of complete units that contains the cited IDs.
5. Continue to enforce the existing 30-second maximum and citation-gap rules.

### Step C: Add optional context without changing the claim

Expand left or right by a small context budget (for example 1.5-3 seconds, or one adjacent sentence) only when all of the following hold:

- the added material completes the same utterance or gives necessary setup;
- there is no detected topic transition or speaker change;
- the resulting span remains within the maximum duration;
- every expanded segment is recorded as context, not silently treated as cited support.

The data model should distinguish `source` (claim support) from `spoken_context` (recommended playback context). The existing `spoken_context_end_ms` can represent one narrow case, but a future model may need both context start and end plus context segment IDs.

### Step D: Snap to the best available boundary

- Caption-only mode: snap to the start/end of complete caption-derived units.
- Word-aligned mode: snap to complete words nearest a strong pause, while retaining caption IDs.
- Low-confidence mode: keep the conservative caption span and flag it for review rather than guessing.

### Step E: Score and classify

Attach deterministic boundary flags and a score to every moment:

- `starts_mid_sentence`
- `ends_mid_sentence`
- `too_short`
- `needs_context`
- `crosses_topic_boundary`
- `large_internal_gap`
- `low_content_density`
- `boundary_confidence`

The score should explain its result. A reviewer should be able to see the cited text, added context, detected pauses, and the reason for every expansion or split.

## Defining a meaningful minimum duration

Duration alone is not meaning. A short visual example can be useful, while a three-second spoken fragment can be only the end of a sentence. Use duration as a triage signal combined with completeness and content.

Suggested initial classes (to be calibrated with real annotations):

| Duration | Default treatment |
| --- | --- |
| Under 4 seconds | `too_short`; merge with adjacent same-topic context or defer unless it is a clearly complete definition, cue, or visual action. |
| 4-7 seconds | `needs_context`; retain only when it is a complete utterance with enough instructional content. Otherwise expand or merge. |
| 7-30 seconds | Normal candidate range; still reject mid-sentence and topic-crossing boundaries. |
| Over 30 seconds | Split at a sentence/topic boundary; never widen past the spoken maximum. |

Additional meaningfulness checks:

- at least one complete sentence or a complete imperative/cue;
- a minimum content-word count (initially test 8-12 words, not a permanent rule);
- no unresolved pronoun-only fragment such as “that one” without its referent;
- a distinct instructional payload rather than a repeated filler sentence;
- a visual-only short moment is allowed only when `visual_source` has been reviewed.

The UI should explain the exception: “Brief citation; playback includes same-topic context” is clearer than presenting a three-second fragment as a normal demonstration.

## Quality gates and reviewer workflow

Add deterministic validation before publication:

1. Reject or defer any moment with an unresolved `starts_mid_sentence` or `ends_mid_sentence` flag, unless a reviewer explicitly accepts the exception.
2. Require a complete utterance, a documented short-moment justification, or a verified visual window.
3. Reject intervals with invalid segment IDs, internal gaps over the configured limit, topic transitions, or durations over 30 seconds.
4. Collapse duplicate windows that have the same source, concept, and near-identical boundaries.
5. Show a confidence/flags column in the review queue and make low-confidence windows the first review target.

The reviewer should be able to compare the baseline and proposed window on a waveform/transcript strip, play a short loop, and choose `accept`, `expand`, `split`, `merge`, or `defer` with a reason. The selected boundary and reason become training/evaluation data for later automation.

### First worksheet pass (2026-07-16)

The 24-item deterministic sample was reviewed using caption text and neighboring caption units only. Nine items were marked `merge` and received optional spoken playback context in canonical YAML; four complete, meaningful short captions were marked `keep` without widening; eleven cases were marked `defer` because the available metadata was not enough to choose a safe boundary. The merge decisions preserve the original cited segment IDs, and the context fields are playback aids rather than expanded claim provenance. A second report should be generated only after deferred cases are inspected with authorized source/audio context.

## Evaluation study

Create a small gold set before changing the default algorithm:

- sample 50-100 published moments across TT SpinMaster, GlobalTTStudio, and at least one other source;
- intentionally include current three-second moments, long moments, caption-heavy videos, and moments with repeated phrasing;
- have a reviewer mark the preferred start/end, whether each edge is mid-sentence, whether the window is meaningful, and whether a visual action is present;
- record whether the preferred boundary is caption, word, pause, topic, or visual driven.

Compare these variants:

1. current first/last cited caption segment;
2. caption merge and sentence snapping;
3. caption merge plus pause/word alignment for authorized local media;
4. semantic change-point proposals plus the same deterministic snapping.

Measure:

- mid-sentence start rate and end rate;
- percentage of moments under four seconds;
- reviewer acceptance rate;
- median and 90th-percentile duration;
- citation-support preservation (no unsupported expansion);
- split/merge accuracy at topic transitions;
- percentage requiring manual review.

The first release should optimize for fewer boundary violations and better reviewer acceptance, not for maximum automation.

## Staged implementation plan: what is automated in each phase

Each phase has an explicit automation boundary. The default path should work with scripts and reviewed data alone; LLM calls are targeted assists for ambiguity, never the source of timestamps.

### Phase 1 - caption-only baseline

**Automation level:** script-only, with no LLM required.

- Add derived sentence-like units while preserving segment IDs.
- Snap canonical spans to complete units.
- Add `too_short`, `starts_mid_sentence`, and `ends_mid_sentence` flags.
- Add fixtures and metrics for the gold set.
- Use deterministic punctuation, continuation-word, gap, duration, and speaker-turn rules. Defer ambiguous cases instead of calling a model by default.

**LLM role:** none in the normal path. An offline audit may use an LLM to inspect a small sample, but its judgment must not change timestamps automatically.

### Phase 2 - context and review controls

**Automation level:** scripts plus human review; optional, narrow LLM assistance.

- Add explicit context start/end and context segment IDs.
- Add merge/expand/split/defer actions and reasons to the review queue.
- Render a boundary strip that makes the difference between citation and playback context obvious.
- Let scripts enforce context budgets, max duration, valid IDs, and topic-gap rules.

**LLM role:** only for ambiguous same-topic or meaningfulness judgments over supplied timed units. It may suggest `merge`, `split`, or `defer`, but scripts and the reviewer decide the boundary.

### Phase 3 - authorized local alignment

**Automation level:** signal-processing scripts; LLM optional and non-authoritative.

- Add optional word timestamps and voice-activity/prosody features for user-supplied local media.
- Store model/version/confidence provenance and provide a caption-only fallback.
- Let scripts snap to complete words and nearby pauses, detect low-confidence alignment, and preserve caption segment IDs.

**LLM role:** summarize alignment warnings or help prioritize review. It must not listen for, invent, or directly write start/end milliseconds. Audio processing remains opt-in for authorized local media.

### Phase 4 - semantic proposals and calibration

**Automation level:** deterministic change-point scripts plus targeted LLM classification and human approval.

- Add cheap lexical/embedding change-point proposals.
- Calibrate duration, pause, and content thresholds from reviewed outcomes.
- Keep low-confidence cases deferred rather than silently publishing guesses.

**LLM role:** label whether adjacent timed units teach the same idea, identify likely merge/split rationale, cluster semantic repetitions, and draft a concise editorial explanation. It receives candidate units and IDs, not permission to create timestamps.

### Phase 5 - validation, reporting, and publication

**Automation level:** script-only gate after review.

- Validate segment IDs, bounds, max duration, gap rules, flags, provenance, and public/private allowlists.
- Generate timestamp links, anchors, TOCs, quality metrics, and regression reports.
- Publish only reviewed canonical YAML so the static build does not require LLM access.

**LLM role:** optional post-hoc analysis of sampled failures for future rule improvements; never a publication or validation bypass.

## Automation split: scripting first, LLM where ambiguity remains

The boundary pipeline should be script-first. Most timestamp work is mechanical and should be reproducible without a model. An LLM is useful for semantic judgment over already-timed units, but it should not be the clock, the transcript authority, or the final publisher.

| Pipeline phase | Can be done with scripts alone | Appropriate LLM assistance | Final authority |
| --- | --- | --- | --- |
| Ingest and normalize captions | Parse cues, normalize text, preserve IDs, validate monotonic times, and detect gaps. | None required. | Script validator. |
| Sentence-like caption units | Merge on punctuation, continuation words, speaker continuity, and gap/duration limits. | Ask whether an ambiguous adjacent pair is one utterance, using the supplied IDs and text only. | Script rules plus review for low confidence. |
| Word/audio alignment | Run authorized local ASR, word alignment, VAD, pause detection, and waveform feature extraction. | None required for the timestamps; a model may summarize alignment warnings. | Alignment script with confidence fallback. |
| Topic boundaries | Compute lexical cohesion, embedding distance, and change points. | Label the proposed transition and explain whether the neighboring units teach the same idea. | Script boundary plus human review. |
| Candidate span construction | Map cited IDs to units, choose the focused contiguous cluster, apply context/max-duration limits, and snap to valid boundaries. | Rank which adjacent unit is useful context or suggest split/merge rationale. | Script; LLM cannot add an uncited time. |
| Short-moment meaningfulness | Calculate duration, word/content counts, sentence completeness flags, and repeated/filler indicators. | Classify whether a complete short cue is pedagogically meaningful and suggest `merge`, `keep`, or `defer`. | Reviewer for exceptions. |
| Duplicate and repetition control | Exact/normalized hashes, near-duplicate similarity, interval overlap, and representative selection. | Cluster semantically similar explanations and describe the distinction between corroboration and repetition. | Scripted dedupe plus editorial decision. |
| Titles and explanations | Enforce length, forbidden framing, capitalization, and source-link formatting. | Produce a concise standalone title or paraphrase from the approved evidence; never copy a long transcript passage. | Editorial review and validator. |
| Review queue and publication | Validate schema, segment IDs, bounds, max duration, flags, and public/private allowlists; generate links and TOCs. | Provide a short rationale for a reviewer, not an approval. | Deterministic validator and human review. |
| Reporting and evaluation | Compute boundary-violation rate, short-window rate, acceptance rate, duration distributions, and provenance parity. | Help inspect a sampled error set or summarize recurring failure modes. | Scripted metrics; study conclusions remain human-owned. |

### Recommended execution contract

1. **Scripted pre-pass:** generate timed units, candidate boundary proposals, flags, scores, and all valid timestamp links. This pass must be runnable offline from normalized private data and must produce the same output for the same inputs.
2. **Optional LLM pass:** send only the relevant timed units and candidate metadata. Request structured fields such as `boundary_judgment`, `same_topic`, `meaningfulness`, `merge_target`, `split_reason`, and `review_note`. Do not request raw timestamps.
3. **Schema and provenance gate:** reject model output that names unknown segment IDs, introduces a time, changes the source URL, or contradicts the deterministic duration/max-gap rules. Store the model/profile and input IDs for auditability.
4. **Human review:** require review for mid-sentence flags, under-four-second spoken windows, topic-transition splits, low-confidence ASR, and every proposed visual demonstration.
5. **Publish:** publish only reviewed canonical YAML. The static build should be able to run with no LLM access because all approved boundaries and explanations are already stored.

### Where an LLM is not worth the cost

Do not spend model calls on cue sorting, duration arithmetic, timestamp URL generation, exact duplicate detection, schema validation, or link/anchor checks. These are faster, cheaper, and more reliable as scripts. Likewise, do not ask an LLM to listen to a waveform when VAD/ASR can expose the relevant timed words and a reviewer can inspect the audio when needed.

### Where an LLM adds the most value

Use the configured low-cost extraction profile for a small, targeted set of ambiguous cases:

- deciding whether a short complete cue has a real instructional payload;
- distinguishing a continuation from a new topic when lexical signals disagree;
- choosing between merge, split, and defer for neighboring units;
- grouping semantically repeated moments and identifying the representative explanation;
- drafting a non-transcript-framed title or concise editorial explanation from approved evidence.

Batch these decisions after the scripted pre-pass, send only the smallest relevant context, cache results by input hash, and retry only invalid or low-confidence outputs. This preserves cost control without making the LLM responsible for boundary correctness.

## Rights and operational boundary

Audio download, ASR, and waveform analysis should remain opt-in for media the operator is authorized to process, especially when the site is public. The public build should continue to expose authored analysis, short rephrased evidence, source links, and standard embeds rather than raw transcripts or downloaded media. A better boundary detector must improve editorial quality; it must not be used to defeat platform blocks or to expand redistribution.

## Recommended backlog follow-up

This study supports a focused implementation item:

**P1-14 - Align moment windows to sentence and meaningful-duration boundaries**

- Implement caption-only sentence merging and boundary snapping first.
- Add short-window and mid-sentence flags plus review actions.
- Add an evaluation set and baseline metrics before enabling word/prosody alignment.
- Keep authorized local ASR optional and preserve claim citation separately from playback context.

Done means the project can measure and reduce mid-sentence and non-meaningful short moments without losing segment-level provenance or violating the 30-second and public/private safeguards.

### Phase 1 implementation evidence (2026-07-16)

The script-only baseline is available as `processors.boundaries` and the CLI command `report-boundaries`. It derives bounded caption units, reports proposed snapped bounds, and does not modify reviewed evidence. `process-pending` now defers new candidates with `starts_mid_sentence`, `ends_mid_sentence`, `too_short`, or `needs_context` flags so an editorial decision is required before promotion.

The first table-tennis baseline is recorded in `docs/moment-boundary-report-table-tennis-2026-07-16.md`: 1,826 of 1,826 non-demo evidence records were evaluable; 16.4% started mid-sentence, 17.5% ended mid-sentence, 3.5% were shorter than four seconds, and 31.9% required context review. These rates are measurement, not a completion claim. The deterministic worksheet exporter now creates a stratified 24-item gold-set sample from the 582 flagged moments at `data/manifests/table-tennis/boundary-review.json`; all 24 remain pending reviewer decisions. A second report must wait until those actions are recorded, so no reduction is claimed yet.

## Open decisions

- Should the first minimum-duration warning be 4 seconds, or should it be driven primarily by complete-sentence/content checks?
- Should context use the existing `spoken_context_end_ms`, or should the model gain a symmetric context range and context segment IDs?
- Which sources are authorized for local audio alignment, and how should that provenance be recorded?
- Which reviewer labels are needed to train a future boundary scorer without making the LLM the timestamp authority?
