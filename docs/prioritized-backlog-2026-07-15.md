# Prioritized project backlog — 2026-07-15

This is the consolidated backlog from the architecture review, content review, legal/platform review, transcript-quotation audit, TOC automation review, and public-to-private transition plan.

It is intentionally ordered. The project should complete the blocking and trust items before another large scrape or extraction batch.

## Current baseline

- 73 concepts, 50 published videos, and 1,118 published evidence items.
- Review queue: 625 items — 450 accepted, 174 pending, 1 rejected.
- Visual coverage: 0 `verified_visual_demo`, 485 `transcript_inferred`, 633 `not_visual`.
- 32 complete normalized transcript/excerpt matches; 38 high-ratio near-verbatim matches.
- 16 concepts have only one supporting source.
- Per-video detail pages and chronological TOCs are implemented.
- Python validation, Astro checks, production build, and published-artifact parity currently pass.

## Priority definitions

- **P0 — protect trust:** complete before expanding public content or running a large scrape.
- **P1 — improve the core product:** complete during the next focused content/product cycle.
- **P2 — harden and scale:** complete after the corpus is trustworthy and usable.
- **Deferred:** deliberately not part of the current milestone.

## P0 — protect trust before more scraping

### P0-01 — Rephrase direct transcript excerpts

**Owner area:** Editorial/content  
**Source:** `docs/content-quotation-audit-2026-07-15.md`  
**Why:** 32 excerpts are complete normalized matches and 38 have high contiguous overlap. The editorial `reason` fields are original, but the public `excerpt` field often presents source wording without a quotation marker.

**Work:**

- Rephrase the 20 highest-priority entries first.
- Rephrase the remaining high-ratio set.
- Resolve duplicated wording across concepts such as `forehand-loop`, `forehand-loop-swing-path`, `body-hand-synchronization`, and `serve-action-decomposition`.
- Add `excerpt_kind: editorial_summary|source_quote`; default new evidence to `editorial_summary`.

**Done when:** the audit reports no unmarked long verbatim excerpts, every intentional quote is short, visibly marked, attributed, and tied to original analysis.

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

## P1 — improve the core product

### P1-01 — Review the visual evidence queue

**Why:** there are 0 verified visual demonstrations. Transcript-inferred windows cannot support the strongest loopable-demo promise.

**Work:** review candidate windows, record exact start/end bounds and visual notes, and promote only confirmed footage to `verified_visual_demo` with manual selection metadata. Prioritize forehand-loop concepts first.

**Done when:** the UI distinguishes transcript evidence, proposed visual windows, and verified visual demonstrations; only the last category loops automatically.

### P1-02 — Process pending candidates before another large scrape

**Why:** 174 review items are pending. Nine published videos have only one concept in their TOC; eight of those have one published moment despite additional local candidates.

**Work:** review the pending candidates for the one-concept videos first, then clear the remaining queue in source batches. For `9OxcCPWI-k8`, five additional candidates are pending beyond `Backhand serve`.

**Done when:** every pending item is accepted, rejected, or explicitly deferred with a reason, and one-concept videos have been checked against their candidate set.

### P1-03 — Localize moments and collapse repetition

**Why:** evidence is concentrated and repetitive: 814 moments share repeated excerpt strings and some concepts have over 100 moments.

**Work:**

- Create a moment-specific summary from the cited segment rather than repeating a candidate definition.
- Add reviewed subtopics such as setup, timing, contact, acceleration, recovery, mistake, correction, and drill.
- Show representative moments first and collapse corroborating moments.
- Flag near-duplicate excerpts during extraction/review.

**Done when:** high-volume concepts remain readable and each visible moment explains what is unique about its timestamp.

### P1-04 — Generate progress and quality data instead of hand-maintaining it

**Why:** progress and quality pages/docs disagree with current counts (`174` pending vs older `68`; `1118` evidence vs older `1110`).

**Work:** emit a versioned `progress.json` and quality report from processor artifacts; render Astro and Markdown views from that data; include generation timestamp and explicit metric names.

**Done when:** README, progress, pipeline, source-progress, and quality reports cannot silently drift from the corpus manifest.

### P1-05 — Prioritize second-source coverage

**Why:** 16 concepts have only one supporting source, and the published channel mix is uneven.

**Work:** make source diversity a review metric and prioritize another channel/video for single-source concepts before adding more moments to already concentrated concepts.

**Done when:** the backlog reports distinct video and channel counts, and each single-source concept has a documented coverage decision or a second independent source.

### P1-06 — Add concept-specific evidence hierarchy

**Why:** generic evidence-type chapters do not adequately structure complex topics such as backhand serve mechanics or forehand-loop motion.

**Work:** add reviewed `subtopic_id`/section metadata and render nested sections such as preparation, contact, racket path, spin variation, deception, error, and drill.

**Done when:** a concept page’s hierarchy is driven by meaning, with generic evidence types retained as secondary labels.

### P1-07 — Resolve taxonomy placeholders

**Why:** seven leaf nodes currently have no concept content, including several push/block/flick leaves and Error correction.

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

## P2 — harden and scale

### P2-01 — Add public-artifact allowlisting and secret scanning

Reject unexpected files under `app/public/data/`; scan for raw transcript/media paths, credentials, cookies, audit responses, and secret-like strings before deployment.

### P2-02 — Reduce generated-data duplication

Keep one canonical publish location and copy it during the Astro build, or enforce byte-for-byte equality with a documented reason for tracking both copies.

### P2-03 — Pin CI actions and Python dependencies

Pin GitHub Actions to reviewed commit SHAs, add a reproducible Python lock/constraints file, and keep the existing Node lockfile authoritative.

### P2-04 — Reduce duplicate CI/deploy work

Use a reusable validation workflow or avoid repeating all tests/builds in both CI and deployment when the same commit artifact is already verified.

### P2-05 — Add privacy-enhanced/click-to-load embeds

Evaluate `youtube-nocookie.com`, click-to-load players, consent behavior, and a privacy notice. Keep the direct YouTube fallback link.

### P2-06 — Use deterministic TOC inputs before optional LLM chapters

Prefer creator chapters and transcript structure heuristics first. Consider LLM chapter proposals only during extraction/review, never as a required build-time call; validate all proposals against timestamps and source text.

### P2-07 — Add model-cost and extraction provenance reporting

Record model, reasoning level, input/output usage, prompt/schema versions, and candidate hash for each extraction job. Keep `gpt-5.4-mini` as the default unless a benchmark justifies escalation.

### P2-08 — Add source-availability monitoring

Periodically check public/embedding status and display a neutral unavailable state. Never bypass a deleted, private, or embedding-disabled source.

### P2-09 — Add graph quality reporting

Track relation counts, concepts with no outgoing relations, cross-listed concepts, prerequisite cycles, single-source concepts, and relation-review coverage. The current graph is connected, but some concepts still need semantic links.

## Deferred by design

- Public offline video hosting or transcoded mirrors without explicit permission/licensing.
- Another large scrape before the pending queue, quotation audit, and visual-review queue are under control.
- LLM-generated TOCs during every site build.
- Recreating YouTube’s browsing or playback experience.

## Recommended execution sequence

1. P0-01, P0-02, P0-03, and P0-04 — reduce quotation, acquisition, freshness, and takedown risk.
2. P0-05 and P0-06 — make the public contract and link integrity explicit.
3. P1-01 and P1-02 — verify visuals and process existing candidates before more ingestion.
4. P1-03, P1-04, and P1-05 — improve evidence usefulness, operational truth, and source diversity.
5. P1-06 through P1-09 — improve hierarchy and private continuity.
6. P2 hardening and scale work.

## Completed work not to re-open as backlog

- Per-video detail routes with linear chronological TOCs.
- Shared deterministic TOC builder and reusable `VideoToc` component.
- Responsive evidence-row action layout.
- Correct global “Knowledge bases” navigation target.
- Low-cost `gpt-5.4-mini` default profile.
- Public/private data boundary and publish-copy parity checks.
- Local-only progress, pipeline, and recent-additions pages.

