# Prioritized project backlog — 2026-07-15

This is the consolidated backlog from the architecture review, content review, legal/platform review, transcript-quotation audit, TOC automation review, and public-to-private transition plan.

It is intentionally ordered. The project should complete the blocking and trust items before another large scrape or extraction batch.

Last refreshed: 2026-07-16 11:07 EEST.

## Current baseline

- 73 concepts, 121 published videos, and 1,814 published evidence items.
- Review queue: 1,200 resolved items — 1,060 accepted, 139 deferred, and 1 rejected; no candidates remain pending.
- Visual coverage: 0 `verified_visual_demo`, 996 `transcript_inferred`, 788 `not_visual`.
- Repetition screen: 1,258 distinct excerpt strings; 426 exact repeated-excerpt groups cover 982 moments.
- 0 complete normalized transcript/excerpt matches; 0 high-ratio near-verbatim matches after the P0-01 editorial pass. A follow-up screen still finds 28 shorter partial overlaps for routine monitoring.
- 2 concepts have only one supporting source: `defensive-rhythm-variation` and `racket-contact-constraint-drill`.
- Per-video detail pages and chronological TOCs are implemented.
- Python validation, Astro checks, production build, and published-artifact parity currently pass.
- LLM tasks now use a private adjustable daily token budget with extraction, rephrase, and benchmark caps; exhausted work is deferred before Codex execution.

## Recent study reconciliation - 2026-07-16

The latest studies were checked against the backlog rather than left as standalone reports:

| Study or review | Findings carried into the backlog | Current item(s) |
| --- | --- | --- |
| `docs/daily-pipeline-automation-review-2026-07-16.md` | ChatGPT app shortcuts are not a runtime dependency, but unattended runs need a lock, idempotent workset, run manifest, exit classes, scheduler environment, and explicit human gates. | P1-16 (planned) |
| `docs/moment-boundary-analysis-study-2026-07-16.md` | Caption-derived moments can start/end mid-sentence or be too short; boundary flags, context separation, a gold set, and script-first/LLM-optional phases are required. | P1-14 |
| `docs/toc-automation-review.md` | TOCs should remain deterministic and build-time LLM-free; creator chapters and pause/keyword grouping are optional inputs, while anchors and timestamps need permanent validation. | P0-06, P2-06 |
| `docs/content-quotation-audit-2026-07-15.md` | Complete/high-ratio overlaps were cleared, but excerpt type, repeated-expression monitoring, and a regression validator remain needed. | P0-01 follow-up; new P1-17 |
| `docs/legal-review-youtube-2026-07-15.md` and `docs/youtube-knowledge-project-precedents-2026-07-15.md` | Public output must remain source-linked analysis; withdrawal, acquisition provenance, private-mode boundaries, and public-artifact checks remain prerequisites for expansion. | P0-02, P0-04, P0-05, P0-07, P1-08, P1-09 |
| `docs/project-review-2026-07-16-00.md` | The corpus is evidence-dense, visual verification is still zero, source diversity and empty leaves need attention, and generated status/encoding/URL checks should stay ahead of broad scraping. | P1-01, P1-03, P1-04, P1-05, P1-07, P1-10, P1-11, P1-12, P2-09 |

The numerical baseline above reflects the latest published artifacts, not the older snapshot values quoted in individual dated reviews. When a study and the current artifacts differ, the generated corpus and quality reports remain authoritative for counts.

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

## P1 — improve the core product

### P1-01 — Review the visual evidence queue

**Why:** there are 0 verified visual demonstrations. Transcript-inferred windows cannot support the strongest loopable-demo promise.

**Work:** review candidate windows, record exact start/end bounds and visual notes, and promote only confirmed footage to `verified_visual_demo` with manual selection metadata. Prioritize forehand-loop concepts first.

**Done when:** the UI distinguishes transcript evidence, proposed visual windows, and verified visual demonstrations; only the last category loops automatically.

### P1-02 — Process pending candidates before another large scrape

**Status:** Controlled expansion and cached queue triage are complete through batch 15 (2026-07-16). The `process-pending` command accepted 146 initial high-confidence matches and added 145 focused evidence moments; subsequent controlled batches accepted additional matches, including 23 candidates and 30 evidence moments from the latest two-public-video continuation. Four members-only entries were skipped. The current queue has 1,060 accepted, 139 deferred, and 1 rejected item, with no pending candidates. The formerly one-concept videos were checked: the new batch removed `push-spin-power-progression` from the single-source list.

**Why:** the queue had 174 pending items. Nine published videos had only one concept in their TOC; eight of those had additional local candidates that could be checked against existing concepts.

**Work:** review the pending candidates for the one-concept videos first, then clear the remaining queue in source batches. For `9OxcCPWI-k8`, five additional candidates are pending beyond `Backhand serve`.

**Done when:** every pending item is accepted, rejected, or explicitly deferred with a reason, and one-concept videos have been checked against their candidate set. **Evidence:** published corpus validates at 73 concepts, 121 videos, and 1,814 evidence moments; all 1,200 queue items have explicit decisions.

### P1-03 — Localize moments and collapse repetition

**Why:** evidence is concentrated and repetitive: 426 exact repeated-excerpt groups cover 982 moments, and some concepts have over 100 moments. `forehand-loop-swing-path` is the largest outlier at 132 moments.

**Work:**

- Create a moment-specific summary from the cited segment rather than repeating a candidate definition.
- Add reviewed subtopics such as setup, timing, contact, acceleration, recovery, mistake, correction, and drill.
- Show representative moments first and collapse corroborating moments.
- Flag near-duplicate excerpts during extraction/review.

**Done when:** high-volume concepts remain readable and each visible moment explains what is unique about its timestamp.

### P1-04 — Generate progress and quality data instead of hand-maintaining it

**Why:** progress and quality pages/docs still contain hand-maintained historical counts, even though the current processor artifacts now report no pending candidates, 1,814 evidence items, and 121 published videos.

**Work:** emit a versioned `progress.json` and quality report from processor artifacts; render Astro and Markdown views from that data; include generation timestamp and explicit metric names. The current local page now derives the GlobalTTStudio configured/eligible split from the corpus plus the explicit members-only set, labels the configured stage separately from eligibility, and shows denominator-aware percentages beside workflow-stage counts.

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

### P1-12 - Separate source-title attribution from display styling

**Why:** ten published source video titles contain promotional all-caps fragments, including `SUCKS`, `STOP`, `SMASH`, `FAST`, and one fully uppercase title. These are original YouTube metadata, not missed transcript rephrasing, but they dominate the visual hierarchy and can make the site feel like it is repeating promotional copy.

**Work:** retain the exact source title in provenance and source inventories, add an optional normalized `display_title` for site headings and TOCs, and show the original title on the source detail/attribution view. Do not rewrite source metadata in canonical records without an explicit provenance field.

**Done when:** source links and attribution preserve the exact original title, while concept/video indexes and TOCs use a readable display form for titles with promotional capitalization; titles without a meaningful change remain unchanged.

### P1-13 - Remove transcript framing from moment titles (complete 2026-07-16)

**Why:** evidence excerpts can begin with extraction scaffolding such as “The transcript explicitly defines ...”, which makes a visible moment title describe the pipeline instead of the table-tennis idea.

**Work:** normalize transcript and speaker reporting leads at the shared display layer. Preserve the canonical excerpt, reason, source URL, and timestamp unchanged for provenance and review.

**Done when:** visible TOC and evidence titles read as standalone editorial statements, including definition phrasing such as “Acceleration: a slow-soft backswing followed by a fast release,” with no transcript-reporting lead.

**Status:** Complete. Implemented in `app/src/lib/videoToc.ts`; Astro diagnostics and the 201-page static build passed on 2026-07-16.

### P1-14 - Align moment windows to sentence and meaningful-duration boundaries

**Why:** the current span resolver uses the first and last cited caption segments. Caption cues can begin or end mid-sentence, and a technically valid three-second fragment may not contain enough instructional meaning to stand alone.

**Work:** implement caption-only sentence-like unit merging and boundary snapping first; add `starts_mid_sentence`, `ends_mid_sentence`, `too_short`, and `needs_context` flags; keep claim-support citations separate from optional playback context; add review actions and a gold-set evaluation before enabling authorized local word/prosody alignment or semantic change-point proposals.

**Done when:** mid-sentence and non-meaningful short-window rates are measured and reduced, every expanded/split window preserves segment-level provenance and the 30-second limit, and low-confidence cases are deferred rather than silently published. See `docs/moment-boundary-analysis-study-2026-07-16.md`.

### P1-15 — Add an adjustable daily LLM budget and task deferral (complete 2026-07-16)

**Why:** extraction, rephrasing, and benchmarking all invoke Codex, but there was no shared daily guard or visible per-task allowance. A long local run could consume the operator's available usage before later, higher-priority work.

**Work:** reserve a conservative prompt-plus-output estimate before each Codex call; reconcile it with reported usage; enforce daily and task caps; record a private per-KB ledger; defer extraction/rephrase/benchmark work when a cap is reached; expose `llm-budget --kb <id>` and keep limits adjustable in `config/processors.yaml`.

**Done when:** no call starts beyond the configured daily or task allowance, deferred work is recorded without creating partial candidates, successful usage is visible by task and date, and disabling or changing the guard requires an explicit config edit. **Status:** Complete; covered by `tests/test_llm_budget.py`, processor tests, Ruff, CLI integration, and the local-only `/progress/` budget section.

### P1-16 — Add an unattended daily-run orchestrator (new 2026-07-16)

**Why:** the individual Python and Codex CLI stages are scriptable, but there is no timer-safe command that replaces the ChatGPT app's `cp` coordination. Running `extract-concepts` without a video ID can reprocess every normalized transcript, and a scheduled job has no single lock, workset, run manifest, or exit-class contract.

**Work:** add a dry-run-first `daily-run` command and per-KB automation policy; acquire a single-run lock; drain cached work before network acquisition; select only eligible, selected, not-yet-complete videos; honor retry cooldowns, the block circuit breaker, the backlog gate, and the daily LLM budget; extract only missing/stale candidates; build the review queue; keep auto-triage, visual approval, auto-rephrase, commit, push, and deployment explicitly opt-in or disabled; write a private run manifest and machine-readable exit classes; provide a Windows Task Scheduler wrapper without registering it automatically.

**Dependencies:** P1-02 cached candidate triage, P1-15 daily LLM budget, P0-04 source quarantine/removal controls, and a confirmed local Codex CLI authentication/runtime environment.

**Done when:** a scheduled invocation runs without ChatGPT app assistance, two invocations cannot overlap, reruns are idempotent unless explicitly forced, blocks/budget/auth/validation failures defer or stop safely with a private manifest, and no unreviewed knowledge or private processing data is published. See `docs/daily-pipeline-automation-review-2026-07-16.md`. **Status:** Planned; review complete, implementation not started.

### P1-17 - Add excerpt classification and overlap regression protection (new 2026-07-16)

**Why:** the quotation audit cleared complete and high-ratio matches, but the public schema still does not distinguish an editorial summary from an intentional source quotation. Lower-ratio repeated phrases and duplicate expressions can recur as new extraction batches arrive, making the public corpus look more like transcript reproduction and weakening independent analysis.

**Work:** add `excerpt_kind: editorial_summary|source_quote` with `editorial_summary` as the default; require visible attribution and short length for `source_quote`; run a deterministic overlap screen against cited transcript segments and across concepts; report new high-overlap, repeated-expression, and unresolved duplicate groups; block or defer publication when a new complete/high-ratio match lacks an explicit reviewed exception.

**Dependencies:** P0-01 rephrasing policy, P0-02 acquisition provenance, and the existing candidate/review queue schema.

**Done when:** every published excerpt has an explicit kind, intentional quotes render with attribution, a new extraction batch cannot reintroduce complete/high-ratio unmarked transcript matches, and repeated wording across related concepts is visible in the review report. **Status:** Planned; the post-pass audit is clean for complete/high-ratio matches but 28 shorter partial overlaps remain for monitoring. See `docs/content-quotation-audit-2026-07-15.md`.

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

Prefer creator chapters and transcript structure heuristics first. Consider LLM chapter proposals only during extraction/review, never as a required build-time call; validate all proposals against timestamps and source text. Keep the current evidence-derived TOC as the zero-token fallback, and treat creator chapter labels as source metadata rather than new knowledge claims.

**Done when:** creator chapters can be shown when available, deterministic pause/keyword grouping can provide secondary navigation when chapters are absent, and every generated section still passes the permanent route, anchor, ordering, timestamp, and public-data validation checks from P0-06. See `docs/toc-automation-review.md`.

### P2-07 — Add model-cost and extraction provenance reporting

Record model, reasoning level, input/output usage, prompt/schema versions, and candidate hash for each extraction job. Keep `gpt-5.4-mini` as the default unless a benchmark justifies escalation.

### P2-08 — Add source-availability monitoring

Periodically check public/embedding status and display a neutral unavailable state. Never bypass a deleted, private, or embedding-disabled source.

### P2-09 — Add graph quality reporting

Track relation counts, concepts with no outgoing relations, cross-listed concepts, prerequisite cycles, single-source concepts, and relation-review coverage. Six concepts currently have no outgoing relation, so an overall connectedness signal is not enough to describe local graph quality.

## Deferred by design

- Public offline video hosting or transcoded mirrors without explicit permission/licensing.
- Another large scrape before the pending queue, quotation audit, and visual-review queue are under control.
- LLM-generated TOCs during every site build.
- Recreating YouTube’s browsing or playback experience.

## Recommended execution sequence

1. P0-01, P0-02, P0-03, and P0-04 — reduce quotation, acquisition, freshness, and takedown risk.
2. P0-05 through P0-07 — make the public contract, link integrity, and precedent-informed content boundary explicit.
3. P1-01 and P1-02 — verify visuals and process existing candidates before more ingestion.
4. P1-03, P1-04, P1-05, and P1-07 — improve evidence usefulness, operational truth, source diversity, and navigation completeness.
5. P1-06, P1-08, P1-09, P1-10, P1-11, and P1-12 — improve hierarchy, private continuity, deployment paths, encoding quality, and source-title presentation.
6. P1-14, P1-16, and P1-17 - improve moment boundaries, make daily processing timer-safe, and prevent quotation-risk regressions.
7. P2 hardening and scale work, including the deterministic TOC input enhancements in P2-06.

## Completed work not to re-open as backlog

- Per-video detail routes with linear chronological TOCs.
- Shared deterministic TOC builder and reusable `VideoToc` component.
- Responsive evidence-row action layout.
- Correct global “Knowledge bases” navigation target.
- Low-cost `gpt-5.4-mini` default profile.
- Public/private data boundary and publish-copy parity checks.
- Local-only progress, pipeline, and recent-additions pages.
- Deterministic cleanup of transcript-reporting leads from visible moment titles.
