# Project, data, and pipeline review - 2026-07-16

This review covers the current repository architecture, processing code, static site, CI configuration, published table-tennis corpus, and maintained documentation. It is a read-only review: existing product and content changes were preserved.

## Executive summary

The core boundary is sound: private normalized transcripts and processor job artifacts stay outside the static site, while the Astro build consumes a sanitized corpus with timestamped source links. The public corpus validates successfully and is large enough to expose the next quality risks.

The main constraint is no longer ingestion volume. Evidence is becoming repetitive, visual demonstrations are not yet verified, and several navigation leaves still look like articles without content. The backlog should therefore prioritize editorial compression, visual review, generated status data, and removal/freshness controls before another large scrape.

## Current measured state

| Signal | Current value | Interpretation |
|---|---:|---|
| Published concepts | 73 | Approved concepts in the sanitized corpus |
| Published videos | 107 | Videos with at least one approved evidence item |
| Evidence moments | 1,686 | Timestamped concept evidence items |
| Distinct excerpt strings | 1,153 | 403 exact repeated-excerpt groups remain |
| Moments in repeated groups | 936 | 55.5% of moments share an excerpt with another moment |
| Review queue | 955 accepted / 103 deferred / 1 rejected | No pending items, but deferred work remains |
| Verified visual demonstrations | 0 | 35 visual intervals are still proposals |
| Single-source concepts | 3 | `defensive-rhythm-variation`, `push-spin-power-progression`, and `racket-contact-constraint-drill` |
| Concepts without outgoing relations | 6 | Relation coverage is uneven even though the graph is navigable |
| Empty navigation leaves | 7 | Forehand/backhand push, backhand counter, forehand/backhand block, forehand flick, and Error correction |

The largest evidence outlier is `forehand-loop-swing-path` with 128 moments. Other high-volume concepts include Contact point (82), Body-hand synchronization (74), Forehand loop against backspin (64), and Contact zone on the ball (54). This supports the existing P1-03 evidence-localization and representative-moment work.

## Architecture review

### Strengths

- `processors/cli.py` makes ingestion, extraction, queue triage, rephrasing, publishing, and validation explicit operator commands.
- `processors/models.py` and the Pydantic validators provide one strong schema boundary for candidates, concepts, relations, source spans, and published corpora.
- `data/publish/` is the canonical sanitized output and `app/public/data/` is checked for byte-for-byte parity.
- Astro routes are generated from the published corpus; the public site has no runtime scraper, database, credentials, or LLM dependency.
- Per-video routes use deterministic chronological TOCs and timestamp anchors, while concept pages retain the knowledge-tree view.

### Risks and follow-up

1. CI validates an existing publish artifact but does not regenerate it or compare a canonical-input hash. A stale but internally valid public corpus could therefore pass CI (P0-03).
2. `app/src/pages/progress.astro` and source inventory modules still contain hand-maintained counts and batches. They can drift from manifests even when the corpus itself is valid (P1-04).
3. Production deployment computes the Astro `base` from `GITHUB_REPOSITORY`, but `deploy-pages.yml` passes a root owner URL as `SITE_URL`. This can make canonical/site metadata point at the wrong host path for project Pages sites; set and test the repository-qualified URL (new P1-10).
4. User-visible strings still contain UTF-8 mojibake such as `Â·`, `â€”`, and `â€œ` in the shared layout, progress page, workflow names, and generated inventory data. Add an encoding scan and normalize affected files (new P1-11).
5. GitHub Actions are referenced by mutable major tags and CI/deploy repeat the same validation/build work. Existing P2-03 and P2-04 remain appropriate.

### Title capitalization audit

No concept label, evidence excerpt, reason, or generated TOC moment title contains an all-caps title fragment. Ten original YouTube video titles do contain promotional capitalization, including `SUCKS`, `STOP`, `SMASH`, `FAST`, and one title that is entirely uppercase. These are source metadata and should not be silently rewritten as if they were editorial text. The UI should expose a calm display form while retaining the exact original title in provenance and the source inventory.

## Content review

- The quotation rephrasing pass removed complete and high-ratio matches, but exact repeated editorial excerpts are still common. The next pass should generate moment-specific summaries and collapse corroborating rows instead of adding more duplicate prose.
- Transcript-inferred evidence is correctly distinguished from visual evidence, but none of the 35 proposed intervals has manual visual verification. The loop/repeat UI should remain disabled for unverified windows.
- Source diversity is improving, but three concepts still rely on one video. Add independent supporting sources before increasing evidence in the already dense concepts.
- The navigation tree is structurally useful, but seven leaves have empty `concept_ids` and no children. They should be marked planned, populated, or removed from public navigation.
- The relation graph has useful typed edges, but six concepts have no outgoing relation. Report incoming versus outgoing coverage separately so connectedness does not hide weak local structure.

## Backlog changes made with this review

- Corrected the backlog baseline to 916 `transcript_inferred` and 770 `not_visual` moments, 3 single-source concepts, and 403 repeated-excerpt groups / 936 affected moments.
- Updated P1-03, P1-05, P1-07, and P2-09 evidence to match the current corpus.
- Added P1-10 for repository-qualified GitHub Pages URL verification.
- Added P1-11 for UTF-8 encoding cleanup and a deployment encoding guard.
- Added P1-12 for separate display and original source-title fields when source titles use promotional capitalization.
- Kept P0-03, P0-04, P1-01, P1-04, P1-06, P1-08, P1-09, and the P2 hardening items open; the review found no evidence to mark them complete.

## Recommended next sequence

1. Keep the public-boundary, freshness, source-removal, and TOC validation gates ahead of another broad scrape.
2. Review the 35 visual proposals and make only manually confirmed windows loopable.
3. Compress repeated moments and fill or explicitly label the seven empty navigation leaves.
4. Generate progress/source inventories from manifests, then fix encoding and project-URL checks in CI.
