# Project review — 2026-07-15

This review covers the repository architecture, processing code, Astro site, CI/deployment setup, published table-tennis content, and the current documentation. It is based on the working tree and generated artifacts as of 2026-07-15 11:06 (Europe/Helsinki). The review is read-only; existing product changes were preserved.

## Executive summary

The project has a sound static-publishing boundary and a clear separation between private processing data and the public corpus. The deterministic video TOC/detail-page work is a good fit for GitHub Pages: the video library stays compact, each published video has its own route, and its contents are ordered by time without requiring an LLM at build time.

The main risks are operational and editorial rather than a broken build:

1. CI validates the existing published artifact but does not prove that it was freshly generated from the canonical YAML/content inputs.
2. The corpus has no `verified_visual_demo` moments, despite the product positioning around video demonstrations and repeatable clips.
3. Progress and quality documents are already drifting from the current corpus (`68` vs `174` pending; `1110` vs `1118` evidence; different latest-batch descriptions).
4. A large amount of evidence is repeated or concentrated in a few concepts and channels, so count growth does not always equal new, independent learning value.
5. TOC/detail-page anchors were validated with an ad-hoc script, but route and browser-level behavior is not yet a first-class automated test.

## Architecture and data flow

```mermaid
flowchart LR
  Y[YouTube sources] --> D[discover / ingest]
  D --> N[private normalized transcripts]
  N --> C[Codex candidate extraction]
  C --> Q[review queue and concept YAML]
  Q --> V[validate canonical corpus]
  V --> P[publish sanitizer]
  P --> A[data/publish and app/public]
  A --> S[Astro static routes]
  S --> G[GitHub Pages]
```

### Repository responsibilities

- `config/` defines project defaults, processor profiles, enabled knowledge bases, and the table-tennis source/taxonomy/navigation configuration.
- `processors/` contains discovery, ingestion, normalization, Codex CLI orchestration, extraction, review-queue handling, publishing, validation, and quality reporting. `processors/cli.py` is the operational entry point.
- `content/kbs/table-tennis/` is the editorial source of truth for concepts, annotations, taxonomy, and navigation.
- `data/` holds private/working artifacts and the sanitized publish output. Raw transcript segments and private media are intentionally outside the public site boundary.
- `app/` is an Astro static site. `app/src/corpora.ts` loads published corpus JSON, while route generation creates knowledge-base, concept, video-index, and per-video detail pages.
- `.github/workflows/` runs Python validation/tests/lint, Astro checks/builds, publication checks, and security scans before Pages deployment.

### Current video-page design

`app/src/lib/videoToc.ts` builds a deterministic chronological TOC from published evidence. `VideoToc.astro` provides the reusable compact/index and full/detail presentations. The video index uses a short preview; `[videoId].astro` owns the full contents, player, concept links, excerpts, evidence types, and timestamp links. This keeps the large evidence set off one monster page and makes the linear source timeline the primary navigation.

## Verification snapshot

The following checks passed during the review:

| Area | Result |
| --- | --- |
| Canonical Python validation | 73 concepts, 60 source records, 1118 evidence items |
| Published-artifact validation | 73 concepts, 50 published videos |
| Python tests | 25 passed |
| Ruff | Passed |
| Astro diagnostics | 24 files, 0 errors/warnings/hints |
| Astro production build | 132 pages built |
| Published corpus/manifest parity | `data/publish` matches `app/public` |
| Detail-page timestamp anchors | 1108 links checked, no missing targets |

Current published metrics are 73 concepts, 50 videos, and 1118 evidence items. The working extraction area contains 60 real normalized videos plus a demo fixture; that is not the same thing as the 50-video public corpus and should remain explicitly labeled as such.

## Findings

### High priority

#### 1. Published-artifact freshness is not proved in CI

`validate-published` checks the already-generated `data/publish`/`app/public` artifact and the queue. The CI and deployment workflows do not regenerate that artifact from canonical content before validating it. Consequently, a change to `content/kbs/table-tennis/` could be accepted while an old but internally valid public JSON remains deployed.

**Recommendation:** add a reproducible freshness check. Either generate a temporary publish artifact in CI from the canonical inputs, or emit and compare a canonical-input hash/manifest during publish. A metadata-only CI mode may be needed because private normalized transcripts are not available on GitHub Actions.

#### 2. No visual demonstrations are verified

Corpus analysis found:

- `verified_visual_demo`: 0
- `transcript_inferred`: 485
- `not_visual`: 633

The current evidence is useful as transcript-backed explanation, but it does not yet support the stronger promise of visually reviewed, loopable demonstrations. The visual status field is present, so the data model can support this; the editorial review queue is the missing step.

**Recommendation:** create a visual-review workflow that selects candidate time windows, records start/end bounds, and requires an explicit review status before labeling a moment as a demonstration or loopable clip. Keep transcript-only evidence clearly labeled.

#### 3. Operational documentation has drifted

The current queue is `625` items: `450` accepted, `174` pending, and `1` rejected. Several files still describe `68` pending items. The quality reports still describe `1110` evidence items, and some pages/docs describe an older eight-video batch while the current progress page reflects the newer ten-video work.

Affected areas include `README.md`, `docs/pipeline.md`, `docs/quality-report-table-tennis.*`, and `app/src/pages/pipeline.astro`; `docs/source-video-progress.md` and `app/src/pages/progress.astro` are closer to current. This is a trust problem for anyone deciding what to process next.

**Recommendation:** generate progress, quality, and pipeline-status views from one machine-readable report. Do not hand-edit counts in Astro or Markdown. Add a CI check that fails when displayed counts do not match the generated manifest.

### Medium priority

#### 4. Evidence volume is highly repetitive and concentrated

There are 1118 evidence records but only 646 unique excerpt strings; 814 moments participate in repeated excerpt groups and 342 distinct excerpt strings occur more than once. `forehand-loop-swing-path` has 109 moments from 15 videos, while other concepts have only one supporting moment. This can make a concept appear well-supported while mostly restating the same explanation.

**Recommendation:** keep a representative primary moment, then place corroborating moments in a collapsible “more examples” section. Add per-moment summaries that explain what is new about that timestamp, and flag near-duplicate excerpts during extraction/review.

#### 5. Source diversity is uneven

The published source mix is 41 videos from TT SpinMaster and 9 from GlobalTTStudio. Sixteen of 73 concepts are single-source concepts. This is acceptable for an early corpus, but it increases the risk of channel-specific terminology or technique claims becoming the apparent consensus.

**Recommendation:** prioritize second-source coverage for single-source concepts and display source count/independence as a confidence signal rather than treating all evidence counts equally.

#### 6. Progress inventory is partly hard-coded

`app/src/pages/progress.astro` imports batch-specific JSON and contains manually maintained totals. This explains why it can disagree with processor artifacts after another extraction run.

**Recommendation:** have a processor command emit a versioned `progress.json` containing source totals, queue state, extraction state, and publication state. The page should render that file and show its generation timestamp.

#### 7. TOC and anchor behavior needs a permanent automated test

The current 1108 detail timestamp links were checked successfully, but that check was performed as a one-off validation. There is no dedicated test that builds the site, enumerates every detail TOC entry, and verifies that its destination anchor exists and is unique.

**Recommendation:** add a `validate-toc` processor/test command and run it in CI. It should cover route existence, target-anchor uniqueness, chronological ordering, and valid YouTube timestamp ranges.

#### 8. Taxonomy contains empty leaf placeholders

Seven leaf nodes currently have no concept beneath them, including Forehand push, Backhand push, Backhand counter, Forehand/Backhand block, Forehand flick, and Error correction. These may be intentional roadmap entries, but they currently look like incomplete navigation.

**Recommendation:** mark planned leaves explicitly, populate them, or remove them until content exists. A “planned” state is preferable to silently empty navigation.

### Lower priority / hardening

#### 9. CI work is duplicated and action versions are broad

CI and Pages deployment both repeat Python validation and the Astro build. GitHub Actions use major version tags rather than immutable commit SHAs. Python dependency ranges are bounded but not lockfile-pinned; Node has a lockfile.

**Recommendation:** share a reusable validation workflow or narrow deployment to the artifact it needs, pin actions to reviewed SHAs, and record a reproducible Python lock/constraints file.

#### 10. Security boundary is good but can be made more explicit

The publish step removes transcript text from public video records, raw/private paths are ignored, and CI scans for disallowed media/raw segments and credential-like strings. This is a solid baseline, but it is an allowlist-by-convention rather than a complete secret-scanning strategy.

**Recommendation:** keep the current output scan and add an explicit public-artifact allowlist plus a standard secret scanner. Treat any unexpected file under `app/public/data/` as a CI failure.

## Strengths worth preserving

- Static Astro output is well matched to free GitHub Pages hosting and has no runtime database or server dependency.
- Knowledge bases are configuration-driven; adding another domain can reuse the same corpus and route machinery.
- The private/public boundary is deliberate: normalized transcripts and media stay out of the published corpus.
- Validation checks graph integrity, prerequisites, navigation placement, transcript segment references, source URLs, and citation bounds.
- The deterministic TOC does not consume LLM calls during builds. Codex is reserved for candidate extraction/review, which keeps recurring publication cheap and predictable.
- The per-video detail route solves the large-index problem while retaining concept links and timestamp-level navigation.

## Prioritized roadmap

### Immediate

1. Add canonical-to-published freshness verification to CI.
2. Regenerate all progress and quality documents from one report; remove hard-coded queue/evidence totals.
3. Add the TOC/anchor validator to the normal test suite.
4. Start a visual-review queue and distinguish transcript evidence from verified demonstrations in the UI.

### Next

1. Deduplicate/cluster repeated moments and show representative evidence first.
2. Add second-source coverage targets for the 16 single-source concepts.
3. Resolve or label the seven empty taxonomy leaves.
4. Add a generated “recent additions” feed keyed to corpus generation metadata.

### Later

1. Pin GitHub Actions and Python dependencies for reproducible builds.
2. Reduce duplicate CI/deploy work with reusable workflows.
3. Add optional creator-provided chapters and heuristic chapter detection before considering LLM-generated TOC proposals.

## Files reviewed

`README.md`, `pyproject.toml`, `config/processors.yaml`, `config/project.yaml`, `config/knowledge-bases.yaml`, `config/kbs/table-tennis/*`, `processors/cli.py`, `processors/pipeline.py`, `processors/ingest.py`, `processors/codex_engine.py`, `processors/models.py`, `data/publish/*`, `content/kbs/table-tennis/*`, `app/src/corpora.ts`, `app/src/lib/videoToc.ts`, `app/src/components/VideoToc.astro`, `app/src/components/EvidenceRow.astro`, `app/src/pages/kb/[kb]/videos/*`, `app/src/pages/progress.astro`, `app/src/pages/pipeline.astro`, `app/src/styles/global.css`, `.github/workflows/ci.yml`, `.github/workflows/deploy-pages.yml`, and the relevant test/quality-report files.

