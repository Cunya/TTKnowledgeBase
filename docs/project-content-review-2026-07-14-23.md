# Project and content review — 2026-07-14 23:32 EEST

## Scope

This review covers the repository architecture, GitHub Pages deployment path, ingestion and extraction safeguards, review queue, published table-tennis corpus, knowledge hierarchy, evidence presentation, and current editorial backlog.

The review used the current uncommitted working tree after the 15-video extraction and 100-candidate editorial batch. It included source inspection, corpus measurements, validation output, test/build results, and representative component review. The in-app browser connection could not be initialized during this pass, so visual conclusions are based on the rendered structure, CSS/component source, prior screenshots, and the successful Astro build rather than a new interactive screenshot session.

## Executive summary

The project has a sound core architecture: private transcripts are separated from public data, claims retain exact timestamp provenance, spoken and visual evidence are modeled separately, the site builds statically for GitHub Pages, and the corpus currently passes validation. The knowledge base is now substantial enough to expose the next class of problems: editorial density, visual verification, relation quality, reproducibility, and automation safety.

The most important next move is not another large scrape. It is a quality pass over the existing 70 concepts and 950 evidence moments. In particular, the project should make CI validate the canonical corpus, replace inferred looping clips with genuinely reviewed visual demonstrations, reduce repeated evidence on very large pages, and align the Codex model configuration with the stated low-cost requirement.

## Current measured state

| Measure | Current value |
|---|---:|
| Approved concepts | 70 |
| Published source videos | 38 |
| Normalized non-demo videos seen by validation | 42 |
| Approved evidence moments | 950 |
| Accepted review candidates | 383 |
| Pending review candidates | 59 |
| Rejected review candidates | 1 |
| Explicit concept relations | 30 |
| Concepts with no relations | 46 |
| Concepts supported by only one video | 21 |
| Evidence with a `visual_source` | 35 |
| Manually verified visual demonstrations | 0 |
| Published corpus JSON size | about 1.1 MB |

## What is working well

### Source-grounded data model

- Canonical evidence retains video IDs, exact transcript segment IDs, start/end times, and timestamped YouTube URLs.
- Validation enforces a 30-second spoken window and prevents large gaps inside one citation.
- Accepted queue items must overlap exact evidence in their mapped canonical concept.
- Full transcripts, audit responses, credentials, and downloaded media remain outside the public corpus.

### Spoken and visual evidence separation

- `source` and `visual_source` are separate, which is the correct foundation for distinguishing an explanation from footage that actually demonstrates a movement.
- Transcript-only evidence cannot be looped by the current component.
- One shared YouTube player avoids creating dozens of simultaneous embeds on evidence-heavy pages.

### Static publishing and multi-KB structure

- Shared processors and routes accept a KB identifier instead of hard-coding table tennis into the framework.
- Astro produces a static site suitable for free GitHub Pages hosting.
- Project Pages base-path handling is present in `astro.config.mjs`.
- Deployment checks prevent common media, transcript, audit, cookie, environment, and credential artifacts from entering the Pages output.

### Editorial restraint

- Generated Codex output enters a review queue instead of becoming public automatically.
- The latest large editorial batch consolidated 99 proposals into existing articles and five durable concepts instead of creating 99 shallow pages.
- Ambiguous material was allowed to remain pending.

## Priority findings

### P1 — CI and deployment do not validate canonical content

Both GitHub workflows run tests, Ruff, and the Astro build, but neither runs:

```powershell
python -m processors.cli validate --kb table-tennis
python -m processors.cli publish --kb table-tennis
```

This means malformed canonical YAML, stale public JSON, invalid queue mappings, bad navigation coverage, or timestamp errors can be committed while CI still passes if the already-generated public data builds successfully.

Recommended change:

1. Run validation in CI before the site build.
2. Add a deterministic publish freshness check: publish in CI and fail if tracked `data/publish/` or `app/public/data/` changes.
3. Keep real transcripts private by providing a committed sanitized validation fixture or a validation mode that checks canonical/public artifacts without requiring ignored normalized transcripts.

### P1 — The central loopable-video promise is still unverified

The corpus has 35 `visual_source` entries, but every one uses `nearby_visual_inference`. There are no `manual_review` selections and no `verified_visual_demo` evidence entries. The UI nevertheless enables looping for any `visual_source` and says that only “reviewed visual examples” can loop.

This is the same failure mode the project was designed to prevent: a timestamp near an explanation may not contain the movement that the text describes.

Recommended change:

1. Rename the UI state for inferred clips to “Proposed visual” and disable automatic looping until manual review, or visually distinguish it very clearly.
2. Review the 35 existing inferred clips first, watching each full interval.
3. Record `selection_method: manual_review`, a concise visual note, and `visual_status: verified_visual_demo` only after confirmation.
4. Add corpus metrics and validation warnings for inferred versus verified visual coverage.

### P1 — The configured extraction model does not match the low-cost requirement

`config/processors.yaml` currently selects `gpt-5.4` for both default and escalation. Low reasoning reduces reasoning effort, but it does not turn the frontier model into the low-cost mini model described in the project plan.

Recommended change:

1. Benchmark `gpt-5.4-mini` on a fixed reviewed sample.
2. If candidate quality remains acceptable, make mini the default.
3. Keep stronger-model retries explicit and recorded; automatic escalation should remain disabled.
4. Record per-job model and approximate input/output usage so future content batches have a visible cost profile.

### P1 — Evidence quantity is now outpacing evidence usability

The corpus has 950 moments but only 443 distinct excerpt strings. A total of 773 moments use text that appears more than once. The largest article, “Forehand loop swing path and racket angle,” contains 106 moments from 13 videos. “Post-serve recovery” has 45 moments, and “Body-hand synchronization” has 38.

Repeated candidate definitions are being used as the excerpt for several different timestamp windows. This preserves traceability but does not explain what is unique about each moment. On the page, many rows therefore look semantically identical even when their source windows differ.

Recommended change:

1. Give each moment a localized claim or summary derived from its exact cited segment rather than repeating the candidate-level definition.
2. Add explicit evidence subtopics such as setup, timing, contact, acceleration, recovery, mistake, correction, and drill.
3. Rank a small set of representative moments per subtopic and collapse additional corroboration under “More supporting moments.”
4. Add editorial warnings for articles over a configurable threshold, such as 30 visible moments or more than three identical excerpts.
5. Treat evidence count as support, not as the primary measure of article completeness.

### P1 — Queue decision preservation needs a content fingerprint

Queue rebuilds now preserve decision fields using `(video_id, candidate_id)`. This protects manual work during ordinary batch additions, but a rerun can reuse a candidate ID while changing its definition, evidence, or relations. A stale accepted/rejected decision could then be carried onto materially changed content.

Recommended change:

1. Store a deterministic candidate hash covering label, definition, evidence segment IDs, and relations.
2. Preserve a decision only when both identity and hash match.
3. When an ID matches but the hash changes, reset it to pending and show a “candidate changed” review note.
4. Add a regression test for changed content under the same candidate ID.

## Content and information-architecture findings

### P2 — The knowledge graph is still mostly a navigation tree

Only 30 explicit relations exist across 70 concepts, and 46 concepts have no relations. All five newly added concepts currently have no relations. The navigation hierarchy makes them discoverable, but it does not yet express important semantic links such as:

- backhand serve as a variation of serve families;
- push variations used with push-rally strategy;
- serve-and-attack patterns using serve planning and third-ball adjustment;
- down-the-line forehand loop as a variation of forehand loop and a tool for opponent targeting.

Recommended change: perform a relation-review pass and require each durable concept to have at least one justified incoming or outgoing relation unless it is intentionally a root concept.

### P2 — Several new articles have high moment counts but only one source

There are 21 single-source concepts. The newest pages are especially concentrated:

- Backhand serve: 35 moments from one video.
- Push-rally strategy: 16 moments from one video.
- Push variations: 14 moments from one video.
- Forehand loop down the line: 14 moments from one video.
- Serve-and-attack patterns: 11 moments from one video.

Many timestamps from one lesson improve detail, but they do not provide independent corroboration. The UI should not make 35 moments from one video feel equivalent to broad multi-source support.

Recommended change: show both moment count and distinct-video/channel count prominently, and prioritize future ingestion that adds a second source to these concepts.

### P2 — Evidence chapter grouping is too generic

`VideoEvidence.astro` assigns moments to four chapters solely from `evidence_type`: understand, execute, practice, and diagnose. This is useful as a first layer but cannot represent a concept-specific hierarchy. For example, a backhand serve article needs toss, contact zone, racket path, acceleration, spin variation, deception, and common errors.

Recommended change: add a reviewed `subtopic_id` or section field to evidence. Use generic evidence type inside each subtopic, not as the entire article structure.

### P2 — Visible encoding corruption remains

At least one canonical label is visibly corrupted:

```text
Push?spin?power progression
```

The evidence component source also contains mojibake such as `Â·`, `â€“`, `â†’`-style sequences. These can appear as broken separators, ranges, and icons in the rendered site.

Recommended change:

1. Replace corrupted source strings with valid UTF-8 characters or HTML-safe equivalents.
2. Add a validation/test scan for replacement characters and common mojibake sequences in public text.
3. Normalize older documentation that still contains corrupted dash sequences.

### P2 — Published-video counts are inconsistent across layers

The canonical validator reports 42 videos because it sees the local normalized set. The published manifest contains 38 videos, all of which currently have approved evidence. Documentation currently describes 42 as published metadata, which is inaccurate.

Recommended change: use explicit metric names everywhere:

- normalized videos;
- extracted videos;
- reviewed/supporting videos;
- published videos.

Generate these numbers from manifests instead of editing them manually in README and pipeline documentation.

### P2 — The remaining queue contains known resolver errors

The 59 pending candidates are manageable and should be cleared before another large scrape. One example is “Backhand loop timing and rhythm” matched to the forehand-loop timing concept with only 0.42 confidence. Other pending candidates are natural groups for serve-receive depth, short-ball decisions, backhand whip mechanics, and body stability.

Recommended editorial order:

1. Process clear matches from `t3HX8AEujWw` and `zd8tcVUWwK4`.
2. Create or consolidate a backhand-loop timing/whip branch from `q9c2_hCwlhs`.
3. Consolidate the short/half-long receive decision tree from `wF-YklKS7pI`.
4. Consolidate serve-receive reading and rhythm from `tWJXY0cUPRQ`.
5. Review the four body-organization candidates from `YUEaL2HiPIE`.
6. Resolve or reject the two ambiguous framework/brush-loop candidates explicitly.

## Engineering and operations findings

### P2 — Generated public data causes very large diffs

The same roughly 1.1 MB corpus is tracked in both `data/publish/` and `app/public/data/`. This is intentional for static publishing, but large content batches produce noisy JSON diffs and increase the chance of the copies drifting.

Recommended change: keep one canonical tracked publish location and copy it into the Astro public directory during build, or enforce byte-for-byte equality in CI if both copies remain tracked.

### P3 — Relation and content quality metrics should become first-class reports

The project currently has strong validity checks but few quality thresholds. A valid corpus can still be repetitive, single-source, relation-poor, or visually unverified.

Recommended command: `processors.cli report-quality --kb table-tennis`, producing machine-readable and Markdown summaries for:

- concepts, supporting videos, and channels;
- moment and excerpt duplication;
- concepts without relations;
- single-source concepts;
- inferred and verified visual coverage;
- evidence count outliers;
- unresolved queue distribution;
- encoding anomalies;
- public-data size.

### P3 — Workflow actions are version-tag pinned, not commit-SHA pinned

The GitHub Actions use stable major tags, which is common and functional. For stronger supply-chain reproducibility, pin actions to reviewed commit SHAs and use dependency automation to update them.

## Recommended next sequence

### Phase 1 — Trust and correctness

1. Add corpus validation and publish-freshness checks to CI.
2. Add candidate content hashes to review-queue preservation.
3. Fix visible encoding corruption and add an automated mojibake scan.
4. Correct published/normalized video metrics in documentation.

### Phase 2 — Core product promise

1. Manually review the 35 inferred visual clips.
2. Prevent inferred clips from being presented as reviewed loopable demonstrations.
3. Add visual-review progress metrics.
4. Select representative visual moments for the highest-traffic forehand-loop concepts first.

### Phase 3 — Content usability

1. Clear the remaining 59-candidate backlog.
2. Add concept-specific evidence subtopics.
3. Rank representative moments and collapse redundant corroboration.
4. Add missing semantic relations, especially for the five newest concepts.
5. Seek second-source evidence for the 21 single-source concepts.

### Phase 4 — Cost and scale

1. Benchmark and adopt the mini extraction model if quality is acceptable.
2. Add cost/usage provenance.
3. Add automated quality reporting.
4. Avoid further large scraping until the current visual and editorial backlog is under control.

## Overall assessment

The system is beyond a prototype: it has a defensible data boundary, a functioning static product, a sizable reviewed corpus, and meaningful validation. Its principal risk is now overproduction—more candidates and moments can make the site look richer while reducing clarity and leaving the visual-demo promise unfulfilled. The next milestone should therefore be a smaller, more navigable, more visually verified corpus rather than a larger raw evidence count.
