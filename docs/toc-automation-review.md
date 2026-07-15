# Automating video contents without extra LLM calls

## Finding

The current per-video contents list does not need an LLM at site-build time. It is a deterministic view of the already reviewed public corpus:

1. Read `app/public/data/kbs/<kb>/corpus.json`.
2. Join each video to concepts whose approved evidence cites that video ID.
3. Sort the linked evidence by `source.start_ms` and then concept label.
4. De-duplicate a concept/video/start-second repetition.
5. Group the moments under their concept labels.
6. Render the approved `evidence_type` and formatted timestamp.
7. Link to the stable `moment-<evidence-id>` anchor on the concept article.

The build performs no semantic inference and spends zero Codex/LLM tokens. The concept labels, evidence types, excerpts, and timestamps already passed through the extraction and editorial-review gates before they reached the public corpus.

## What is already deterministic

| Contents feature | Current source | Automation status |
|---|---|---|
| Video title and channel | `Corpus.videos` | Fully scripted |
| Connected concepts | `Concept.evidence[].source.video_id` | Fully scripted |
| Concept order | Existing corpus order | Scripted; could be changed to first timestamp |
| Moment order | `source.start_ms` | Fully scripted |
| Timestamp display | `start_ms` formatter | Fully scripted |
| Evidence type label | Reviewed `evidence_type` | Fully scripted at build time |
| Concept/moment links | Concept slug + evidence ID | Fully scripted |
| Duplicate suppression | Same concept/video/start second | Fully scripted |
| Anchor validation | Static-build inspection | Scriptable validation rule |

The only model-dependent history is upstream: Codex originally proposed concepts and evidence types, and a reviewer decided what entered the published corpus. Rebuilding the TOC does not re-run that work.

## Opportunities to remove more model work

### 1. Keep the current TOC as the default

This is the safest and cheapest design. A new reviewed concept or evidence item automatically appears in the relevant video contents list on the next publish/build. No extra schema or model prompt is needed.

The current Astro page derives the view in `app/src/pages/kb/[kb]/videos/index.astro`. If the corpus remains at this scale, keeping the derivation there is simpler than creating another generated artifact.

### 2. Use source chapters when available — no LLM

YouTube metadata may contain creator-provided chapters. The current `Video` model does not expose chapters to the browser, so this would require adding a reviewed-safe field such as:

```json
{
  "start_ms": 90000,
  "title": "Opening the forehand loop"
}
```

The TOC could show creator chapters first, then the evidence-derived concept moments underneath. Chapter titles must remain source metadata, not be presented as concepts or verified claims. Missing chapters should simply fall back to the current evidence list.

### 3. Use transcript structure heuristics — no LLM

For videos without chapters, a script could propose section boundaries from:

- long pauses between transcript segments;
- explicit cues such as “next,” “now let’s,” or “the mistake is”;
- changes in evidence type;
- contiguous runs of moments around the same concept;
- title/description keywords already present in metadata.

These heuristics can produce useful navigation boundaries, but labels will be weak unless they reuse an existing reviewed concept label. Treat heuristic sections as navigation aids, never as new knowledge claims.

### 4. Add optional semantic chapter proposals during extraction

If a true video-level summary is desired, ask the existing extraction job for a small `video_sections` proposal while it already has the transcript in context. This adds no separate per-build calls and can be cached with the transcript hash, model, prompt version, and schema version.

The proposal should contain only:

- a short title;
- `start_ms` and `end_ms` backed by supplied segment IDs;
- the related existing concept IDs, when applicable;
- a confidence/uncertainty note.

It must remain private and pending review. An LLM must not decide that a movement is visibly demonstrated, widen a spoken citation, or publish a new concept merely because it suggested a chapter title.

## Recommended architecture

Use a four-level fallback chain:

```text
creator chapters
    ↓ if absent
approved evidence-derived concepts and timestamps
    ↓ if sparse
deterministic transcript/pause grouping
    ↓ optional, reviewed only
LLM semantic chapter proposal
```

The published browser data should contain only approved chapters or approved evidence references. A proposal can be stored beside private candidates, but it should never be required for the site to build.

For maintainability, the next useful automation is not another prompt. It is a small reusable TOC builder/validator, either:

- a pure TypeScript helper shared by the video index and future search/recent pages; or
- a publish-time `video-toc.json` artifact generated from the sanitized corpus, if several pages need the same precomputed index.

The artifact is optional. The current corpus contains 50 published videos and 1,118 evidence moments, which is small enough for Astro to derive efficiently.

## Suggested validation rules

An automated `validate-toc` check could verify that:

1. every listed video exists in the published corpus;
2. every concept link targets an existing concept slug;
3. every moment link targets an existing `moment-<evidence-id>` anchor;
4. every listed moment's `source.video_id` equals the containing video;
5. timestamps are non-negative and monotonically ordered within each video;
6. duplicate concept/video/start-second rows are either collapsed or explicitly marked;
7. no private candidate, transcript, or Codex audit field is copied into the public TOC;
8. no proposed visual clip is presented as a verified demonstration.

The current build has already been checked this way: all 1,108 generated timestamp links resolve to a published evidence anchor.

## Cost and review boundary

| Approach | Extra LLM calls during build | Editorial risk | Recommendation |
|---|---:|---|---|
| Evidence-derived TOC (current) | 0 | Low | Keep as the baseline |
| Creator chapters | 0 | Low, if labeled as source metadata | Add when metadata support is available |
| Pause/keyword grouping | 0 | Medium for misleading labels | Use only as secondary navigation |
| Cached extraction-time chapter proposal | 0 after extraction | Medium; requires review | Optional enhancement |
| Fresh LLM call per page/build | Many | High cost and nondeterminism | Avoid |

The practical rule is: **LLMs may propose semantic organization once, but scripts should render, link, sort, deduplicate, and validate it forever after.**

## Implementation follow-up

The deterministic path is now shared by `app/src/lib/videoToc.ts` and `app/src/components/VideoToc.astro`. The library index uses a compact concept preview, while each published video has a static `/kb/<kb>/videos/<video-id>/` route with a complete linear-by-time contents stream, excerpt, evidence type, concept link, and direct YouTube timestamp. This keeps the index navigable without adding any LLM work to the build.
