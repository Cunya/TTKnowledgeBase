# Prioritized project backlog — 2026-07-15

This is the consolidated backlog from the architecture review, content review, legal/platform review, transcript-quotation audit, TOC automation review, and public-to-private transition plan.

It is intentionally ordered. The project should complete the blocking and trust items before another large scrape or extraction batch.

Last refreshed: 2026-10-16 19:18 EEST.

## Processing throughput study — 2026-10-12

- Source: [processing throughput without weaker quality gates](processing-throughput-review-2026-10-12.md). Latest cycle succeeded, but accepted only two of ten proposals and added one evidence moment; eligible-video completion stayed at 61/752.
- P1-44 tracks output-equivalent redundant persistence removal. P1-38 needs proposal-level fairness; fair video selection is lost when the queue is sliced. P1-45 tracks evaluated boundary-aware retries. P1-46 tracks no-change regeneration and bounded cached-only capacity.
- Keep every semantic, provenance, boundary, visual, budget, locking, and publishing gate. No model/profile/runtime/schedule change was made; semantic speedups require P1-34 quality evidence before activation.

## Specification review reconciliation — 2026-09-19

Source: [specification gaps and issues](specification-gaps-and-issues-2026-09-19.md).

- Current regenerated public snapshot: 342 concepts, 202 videos, 1,828 evidence moments, 35 inferred visual windows, and zero verified demonstrations. The August baseline below is historical.
- Inventory: 838 videos, 752 eligible, 60 complete, 692 with automated work remaining, 86 excluded. Queue: 6,930 proposals (1,249 accepted, 101 rejected, 65 pending, 5,515 deferred); 90 accepted proposals remain absent from the public-corpus incorporation calculation. Continue P1-34; do not confuse public absence with lost canonical evidence.
- P0-12 closes queue auto-acceptance and relation/public-artifact validation bypasses. P1-42 fixes citation accounting, source-video retention, and demo validation.
- P1-43 tracks visual-limit/vocabulary decisions and three quarantined overlong relation citations. Existing P1-01/P1-13, P1-32/P1-33/P1-34, P1-35, and P2-01 retain the remaining visual, editorial, planning, and private-artifact work; dependencies and acceptance remain in those items.
- P2-01 mitigation: private successful audit files, budget backups, cp manifests, and temporary writes are now ignored. Already tracked files/history still require operator remediation; this review did not stage or remove them.

## Opponent feature-parity study — 2026-09-19

- The published site has partial opponent parity: an Opponent adaptation topic branch, opponent-related concepts, generic concept-relation arrows, and the shared evidence player are present.
- Opponent movement/shot arrows, structured opponent profiles, tactical sequences, match history, and opponent-specific annotations are not implemented. Generic relation arrows must not be presented as directional tactics.
- Full findings and the minimum future scope are recorded in [opponent feature parity](opponent-feature-parity-2026-09-19.md). Track the definition work under P2-11; no implementation is authorized by this study.

## Atlas classification audit - 2026-07-22

- Moved four receive/point-selection tactics out of the Push shot branch: `loop-against-half-long-ball` and `deceptive-service-return-variation` now live under Serve receive, while `one-push-one-hit` and `push-first-then-drive-is-incorrect` now live under Strategy and point patterns.
- The Push branch retains concepts whose primary subject is push execution, spin, contact, or push-specific match use.
- Acceptance evidence: navigation validation reports no unknown concept IDs and each moved concept appears in its intended learning path.
- Extended the audit across all 514 atlas concepts. Corrected additional clear mismatches: receive actions moved out of Loop/Push, serve-spin variation moved out of Forehand loop, backspin-push training moved to Training and drills, a push error moved to Push, and forehand-transition footwork moved to Footwork and spacing.
- Process finding: automatic placement previously accepted any highest keyword score, including weak or near-tied matches. Added a strong-match and margin gate so ambiguous generated concepts stay unplaced for editorial review.
- Progress-page finding: the workflow total used the full public corpus count as “published” while source rows used configured eligible videos, producing impossible percentages. Added an explicit configured-published total and dynamic snapshot timestamp.
- Clarified the operator page’s primary outcome: show the published knowledge corpus first, counting videos with available approved concepts and evidence moments; keep configured workflow progress as a separate operational view.
- Progress-table clarity: renamed mixed-unit columns to identify whether they count videos, transcripts, candidates, evidence moments, concepts, proposed visual windows, or reviewer-verified visual demonstrations, and added a unit legend.
- Acquisition safety finding: an active transcript block was treated as video-specific, so cp could continue network attempts against other videos on the same route. The ingest circuit breaker now treats active blocked retry windows as route-wide and stops before any request unless an alternate route or explicit retry override is supplied.
- The route-wide gate is limited to `blocked: true`; ordinary unavailable, transient, and members-only failures remain per-video skips so unaffected videos can continue processing.
- Monitor usability: expose the active route-wide block deadline from the same retry manifest used by ingest, so operators can see when the current route is safe to retry.
- Documentation: added `docs/codex-cli-usage.md`, documenting the local Codex extraction, review, summary, budget, audit, failure, and publishing controls.
- Added `docs/codex-cli-python-integration.md`, documenting the general Python subprocess pattern used to call Codex CLI, including preflight, schemas, temporary files, timeouts, provenance, budgets, and failure handling.
- Recorded the operator-provided playlist `PLoTZwCwIlt2WXTvv3h-Xpk6rxoXttkE3C` as a disabled future source candidate.
- Process finding: automatic placement previously accepted any highest keyword score, including weak or near-tied matches. Added a strong-match and margin gate so ambiguous generated concepts stay unplaced for editorial review.

## Research reconciliation — 2026-07-19

- Added a local `/research/` comparison page covering glossaries, drill databases, coaching academies, structured training programs, and AI coaching tools.
- Key follow-up: consider adding drill metadata and progression links to reviewed concepts while keeping personalization and match-analysis features separate from the public corpus.

## Historical baseline — August 2026

- Safe public baseline after quarantine: 73 concepts, 51 published videos, and 1,119 non-demo evidence moments; 752 eligible videos have normalized transcripts.
- Count interpretation review (2026-08-30): the 533 canonical concept files remain present, but 460 are unreviewed quarantine history. The 2026-08-29 Codex cycle failed before publication on a response-schema validation error, so the safe public snapshot has not replenished since 2026-08-12. See `docs/project-review-2026-08-30-13.md`.
- Review queue: 6,934 items — 454 accepted, 6,470 awaiting Codex adjudication, 9 rejected, 1 pending, and 0 assigned to human review. The inventory has 43 complete videos, 709 with automated work remaining, and 86 excluded.
- Concept provenance: the 460 concepts created by `automatic_candidate_review` and their 4,775 heuristic evidence moments are preserved as unreviewed history but excluded from publication. A concept returns only after independent Codex acceptance; legacy evidence remains quarantined.
- Historical moment-support audit: 3,346 of 4,663 matched heuristic records silently lost one or more cited segments. The new path exposes dispersed citations and fails closed; all affected heuristic records are quarantined pending Codex re-adjudication.
- Timestamp-envelope audit: approved content has zero incomplete source envelopes. Safe legacy cases were repaired; three spans that would exceed 30 seconds remain quarantined for Codex re-adjudication.
- Caption-only boundary screen: 5.09% start mid-sentence, 5.43% end mid-sentence, 1.09% are under four seconds, and 9.88% need context review.
- Visual coverage: 0 `verified_visual_demo`; only 35 evidence records have a separate proposed `visual_source`, all classified as nearby inference.
- Current public quality structure: 0 isolated concepts and 16 single-source concepts. Taxonomy and collision remediation for the quarantined legacy concepts remains under P1-32.
- Python validation now enforces exact source envelopes for approved evidence; Codex semantic adjudication plus deterministic checks establish the publication path's support/topic decision. A versioned accuracy benchmark remains open under P1-34.
- Full evidence and recommendations: `docs/project-review-2026-08-12-11.md`.

## Recent study reconciliation - 2026-07-16

The latest studies were checked against the backlog rather than left as standalone reports:

| Study or review | Findings carried into the backlog | Current item(s) |
| --- | --- | --- |
| `docs/daily-pipeline-automation-review-2026-07-16.md` | ChatGPT app shortcuts are not a runtime dependency, but unattended runs need a lock, idempotent workset, run manifest, exit classes, scheduler environment, and explicit human gates. | P1-16 (in progress) |
| `docs/moment-boundary-analysis-study-2026-07-16.md` | Caption-derived moments can start/end mid-sentence or be too short; boundary flags, context separation, a gold set, and script-first/LLM-optional phases are required. | P1-14 |
| `docs/toc-automation-review.md` | TOCs should remain deterministic and build-time LLM-free; creator chapters and pause/keyword grouping are optional inputs, while anchors and timestamps need permanent validation. | P0-06, P2-06 |
| `docs/content-quotation-audit-2026-07-15.md` | Complete/high-ratio overlaps were cleared, but excerpt type, repeated-expression monitoring, and a regression validator remain needed. | P0-01 follow-up; new P1-17 |
| `docs/legal-review-youtube-2026-07-15.md` and `docs/youtube-knowledge-project-precedents-2026-07-15.md` | Public output must remain source-linked analysis; withdrawal, acquisition provenance, private-mode boundaries, and public-artifact checks remain prerequisites for expansion. | P0-02, P0-04, P0-05, P0-07, P1-08, P1-09 |
| `docs/project-review-2026-07-16-00.md` | The corpus is evidence-dense, visual verification is still zero, source diversity and empty leaves need attention, and generated status/encoding/URL checks should stay ahead of broad scraping. | P1-01, P1-03, P1-04, P1-05, P1-07, P1-10, P1-11, P1-12, P2-09 |
| `docs/project-review-2026-08-12-11.md` | Heuristic publication bypassed semantic adjudication; cited clusters were silently dropped; resolution states and source envelopes were inconsistent; taxonomy, summaries, ranking, transcript provenance, optional human advice, and backlog rendering need semantic-quality controls. | P0-08, P0-09, P0-10, P1-04, P1-32, P1-33, P1-34, P1-35 |
| `docs/project-review-2026-08-30-13.md` | The safe public contraction is an intentional quarantine, but recovery is stalled by a hard-stop Codex response-schema failure and the count layers need clearer operator separation. | P0-11, P1-34, P1-36, P1-04 |
| `docs/Session Logs/2026-08-30-17.md` | The registered 21:00 task reaches deferred recovery, but bypasses the documented wrapper lock and has no persistent temporal rotation for repeatedly deferred work. | P1-16 hardening, P1-37, P1-38 |
| `docs/Session Logs/2026-08-30-17.md` | Two recovery cycles failed on a transient Windows permission error during private LLM-budget ledger replacement; generated-file writes need bounded retry and collision-resistant temporary names. | P1-39 |
| `docs/Session Logs/2026-08-30-17.md`, `docs/Session Logs/2026-08-30-22.md` | The monitor received only the phase header while `process-pending` waited inside a captured Codex subprocess; after heartbeats were added, the latest run exposed a second fault: one timed-out adjudication still aborted the whole cached-triage stage. | P1-40, P1-41 |

The August baseline above is historical. The September specification-review snapshot supersedes it; generated corpus and quality reports remain authoritative for current counts.

## Priority definitions

- **P0 — protect trust:** complete before expanding public content or running a large scrape.
- **P1 — improve the core product:** complete during the next focused content/product cycle.
- **P2 — harden and scale:** complete after the corpus is trustworthy and usable.
- **Deferred:** deliberately not part of the current milestone.

## P0 — protect trust before more scraping

### P0-01 — Rephrase direct transcript excerpts

**Status:** Complete for the rephrasing pass and automatic guard (2026-07-15). The canonical excerpt wording was rewritten across the audited high-overlap set; the pipeline now offers `rephrase-excerpts` and `publish --auto-rephrase-high-overlap`. Source segment IDs, timestamps, evidence types, reasons, and provenance are preserved. The `excerpt_kind` field and validator remain a follow-up hardening item.

**Owner area:** Editorial/content  
**Source:** `docs/content-quotation-audit-2026-07-15.md`  
**Why:** 32 excerpts are complete normalized matches and 38 have high contiguous overlap. The editorial `reason` fields are original, but the public `excerpt` field often presents source wording without a quotation marker.

**Work:**

- Rephrase the 20 highest-priority entries first.
- Rephrase the remaining high-ratio set.
- Resolve duplicated wording across concepts such as `forehand-loop`, `forehand-loop-swing-path`, `body-hand-synchronization`, and `serve-action-decomposition`.
- Add `excerpt_kind: editorial_summary|source_quote`; default new evidence to `editorial_summary` (follow-up schema/validator work).

**Done when:** the audit reports no complete or high-ratio unmarked verbatim excerpts, every intentional quote is short, visibly marked, attributed, and tied to original analysis. **Evidence:** the post-pass screen reports 0 complete matches and 0 high-ratio matches; 28 lower-ratio partial overlaps remain for monitoring.

### P0-02 — Decide and document the transcript-acquisition basis

**Owner area:** Pipeline/legal  
**Source:** `docs/legal-review-youtube-2026-07-15.md`  
**Why:** automated transcript retrieval is a separate YouTube Terms/platform issue from copyright analysis of the final summaries.

**Work:**

- Document the permitted acquisition path for each source class.
- Prefer creator-provided, creator-authorized, or user-supplied transcripts where possible.
- Record acquisition method and date in provenance.
- Avoid aggressive scraping or block-evasion behavior.
- Do not make automated acquisition a prerequisite for public playback.

**Done when:** each published source has a documented rights/acquisition basis and the operator can explain which steps are local processing versus permitted source access.

### P0-03 — Add canonical-to-published freshness verification

**Owner area:** CI/publishing  
**Source:** `docs/project-review-2026-07-15-11.md`  
**Why:** CI currently validates the existing publish artifact but does not prove that it was freshly generated from canonical content.

**Work:**

- Add a deterministic canonical-input hash or temporary publish step.
- Fail CI if `data/publish/` and `app/public/data/` are stale or inconsistent.
- Provide a sanitized/metadata-only CI path where private transcripts are unavailable.

**Done when:** a canonical YAML change cannot pass CI while an older public corpus remains deployed.

### P0-04 — Add source quarantine and removal controls

**Owner area:** Publishing/operations  
**Source:** legal review and public-to-private transition plan  
**Why:** creators can disable embedding, remove videos, or request removal; the project needs a controlled response.

**Work:**

- Add `published`, `withdrawn`, `quarantined`, `removed`, and `embedding_disabled` source states.
- Add a private removal-request record.
- Exclude quarantined IDs from public corpus, pages, embeds, thumbnails, excerpts, and search indexes.
- Add a single operator command for quarantine + rebuild.

**Done when:** one source can be removed from the public build without editing dozens of concept pages manually, and CI fails if a quarantined ID leaks into `app/public/data/`.

### P0-05 — Add a public source/permissions/removal page

**Owner area:** Site/legal  
**Why:** the site should identify itself as independent, explain its source-linked analysis model, and give creators a clear contact path.

**Work:**

- Add attribution and independence language.
- Explain short excerpts, links, standard embeds, transcript-inferred evidence, and visual verification.
- Provide a removal-request email/form and response expectations.
- Add a privacy notice and YouTube/Google policy links where applicable.

**Done when:** a creator can understand the site’s purpose and request a specific removal without searching the repository.

### P0-06 — Add permanent TOC/anchor validation

**Owner area:** Site/QA  
**Source:** TOC automation review and project review  
**Why:** detail-page timestamp links were checked manually; route/anchor correctness is not yet a permanent CI contract.

**Work:** add `validate-toc` coverage for route existence, unique anchors, chronological order, valid timestamp ranges, and concept/video link targets.

**Done when:** every generated TOC link is validated automatically in CI.

### P0-07 — Enforce the precedent-informed public/private boundary

**Owner area:** Publishing/legal/operations
**Source:** `docs/youtube-knowledge-project-precedents-2026-07-15.md`
**Why:** reported cases distinguish transformative search and commentary from public redistribution of complete source material. YouTube Terms and API policies add independent restrictions on scraping, downloading, storage, attribution, and player behavior.

**Work:**

- Keep public output to project-authored analysis, short rephrased/contextualized evidence, source links, and standard YouTube embeds.
- Add a public-artifact assertion that rejects raw transcripts, downloaded/transcoded media, and source IDs in `withdrawn`/`quarantined` states.
- Make `publication_mode=private` localhost-only and refuse GitHub Pages deployment; keep private transcripts/media in a separate access-controlled store.
- Add an operator checklist for creator permission, embed eligibility, removal requests, and acquisition provenance before expanding the corpus.
- Require explicit permission or a license for any public full transcript, downloaded clip, transcoded video, or offline sharing feature.

**Done when:** the public build cannot publish a full transcript or source media by accident, private mode cannot deploy to Pages, and each published source has a recorded acquisition/status basis.

The 2026-08-12 audit also found 27 tracked files under `data/manifests/`, including historical budget ledgers and summary-audit metadata. Review their retention need and move private runtime/audit state out of Git; keep only deliberately sanitized, documented fixtures or public-safe snapshots.

### P0-08 — Replace heuristic promotion with a Codex semantic gate

**Status:** Implemented (2026-08-12); legacy Codex re-adjudication continues under P1-34.

**Owner area:** Editorial/pipeline
**Source:** `docs/project-review-2026-08-12-11.md`

**Why:** 460 of 533 published concepts were created by `automatic_candidate_review`. The former high-confidence/fuzzy-match route wrote approved canonical concepts and evidence without a semantic decision grounded in the exact retained transcript span.

**Work:** use schema-constrained Codex CLI as the default accept-existing/create-new/reject/defer decision; enforce exact supplied segment IDs, a single supported span, controlled taxonomy values, complete timestamps, and durable model provenance in deterministic code; quarantine the legacy heuristic corpus; keep human input as optional advice or an explicit override.

**Dependencies:** the review queue, configured Codex model/budget, canonical provenance fields, normalized transcripts, and processor write locks.

**Done when:** heuristic confidence cannot publish canonical knowledge; every new publication has a durable Codex semantic decision plus deterministic support validation; all 460 legacy concepts are quarantined or independently re-adjudicated; and optional human decisions remain advisory/override metadata rather than the default queue. The mechanism and quarantine are complete: 4,775 legacy evidence moments and all 460 heuristic concepts were marked unreviewed, while approved editorial content remained publishable.

### P0-09 — Preserve focused claim support and every cited cluster

**Status:** Implemented for new work and legacy output quarantined (2026-08-12); corpus drain continues under P1-34.

**Owner area:** Extraction/review/validation
**Source:** `docs/project-review-2026-08-12-11.md`

**Why:** the extractor sends whole transcripts despite the configured 80-segment job limit, while promotion selects only the largest contiguous cited group and retains the original multi-cluster rationale. In a matched audit, 3,346 of 4,663 automatically accepted records lost cited segments; some resulting moments no longer support their published topic.

**Work:** implement overlapping bounded extraction jobs; require one focused proposition per contiguous support span; split or defer dispersed citations instead of discarding them; retain a machine-checkable candidate-to-canonical segment map; remediate affected accepted records in priority order.

**Dependencies:** P0-08, normalized transcript segments, configured extraction chunk limits, shared boundary logic, and the private candidate/queue history.

**Done when:** promotion reports zero silent segment loss, every published reason and excerpt is scoped to its retained contiguous span, dispersed candidates are deferred without discarding any cited cluster, and a stratified accuracy set passes claim-support and topic-mapping targets. Extraction now runs configured 80-segment jobs with eight-segment overlap, boundary assessment exposes dropped clusters, and Codex adjudication selects one exact supplied span; all affected heuristic output was quarantined.

### P0-10 — Make source timestamps enclose every cited segment

**Status:** Implemented (2026-08-12); three overlong legacy cases remain quarantined for Codex re-adjudication.

**Owner area:** Validation/content
**Source:** `docs/project-review-2026-08-12-11.md`

**Why:** 36 canonical source windows end before the end of their last cited transcript segment; 12 truncate more than 1.2 seconds and the worst truncation is 9.5 seconds. Existing validation proves that IDs and ranges exist, but not that playback encloses the cited speech.

**Work:** require `source.start_ms <= min(segment.start_ms)` and `source.end_ms >= max(segment.end_ms)`; keep optional listening context in a separate field; fix the 36 current records; add direct timestamp playback checks to review.

**Dependencies:** P0-09, normalized segment durations, canonical source models, and transcript-backed validation.

**Done when:** validation rejects every incomplete source envelope, the approved mismatch count is zero, and the accuracy set confirms that timestamp links play the full cited claim without conflating context or visual windows. Validation now checks the effective end of every cited caption; the repair command fixed safe legacy envelopes and quarantined three spans that would exceed the 30-second contract.

### P0-11 — Make Codex adjudication failures recoverable and observable

**Status:** Implemented in code (2026-08-30); live controlled retry pending.

**Owner area:** Codex integration/operations
**Source:** `docs/project-review-2026-08-30-13.md`

**Why:** the 2026-08-29 controlled cycle stopped before publication when a schema-validating response for `create_new` also supplied a non-null canonical concept ID. A single malformed response aborted the retry batch, leaving 6,470 deferred decisions untouched and making the post-quarantine count remain at 73 concepts / 51 videos / 1,119 moments.

**Work:** align the prompt, JSON schema, and Pydantic invariants for every adjudication decision; record the offending item as a bounded failure/defer with provenance; continue only when the batch contract permits it; expose the last successful publish timestamp and the failed cycle separately.

**Dependencies:** Codex response schema, `process-pending`, retry manifests, per-KB lock, and P1-34's bounded queue drain.

**Done when:** one invalid model response cannot abort an otherwise safe bounded batch without an explicit stage-level reason, the queue item remains retryable, failure manifests identify the exact item and schema rule, and no publish is emitted from a failed or partial adjudication stage. The schema-validation path now records a private failure artifact, defers the item with provenance, and continues the bounded batch; a live controlled retry remains to be observed.

## P1 — improve the core product

### P1-01 — Review the visual evidence queue

**Why:** there are 0 verified visual demonstrations. Transcript-inferred windows cannot support the strongest loopable-demo promise.

**Work:** review candidate windows, record exact start/end bounds and visual notes, and promote only confirmed footage to `verified_visual_demo` with manual selection metadata. Prioritize forehand-loop concepts first.

**Done when:** the UI distinguishes transcript evidence, proposed visual windows, and verified visual demonstrations; only the last category loops automatically.

### P1-02 — Process pending candidates before another large scrape

**Status:** Superseded as a public-expansion gate by P0-08 through P0-10 (updated 2026-08-12). The heuristic queue reached 5,117 accepted and 1,807 human-review items but created 460 unsafe concepts and silently discarded cited clusters. Those promotions are now quarantined; the live queue has 6,470 Codex decisions remaining.

**Why:** the queue had 174 pending items. Nine published videos had only one concept in their TOC; eight of those had additional local candidates that could be checked against existing concepts.

**Work:** review the pending candidates for the one-concept videos first, then clear the remaining queue in source batches. For `9OxcCPWI-k8`, five additional candidates are pending beyond `Backhand serve`.

**Done when:** every pending item has a final Codex accept/reject decision or a visible automated defer with reason, one-concept videos have been checked against their candidate set, and the P0 semantic-support/timestamp gates prevent unsupported public knowledge.

### P1-03 — Localize moments and collapse repetition

**Wrist alias collision (2026-10-16 23:19 EEST):** A new private draft proposed `stable wrist`, already used by `concept-backhand-racket-face-angle-adjustment` and `concept-shoulder-elbow-and-wrist-stability`. Removed that optional alias from the unverified wrist proposal; no collision was published. Review the legacy shared alias in those two distinct topics during their full audits, narrowing overly broad aliases rather than automatically merging different concepts. Source: private `media/audit-wrist-unverified-proposal-2026-10-16-23.json`. Dependency: P1-51 source/semantic review. Acceptance: no new canonical term collision; legacy ambiguity resolved with source-grounded specific names or documented distinct-topic cross-references, preserving valid reviewed content.

**Why:** evidence is concentrated and repetitive: 426 exact repeated-excerpt groups cover 982 moments, and some concepts have over 100 moments. `forehand-loop-swing-path` is the largest outlier at 132 moments.

**Work:**

- Create a moment-specific summary from the cited segment rather than repeating a candidate definition.
- Add reviewed subtopics such as setup, timing, contact, acceleration, recovery, mistake, correction, and drill.
- Show representative moments first and collapse corroborating moments.
- Flag near-duplicate excerpts during extraction/review.

**Done when:** high-volume concepts remain readable and each visible moment explains what is unique about its timestamp.

### P1-04 — Generate progress and quality data instead of hand-maintaining it

**Why:** progress and quality pages previously contained hand-maintained historical counts that could drift from processor artifacts.

**Work:** emit a versioned `progress.json` from processor artifacts during `publish`; render the local Astro progress page from that data; include generation timestamp and explicit metric names. Source discovery, configuration, extraction, review, publication, evidence, visual, backlog, and members-only counts are now generated without LLM calls. Extend quality generation with automatic-versus-editorial provenance, silent segment-loss, resolution consistency, exact source-envelope, taxonomy vocabulary, alias collision, summary provenance, review-backlog, graph, and transcript-origin metrics. Remove hard-coded corpus totals from the local Pipeline page.

**Status:** Phase 1 complete (2026-07-16); semantic quality coverage remains open (updated 2026-08-12). `processors.progress` writes `app/src/data/generated/<kb>-progress.json` on every publish, and the local progress page consumes it. The local Pipeline page and dated planning baseline have drifted from the 533-concept/5,892-moment corpus, and the current quality report does not surface the P0-08 through P0-10 risks.

**Done when:** README, progress, pipeline, source-progress, and quality reports cannot silently drift from the corpus manifest.

### P1-05 — Prioritize second-source coverage

**Why:** 2 concepts have only one supporting source, and the published channel mix is uneven.

**Work:** make source diversity a review metric and prioritize another channel/video for single-source concepts before adding more moments to already concentrated concepts.

**Done when:** the backlog reports distinct video and channel counts, and each single-source concept has a documented coverage decision or a second independent source.

### P1-06 — Add concept-specific evidence hierarchy

**Why:** generic evidence-type chapters do not adequately structure complex topics such as backhand serve mechanics or forehand-loop motion.

**Work:** add reviewed `subtopic_id`/section metadata and render nested sections such as preparation, contact, racket path, spin variation, deception, error, and drill.

**Done when:** a concept page’s hierarchy is driven by meaning, with generic evidence types retained as secondary labels.

### P1-07 — Resolve taxonomy placeholders

**Why:** seven leaf nodes currently have no concept content: forehand push, backhand push, backhand counter, forehand block, backhand block, forehand flick, and Error correction.

**Work:** mark them as planned, populate them, or remove them until content exists.

**Done when:** no empty leaf looks like a missing article in the public navigation.

### P1-08 — Add local/private mode controls

**Why:** the project should stay online by default but be able to transition a KB or source set to personal use.

**Work:** add `publication_mode: public|private`, source-level public status, localhost-only private startup, public-build refusal for private mode, and separate private storage.

**Done when:** switching modes does not expose private transcripts/media and does not change stable concept IDs or provenance.

### P1-09 — Add project-owned offline export

**Why:** a personal continuity copy should preserve the project’s own work even if public sources are withdrawn.

**Work:** export code, taxonomy, navigation, concept definitions, relationships, review decisions, source IDs/URLs, permissions, hashes, and status. Encrypt the local backup and keep it outside the public artifact.

**Done when:** the export is reproducible, local-only, access-controlled, and clearly excludes unlicensed source redistribution by default.

### P1-10 - Verify the project-qualified GitHub Pages URL

**Why:** the deployment workflow sets `SITE_URL` to the owner root (`https://<owner>.github.io`) while the Astro base path is repository-qualified for project Pages. Canonical or metadata URLs can therefore omit `/TTKnowledgeBase/`, recreating the earlier 404/confusing-link failure mode.

**Work:** derive `SITE_URL` from `github.repository` (or configure it explicitly), add a production-like build test with `GITHUB_REPOSITORY=cunya/TTKnowledgeBase`, and verify the root, KB, video, and concept routes under the project path.

**Done when:** generated site metadata and all internal links resolve under `https://<owner>.github.io/<repository>/` in a production-like build, while local development remains rooted at `/`.

### P1-11 - Remove UTF-8 mojibake from published UI and workflow labels

**Why:** user-visible strings still contain corrupted sequences such as `Â·`, `â€”`, and `â€œ` in the shared layout, progress page, inventory data, and GitHub Actions run names. This reduces trust and makes timestamps, separators, and titles harder to read.

**Work:** normalize affected tracked files as UTF-8, add a deterministic scan for replacement/mojibake sequences to CI, and verify rendered titles, labels, and source names in the production build.

**Done when:** the scan is clean, the rendered site contains no known mojibake sequences, and source titles preserve intentional punctuation and emoji.

### P1-12 - Keep atlas parents semantically aligned

**Why:** recurring navigation edits had placed stroke-specific concepts under unrelated parents such as Serve, Drive, and Fundamentals, making the relationship atlas misleading.

**Work:** review navigation assignments against each concept's label, definition, evidence summary, and facets after processing and before publication; keep shared principles in Fundamentals and stroke-specific concepts under the matching shot family.

**Status:** Ongoing audit (2026-07-19): moved wrist stability to Fundamentals, flick mechanics to Flick, forehand framework out of Serve, and removed the equipment-only Brush direction for gluing from Forehand loop contact while retaining it under Equipment → Glue application. Added intermediate Serve, Serve receive, and Fundamentals groups to prevent overloaded parent lists. Continue auditing as new concepts are approved.

**Done when:** every published concept has a defensible primary atlas parent, duplicate cross-listings are intentional, automatic placement reads the evidence summary, and navigation validation is part of the publish gate.

### P1-12 - Separate source-title attribution from display styling

**Why:** ten published source video titles contain promotional all-caps fragments, including `SUCKS`, `STOP`, `SMASH`, `FAST`, and one fully uppercase title. These are original YouTube metadata, not missed transcript rephrasing, but they dominate the visual hierarchy and can make the site feel like it is repeating promotional copy.

**Work:** retain the exact source title in provenance and source inventories, add an optional normalized `display_title` for site headings and TOCs, and show the original title on the source detail/attribution view. Do not rewrite source metadata in canonical records without an explicit provenance field.

**Done when:** source links and attribution preserve the exact original title, while concept/video indexes and TOCs use a readable display form for titles with promotional capitalization; titles without a meaningful change remain unchanged.

### P1-13 - Remove transcript framing from moment titles (complete 2026-07-16)

**Why:** evidence excerpts can begin with extraction scaffolding such as “The transcript explicitly defines ...”, which makes a visible moment title describe the pipeline instead of the table-tennis idea.

**Work:** normalize transcript and speaker reporting leads at the shared display layer, and collapse sentence-like definition/specification scaffolding into concise technique titles. Preserve the canonical excerpt, reason, source URL, and timestamp unchanged for provenance and review.

**Done when:** visible TOC and evidence titles read as standalone editorial statements, including definition phrasing such as “Acceleration: a slow-soft backswing followed by a fast release,” concise titles such as “Short takeback-to-contact distance” and “Peak-of-bounce timing,” and no transcript-reporting lead.

**Status:** Complete. Implemented in `app/src/lib/videoToc.ts`; Astro diagnostics and the 201-page static build passed on 2026-07-16.

### P1-14 - Align moment windows to sentence and meaningful-duration boundaries

**Status:** In progress — Phase 1 caption-only baseline and Phase 2 review-worksheet tooling were implemented (2026-07-16). The first 24-item review pass recorded 9 safe caption-context merges, 4 meaningful short-window keeps, and 11 conservative deferrals; the deferred cases still need source/audio inspection and measured reduction remains open. The `report-boundaries` command measured 1,826/1,826 local-caption-backed moments: 16.4% start mid-sentence, 17.5% end mid-sentence, 3.5% are under four seconds, and 31.9% require context review. `process-pending` defers newly flagged candidates with the boundary flags instead of silently accepting them. `prepare-boundary-review` exported the deterministic sample from the 582 flagged moments, and `validate-boundary-review` checks the recorded decisions without applying them. A 1.2-second UI-only spoken-playback tail now cushions caption timing without changing transcript citations; the remaining work is audio/visual inspection of deferred windows. Baseline: `docs/moment-boundary-report-table-tennis-2026-07-16.md`.

**Why:** the current span resolver uses the first and last cited caption segments. Caption cues can begin or end mid-sentence, and a technically valid three-second fragment may not contain enough instructional meaning to stand alone.

**Work:** implement caption-only sentence-like unit merging and boundary snapping first; add `starts_mid_sentence`, `ends_mid_sentence`, `too_short`, and `needs_context` flags; keep claim-support citations separate from optional playback context; add review actions and a gold-set evaluation before enabling authorized local word/prosody alignment or semantic change-point proposals. The first worksheet pass is recorded; the remaining operator step is to inspect the 11 deferred cases, apply only further reviewed canonical changes, and publish a second report showing reduction.

**Done when:** mid-sentence and non-meaningful short-window rates are measured and reduced, every expanded/split window preserves segment-level provenance and the 30-second limit, and low-confidence cases are deferred rather than silently published. See `docs/moment-boundary-analysis-study-2026-07-16.md`. **Next study:** use private ASR word timing and confidence only as an audio-boundary signal, as specified in `docs/asr-audio-boundary-verification-2026-07-21.md`; do not replace caption segment provenance.

**2026-10-14 follow-up:** After targeted source repairs, the approved-only non-demo caption screen evaluated 1,871 citations and flagged 193 starts/205 ends mid-sentence, 61 short windows, and 381 needing context (20.36%). These are overlapping heuristic review signals, not established claim errors. Review the remaining windows without inventing timestamps or treating adjacent uncited text as claim support; use the existing worksheet/semantic benchmark. Source: [expanded affected-content audit](affected-content-spot-check-2026-10-14.md), 00:39 EEST snapshot. This broader boundary review remains open.

**2026-10-14 timing conflict:** Batch two quarantined the final foot/hand coordination fragment in m93pWt9MIZE: completing its captions would require an endpoint beyond the cached video duration. Reconcile source duration and caption timing before restoration; do not guess a truncated envelope. Acceptance: an authoritative duration/timing check permits a complete, enclosed citation, or the fragment remains excluded. Evidence: [second remediation report](published-content-remediation-batch-2-2026-10-14.md), editorial archive, and private normalized cache.

**Automation study finding:** The whole current corpus contains nine further selected-caption tails 33–1,560 ms beyond cached video duration, masked by clamping in assessment, envelope repair and validation. Flag raw-envelope disagreements consistently and reconcile precision/timing before deciding repair or quarantine; small overshoots do not prove incorrect spoken content. Source: [automated repair study](automated-published-repair-study-2026-10-14.md), P1-51. Acceptance: both evidence and relation validators expose unreconciled selected-tail conflicts; no guessed trim, fabricated duration or blanket error verdict.

**Implementation:** Shared raw-duration guard now covers assessment, envelope repair and validation. All nine measured conflicting citations were reversibly excluded through eight reviewed mechanical plans, retaining source/visual metadata and archived originals. Authoritative timing reconciliation remains open; these actions add no semantic audit credit.

**18-hour full-audit finding:** Active-block final grip citation in etKOmktKw1k was also quarantined: selected final caption ends at 492080 ms against cached duration 492000 ms; its existing source was clamped to 492000. Apply the same authoritative timing reconciliation acceptance before restoration. Original source/record is retained in the full-audit repair archive; see [continuation evidence](full-published-audit-workflow-2026-10-14.md#continuation-at-1800). Status: unresolved timing reconciliation; dependency of P1-50, excluded from publication.

### P1-15 — Add an adjustable daily LLM budget and task deferral (complete 2026-07-16)

**Why:** extraction, rephrasing, and benchmarking all invoke Codex, but there was no shared daily guard or visible per-task allowance. A long local run could consume the operator's available usage before later, higher-priority work.

**Work:** reserve a conservative prompt-plus-output estimate before each Codex call; reconcile it with reported usage; enforce daily and task caps; record a private per-KB ledger; defer extraction/rephrase/benchmark work when a cap is reached; expose `llm-budget --kb <id>` and keep limits adjustable in `config/processors.yaml`.

**Done when:** no call starts beyond the configured daily or task allowance, deferred work is recorded without creating partial candidates, successful usage is visible by task and date, and disabling or changing the guard requires an explicit config edit. **Status:** Complete; covered by `tests/test_llm_budget.py`, processor tests, Ruff, CLI integration, and the local-only `/progress/` budget section.

### P1-16 — Add an unattended daily-run orchestrator (new 2026-07-16)

**Why:** the individual Python and Codex CLI stages are scriptable, but there is no timer-safe command that replaces the ChatGPT app's `cp` coordination. Running `extract-concepts` without a video ID can reprocess every normalized transcript, and a scheduled job has no single lock, workset, run manifest, or exit-class contract.

**Work:** add a dry-run-first `daily-run` command and per-KB automation policy; acquire a single-run lock; drain cached work before network acquisition; select only eligible, selected, not-yet-complete videos; honor retry cooldowns, the block circuit breaker, the backlog gate, and the daily LLM budget; extract only missing/stale candidates; build the review queue; keep auto-triage, visual approval, auto-rephrase, commit, push, and deployment explicitly opt-in or disabled; write a private run manifest and machine-readable exit classes; provide a Windows Task Scheduler wrapper without registering it automatically. The 2026-09-10 whole-process review also requires the continuation discovery flag to invoke configured-source discovery only after extraction, adjudication, and acquisition worksets are empty, a timeout budget that covers a ten-candidate adjudication pass, crash-recoverable wrapper locking, bounded monitor request bodies, and clean invalid-URL CLI errors.

**Dependencies:** P1-02 cached candidate triage, P1-15 daily LLM budget, P0-04 source quarantine/removal controls, and a confirmed local Codex CLI authentication/runtime environment.

**Done when:** a scheduled invocation runs without ChatGPT app assistance, two invocations cannot overlap, reruns are idempotent unless explicitly forced, blocks/budget/auth/validation failures defer or stop safely with a private manifest, and no unreviewed knowledge or private processing data is published. See `docs/daily-pipeline-automation-review-2026-07-16.md`. **Status:** Phase 1 complete (2026-07-19); 2026-09-10 hardening is in progress: shared `scripts/run-cp.py` orchestrator, selected-batch acquisition, live configured-source continuation discovery, private `cp.latest.json` manifest, Windows 21:00 task action, and local start/stop monitor are implemented. Remaining hardening: explicit dry-run/exit-class reporting and broader unattended environment checks.

### P1-17 - Add excerpt classification and overlap regression protection (new 2026-07-16)

**Why:** the quotation audit cleared complete and high-ratio matches, but the public schema still does not distinguish an editorial summary from an intentional source quotation. Lower-ratio repeated phrases and duplicate expressions can recur as new extraction batches arrive, making the public corpus look more like transcript reproduction and weakening independent analysis.

**Work:** add `excerpt_kind: editorial_summary|source_quote` with `editorial_summary` as the default; require visible attribution and short length for `source_quote`; run a deterministic overlap screen against cited transcript segments and across concepts; report new high-overlap, repeated-expression, and unresolved duplicate groups; block or defer publication when a new complete/high-ratio match lacks an explicit reviewed exception.

**Dependencies:** P0-01 rephrasing policy, P0-02 acquisition provenance, and the existing candidate/review queue schema.

**Done when:** every published excerpt has an explicit kind, intentional quotes render with attribution, a new extraction batch cannot reintroduce complete/high-ratio unmarked transcript matches, and repeated wording across related concepts is visible in the review report. **Status:** Planned; the post-pass audit is clean for complete/high-ratio matches but 28 shorter partial overlaps remain for monitoring. See `docs/content-quotation-audit-2026-07-15.md`.

### P1-32 — Reconcile concept identity, taxonomy, navigation, and graph quality

**Status:** Open (2026-08-12); navigation mismatch remediated (2026-09-10 and 2026-09-15), with editorial taxonomy work remaining.

**Owner area:** Editorial/taxonomy
**Source:** `docs/project-review-2026-08-12-11.md`

**Why:** the corpus now has 42 free-form concept types, 41 concepts with facets outside the configured vocabulary, 43 exact normalized label/alias collision groups, 460 automatic concepts with no relations, one automatically created concept omitted from navigation, six approved Codex-semantic concepts omitted from navigation during the 2026-09-10 bounded run, one newly accepted Codex concept omitted during the 2026-09-15 run because placement ran before its generated evidence summary existed, and two more approved concepts omitted during the 2026-09-15 18:30 run. The 2026-09-15 fix makes the shared placement signal include aliases, facets, evidence excerpts, and evidence reasons; the two latest concepts were manually placed and the next live cycle published successfully. The 2026-09-16 run also exposed an accepted review item whose original proposal citations did not include the exact Codex-adjudicated span; the queue now persists that span so validation can trace the accepted decision. Ambiguous generated concepts now go to a visible editorial holding node instead of remaining approved and unplaced. 153 single-evidence concepts and 156 single-source concepts remain. These patterns indicate a micro-concept collection rather than a consistently edited wiki graph.

**Work:** audit the 460 automatically created concepts against durable article boundaries; merge duplicates and overlapping aliases; enforce controlled types/facets; require an explicit navigation decision; review relationships and source diversity; keep semantic placement fail-closed, route ambiguous generated concepts to the configured editorial holding node, persist exact Codex-adjudicated segment IDs alongside accepted queue proposals, and remove the automatic-navigation exemption after the existing backlog is classified.

**Dependencies:** P0-08, P0-09, configured taxonomy vocabulary, navigation validation, and the published-content remediation queue in P1-34.

**Done when:** schema validation enforces the configured vocabulary, normalized aliases resolve unambiguously or have documented exceptions, every approved concept has a reviewed navigation status, and graph/singleton/source-diversity reports have explicit editorial dispositions.

### P1-33 — Replace fallback summaries and rank evidence by reviewed support

**Status:** Open (2026-08-12).

**Owner area:** Editorial/site

**2026-10-14 producer finding:** The deterministic generator still emits the boilerplate removed in manual repairs; 70 current article summaries contain that template. Remove the wrapper and unsupported additional-points sentence at the shared producer, version its format, and draft refreshes only for marked deterministic summaries. Preserve manual/Codex prose and review supporting reasons before semantic clearance. The full scan also found 662 reasons matching the existing scaffolding filter; treat them as review signals. Source: [automated repair study](automated-published-repair-study-2026-10-14.md), dependency of P1-51.

**Implementation:** Direct-synthesis-v11 removes the filler at the producer. Seventy exact template-deletion plans were reviewed and applied, retaining the remaining prose and original generator/hash provenance. Manual/Codex summaries are excluded from this mechanical rewrite. Reason-level support and broader quality evaluation remain open.
**Source:** `docs/project-review-2026-08-12-11.md`

**Why:** 460 public summaries were produced by a deterministic concatenation fallback rather than editorial synthesis. The evidence rank is 70% model confidence, even though confidence has admitted unsupported or misclassified moments, and there are no verified visuals to distinguish the best examples.

**Work:** regenerate summaries only from reviewed, semantically supported evidence; require readable article structure and source diversity; rank representative moments by human support status, boundary completeness, topic specificity, source diversity, and redundancy before using model confidence as a tiebreaker.

**Dependencies:** P0-09, P0-10, P1-32, evidence-summary provenance, and a judged representative-moment sample.

**Done when:** no approved article relies on an unreviewed concatenation summary, summary provenance identifies the reviewed evidence set, and a judged sample shows that the first displayed moments are both topically correct and complete at their timestamps.

### P1-34 — Drain Codex re-adjudication and build an accuracy benchmark

**Role-pair correction evidence (2026-10-16 23:04 EEST):** Complete primary feedback before targeted Luna/high drafting separated the borrowed-power observation and late/prepared instruction. The flick repair removed borrowed backhand/banana identity, forehand-loop timing transfer and unowned space/control benefits. A rejected causal peak-jamming phrase was replaced by the actual example and freshly verified. Both articles are applied after final primary review. Retain the original false-acceptance cases as frozen controls: this is supervised correction evidence, not proof the verifier is safe without primary review. Evidence: private `media/audit-role-pair-*` and P1-51.

**Owned-source role control (2026-10-16 22:30 EEST):** Actual 15El26 asks why players struggle against underspin;27–28 describe a reliance on borrowed power and lack of active force. The source-only Luna/high verifier framed this as advice to avoid active force. Keep the observation-versus-recommendation negative control: the criticized tendency must not become an endorsed instruction, and separate late/prepared conditions from another source cannot supply its role. No borrowed-force proposal was approved. Source: private `media/audit-owned-source-primary-findings-2026-10-16-22.json` and exact dossiers. Acceptance: preserve rhetorical/observational role after wording/source edits; full independent support alone is insufficient while this real false acceptance remains. Dependency: P1-51 source correction and fresh primary review.

**2026-10-16 21:52 accuracy control:** A targeted repair falsely quarantined a backhand-error citation because its legacy evidence ID contains `forehand-loop`, despite the current concept and selected final question explicitly identifying backhand. Source: private `media/audit-next8-2026-10-16-21*`, first article. Preserve as a negative quarantine control alongside source-support controls: evidence IDs are stable opaque references, not authoritative topic labels. Acceptance: current concept plus actual selected wording govern relevance; retain the valid citation with a reader-facing reason, and narrow unsupported topspin/commonness claims only after fresh full verification. This is not permission to disregard real topic mismatches or approve unsupported labels.

**Status:** In progress (2026-10-14); safe gate is live. Two published-content remediation batches applied 62 evidence actions; the second revised seven concepts and quarantined 31 topic mismatches plus one caption/duration conflict. Six unflagged controls were supported. Further source-balanced review, legacy queue drain, and the accuracy benchmark remain. Positive source-selection control: banana-flick 6vwxmC36InY:00002-06 has a valid contiguous it referent and explicit spin variants, but draft support omitted 00006. Benchmark must retain supported anaphora and distinguish missing chosen support from absent source evidence; details in the 20:00 session and repair study. Rally-rhythm full review confirms the same missing chosen-support continuation issue for real fast/slow and backswing claims; retain these as positive controls alongside remaining identity/topic failures, rather than treating all machine exceptions as false source claims. Rip review positive controls: repeated explicit topic can ground a conversational friction-key reference; generic lift/lower wording need not identify anatomy if proposed text also stays generic. Broader related examples need limited source-grounded relevance, not identical heading words. New polarity/actor controls: 15Elc borrowed-force backspin critique was converted to affirmative advice; body-rotation reason swaps incoming center ball with outgoing direction. Freeze actual source windows and distinguish valid late-ball borrowing instruction from rejected broad underspin recommendation.

**Owner area:** Editorial/review tooling/QA
**Source:** `docs/project-review-2026-08-12-11.md`

**Why:** the legacy heuristic corpus is now safely excluded, but 6,470 candidates still await bounded Codex adjudication after one live schema-constrained acceptance. The optional human-advisory page does not provide a corpus accuracy benchmark or full remediation controls. Legacy transcript metadata misclassified 163 generated tracks as manual; the shared reader now normalizes missing origin from the stored youtube-transcript-api Boolean, preserving explicit origins and raw cache data (2026-10-14). Many caption tracks still contain fragmentary segments.

**Work:** drain the deferred queue through bounded, source-balanced Codex CLI passes under the configured budget; prioritize the former segment-loss, contradictory-resolution, timestamp, low-similarity, and generated-caption risks; build a versioned accuracy benchmark stratified by source, caption origin, concept type, provenance, and risk; record optional human advice/overrides separately; migrate legacy transcript-origin metadata.

**Dependencies:** P0-08 through P0-10, configured Codex budget, normalized transcript provenance, canonical locking, and source-balanced selection.

**Done when:** every eligible legacy candidate reaches a final Codex accept/reject decision or a visible automated defer with reason; a versioned benchmark measures claim support, topic mapping, boundary completeness, caption reliability, and playback accuracy; model/version results and optional human disagreements are recorded; and release thresholds are documented. Human participation is useful augmentation, not a completion dependency.

**2026-10-14 remediation batch:** Reviewed eight shortest citations from the prior truncated boundary sample plus three unflagged control citations. Found repeated broad descriptions attached to split caption fragments. Applied twelve evidence actions across five concepts (eight amendments, three consolidations, one label-only demonstration quarantine) and revised four summaries; original records retained in the editorial archive. The three controls were supported. Source: [first bounded published-content remediation](published-content-remediation-batch-2026-10-14.md). This risk-selected batch is not a prevalence estimate; further source-balanced semantic/boundary review remains open.

**2026-10-14 second batch:** [Second bounded remediation](published-content-remediation-batch-2-2026-10-14.md) found ball/racket/spatial-object confusion in a whole article: reviewed 41 approved citations, quarantined 31 misplaced records, and retained eight supported topic citations after two consolidations. Across seven files, fifty evidence actions repaired fragment-level support and topic mapping; seven summaries revised. Prompt 1.1.2 now distinguishes the object described. Dependencies remain exact-caption support, per-KB locking, and idle release verification. Further benchmark/remapping work is open: only restore quarantined rows after independently reviewed topic mapping and complete source support.

**2026-10-15 frozen-evaluation findings — open:** Two model passes accepted a hand-position referent absent from the selected incomplete clause (`4WWIQdr3R8g:00030`); primary review removed that inference before application. Include the rejected actual proposal and the supported complete-clause control in the versioned benchmark. Also retain real false-positive cases where the verifier treated inherited confidence/approval as transcript claims. Repair contract 1.0.8 removes those two processing fields at the shared verifier-input boundary; retained/quarantined transport tests and a real blocked-case replay passed. This fixes the input leak, not model accuracy in general. Acceptance: the frozen benchmark must distinguish unsupported referents/conditions from supported controls and must not use prior confidence/approval as evidence. 2026-10-15 12:34 control replay: configured GPT-6 Luna low with compact contract 1.1.0 again accepted the known unsupported hand referent; the complete-clause control also passed (two calls / 38,570 processor tokens). The model switch and compaction did not resolve this accuracy defect. At 12:44, high effort on unchanged policy 1.1.0 also falsely accepted it (two controls / 38,637 tokens). General referent-grounding verifier policy 1.1.1 at high then rejected the unsupported proposal and accepted the complete-clause control (two controls / 38,547 tokens). This is one frozen pair, not corpus-wide accuracy; broader benchmark and explicit primary source review remain required. 2026-10-15 15:21 full-campaign primary finding: the model-supported backhand-push-follow-through plan extends a long-push wrist-flick claim to short balls because a separate line says the fundamental push works short/long. Add this actual condition-leakage proposal plus a long-only control to frozen evaluation; preserve speaker/condition scope. Full-campaign primary review also flagged the model-supported banana-flick arm-shape comparison from this angle: without defined geometry, retain only complete elbow/wrist instructions or require footage/context review. Include this deictic-condition case in the frozen evaluation. Positive control from 19:10 primary review: forehand-contact-spacing uses a generic outside-body citation as written alongside a separate explicit forehand-drive source. Retain it to prevent false rejection of relevant examples that do not independently prove the entire heading; distinguish that from adding unowned stroke qualifiers to a citation. 19:33 primary spin-role finding: forward-brushing-on-topspin lacks an owned explicit topspin condition, and a reason should distinguish feedback on insufficient produced spin from an incoming no-spin condition. Retain this actual ambiguous proposal and a clearly produced-shot control in frozen evaluation; require reviewed ownership for contextual spin labels. Dependencies remain P1-50/P1-51 source dossiers and recorded real-call provenance. See [the continuation session](Session%20Logs/2026-10-15-10.md).

**Redesign pilot finding (2026-10-15 23:32) — open:** [Actual-source evaluation](audit-throughput-redesign-2026-10-15.md) used10 deliberate source cases /138 units,13 calls /339,389 tokens.37 primary-known defects were machine-passed, including16 previously rejected by saved checks; two supported controls were rejected. This is not a population error rate. No candidate received public approval from the pilot. Block unattended semantic clearance; retain exact final primary-review artifact enforcement and preserve these actual false passes/controls for P1-34. Investigate prose wrappers, deictic topic fit and polarity/role/condition errors before any accuracy claim. The original referent control pair still distinguishes bad/good.

**Primary coverage finding (2026-10-16 00:30) — open:** Seven new complete plans reveal false exclusions as well as false claims: fast-response draft drops actual related compact-motion/power/feet/receive examples, and brush relation target now explicitly describes generating spin. Preserve/narrow valid owned clauses; exact-heading terms are not required for relevant examples. Heavy spin does not establish backspin, and press/brush alone does not establish forward direction. Frozen actual source/plan evidence in [primary expansion log](Session%20Logs/2026-10-16-00.md); dependencies P1-51 targeted repair and exact source/target freshness. No blanket restoration or source-context ownership inferred.

**Contact-primary controls (2026-10-16 00:34) — open:** Full94-unit source review retains actual failure cases for unfinished selected caption treated as whole timing rule, omitted nonattack/defense drill qualifier, source-local racket-region observation universalized, ambiguous error-versus-prescription polarity, and deictic position treated as geometric proof. Also preserve supported precise-distance/body-stability/multiple-point brushing controls to detect false exclusions. Dependencies P1-51 targeted exact-proof repair and P1-50 closure; acceptance is concrete clause/condition grounding without unowned context or invented visual review. Evidence [contact review log](Session%20Logs/2026-10-16-00.md).

**Control/counterloop/spacing primary finding (2026-10-16 00:40) — open:** Complete91-unit source review retains actual failures of full definitions on disconnected fragments, completion targets turned into drill procedures, source selection cue turned into whole stroke definition, source-local spacing universalized, and opponent target side conflated with hitter stroke side. Correct these without discarding supported controlled-power/rhythm/spacing examples. Evidence [session/source review](Session%20Logs/2026-10-16-00.md), P1-51 targeted repair and P1-50 full coverage; exact source ownership and final primary approval required.

**Serve/defense/grip primary finding (2026-10-16 10:15) — open:** Actual100-unit source review records handpath versus balltrajectory confusion; opponent serve target versus servingstroke role confusion; attacker-versus-blocker rhythm tactics misassigned as defender actions; flick-specific grip timing universalized; and lesson-local flick spin limitation treated as universal despite supported deceptive-flick control. Preserve source/method/actor conditions and true tactics without silently redefining durable topics or deleting supported alternatives. Evidence [complete primary review log](Session%20Logs/2026-10-16-10.md); dependencies P1-51 targeted repair and P1-50 exhaustive closure, exact final primary approval required.

**Confirmed grip-polarity regression (2026-10-16 10:47) — add to frozen controls:** Actual Firm grip during block plan retained affirmativetightgriplabel/defs while owned4cb63–69/evidence warn NOTtight againstfastpowerfultopspin. Targetedrepair nowcorrected/appliedwithfreshprimaryproof; preserveactualbefore/after/source/policyprovenance and requiremodeldistinguishpolarity, not justmatchinggripwords. Additionalcompleteprimaryfindings: unownedcenterofgravity/backswingphases/fingerarc/acceleration/palmbenefits andunsupportedratings. Evidence [session](Session%20Logs/2026-10-16-10.md), P1-51/P1-50; broaderaccuracyremainsopen.

### P1-50 — Audit and repair every published article with saved coverage

**Status:** In progress (2026-10-16 12:53 EEST). Currentclearance92/377articles,683/4465units;285articles/3782units pending. Original379articles/4501units retain twoarticleexclusions,34revieweddifficultyclears,twoarchivedcitationquarantines. Friction-vs-impact dependency reopening resolvedbycompletefresh seven-unit/five-caption sourceandtopic-overlapreview recordedundercurrentfingerprint,zero modelcalls/nocanonicalchange; oldappliedplan remainshistorical. Lastrelease verified261Python155.84s,ninemonitortests,Ruff,zeroAstrodiagnostics/635pages,brushing/positioningliveroutes. Confirmedrepair3 deferredbyaccountquotaguard:session63389terminal,zerocalls/zeromodeltokens,fivehour89percent/weekly43percent,fivehourresetmorethan10minutesaway;checkpointpreserved:half-longball/heavy-spinserve/highqualityattacklabel. Accountquota80percent/fivehour10minuteexception enforced. Normalprocessingpaused;fullprimary/correction/footageclosure remainsopen. [Evidence/history](audit-throughput-redesign-2026-10-15.md); `media/audit-friction-dependency-review-2026-10-16-12.json`.

**Cost-review dependency:** [Throughput implementation](audit-throughput-redesign-2026-10-15.md) retains complete fixed-cohort accounting, primary approval and strict closure. Current counts are in Status; dated prior checkpoints remain history. Stale overlap-dependent plans require targeted freshness review, not bypass or global rerun.

**Owner area:** Editorial/published-content accuracy

**Continuation finding:** The repair gate exposed summary writes splitting multiline YAML definitions and leaving wrapped hash continuations behind. Shared writer now replaces/inserts complete scalar blocks for folded, literal, plain and quoted summaries, including wrapped metadata. Thirteen focused summary tests passed, including five format regressions; full repair release verification passed with 162 Python tests, nine monitor tests, Ruff, validators and a zero-diagnostic Astro build. Both deterministic and Codex callers use the same fix. Backlog status classification now uses the leading clause so later blocked/complete wording cannot mislabel this In progress campaign; the live view was verified. The corpus campaign remains in progress.
**Source:** Operator rejected ad hoc sampling; [full audit workflow](full-published-audit-workflow-2026-10-14.md) and [complete coverage report](full-published-audit-coverage-2026-10-14.md).

**Why:** Spot repairs identify errors but cannot show remaining unchecked claims or establish corpus-wide coverage. Object/topic confusion and fragment-only citations also contaminate article summaries/facets.

**Work:** Enumerate every public article field, citation, relation, and visual claim, including unflagged content. Review full dossiers in stable order, save source-grounded per-unit findings, repair canonical YAML with history, and recheck changed fingerprints. Do not count deterministic validation or previous samples as complete semantic reviews. Resolve all unchecked, needs-fix, needs-footage, and stale units; retain removed/changed records and prior decisions in history. Keep processing paused until this audit finishes or the operator explicitly changes that instruction.

**Dependencies:** P1-14 boundary/timing reconciliation, P1-34 semantic/attribution quality, P1-49 repair history, exact cached captions, per-KB lock, full clip inspection for visual support, and idle release verification.

**Done when:** Every unchanged current public unit has an explicit supported review with provenance, no structural errors or unresolved findings remain, canonical repairs are archived, final release checks and affected routes pass, the coverage/backlog views show completion, and the operator's processing state is restored deliberately. Recorded coverage does not claim infallible accuracy.

### P1-51 — Automate whole-corpus repair drafts and independent verification

**Owned-source experiment in progress (2026-10-16 22:18 EEST):** A finite private Luna/high verification job tests three prepared real-caption windows for backhand rotation, flick-rise timing and borrowed-force context. Preflight rebuilt current dossiers and checked exact IDs/times/video bounds/30-second limit; a same-video multi-citation match was corrected before any model call by requiring overlapping actual segment IDs. At most six verification calls under the KB lock and existing quota/budget guards. No canonical changes, publication or approval. Private evidence: `media/audit-owned-source-verification-2026-10-16-22*`. Acceptance: inspect every dependent claim and independent verdict, record fresh complete primary review, and apply only through archived source correction with current fingerprint; do not bind old approvals or treat added context as automatic clearance. Separate pinch-topic evidence still needs its own valid source record. Starting quota29% five-hour/74% weekly; normal processing stays paused.

**Generic repair correction (2026-10-16 22:12 EEST):** Implemented source-grounded heading correction and opaque-ID policy (draft 1.1.1 / verifier 1.1.2), including reducer propagation. All 79 focused repair tests pass. Real Luna/high replay retained the valid backhand citation despite its forehand ID, rejected/corrected reversed grip timing, and accepted elbow-speed wording without treating an obsolete serve ID as a claim. Primary review still caught dropped flick scope; the verifier rejected an invented make-room instruction. Targeted follow-ups removed both, qualified aliases, cleared an unsupported beginner rating and preserved actual drive/loop forearm wording. All eight articles received complete primary review; six guarded repairs applied, two wrist/source-scope exceptions remain. Total 37 finite calls/807324 recorded tokens/751.23 seconds model phase, including the original 16-call diagnostic batch. This is bounded case evidence, not whole-corpus accuracy certification. Full idle release passed 284 Python/nine Node tests, Ruff, validators and zero-diagnostic Astro build (635 pages); see current session for final local checks. No old pending approval is valid under the new policy versions.

**Eight-article execution (started 2026-10-16 21:50 EEST):** The original finite Luna/high job finished after 16 calls within its 20-call cap; starting quota 10% five-hour/71% weekly. Exact baseline/dossiers/IDs: private `media/audit-next8-2026-10-16-21*`; subsequent new-policy controls/follow-ups use `media/audit-heading-*`. Scope includes backhand errors/wrist, heavy-backspin push, contact grip, serve elbow, forearm position and footwork quality. Six guarded applications retain stroke/phase/lesson qualifications; two wrist cases need actual source ownership. Normal processing remains paused.

**Status:** Blocked (2026-10-16 23:22 EEST) by configured weekly quota guard:81% used versus80% cutoff (five-hour74%). Same blocker confirmed across three consecutive goal turns; no live worker or exact independently verified/primary-ready alternative exists. Coverage remains149/377 articles and1098/4424units supported;228articles/3326units pending,one existing overlap,zero structural/source-metadata errors. The wrist baseline/draft is saved privately with its colliding alias removed; independent verification never ran. Resume only when actual quota permits: verify the alias-corrected full proposal against a fresh matching dossier, record exact final primary review, then guarded application/navigation alignment. Do not blindly apply the older cached alias or reset the cleared corpus. Evidence:`media/audit-wrist-unverified-proposal-2026-10-16-23.json` and current session. Last full release and local checks passed297Python/nineNode tests,Ruff,validators,zeroAstrodiagnostics/635pages. Normal processing remains paused; no reset,guard bypass,unverified publication or footage approval. Full audit incomplete.

**Owned-context study — P1-51/P1-34:** Inspected actual timed neighboring captions for four blocked articles. Proposed Paymo05-10 for backhand forearm rotation(27.567s),BTo163-171 for rise-timing/backhand context(24.160s),15El26-30 for the underspin-struggle/borrowed-power observation(25.633s),and additional ae9 finger-pressure topic proof53-57(20.734s). Every proposed ID resolves to its real caption;spans stay within video duration,30second limit and existing gap limit. The pinch topic53 through mechanics65 spans60.267s and is rejected as one citation:separate bounded topic/mechanics records and exact clause ownership must be reviewed,not a guessed trim or automatic exception. Source:private exact fingerprints/plan hashes and selected rows in the artifact above;[operations](operations.md#owned-context-preparation--2026-10-16-1916-eest). Dependencies:existing P1-51 owned-source editing/archives,full fresh primary and Luna verification,quota allowance. Acceptance:actual source rows only,no inference from titles,neither independent evidence nor playback context silently supplies another citation's qualifier;preserve originals and verify every dependent claim before applying. Flick/borrowed-force semantics remain proposals,not clearance. No corpus/source files changed or approvals added.

**19-hour source checkpoint:** Fourcalls/83255tokens/82.58s modelphases;twoexactcompleteprimaryreviews andguardedapplications. Preserve spoken nonexclusive drive-envelope prohibitions ratherthan strict above/below boundaries or inventedcontactgeometry. Right-leg loading explicitly FOR THE LOOP;negation is neitherleftlegnorbehindplayer,not aninstruction toputweightbehind. Noinventedhandedness/footangle/visualattestation. Actualquota77percentfive-hour;smallerbatchchosennearcutoff,guardsunchanged. Dependencies/acceptance:fullidle gate/currentbacklog/HTTPverification,remaining actualsource/topic/overlap work. Evidence media/audit-batch2-*2026-10-16-19 and[session](Session%20Logs/2026-10-16-19.md).

**Latest batch B evidence:**32Luna/highcalls/666173tokens/693.22s modelphases,including two boundedthree-case followups. Actualownedconditionspreserved:backspintimingmidstroke,AFTERrecoveryclearance,fastserveversusmanysidespin-topspinserve,fastballcompactoverride/slowballdistancesizing/morefootmovement,heavyspinserve side-contact,step-aroundexplosivefootwork,downwardflickchop,contact-onlyfingerforceversusseparatespeedcue. No inventedfootangle. Borrowforce finalobservationdoesnotendorsethecriticizedtendency,butverifierdisputesincomingorigin/topiclink;no forcedapplication. Retain timingsequence,condition-scope,observationalrole andsource-referent cases underP1-34;remaining source/context andoverlap work staysunderP1-51/P1-03. Acceptance:actualownedclauses,freshcompleteprimary,noautomaticendorsementofobservations,noafter-contactbrushinference,completebatchrelease. Private media/audit-batch10b-*2026-10-16-18;[current session](Session%20Logs/2026-10-16-18.md).

**Latest source findings:** The spacing proposal borrowed HAND from a separate hand-to-ball citation into a personal forearm-from-body example;final follow-up removed that inferred object and preserved experience scope. The verifier falsely rejected cross-court alias despite owned9b140;one verifier-only follow-up accepted the unchanged valid alias. Retain both actual controls underP1-34. Block-spin-reading and close-distance-for-pushes still lack owned stroke qualifiers. Three changed advisory overlaps inspected:two current empty sets cleared;backhand-swing-arc-spacing versus create-space-and-avoid-jamming needs consolidation/boundary review underP1-03/P1-51. Dependencies:actual source ownership,existing overlap-only workflow and archives. Acceptance:do not infer block/push identities or erase valid cross-court wording;resolve real spacing overlap without deleting evidence;preserve every batch outcome and full-release evidence. Private media/audit-batch10-*2026-10-16-18;[session](Session%20Logs/2026-10-16-18.md).

**Status:** In progress (2026-10-16 17:38 EEST). Finite six-article continuation applied three additional complete source/primary-reviewed corrections;three remain blocked/disputed. Current116/377articles and855/4452units supported;261articles/3597units pending;full idle release passed274Python/nineNode tests,Ruff,zeroAstrodiagnostics/635pages. [Six-article checkpoint](audit-continuation-six-2026-10-16-17.md). Previous saved20 checkpoint: Saved next20 continuation applied ten additional complete source/primary-reviewed corrections using finite Luna/high CLI jobs;ten batch cases remain blocked/disputed. Current113/377articles and834/4452units supported;264articles/3618units pending;full idle release passed274Python/nineNode tests,Ruff,zeroAstrodiagnostics/635pages. No footage approval. [Continuation evidence](audit-continuation-2026-10-16-17.md). Previous frozen20 benchmark: 11 complete source/primary-reviewed applications,nine blocked/disputed;45 GPT-6 Luna/high calls and974168 processor tokens including two passing frozen referent controls. Model phases17.03min;batch application160.04s. Audit ledger103/377articles,762/4457units supported;274articles/3695units pending. Eight optional ratings removed;no footage approved. Normal processing paused. Generic next fixes:typed reviewed metadata,actual owned-source-context edits and explicit restoration of rejected quarantines. Local startup/import delay remains unexplained;no unrestricted retries or remaining-hours forecast. Release evidence and all20 outcomes: [benchmark report](audit-benchmark20-2026-10-16.md); [session](Session%20Logs/2026-10-16-15.md). App-hang study16:35:bounded audit finished15:46;failed chat Stop requests16:28 returned thread_not_found before16:29restart. Use finite CLI jobs instead of interactive audit REPL;app routing rootcause remains external/unconfirmed. [Evidence](chat-hang-investigation-2026-10-16.md).

**Owner area:** Generic processors/editorial verification
**Source:** Operator requested a generic or automated alternative to individual repairs; [automation study and measured findings](automated-published-repair-study-2026-10-14.md).

**Why:** The original findings-only checks repeated source context and required manual repairs. Producer recurrence and correlated verifier mistakes require shared controls and measured accuracy; two model calls do not establish correctness.

**Work:** Complete bounded actual-source accuracy/cost evaluation and idle release verification; reconcile/apply remaining fresh primary-ready plans, then cover remaining units with complete-proof audit batches and targeted repairs. Preserve primary review and source/topic/target/context/policy/model invalidation. Park unresolved cases until concrete evidence/findings change. Measure actual tokens per resolved unit against a comparable frozen baseline (target at least50% reduction), not request characters or smaller-call claims. Retain original fixed-cohort accounting and archived nullable-field removals; no global rerun, model escalation or unattended approval.

**Dependencies:** P1-14 timing precision/reconciliation, P1-33 summary producer/provenance, P1-34 accuracy benchmark, P1-50 exhaustive baseline/closure, current model/budgets and shared locks/transport/validators.

**October 14 findings and resolution:** Live reduction needed an untrusted-proposal assembly contract before actual selected-source verification. Required-key wire objects now guarantee every unit is represented; schema/runtime constraints reject duplicate edits and quarantine-plus-rewrite contradictions. Verifier topic fields and quarantine status mirror the proposed result. Primary needs-fix notes participate in plan identity and application freshness. Twenty-five focused repair tests and the final 199-test release gate passed. Older plans remain in private history and cannot bypass version/finding checks. The middle-target article was narrowed to short backhand-serve loops after primary review rejected unsupported sidespin specificity; the rushing article retains its served-sidespin condition. Front-of-table attack was excluded with its original archived because its selected cue supports a different topic. No footage was attested. Evidence: [implementation checkpoint](automated-published-repair-study-2026-10-14.md#verified-continuation-checkpoint--2026-10-15-0034-eest), [session log](Session%20Logs/2026-10-15-00.md), and [current coverage](full-published-audit-coverage-2026-10-14.md).

**October 15 verifier boundary:** Implemented and source-replayed under 1.0.8; prior processing confidence/approval no longer enters the independent claim target. Primary review also blocked unsupported hand referents, deictic visual comparisons and overbroad pushing/forehand conditions. These actual cases remain P1-34 frozen-evaluation work, with evidence in the [session log](Session%20Logs/2026-10-15-10.md).

**Operator model decision (12:08 EEST):** User explicitly selected GPT-6 Luna (`gpt-6-luna`) for subsequent processor calls, retaining low effort, disabled automatic escalation and existing budgets. Configuration/docs updated; historic model provenance is preserved. This selects the model for the Planned efficiency work and does not implement caching/batching, resume processing, rerun the audit or prove accuracy/token savings. Source: [session log](Session%20Logs/2026-10-15-12.md); dependencies/acceptance remain the P1-34 controls and P1-50 coverage gates.

**Efficiency follow-up — phase 1 implemented, P1 (2026-10-15 12:34):** Source: operator's time/token concern and [measured cost review](automated-published-repair-study-2026-10-14.md#audit-efficiency-review--2026-10-15). Last continuation: 53 calls / 1,570,862 recorded processor tokens for ten completed articles, excluding chat usage. Global version invalidation and whole-article retries repeat unchanged work. First implement stage-specific draft/verification cache identity and unit/dependency reuse; compact repeated caption/record payloads and response notes; then evaluate small-article batching and persistent exception parking. Every initial unit stays covered, and changed topic/target/source dependencies reopen affected reviews. Dependencies: existing checkpoints/locks, P1-34 frozen controls, P1-50 full coverage and explicit editorial application. Acceptance: verifier-only changes reuse unaffected drafts; unchanged parked exceptions make zero calls; unrelated supported units are reused only with valid dependency fingerprints; no source row/unit or safety gate disappears; measure calls/tokens per resolved unit before/after with no new false acceptances on frozen cases. Contract 1.1.0 implements stage/dependency caching, targeted revisions, compact input and exception parking in the existing checkpoint/transport. Corpus-wide source-preservation assertions passed: 420 initial draft requests, 14,398,522 original serialized characters versus 7,275,269 compact (49.5% reduction; 46.7% versus equally minified originals). Forty-three focused repair tests pass, including source/topic/definition/target/overlap/metadata/model invalidation and no-op rejection reuse. Two live GPT-6 Luna low controls used 38,570 recorded processor tokens; the supported clause passed, but the known unsupported referent was falsely accepted again. No new corpus approvals or canonical changes. Legacy checkpoints need a one-time policy refresh; their old digests are not blindly trusted. Batching and resolved-unit token/runtime benchmarks remain open; no unattended approval or general accuracy/savings claim.

**Processor Apps opt-out (19:27 EEST) — implemented, idle/live verification pending:** The failed component was unnecessary Apps MCP startup in source-only jobs. Official OpenAI config docs and installed CLI feature check confirm per-run features.apps=false. Extraction, shared repair/adjudication, summary, batch summary and rephrase children now set that flag and record apps_enabled false in provenance; global settings/model/high/budgets remain unchanged. Five caller-contract regressions and all 231 Python tests/Ruff pass. Dependencies: original campaign idle before actual retry/final release gate. Acceptance: inspected failed jobs resume with the opt-out and unchanged source guards; record actual startup/token behavior before claiming savings. This disables Apps only, not every inherited MCP/plugin; valid semantic caches are preserved. See [19:00 session](Session%20Logs/2026-10-15-19.md).

**Campaign failure recovery (18:28 EEST) — implemented, release gate pending:** Source: 51 real Codex Apps MCP startup/HTTP response-decoding failures plus two runtime-rejected difficulty responses (text null with strings [] or facets []). Shared draft schema now forces unused representation channels to null, matching existing runtime acceptance; valid cached semantics/policies remain unchanged. Shared planner stops after three consecutive live CodexError failures, resets after fresh success, preserves checkpoints and supports inspected --retry-failed recovery. Dependencies: active original pass must release lock before retry/application/final release gate. Acceptance: focused shape/nullable-clear/circuit/reset/resume tests and full release gate pass; retry all failed articles at Luna/high without counting failed attempts as coverage, preserve budgets/history, and keep normal processing paused. Evidence: [18:00 session](Session%20Logs/2026-10-15-18.md), private inspected report retained under media.

**Primary topic/semantic-facet findings (18:53 EEST) — open:** Model-supported flick control mixes arm advice whose owned rows do not establish flick (one serving-tutorial source); serve-acceleration needs actual serving-context IDs added to its reviewed proof; close-to-body explosiveness wrongly uses table-distance close for racket/body proximity. Source: [complete primary reviews](Session%20Logs/2026-10-15-18.md), P1-34/P1-51. Dependencies: original pass lock release, record fresh findings, targeted source/metadata repair. Acceptance: preserve actual source mechanics and durable topic, own every context ID used as support, quarantine misplaced records reversibly, and supply/check per-KB facet meanings as well as allowed vocabulary. Retain these actual false acceptances in frozen evaluation. No blanket subject inference or auto-approval from matching words.

**Primary metadata/prose finding (17:00 EEST):** Compact body framework still has concept_type new (processing novelty, not durable topic class), while compact-arm/body summaries retain source-reporting wrappers despite semantic model support. Source: [complete primary review](Session%20Logs/2026-10-15-17.md), P1-33/P1-51. Dependencies: running campaign lock release and fresh primary findings. Acceptance: replace wrappers with direct source-grounded prose; explicitly review/correct operational type without expanding model edit privileges or bulk-approving proposals; preserve valid source/visual fields and archive prior content.

**Full-campaign taxonomy finding (15:34 EEST):** Five current terminal plans propose unregistered category/distance values; one passes semantic model verification but cannot pass the existing application taxonomy guard. Source: deterministic exact-value comparison with config/kbs/table-tennis/taxonomy.yaml and [primary review checkpoint](Session%20Logs/2026-10-15-15.md). Dependency: let current campaign finish before changing its policies. Acceptance: provide configured per-KB vocabulary to shared draft/verification inputs and typed constraints, reject unregistered proposals before marking a plan ready, and refresh affected units/stages only; preserve source-grounded measurements in prose rather than inventing classifications. No application/publication bypass.

**Full-campaign primary repair finding (15:23 EEST):** Attack and block-angle plans still retain easy/intermediate difficulty despite explicit unsupported findings in both draft and revision. Acceptance: remove unsupported nullable ratings rather than merely labeling them uncertain, then verify the resulting value; preserve existing source-grounded mechanics. Pressure-management definition and C-shape citation need separately scoped conditions. Dependencies: complete current campaign, record fresh primary findings, targeted repair and exact source verification. Private reviewed plan hashes and per-unit decisions are staged; source evidence is in the [15:00 session](Session%20Logs/2026-10-15-15.md).

**Done when:** Known defects and supported controls pass frozen accuracy/false-positive evaluation; no unit/source chunk can be omitted or cleared through incomplete support; invalid IDs, stale inputs and unauthorized fields fail closed; interruptions/resume preserve source/visual/provenance/unrelated material and repair history; only reviewed canonical YAML is published. The entire fixed corpus receives dispositions with repaired/quarantined/unresolved counts, final strict audit/release gates and affected routes pass, and the planning view reflects the actual campaign status. Two model calls are not assumed to guarantee correctness.

### P1-35 — Make backlog IDs and HTML coverage self-validating

**Status:** Open (2026-08-12).

**Owner area:** Planning/site/QA
**Source:** `docs/project-review-2026-08-12-11.md`

**Why:** the canonical Markdown has duplicate `P1-03`, `P1-12`, and `P1-16` headings, while the local feature map omitted `P1-27` and `P1-28`. The first build after this study also omitted all new IDs until the curated map was edited. A green Astro build can therefore hide backlog work.

**Work:** assign stable unique IDs to follow-ups/hardening items and update references; derive feature membership from maintained metadata or validate the curated map; render an explicit ungrouped section instead of dropping unknown items; fail tests/builds on duplicate IDs, missing mappings, or mapped IDs absent from Markdown.

**Dependencies:** the canonical Markdown backlog, local `backlog.astro` parser, documentation links, and a migration map for existing duplicate IDs.

**Done when:** every backlog heading has a unique stable ID, every item appears exactly once in `/backlog/`, unmapped and duplicate IDs fail verification, and automated tests compare the Markdown inventory with rendered feature membership.

### P1-36 — Explain safe-public, quarantined, and inventory counts separately

**Status:** Implemented (2026-08-30); continue reconciliation during recovery.

**Owner area:** Operations/site
**Source:** `docs/project-review-2026-08-30-13.md`

**Why:** the intentional safety contraction from 533 / 729 / 5,892 to 73 / 51 / 1,119 looks like data loss when the page shows only the safe public snapshot. The same project also has 752 eligible normalized videos and 838 total inventory entries, which are different units and states.

**Work:** show safe published counts, quarantined historical counts, eligible inventory counts, and last-successful-publish time as separate labeled metrics. Include the quarantine reason and link to the recovery queue without implying that unreviewed history is public knowledge.

**Dependencies:** P0-11, P1-04, generated progress data, inventory ledger, and local operator/dashboard surfaces.

**Done when:** an operator can reconcile every headline count to a named artifact and timestamp, failed cycles cannot make a stale publish look current, and the site clearly distinguishes available public content from quarantined recoverable history. `/progress/` now renders safe-public, quarantined-history, and full-inventory layers with the last successful publish timestamp; the generated snapshot remains unchanged by failed cycles.

### P1-37 — Make scheduled and interactive runs share one per-KB lock

**Status:** Implemented (2026-08-30); live overlap observation remains.

**Owner area:** Operations/orchestration
**Source:** `docs/Session Logs/2026-08-30-17.md`

**Why:** the registered Windows task invokes `scripts/run-cp.py` directly, while the documented PowerShell wrapper owns the per-KB lock. The monitor also invokes `run-cp.py` directly, so Task Scheduler’s `IgnoreNew` policy does not prevent an interactive monitor cycle from overlapping the scheduled cycle.

**Work:** acquire one atomic per-KB run lock inside the shared orchestrator, or make every entry point use the same wrapper; hold it for every mutating stage; record a clear skipped/overlap result in the private manifest and preserve cleanup after crashes or termination.

**Done when:** scheduled, monitor, and manual invocations cannot mutate the same KB concurrently; an overlap exits safely with an explicit reason; and the lock lifecycle is tested on success, failure, and interruption. `run-cp.py` now owns an OS-level per-KB lock shared by all entry points and holds it through the full processing cycle; it records overlap attempts privately and the lock is covered by a cross-process regression test.

### P1-38 — Rotate deferred adjudication work across time

**Status:** In progress (2026-10-12); video-pool rotation implemented; October 13 proposal selection now orders by fewest attempts then oldest attempt. Exact proposal-selection manifests and source-level quality evaluation remain open.

**2026-10-12 source finding:** `processors/pipeline.py:694` slices matching proposals in queue order after receiving a set of video IDs. In the current 50-video pool, 72 pending proposals coexist with six repeatedly deferred proposals occupying six of the predicted next ten slots. See [throughput review](processing-throughput-review-2026-10-12.md).

**Follow-up acceptance:** Select actual proposals by pending/attempt-aware source rotation, record exact proposal IDs/reasons, prove deferred work eventually receives service, and check concept identity/duplicate-topic quality under P1-34. Keep difficult proposals retryable without permanent exclusion or automatic acceptance/rejection.

**Owner area:** Operations/review queue
**Source:** `docs/Session Logs/2026-08-30-17.md`

**Why:** the current selector is source-balanced and view-ranked, but it has no persistent cursor, retry cooldown, or starvation guard. A set of unresolved high-view videos can therefore occupy the next 50-video adjudication batch on every scheduled run while later quarantined work waits.

**Work:** add deterministic attempt-aware rotation or a retry schedule to the private ledger; allow successful and newly eligible work to advance; retain deferred items as retryable without making them permanently highest priority.

**Done when:** repeated deferrals are visible with next-attempt timing, later eligible videos receive bounded service, source balance remains intact, and the run manifest explains selection priority. The private ledger now carries per-video pending/deferred counts, attempts, and latest attempt time; selection prioritizes untouched/less-attempted work before repeated retries while retaining source rotation and view-count ordering as tie-breakers.

### P1-39 — Make generated ledger replacement resilient to transient Windows locks

**Status:** Implemented (2026-08-30); live recovery retry remains to be observed.

**Owner area:** Operations/runtime reliability
**Source:** `docs/Session Logs/2026-08-30-17.md`

**Why:** The 2026-08-30 recovery cycles reached Codex adjudication but failed when `processors.llm_budget.BudgetManager.finish()` atomically replaced the private `llm-budget.json` ledger. Windows returned `WinError 5` for the fixed `.tmp` replacement path, leaving a stale temporary file and aborting the whole `run-cp.py` cycle. The monitor log does not identify Avast as the cause; a short-lived external handle remains a possible environmental cause.

**Work:** Use collision-resistant per-process temporary JSON names, retry transient `PermissionError` replacement failures with bounded backoff, retain the last readable target when replacement cannot complete, mark monitor-forced interruptions in the private run manifest, cover the behavior with regression tests, and document the operational failure mode.

**Done when:** Budget reconciliation survives transient Windows file locks without losing the readable ledger or aborting the batch; persistent permission errors still fail closed with an actionable log; forced monitor stops do not leave a running manifest; and a later scheduled or manually authorized recovery cycle completes without the same write failure. The shared generated-file replacement helper now retries five times with bounded backoff and is used by JSON and round-trip YAML writers; the monitor records an interrupted manifest when it terminates its matching child.

**Evidence:** `processors/utils.py`, `processors/pipeline.py`, `scripts/processor-monitor.mjs`, `tests/test_utils.py`, `docs/operations.md`, and the 2026-08-30 and 2026-09-10 session logs. Targeted tests and Ruff pass; the monitor now reconciles an orphaned `status: running` manifest when its recorded processor PID is gone.

### P1-40 — Show progress while a Codex adjudication phase is in flight

**Status:** Implemented (2026-09-15); live monitor restart observation remains.

**Owner area:** Operations/monitoring
**Source:** `docs/Session Logs/2026-08-30-17.md`

**Why:** The monitor streams `run-cp.py` stdout, but `process-pending` prints its summary only after the bounded video batch returns. Each Codex call is executed with captured output so usage and schema results can be parsed, leaving the monitor with only `=== small fair retry batch for unclear candidates ===` during a long call. The 17:23 recovery phase therefore looked hung even though it was inside the adjudication path; the 17:45 attempt was manually stopped before it could emit a summary.

**Work:** Emit flushed, privacy-safe progress events before, during, and after each selected video/candidate adjudication, including counters, video/candidate identifiers, outcome, and elapsed time; expose the latest heartbeat in the monitor and retain stage timeout/error reporting. Do not stream prompts, transcripts, raw Codex output, or credentials into the monitor.

**Done when:** During a long adjudication phase the monitor shows a heartbeat at least every 15 seconds while waiting for Codex, identifies the selected item by safe IDs and counters, distinguishes waiting for Codex from post-processing and file writes, records the last completed item after interruption, and tests verify the events are flushed and bounded without exposing source text. The adjudication subprocess now emits 15-second heartbeat events, the CLI prints flushed bounded progress lines that `run-cp.py` forwards to the monitor, and the monitor derives the current ten-item pass, the eligible candidates in the selected video pool, and the full retryable backlog from those lines. Every orchestrator stage now also emits a plain-language purpose, a `Stage x/y` position, a 15-second no-new-output heartbeat, and a duration-bearing completion line; heartbeat lines include the video ID. Failed cycles now also expose an allowlisted publish-validation or safe-stop reason in the monitor log and `lastRun.reason`.

**Dependencies:** P0-11 recoverable adjudication errors, P1-16 stage timeouts, `scripts/run-cp.py` output capture, and the monitor's current-stage API. Concept-proposal decision buckets now name the subject and show their unit (`concept proposals`) beside each count; inventory buckets show `videos`.

**Evidence:** `scripts/run-cp.py`, `processors/cli.py`, `processors/pipeline.py`, `processors/codex_engine.py`, `scripts/processor-monitor.mjs`, `tests/test_pipeline.py`, `tests/test_codex_engine.py`, and the 2026-08-30 and 2026-09-10 session logs. The live run confirmed bounded `[adjudication] x/10` events; the progress format now labels the selected-video pool separately from the full adjudication backlog (`remaining/starting-total`, including pending and deferred proposals), and stage logs/manifests now carry `Stage x/y`. After restart, a real four-stage cycle showed `Stage 1/4` through `Stage 4/4` and published successfully; focused/full tests, Ruff, Node syntax checks, validation, and Astro build pass.

### P1-41 — Isolate per-candidate Codex timeouts

**Status:** Implemented (2026-08-30); live recovery observation remains.

**Owner area:** Processing reliability

**Source:** `docs/Session Logs/2026-08-30-22.md`

**Why:** The latest cached-triage run reached one captured Codex adjudication's five-minute timeout. `subprocess.TimeoutExpired` escaped the candidate loop, so the whole stage returned exit 1 even though the failure was local to one candidate and should have been retryable.

**Work:** Convert bounded adjudication timeouts into a typed Codex error with a bounded private audit record, release or reconcile the associated token reservation, mark only that candidate deferred with its attempt/provenance, and continue the selected batch.

**Done when:** A timed-out candidate is not accepted or published, its queue item records a retryable defer and timeout provenance, the next selected candidate is processed in the same stage, the private failure audit retains bounded diagnostics, and persistent stage-level failures still fail closed. Implemented in `processors/codex_engine.py` and `processors/pipeline.py` with regression coverage.

**Dependencies:** P0-11 recoverable adjudication errors, P1-16 stage timeouts, and P1-40 live progress reporting.

**Evidence:** `processors/codex_engine.py`, `processors/pipeline.py`, `tests/test_codex_engine.py`, `tests/test_pipeline.py`, and the 2026-08-30 22:00 session log. Focused tests and Ruff pass; a live recovery run remains.

### P0-12 — Close review and publication trust bypasses

**Status:** Complete (2026-09-19).
**Owner area:** Pipeline/publication
**Source:** `docs/specification-gaps-and-issues-2026-09-19.md`
**Why:** Queue rebuilding inferred acceptance from similarity, relation sources bypassed citation checks, and public validation permitted private transcripts or unapproved records.
**Work:** Require explicit persisted review decisions; share evidence/relation citation validation; publish approved relations only; reject private/unapproved public payloads.
**Dependencies:** Existing canonical review states, segment IDs, and P0-09/P0-10 citation contract.
**Done when:** Regression checks prevent inferred acceptance, invented relation citations, unapproved relation publication, and private transcript payloads. Three invalid relation spans remain preserved as unreviewed pending P1-43.

### P1-42 — Align inventory and publication with reviewed citations

**Status:** Complete (2026-09-19).
**Owner area:** Pipeline/inventory
**Source:** `docs/specification-gaps-and-issues-2026-09-19.md`
**Why:** Inventory ignored adjudicated citation IDs, publication lost separately cited videos, and demo validation could crash or retain excluded demo relation sources.
**Work:** Reuse citation-ID accounting, include visual/relation video references in sanitized output, and handle demo exclusions consistently.
**Dependencies:** P0-12 and existing stored adjudicated segment IDs.
**Done when:** Regression checks recognize incorporated adjudicated citations, retain cross-video source metadata, and validate the include-demo path without an unbound variable.

### P1-43 — Finish visual and relation policy enforcement

**Status:** Open (2026-09-19).
**Owner area:** Editorial/schema
**Source:** `docs/specification-gaps-and-issues-2026-09-19.md`
**Why:** Inferred visual windows lack an enforced 15-second limit with reviewed exceptions, canonical relation vocabulary differs from extraction, and three overlong relation spans require review.
**Work:** Define reviewed visual exceptions and supported relation vocabulary; validate canonical/public payloads consistently; reselect supported spans for brush-around-the-ball, contact-zone-on-ball, and weight-transfer-through-stroke relations preserved as unreviewed.
**Dependencies:** P0-12, editorial vocabulary decision, complete clip inspection for visual exceptions, and transcript-backed relation review.
**Done when:** Oversized inferred windows fail without an explicit reviewed exception; unsupported relation types fail with a documented migration; all three quarantined relations have supported bounded citations or a tracked rejection.

**P1-51 throughput acceptance update (2026-10-16):** Source: operator time/token concern and measured study. Dependencies: current final-primary/source hashes,KB lock,transaction/archive guards,quota cutoff,P1-34 frozen accuracy controls. Acceptance: optional rating removals explicitly authorized by exact-current complete primary review make zero model calls and preserve all other values; full release once per representative20–30article batch; actual changed-source/topic/target dependencies reopen required units while advisory overlap changes do not invalidate unchanged claims; whole-transaction scratch profile and matched20article runtime/token/quality benchmark show no new false acceptance. Status: implemented core throughput safeguards; focused regressions passed. Exact-current difficulty-only typed plans make zero model calls; batch snapshots retain external-write/source/target guards; safe archive serialization validates values; overlap changes preserve claims but leave explicit review pending; private text/citation/footage queues added. Full post-application audit rebuild remains once per article. Scratch transaction benchmark and full release evidence follow in the implementation checkpoint. Representative real20article semantic/quality benchmark and full corpus clearance remain open; no shorter completion forecast.

### P1-52 — Stop new LLM calls at account quota threshold

**Status:** Complete (2026-10-16).

**Source:** Operator requested 80% or configurable cutoff with five-hour window exemption only when <=10 minutes remain.

**Dependencies:** Codex authenticated account quota endpoint, shared token-budget reserve guard, existing per-KB checkpoint and lock.

**Acceptance:** Before every new processor model call, read actual quota; configurable cutoff applies to all reported buckets. Five-hour windows block at threshold only with >600 seconds remaining; weekly remains independent. Missing/invalid/expired quota defers without reserving or calling the model. Local budgets still apply. Retain existing call checkpoints, do not kill in-flight calls, no automatic resets/purchases. Verify exact boundary, configurable threshold, multi-bucket precedence, unavailable data, cleanup, shared reserve integration, full release and local backlog.

**Evidence:** 20 focused quota/budget tests and Ruff passed; live read-only account lookup succeeded. New module `processors/account_quota.py`; configuration `llm_budget.account_quota`; [operations](operations.md#account-quota-cutoff). Full release passed:261 Python tests,nine monitor tests,Ruff,zero Astro diagnostics,635pages. Evidence: `media/account-quota-release-2026-10-16-12.log`.

### P1-53 — Close normal-processing recurrence gaps exposed by the full audit

**Status:** In progress (2026-10-16 18:06 EEST). Pipeline fixes implemented and full idle release verified: 281 Python tests, nine Node tests, Ruff, reviewed/published validation and zero-diagnostic Astro build (635 pages). Broader P1-34 live accuracy controls and the full corpus audit remain pre-resume work. Normal processing remains paused.

**Priority:** P1 for causal summary cleanup, post-verification semantic rewrites and summary pause/lock bypass; P2 for omitted new-concept type verification. Complete these controls before normal generation resumes.

**Why:** Reviewed knowledge can become unsupported after a later rewrite, and direct summary writes can change the fixed audit target. The audit's corrections will recur unless the final saved values and all write entry points are protected.

**Source finding:** [Normal-processing review](normal-processing-audit-review-2026-10-16.md). Controlled temporary/mocked reproductions confirmed cleanup invents “because,” unrelated rephrased knowledge retains approval, a direct summary-write CLI reaches its writer during the audit pause, and new `concept_type` is saved without verifier coverage. No production content changed and no model calls ran.

**Work:** Remove causal grammar substitution; guard both summary-write engines with the existing pause and KB lock; independently verify final semantic excerpt/summary rewrites against exact owned captions before replacement; include new concept type in shared verifier coverage. Reuse existing gates and atomic file replacement, without a new worker framework or model escalation. Supply domain-owned facet meanings under existing P1-51 scope rather than infer meaning from allowed enum spelling.

**Dependencies:** P1-33 summary quality/provenance, P1-34 actual positive/negative accuracy controls, P1-51 shared verifier/source ownership, P1-52 quota guard, per-KB lock and current audit pause.

**Lock integration constraint:** `run-cp.py` owns the KB lock across child CLI stages. Preserve that ownership while protecting direct summary commands; a naive nested child acquisition would block the normal runner itself. Test both direct contention and the complete parent/child cycle, without an unverified lock-bypass option.

**Implementation:** Removed the causal cleanup substitution; final excerpt and optional Codex-summary wording now passes the shared exact-source verifier before replacement. Direct summary writes check pause and acquire the KB lock; summary persistence uses atomic replacement. Removed the runner's redundant summary child stage because its existing publish stage fills missing summaries while retaining the parent lock. New/restored concept type joins verifier unit coverage, and domain-owned facet meanings accompany normal candidate verification. No lock-bypass flag, model escalation, processing resume or audit approval was introduced. Rejected rewrite and paused/contended-write regressions passed; final release evidence follows.

**Release evidence:** `media/p1-53-release.log`: 281 Python tests in 246.17 seconds, nine Node tests, Ruff, validators and zero Astro errors/warnings; 635 pages. Controlled regressions cover rejected final excerpt/summary preservation, both engines' pause/lock rejection, causal cleanup and metadata unit coverage. No live Luna replay ran at the configured quota cutoff. Complete real semantic-accuracy controls under P1-34 before resumption; do not count fixture verifier tests as model-accuracy proof. Audit coverage remains 116/377 supported, 261 pending.

**Done when:** Cleanup never introduces an unsupported causal relationship; unsupported or uncertain rewritten text leaves canonical bytes/approval unchanged; verifier/budget/transport failure cannot fall back to formatting-only approval; paused/contended summary writes cannot reach either writer, while preview stays read-only; every saved new concept type is included in exact final verification; actual qualifier/causal/facet/typo/question-answer controls distinguish bad claims from supported wording. Focused regressions and the full idle release gate pass before normal processing resumes. Keep original sources and all disputed audit findings.

## P2 — harden and scale

### P1-44 — Remove redundant adjudication checkpoint writes

**Status:** Complete (2026-10-12); persistence equivalence, replay timing, and full release gate verified.

**Why:** A ten-item pass checkpoints after item ten, then immediately writes the entire queue again and rewrites all 597 concept documents. Read-only measurements took 14.94s for a queue dump and 5.07s for concept serialization, roughly 20s of avoidable serialization in the observed 292s cycle.

**Work:** Flush only uncheckpointed queue mutations and dirty concept documents at successful exit; preserve the existing ten-item checkpoint and atomic replacement. Keep model inputs, decisions, validation, and canonical contents equivalent.

**Dependencies:** Existing dirty-concept tracking, P1-39 atomic replacement, checkpoint regression tests, and idle runtime before release verification.

**Done when:** Zero/nine/ten/eleven/twenty-item and interrupted passes preserve all intended queue/canonical changes; new concepts, restoration, duplicate evidence, and all-deferred cases are covered; unrelated concept bytes/mtimes stay unchanged; measured cycle time improves with identical reviewed content and unchanged failure handling.

**Source:** [throughput review](processing-throughput-review-2026-10-12.md), `processors/pipeline.py:565`, `:638`, `:917`.

**Implementation:** Final partial batches now reuse dirty-concept persistence; empty or fully checkpointed passes skip the redundant final queue save. Model inputs, decision order, thresholds, and validators are unchanged. Regression coverage exercises zero/nine/ten/eleven/twenty proposals across accept/defer/reject/new/restored/duplicate evidence paths and checks unchanged bytes/mtimes; the existing interruption test retains ten-item recovery coverage.

**Verification:** Full release gate passed with 127 tests, Ruff, published-artifact validation, and zero Astro diagnostics. Reviewed YAML hashes and published corpus content (excluding generation timestamp) remained identical. A temporary-copy ten-proposal all-deferred replay with stubbed model calls took 47.63s before and 28.08s after (19.55s saved), with identical input, queue (excluding attempt times), and semantic-concept hashes. Single before/after observation; live model-cycle timing remains unmeasured.

### P1-45 — Evaluate boundary-aware retries with durable provenance

**Status:** Planned (2026-10-12); quality benefit not yet established.

**Why:** Codex retries see neither their prior deterministic failure nor the caption-unit boundaries enforced after selection. The queue contains 149 boundary-related deferrals; one deferred proposal has 135 attempts. Queue regeneration also omits adjudication provenance.

**Work:** Preserve provenance/fingerprints across rebuilds; provide exact caption units and prior failure feedback to a versioned repair prompt; require a fresh semantic decision and every existing validator. Schedule unchanged failures visibly without endless immediate repeats or permanent abandonment.

**Dependencies:** P1-34 stratified quality benchmark, P1-38 actual-proposal fairness, shared boundary assessment, existing model/profile, and private audit contract.

**Done when:** Fixed-sample evaluation shows fewer repeated failures without worse judged entailment, identity, excerpt, or boundary quality; unsupported/dispersed/overlong cases remain blocked; model provenance survives regeneration; no automatic timestamp expansion or weaker acceptance threshold is introduced. Eventual retry coverage remains explicit.

**Source:** [throughput review](processing-throughput-review-2026-10-12.md), `processors/pipeline.py:413`, `:441`, `:727`, `:785`, `processors/codex_engine.py:276`.

### P1-46 — Reduce no-change cycle overhead and evaluate cached-only capacity

**Status:** Planned (2026-10-12); runtime and scheduler unchanged.

**Why:** The latest no-extraction cycle spent 33.1s rebuilding the queue. The daily task checks ten proposals; increasing attempts alone does not resolve low-yield repeated deferrals.

**Work:** Fingerprint candidate inputs/schema before skipping redundant queue regeneration, preserve all provenance, then measure a bounded sequential cached-only workload with the existing model and quality gates. Consider greater capacity only after retry/selection improvements are evaluated.

**Dependencies:** P1-44, P1-38, P1-45/P1-34 quality evidence, P1-16 stage limits, shared per-KB lock, daily token budget, and operator choice of compute schedule.

**Done when:** Unchanged candidate state safely avoids regeneration; changed/new/removed inputs invalidate it; replay measures supported final decisions per time/token alongside quality and source fairness; larger batches retain bounded worst-case runtime/checkpoints and safe publication failure handling. Acquisition pacing and source-policy controls remain unchanged.

**Source:** [throughput review](processing-throughput-review-2026-10-12.md), `scripts/run-cp.py:219`, `:344`, `:371`.

### P1-47 — Record monitor history independently of browser polling

**Status:** Complete (2026-10-12). Full release gate passed: 133 Python tests, five Node chart tests, Ruff, reviewed/published validation, and Astro diagnostics/build. Restarted idle monitor rendered all 11 graphs with line paths and honest missing-history labels; saved observations survive refresh.

**Why:** Seven-day graphs showed one point because the monitor recorded changes only when a browser polled its status API. Scheduled processing without an open page produced no history. Charts also used observation indexes and a zero-based scale that concealed small count changes.

**Work:** October 13 readability follow-up enlarges axis labels from 10 to 18 SVG pixels, darkens their text, emphasizes latest counts at 18 CSS pixels, and expands plot margins to avoid clipping. Source: user feedback and the 2026-10-13 session log; nine Node tests and a read-only browser preview pass. Production monitor reloaded between cycles on October 13; live labels are 18px and fit their cards.  Record private count observations on inventory-ledger writes; make the monitor a read-only history consumer that reloads each refresh; recover only real latest-run before/after observations; render elapsed time across seven days, step changes, useful value ranges, and explicit missing-history labels.

**Dependencies:** P1-28 inventory ledger, existing per-KB write ownership/atomic replacement, P1-40 monitor telemetry, and local-only history privacy.

**Done when:** Scheduled/CLI ledger writes record observations without a browser; repeated unchanged counts produce a visible flat line; restarts retain observations; pruning preserves a boundary anchor and seven-day endpoints under the 1,000-observation cap; absent days are labeled rather than invented; Python/Node tests, release gate, and the restarted live monitor pass. History errors warn without stopping knowledge processing or overwriting an unreadable history file.

**Source:** User-reported single-point graphs; `docs/Session Logs/2026-10-12-12.md` (12:31 onward), `processors/bucket_history.py`, `processors/inventory.py`, `scripts/monitor-history.mjs`, and `scripts/processor-monitor.mjs`.

### P1-48 — Preserve decisions for colliding extraction candidate IDs

**Status:** Complete (2026-10-14). Both pre-cycle and final post-cycle release gates passed; live queue preservation and changed next-batch selection verified.

**Why:** `build_review_queue` indexed only video ID and candidate ID. Distinct proposals sharing an extraction ID overwrite each other in that index; rebuilding resets accepted/deferred decisions and attempt counters, causing the same ten proposals to return on every cycle with no new published evidence.

**Work:** Match video ID, candidate ID, and normalized content hash; retain unchanged decisions, attempts, provenance, and manual history independently. Reset genuinely changed content to pending. Order bounded adjudication by fewest attempts then oldest attempt so surviving deferrals rotate behind untouched work.

**Dependencies:** P1-28 reviewed queue, P1-38 retry fairness, per-KB lock, and existing source/semantic validators.

**Done when:** Duplicate-ID proposals retain separate accepted/rejected/deferred metadata across repeated rebuilds; changed proposals require fresh review; untouched work outranks repeatedly deferred work without permanently excluding retries; actual queue replay, Python/Node tests, Ruff, full release gate, and local backlog verification pass. Never reconstruct erased decisions from logs or published evidence.

**Source:** User report of repetitive zero-growth cycles; `docs/Session Logs/2026-10-13-23.md`, `processors/pipeline.py`, `tests/test_pipeline.py`.

**Evidence:** Both locked rebuilds preserved all 6,934 queue records, including 12 repeated video/candidate IDs. The normal ten-candidate cycle accepted six and deferred four, adding two concepts and three evidence moments. All ten decisions, attempts, and provenance survived its queue rebuild; the next ten within the same pool are different proposals and none of the six accepted proposals is eligible. Full release gate passed 134 Python tests, nine Node tests, Ruff, validation/publish checks, and zero-diagnostic Astro build (586 pages after the controlled cycle). Published corpus: 346 concepts, 210 videos, 1,879 evidence moments. Logs: `docs/Session Logs/2026-10-13-23.md` and `docs/Session Logs/2026-10-14-00.md`.

### P1-49 — Correct sampled published-content scope, citations, and repetition

**Status:** Complete (2026-10-14); targeted and expanded repairs passed the final release gate: 142 Python tests, nine Node tests, Ruff, reviewed/public validation, and zero-diagnostic Astro build. Fifteen concept files were directly corrected; forty evidence editorial actions are archived. Broader boundary/semantic quality work remains under P1-14/P1-33/P1-34.

**Why:** The post-collision spot check found an unqualified forearm-drive definition based on penhold-specific advice, a half-long definition missing near-end-line depth, a ready-position excerpt containing a clause outside its cited segment IDs/window, three exact duplicate-citation pairs plus overlapping repeats, and deterministic summaries containing adjudication rationale. The defensive-block claim is supported, but its far/beginner facets are not established by the selected passage. These are public-content defects even though structural validation passes.

**Work:** Correct the definitions with supported qualifiers; trim or complete the ready-position citation; review and consolidate exact/overlapping duplicate source moments without losing provenance or merging distinct claims; remove unsupported facets or provide reviewed support; rewrite the affected summaries for readers. Add regression cases for exact evidence duplication, required claim qualifiers, and support clauses outside cited IDs; carry broader quality gates into P1-33/P1-34.

**Dependencies:** Completed P1-48 queue identity repair, P1-03 moment deduplication, P1-33 summary quality, P1-34 semantic-quality benchmark, and the per-KB lock/idle release gate before canonical writes.

**Done when:** Findings F1–F5 in the report are resolved in reviewed YAML, excerpts are fully supported by their selected IDs, duplicate moments are consolidated with editorial history retained, visual statuses stay honest, unsupported facets are corrected, summaries contain no review scaffolding, and full release/local-route verification passes. Do not treat this small sample as a whole-corpus certification.

**Source:** [Affected-content spot check](affected-content-spot-check-2026-10-14.md), `docs/Session Logs/2026-10-14-00.md`; five published concepts, 17 evidence records compared with exact caption rows and adjacent context. Report F1–F5 supplies IDs, timestamps, and correction targets.

**Implementation evidence:** Expanded review covered all 12 colliding ID groups and 13 public exact-citation duplicate groups. Two outgoing-shot citations are quarantined, and the configured model rejected their proposal on replay. Four complete backhand-serve windows replace fragment-only citations; distinct claims are retained. Editorial archive preserves superseded records/article fields. Incorporation and validation prevent exact repeats while preserving distinct visual windows; prompt 1.1.1 and correction advice strengthen semantic review (the audited mismatch replay retains its actual 1.1.0 provenance). Summary fallback excludes detected review rationale and fingerprints its reviewed definition. See report F6/F7 and session logs.

### P2-01 — Add public-artifact allowlisting and secret scanning

Reject unexpected files under `app/public/data/`; scan for raw transcript/media paths, credentials, cookies, audit responses, and secret-like strings before deployment. Audit the 27 currently tracked `data/manifests/` files and remove private budget/summary audit state from version control unless a file has a documented sanitized-public purpose.

### P2-02 — Reduce generated-data duplication

Keep one canonical publish location and copy it during the Astro build, or enforce byte-for-byte equality with a documented reason for tracking both copies.

### P2-03 — Pin CI actions and Python dependencies

Pin GitHub Actions to reviewed commit SHAs, add a reproducible Python lock/constraints file, and keep the existing Node lockfile authoritative.

### P2-04 — Reduce duplicate CI/deploy work

Use a reusable validation workflow or avoid repeating all tests/builds in both CI and deployment when the same commit artifact is already verified.

### P2-05 — Add privacy-enhanced/click-to-load embeds

Evaluate `youtube-nocookie.com`, click-to-load players, consent behavior, and a privacy notice. Keep the direct YouTube fallback link.

### P2-06 — Use deterministic TOC inputs before optional LLM chapters

Prefer creator chapters and transcript structure heuristics first. Consider LLM chapter proposals only during extraction/review, never as a required build-time call; validate all proposals against timestamps and source text. Keep the current evidence-derived TOC as the zero-token fallback, and treat creator chapter labels as source metadata rather than new knowledge claims.

**Done when:** creator chapters can be shown when available, deterministic pause/keyword grouping can provide secondary navigation when chapters are absent, and every generated section still passes the permanent route, anchor, ordering, timestamp, and public-data validation checks from P0-06. See `docs/toc-automation-review.md`.

### P2-07 — Add model-cost and extraction provenance reporting

Record model, reasoning level, input/output usage, prompt/schema versions, and candidate hash for each extraction job. Keep the lowest-cost model supported by the installed CLI (`gpt-5.6-luna`) as the default unless a benchmark justifies escalation.

### P2-08 — Add source-availability monitoring

Periodically check public/embedding status and display a neutral unavailable state. Never bypass a deleted, private, or embedding-disabled source.

### P2-09 — Add graph quality reporting

Track relation counts, concepts with no outgoing relations, cross-listed concepts, prerequisite cycles, single-source concepts, and relation-review coverage. The 2026-08-12 corpus has 466 concepts with no outgoing relation, including all 460 automatically created concepts, so an overall connectedness signal is not enough to describe local graph quality.

## Deferred by design

### P1-03 follow-up — rank concept evidence moments by relevance

**Status:** Complete (2026-07-20).

**Finding:** Concept pages exposed all supporting moments in processing order, making the strongest examples harder to find as evidence volume grew.

**Acceptance:** Apply a deterministic, review-grounded relevance ranking; show the internal numeric score only in local development; keep production ordering useful without publishing internal scoring details; display no more than the top 20 moments per concept and no more than 5 in each of the four evidence subsections.

**Evidence:** `app/src/lib/evidenceRelevance.ts`, the concept page and evidence components, and the 2026-07-20 session log. Astro build passed with 0 diagnostics.

### P1-16 hardening — clarify stage failures and monitor retries

**Status:** Complete (2026-07-20).

**Finding:** A `process-pending` child returned exit 1, but the orchestrator recorded only `cached triage failed: 1`; child output was not captured.

**Acceptance:** Capture bounded stdout/stderr per stage, record an explicit failed outcome/reason, and expose a consecutive-failure retry count that resets after success.

**Evidence:** `scripts/run-cp.py`, `scripts/processor-monitor.mjs`, and the 2026-07-20 session log.

### P1-18 — Audit atlas parent assignments

**Status:** Complete (2026-07-21); the full 371-concept navigation audit corrected eight additional misleading assignments.

**Audit update:** The 2026-07-21 pass corrected `Close-step`, `Backhand system body-led ripping`, `Flat-hit swing size control`, `Open shoulder and pivot for forehand transition`, `Post-shot recovery to ready position`, `Rhythm, spacing, and recovery for backhand rip`, `Forearm position relative to the elbow`, and `Push-flick close-distance control`. Reviewed remaining serve/receive, flick/receive, and shared-mechanics placements were retained where the evidence supported them. See `docs/concept-navigation-audit-2026-07-21.md`.

**Finding:** `Hop step` was listed under Backhand loop even though its evidence describes a footwork adjustment between strokes. `Preparation stroke and backswing for backhand serve` was listed under Serve receive despite describing serve mechanics.

**Completed:** Moved `Hop step` to Fundamentals → Footwork and spacing, and moved the backhand-serve preparation concept to Serve → Serve mechanics. The summary-aware pass also moved `Definition of a good shot`, `Defense is crucial`, and `Accurate foot placement and balance` out of specific shot/strategy placements into shared fundamentals or strategy; moved `Self-review through recording` to Training; and moved `Aggressive push only against weak spin`, `Push-flick timing and contact`, and `Forehand backspin receive` to the push/serve-receive paths supported by their summaries. Reviewed the remaining obvious serve/receive and flick/receive label conflicts; the remaining receive placements describe incoming-ball or receive-shot decisions.

**Done when:** every atlas placement is defensible from the concept label, definition, evidence summary, and facets, with navigation validation included in the publication checks. **Evidence:** full 371-concept audit report in `docs/concept-navigation-audit-2026-07-21.md` and release-gate verification on 2026-07-21.

- Public offline video hosting or transcoded mirrors without explicit permission/licensing.
- Another large scrape before the pending queue, quotation audit, and visual-review queue are under control.
- LLM-generated TOCs during every site build.
- Recreating YouTube’s browsing or playback experience.

## Recommended execution sequence

1. P0-08, P0-09, and P0-10 — retain the completed Codex semantic gate, focused transcript support, and exact timestamp-envelope checks.
2. P0-01 through P0-07 — retain quotation, acquisition, freshness, takedown, link, and public/private protections while remediation runs.
3. P1-34 and P1-30 — drain legacy candidates through bounded Codex passes, build the accuracy benchmark, and retain optional human advice/override tooling.
4. P1-32, P1-33, and P1-35 — reconcile concept identity/taxonomy/navigation/relationships, replace fallback summaries and confidence-led evidence ordering, and make planning coverage self-validating.
5. P1-01, P1-03, P1-04, P1-05, P1-06, P1-07, and P1-14 — improve visuals, moment usefulness, generated quality truth, diversity, hierarchy, and caption boundaries.
6. P1-08 through P1-12, P1-16, and P1-17 — harden private continuity, deployment paths, encoding, orchestration, and quotation regression protection.
7. Continue P1-28/P1-31 inventory processing through the Codex-first gate without starting an unbounded scrape; then complete P2 hardening and scale work.

## Completed work not to re-open as backlog

- Per-video detail routes with linear chronological TOCs.
- Shared deterministic TOC builder and reusable `VideoToc` component.
- Responsive evidence-row action layout.
- Correct global “Knowledge bases” navigation target.
- Low-cost `gpt-5.6-luna` default profile supported by the installed CLI.
- Public/private data boundary and publish-copy parity checks.
- Local-only progress, pipeline, and recent-additions pages.
- Local-only dashboard management index with full-width, non-overlapping workspace rows.
- Per-video contents pages now include reviewed concept summaries before the chronological moment list.
- Concept articles expose the reviewed definition in an explicitly labeled Summary section before their evidence library.
- The original 73 editorial concepts received direct `evidence_summary` paragraphs. This does not cover the later 460 automatically created concepts, whose deterministic fallback summaries remain open under P1-33.
- Deterministic cleanup of transcript-reporting leads from visible moment titles.

### P1-19  Separate discovery inventory from configured batch history

**Status:** Superseded by P1-28 after runtime-history clarification (2026-08-05).

**Finding:** The original review treated the configured entries as the controlled live workset. The later implementation and documentation show that these entries are accumulated controlled-batch history: after exhausting them, `run-cp.py` continued automatically through highest-viewed unseen discovery entries without appending those videos to `sources.yaml`. The actual workset is generated per run and stored in private manifest fields. A separate bug in `scripts/run-cp.py` also allowed the cp report path to be overwritten by a discovery manifest path, leaving stale monitor reporting.

**Acceptance:** Retain configured entries as provenance, preserve `cp.latest.json` as the authoritative latest-run manifest, and implement the full-inventory eligibility/completion ledger and generated-workset reporting defined by P1-28.

### P1-20  Make sleep/network interruption cleanup bounded on Windows

**Status:** Implementation complete; production monitor restart/runtime verification pending (2026-07-21).

**Finding:** After a sleep/resume interruption, the monitor's SIGTERM stopped the cp parent but left nested discovery workers running. A GlobalTTStudio discovery worker also remained in a yt-dlp retry state for approximately 100 minutes after an access-violation/connection-aborted warning.

**Acceptance:** Stop terminates the verified Windows process tree; discovery and ingest have bounded per-stage/per-request timeouts; the monitor records an explicit timeout/interrupted outcome and leaves no processor descendants running. Implementation is present in `scripts/processor-monitor.mjs` and `scripts/run-cp.py`; a forced timeout smoke test passed.
# Automatic new-concept promotion is now implemented: high-confidence explicit `new` candidates with valid evidence can create canonical YAML, while ambiguous and duplicate candidates remain deferred. `process-pending --retry-deferred` backfills previously processed videos.

### P1-21 — Expose serve-type hierarchy in the atlas

**Status:** Implemented (2026-07-21).

**Finding:** Generic Serve sections existed, but named serve families were not visible as navigation branches, making Hook, Pendulum, and Reverse Pendulum material difficult to browse by type. Backhand serve is an execution-side/mechanics category rather than a named serve family.

**Acceptance:** Add a Serve types branch with Forehand serves and Backhand serves parent groups; place named serve-family children and related existing concepts beneath the supported parent; preserve generic mechanics, spin, placement, and third-ball sections as shared cross-links; do not invent unsupported concepts or evidence.

**Evidence:** `config/kbs/table-tennis/navigation.yaml` and the 2026-07-21 session log. Full site build and navigation validation remain required after this change.

**Audit note:** The first grouping pass over-associated generic sidespin/disguise concepts with Pendulum and Reverse Pendulum. Those links were removed; Pendulum remains empty until direct reviewed evidence is available, and Reverse Pendulum retains only the directly comparative backhand-serve concept.

### P1-22 — Cool down newly detected members-only videos

**Status:** Implemented (2026-07-21).

**Finding:** Known `members_only` configuration entries were excluded, but a video newly identified as members-only during ingestion was recorded as a generic failure and could be selected again on every cp cycle.

**Acceptance:** Classify members-only acquisition errors explicitly, record `availability: members_only` and a three-day `next_retry_at` in the private retry manifest, skip without counting the item as a batch failure during the cooldown, and exclude it from both configured and discovered cp selection until the cooldown expires.

**Evidence:** `processors/ingest.py`, `processors/cli.py`, `scripts/run-cp.py`, and the 2026-07-21 session log. Targeted tests and Ruff passed.

### P1-23 — Preserve base-language caption coverage with regional fallback

**Status:** Implemented (2026-08-04).

**Finding:** The ingest default correctly requests `en` and succeeds for many videos, but `youtube-transcript-api` performs exact language matching. Videos exposing only manually created `en-US` tracks were rejected even though `en-US` is the same source language; `en` listed only under translation languages was not a usable original track.

**Acceptance:** Keep exact configured language priorities first; when an exact track is absent, select a same-base regional source track deterministically for both transcript adapters. Read the default priority from the KB configuration, preserve explicit `--languages` overrides, reject unrelated languages, and cover the behavior with offline tests.

**Evidence:** `processors/ingest.py`, `processors/cli.py`, `tests/test_ingest.py`, and the 2026-08-04 session log. The fallback is source-track based and does not request or publish translated captions as if they were originals.

### P1-24 — Add task-manager-style resource telemetry to the processor monitor

**Status:** Implemented (2026-08-04).

**Finding:** The monitor's Resources panel first showed a long process list with cumulative CPU seconds and memory values but no current load context. Its initial telemetry revision then used whole-machine CPU/memory and every Python/Node process, which mixed this project with unrelated workstation services.

**Acceptance:** Identify the repository monitor, processes whose command or executable path belongs to the repository, and their descendants. Show only their aggregate current CPU, aggregate working-set memory, rolling histories, and process details; exclude unrelated machine processes and whole-machine totals; degrade clearly when the project snapshot is unavailable.

**Evidence:** `scripts/processor-monitor.mjs` and the 2026-08-04 and 2026-08-05 session logs. Live `/api/status` and monitor-page checks passed after safe service restarts.

### P1-25 — Show the next processor start countdown

**Status:** Complete (2026-10-13). Reloaded the idle production monitor and verified live cooldown restoration, controls, larger chart labels, and full-height output.

**Why:** The monitor API retained `nextRunAt`, but the Run State panel originally showed only a fixed local timestamp. A follow-up found that changing the cooldown while the loop was already active updated the stored value but did not rebuild the existing idle timer, leaving the displayed next-run time unchanged.

**Done when:** Show a live countdown to the next process start alongside the exact local time, label the configurable delay as “Cooldown between runs (minutes),” and use Start loop only to start processing and Enter in the cooldown field to save/apply the delay independently. Persist the last successfully applied cooldown per KB across page and service restarts; disable Start while the loop or child is active and Stop when both are stopped. Applying a cooldown while idle must immediately rebuild the timer and update `nextRunAt`; applying it during a run must preserve that run and use the new delay after completion. Show the active process start time while a cycle is running and retain the stopped/pending states.

**Dependencies:** Existing monitor loop/child state, per-KB private settings, and P1-24 telemetry. Layout acceptance: Fill the active-output article’s available height with its scrollable black output area. Keep the Run State card at a stable height across cooldown, active, stopped, and failure labels. Reserve equal line boxes for the schedule and latest-outcome text, use tabular time numerals, and contain unusually long messages within their rows instead of shifting panels below. On wide screens, give active output exactly half of the main workspace and arrange route lockout, run state, project resources, and monitor events in a two-by-two grid in the other half; collapse cleanly on narrower screens.

**Evidence:** `scripts/processor-monitor.mjs` and the 2026-08-04 and 2026-08-05 session logs. `node --check` passed; live API checks verified active-run deferral and exact idle rescheduling. Browser measurements verified the Run State card remains 158 px tall with equal status rows and consistent text metrics. A separate idle monitor verified the 50/50 main grid, two-by-two operations grid, and narrow-screen stack without starting a processor cycle.

**Work:** Cooldown is saved atomically in ignored per-KB `local-monitor-settings.json`; Enter applies without starting a stopped loop. Start/Stop reflect loop and child state, including shutdown. Focused controls tests cover persistence, validation, rescheduling, active/stopped behavior, restored input, and Enter. Production service reloaded between cycles and verified live; see `docs/Session Logs/2026-10-13-11.md`.

### P1-26 — Visualize Source summary state relationships

**Status:** Implemented (2026-08-04).

**Finding:** The Source summary table mixed video stages, candidate decisions, public knowledge outputs, and visual-review counts in one wide row. Percentages identified denominators, but the table did not make sequential stages, exclusion branches, review branches, or differing units visually clear. The first graph iteration also labeled all 690 videos outside the current configuration as “Not selected,” obscuring that 589 were already in the public corpus.

**Acceptance:** Lead with the user-facing content split: 838 known source videos = 729 on the site + 109 not on the site, with 101 not published and 8 members-only. Define “on the site” as providing at least one approved moment. Preserve configured batch-history stages, discovery-continuation provenance, fully-reviewed versus review-backlog split, full-corpus candidate decisions, detailed source metrics, and separate visual-verification counts as explicitly labeled operator detail. Make clear that `sources.yaml` entries are accumulated batch history and that `run-cp.py` generates the live workset per run.

**Evidence:** `app/src/pages/progress.astro`, `app/src/styles/global.css`, `docs/source-video-progress.md`, and the 2026-08-04 22:00 and 2026-08-05 00:00 session logs. Astro diagnostics/build passed with 0 findings. Live local verification confirmed the primary 838 = 729 on-site + 109 not-on-site content split, its 101 not-published + 8 members-only breakdown, and the subordinate 148 configured-batch-history + 690 discovery-continuation provenance split render clearly in dark mode.

### P1-27 — Assign ownership and completion guidance to outstanding work

**Status:** Implemented (2026-08-04).

**Finding:** The progress page named outstanding work and recommended broad actions, but it did not identify which operational role should act or describe the concrete review, curation, rights, validation, and publishing steps needed to finish each state.

**Acceptance:** Add an explicit owner and actionable completion procedure to every Outstanding work row. Distinguish editorial review, visual review, source curation, and access/rights decisions, and mirror the guidance in the source-progress documentation.

**Evidence:** `app/src/pages/progress.astro`, `docs/source-video-progress.md`, and the 2026-08-04 22:00 session log.

### P1-28 — Complete every eligible video in the three-source inventory

**Status:** In progress — fair processing and Codex-first adjudication are implemented; the corpus-wide decision backlog is still draining (updated 2026-09-10).

**Finding:** Automatic discovery-catalog continuation already processed hundreds of videos beyond the 148 entries accumulated in `sources.yaml`, so replacing a supposedly manual workset is not the required change. The remaining gap is draining final Codex decisions across the durable 838-video inventory. After quarantine, 43 eligible videos are complete, 709 have automated work remaining, and 86 are excluded; the safe public corpus contains 51 videos.

**Acceptance:** Implement the phased plan in `docs/exhaustive-source-completion-plan-2026-08-05.md`: build a private full-inventory ledger; generate run batches from incomplete eligible states; define strict completion; adjudicate unclear candidates with Codex while retaining optional human advice/override; classify the 101 non-public entries; and report the actual latest selected batch from `cp.latest.json`. Preserve source-grounding, visual-review honesty, private-data boundaries, pacing, cooldowns, budget guards, and the route-wide block circuit breaker.

**Dependencies:** Existing discovery manifests, ingest retry state, language fallback, Codex budget, review queue, canonical validation, P1-16 orchestration, P1-22 members-only cooldown, and P1-23 regional caption fallback.

**Done when:** All 838 inventory entries have a durable eligibility result; every eligible video is fully processed with final Codex candidate decisions and incorporated accepted evidence; automated deferrals remain visible and retryable; no eligible video remains generically pending, waiting, or unclassified; exclusion reasons are specific; progress and monitor views distinguish actual completion from work remaining; and the full release gate passes while the processor is idle. Optional human advice does not define completion.

**Implementation evidence:** `processors/inventory.py` builds the ignored private 838-video ledger; `scripts/run-cp.py` records and executes ledger-selected extraction, Codex-adjudication, and acquisition batches; `process-pending` records model/provenance and keeps uncertainty in the automated deferred queue; progress and monitor views consume ledger and latest-batch summaries. The monitor now exposes the current ten-item batch, the eligible retry candidates in the selected source-balanced video pool, and the full adjudication backlog (pending, deferred, and human-advice proposals admitted to the pass) in live progress telemetry, plus a bounded change-only history of inventory and candidate-decision bucket counts retained privately for at least seven days. The monitor renders one native SVG history graph for every inventory and candidate bucket, alongside exact timestamped snapshots. The initial ledger classified the full 109-video not-on-site group as 23 processed videos with no approved moments, 85 members-only videos, and one repeatedly subtitle-disabled public video. This corrects the earlier configuration-only count of eight members-only entries.

**Evidence:** `docs/exhaustive-source-completion-plan-2026-08-05.md`, `processors/inventory.py`, `scripts/run-cp.py`, `scripts/processor-monitor.mjs`, `app/src/pages/progress.astro`, `tests/test_inventory.py`, and the 2026-08-05 session log.

### P1-29 — Start both local services from the Windows launcher

**Status:** Implemented (2026-08-05; lifecycle hardening 2026-08-30).

**Finding:** The root `start.bat` launched the Astro development server but did not start the processor monitor, so the site was available on port 4321 while the expected monitor remained unavailable on port 4322.

**Acceptance:** Stop verified existing project services before startup, start the processor monitor before Astro, verify the new monitor process owns port 4322 and its root becomes ready, retain Astro in the foreground for visible diagnostics, and clean up both services on Ctrl+C without touching unrelated processes.

**Evidence:** `start.bat`, `scripts/start-local.ps1`, `README.md`, `docs/operations.md`, and the 2026-08-30 session log.

### P1-30 — Provide bounded optional human advice and overrides

**Status:** Implemented (2026-08-05).

**Finding:** Operators sometimes want to augment a Codex decision with domain advice or explicitly override it. They need a focused interface combining the candidate claim, exact cited captions, nearby transcript context, canonical concept choices, and an audited decision without making human action the normal queue.

**Acceptance:** Keep a local-only advisory workspace that shows no more than five selected candidates at once; explains that advice/override is optional; distinguishes cited segments from context; exposes boundary flags and Codex rationale; supports accept, reject, and keep-for-later overrides; requires a useful note and confirmations; preserves audit history; never verifies visual evidence; and refuses canonical writes while the processor loop or a cycle is active.

**Dependencies:** P1-14 caption boundaries, P1-28 Codex adjudication state, normalized transcript segment IDs, canonical concept validation, and the local processor monitor.

**Evidence:** `app/src/pages/human-review.astro`, `processors/human_review.py`, guarded monitor endpoints in `scripts/processor-monitor.mjs`, `tests/test_human_review.py`, and the 2026-08-05 session log. The local API returned five of the live queue's candidates with exact context; focused tests, Ruff, and Astro diagnostics/build passed. The completion follow-up added fair source rotation and an explicitly confirmed create-new action so genuinely distinct candidates can reach a final canonical state without hand-editing YAML.

### P1-31 — Balance exhaustive processing across all registered sources

**Status:** Implemented (2026-08-05).

**Finding:** The full-inventory ledger sorted records by source ID and then selected the first 50 adjudication videos. This repeatedly advanced Free Coach Brad Han while Global TT Studio and PingSunday/Xiaohan remained unchanged, even though all three had substantial automated work.

**Acceptance:** Select small extraction, Codex-adjudication, and acquisition batches by deterministic round-robin over every source that currently has eligible work; retain view-count priority within each source; record `source_id` in every manifest assignment; use the same fair source rotation for optional five-item advisory batches; and report fully processed eligible videos separately from automated work remaining.

**Dependencies:** P1-28 inventory ledger and run worksets, P1-30 human-review workspace, source provenance in discovery catalogs, and the existing non-overlap/lock controls.

**Evidence:** `processors/inventory.py`, `processors/human_review.py`, `scripts/processor-monitor.mjs`, `app/src/pages/progress.astro`, `tests/test_inventory.py`, and the 2026-08-05 session log. Against the current ledger, the next 50-video adjudication selection is 17 Free Coach Brad Han, 17 Global TT Studio, and 16 PingSunday/Xiaohan rather than 50 from one source.

### P2-10 — Prototype an authorized media-download and ASR transcript route

**Status:** In progress — one-video smoke test implemented (2026-07-21); not enabled in `cp`, the monitor, or the scheduler.

**Finding:** Caption-first ingestion cannot process videos with no usable captions and cannot independently verify caption accuracy. The current optional audio fallback is temporary and does not yet define a full media retention, video-to-audio, ASR provenance, comparison, or review workflow.

**Acceptance:** Implement the separate route described in `docs/experimental-media-asr-route-plan-2026-07-21.md`: storage gates; bounded private video download retained by default for the initial experiment; audio extraction; pinned local ASR with stable private segment IDs; caption-vs-ASR comparison; explicit transcript-origin values distinguishing `local_asr` from `youtube_manual` and `youtube_generated`; and validation that prevents unreviewed ASR evidence or media from reaching public output. Start with a one-video smoke test before expanding to the 10–20-video gold set. Add cleanup previews and deletion/retention controls later, then make an explicit go/no-go decision before any production enablement.

**Dependencies:** P0-02, P0-04, P0-07, P1-14, and an operator-approved acquisition/cleanup policy. Expiry tracking is intentionally deferred for now. This route must remain separate from normal caption ingestion and unattended processing.

**Evidence:** `processors/ingest.py`, `processors/cli.py`, `processors/models.py`, `tests/test_ingest.py`, and `docs/experimental-media-asr-route-plan-2026-07-21.md`. The one-video route retains private media and writes local-ASR provenance; caption comparison, review-state validation, cleanup controls, and the 10–20-video evaluation remain incomplete.

### P2-11 — Define opponent-facing tactical parity

**Status:** Planned (2026-09-19); parity baseline documented, implementation not started.

**Why:** The published corpus can browse opponent-related concepts and generic concept relations, but it has no trustworthy way to represent opponent cues, directional tactics, shot sequences, or opponent-specific notes. A generic relation arrow is not an opponent movement arrow.

**Work:** Decide the smallest source-grounded opponent vocabulary and data shape; distinguish concept navigation from tactical direction; define whether structured opponent facets, sequence maps, and local match notes belong in this product or a separate private tool.

**Dependencies:** P1-32 concept/graph curation, P1-43 relation-vocabulary policy, and a separate privacy decision for any opponent-specific records.

**Done when:** The parity scope and relation vocabulary are accepted, generic and tactical arrows have distinct semantics, and a reviewed example demonstrates the intended UI without inventing opponent behavior. Do not add opponent tracking or match history until the privacy boundary is explicit.

**Evidence:** `docs/opponent-feature-parity-2026-09-19.md`, `app/src/components/ConceptConnections.astro`, `app/src/types.ts`, and the current published corpus.

**Redesign release checkpoint (2026-10-16 10:52 EEST), P1-50/P1-51:** Full release gate passed after grip polarity correction (245 Python tests, nine monitor tests, Ruff, zero Astro diagnostics, 635 pages); affected live route verified. Strict audit remains incomplete: 81/377 articles, 601/4473 units supported; 296 articles and 3872 units pending. Evidence: `media/audit-grip-polarity-release-2026-10-16-10.log`. Normal processing remains paused.


**P1-51 implementation benchmark (2026-10-16 14:27 EEST):** Zero-model difficulty-only plans, checked snapshot reuse, safe value-checked archives, explicit overlap-only pending review and separate private work queues implemented;87 focused tests and Ruff passed. Actual168-record/2.18MB archive path:old10.10–12.19s vs new3.66–3.69s, approximately3× faster. Twenty seeded scratch transactions preserved all history and averaged3.90s; no model calls or production content changes. Evidence [updated diagnosis](audit-throughput-diagnosis-2026-10-16.md), private media/throughput-benchmark-2026-10-16-14.json. These application measurements do not establish semantic throughput; real representative20article quality/token/runtime benchmark remains open, as does corpus clearance. Full post-application rebuild remains once per article; further dependency caching deferred pending evidence. Full release result recorded at the next checkpoint.

**P1-51 frozen20 first-pass checkpoint (2026-10-16 15:13 EEST):** User authorized full-audit continuation with GPT-6 Luna/high, starting with a frozen mixed20article/187unit benchmark. First pass37calls/798308processor tokens/811.03s; typed rating removalzero calls. Both actual frozen referent controls passed at Luna/high:unsupported rejected,supported retained;2calls/38646tokens/26.17s,not general accuracy proof. Final-primary review imported19 complete records; typed twentieth already approved. No application/publication yet; bounded five-case follow-up active. Preserve all20 outcomes,including false exclusions of valid placement-training and backspin stroke-phase evidence. Dependencies/gaps: typed exact-reviewed metadata correction, owned-source-context proposal/review, and safe restoration of rejected quarantines (current draft excludes quarantined units from correction). Acceptance: actual reviewed source IDs/timing only,complete before/after delta,archives,fresh primary proof,no automatic reinstatement or visual attestation. Measure repeated local CLI/import/corpus-loading delays separately; cause of environmental slowdown unproven. Evidence media/audit-benchmark20-*2026-10-16-14 files and[session](Session%20Logs/2026-10-16-15.md). Full corpus clearance remains92/377 pending further verified application;normal processing paused. Do not repeat an unchanged broad campaign or issue a new completion forecast.


**P1-51 operational reliability finding (2026-10-16 16:35), priorityP1:** Source:user-reported chat hang,[app/runtime evidence](chat-hang-investigation-2026-10-16.md). Status:diagnosis complete and finite-CLI operational mitigation documented;app-side rootcause unresolved. Dependencies:existing bounded CLI,per-KB lock,private checkpoint/log andexternal client routing. Acceptance:every auditworker exits at its cap;completion/running claims match process andsavedcheckpoint;no interactive prompt mistaken for active audit;all completedreviews survive resume;never bypass source/primary guards or reset corpus to recover UI. App-side follow-up requires evidence-backed vendor fix,not project cache deletion or unproved dependency changes. Independent OS-managed execution is deferred until restart-survival is requested. Full corpus audit remains103/377supported,274pending.

**P1-51/P1-34 saved-checkpoint continuation (2026-10-16 17:22 EEST):** User authorized finite CLI jobs at GPT-6 Luna/high. Saved twenty-article/180-unit cohort resumed without reset; resumed round20calls/439402tokens/408.08s plus bounded four-case follow-up8calls/179881tokens/159.58s. Complete twenty-record final primary review retained newly found missing-backhand qualifiers, hook-serve topic mismatch and false generic-sequence exclusion. Ten exact machine+primary-ready plans selected for application; ten remain blocked/disputed. Long-push wrist-flick condition and actual serve-target actors now preserved. Source ownership, typed metadata and rejected-quarantine restoration remain open under existing P1-51 dependencies; acceptance requires actual IDs/times, archived values, fresh complete primary and one idle batch release. No footage approval, normal processing paused. [Report and evidence](audit-continuation-2026-10-16-17.md); final release/counts recorded below when complete. No new forecast or unchanged broad retry.

**P1-51 next20 application checkpoint (2026-10-16 17:24 EEST):** Allten selected guarded applications exited0. Current113/377articles and834/4452units supported;264articles/3618units pending,zero structural/source-metadata/overlap findings. Five unsupported optionalratingsremoved separately. All20outcomes retained:tenapplied/tenblocked-disputed. Singlefullidlerelease passed274Python/nineNode tests,Ruff,zeroAstrodiagnostics/635pages;normalprocessingpaused. Fullcorpus acceptance remainsopen underP1-50/P1-51,not satisfiedby machineplans or thisbatch.




**P1-51/P1-34 finite six-article continuation (2026-10-16 17:38 EEST):** Fresh saved cohort completed12Luna/highcalls/266621tokens/254.64s;three guarded applications,three blocked/disputed. Current116/377articles,855/4452units supported;261articles/3597units pending;zero structural/source-metadata/overlap findings. Source:[six-article report](audit-continuation-six-2026-10-16-17.md). Existing dependencies:actual owned-context edits,typed metadata,explicit quarantine restoration. Additional P1-34 controls:obvious spelling normalization in paraphrases and explicit question/answer support despite an unfinished neighboring row;do not fix false acceptance by indiscriminate rejection. Acceptance:actual source roles/conditions preserved,all six outcomes retained,complete fresh primary,no forced machine overrides,full idle release and current localbacklog verified. Fullaudit remainsopen;normalprocessingpaused,nofootageapproval. Final release result follows.


**P1-51 six-article release checkpoint (2026-10-16 17:41 EEST):** Fullidle releasepassed274Python tests103.53s,nineNode tests,Ruff,reviewed/publicvalidation,zeroAstroerrors/warnings/635pages. Current116/377supported,261pending;nofootageapproval,normalprocessingpaused. Evidence media/audit-batch6-release-2026-10-16-17.log;[report](audit-continuation-six-2026-10-16-17.md). Currentplanningview rebuilt/localHTTPverified at finalsessioncheckpoint.
