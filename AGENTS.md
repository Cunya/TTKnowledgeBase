# AGENTS.md

## Mission

Build and maintain a generic, multi-domain knowledge-base generator whose first knowledge base covers table tennis. The system converts timestamped YouTube transcripts into reviewed wiki-style concepts with traceable spoken citations and separate loopable visual demonstrations, then publishes a static Astro site suitable for free GitHub Pages hosting.

Read these before making architectural or pipeline changes:

- `README.md`
- `docs/pipeline.md`
- `docs/youtube-knowledge-base-plan.md`
- `docs/operations.md`

## Repository map

- `processors/`: Python ingestion, Codex CLI extraction, validation, review-queue, and publishing code.
- `config/knowledge-bases.yaml`: registered knowledge bases.
- `config/kbs/<kb>/`: per-KB sources, taxonomy, and settings.
- `config/processors.yaml`: Codex model and execution profile.
- `content/kbs/<kb>/concepts/`: reviewed canonical concept YAML; editorial source of truth.
- `content/kbs/<kb>/annotations/`: file-based review queue and editorial annotations.
- `data/normalized/`: private timed transcripts and metadata; generated and gitignored.
- `data/derived/`: private Codex candidates; generated and gitignored.
- `data/publish/`: sanitized publish output.
- `app/`: Astro/TypeScript static site.
- `app/public/data/`: only browser-safe corpus data copied by publishing.
- `media/`: temporary review or future offline media; always gitignored and never part of GitHub Pages.

## Non-negotiable data rules

1. Never invent a timestamp, transcript segment ID, quotation, coach identity, or source attribution.
2. Every published knowledge claim must have a transcript-backed `source` with valid segment IDs.
3. A spoken citation is not automatically a visual demonstration.
4. Use optional `visual_source` for the separate window where the movement is actually visible.
5. The site may loop only `visual_source`. Transcript-only evidence must be presented as a spoken citation with looping disabled.
6. Keep inferred visual clips at 15 seconds or less unless a reviewed exception is justified.
7. Use `selection_method: nearby_visual_inference` for a proposed nearby visual window. Use `manual_review` only after watching the complete selected clip and confirming it illustrates the stated concept.
8. Preserve `visual_status` honestly. Do not mark a transcript-inferred demonstration as verified.
9. LLM output is a proposal. It never becomes approved public knowledge without review and tracked concept YAML.
10. Do not publish full raw transcripts, Codex audit data, credentials, cookies, downloaded media, or offline archives.

## Multi-KB boundaries

Do not hard-code table-tennis assumptions into shared processors or generic site routes. All pipeline commands accept `--kb`; private, reviewed, and published data are isolated by KB ID. Domain-specific terminology belongs in `config/kbs/<kb>/taxonomy.yaml` or that KB's reviewed content.

The current table-tennis sources include TT SpinMaster (`@FreeCoachBradHan`) and GlobalTTStudio. Coach identity metadata remains provisional unless supported by an authoritative primary source.

## Normal content pipeline

Run Python commands from the repository root using the checked virtual environment:

```powershell
$env:PYTHONUTF8='1'
.\.venv\Scripts\python.exe -m processors.cli discover CHANNEL_OR_PLAYLIST_URL --kb table-tennis
.\.venv\Scripts\python.exe -m processors.cli ingest --kb table-tennis VIDEO_URL_1 VIDEO_URL_2
.\.venv\Scripts\python.exe -m processors.cli extract-concepts --kb table-tennis --engine codex --video-id VIDEO_ID
.\.venv\Scripts\python.exe -m processors.cli build-review-queue --kb table-tennis
```

Then review candidates and edit canonical YAML in `content/kbs/<kb>/concepts/`. Do not bulk-promote the generated review queue.

For visual selection, inspect nearby footage on a temporary local copy, keep that copy under `media/`, and record only the resulting timestamp metadata in reviewed YAML. Never commit the review media.

Publish only after review:

```powershell
.\.venv\Scripts\python.exe -m processors.cli validate --kb table-tennis
.\.venv\Scripts\python.exe -m processors.cli publish --kb table-tennis
```

The current CLI requires explicit URLs for `ingest`; entries in `sources.yaml` document the selection but do not cause ingestion by themselves.

## Codex extraction contract

Python invokes `codex exec`; agents should not handcraft candidate JSON as a substitute for extraction. The invocation must remain schema-constrained, ephemeral, read-only, auditable, and time-bounded. It must cite supplied transcript segment IDs only.

Use the configured default model/profile in `config/processors.yaml`. Do not silently switch to a more expensive model or enable automatic escalation. A stronger retry requires an explicit editorial decision and recorded provenance.

Generated candidate files remain private and unpublishable. Promote only defensible concepts with supported definitions, stable IDs/slugs, reviewed relations, concise excerpts, and canonical URLs.

## Concept editorial guidelines

- Prefer a wiki article with a useful definition and several cross-video examples over a flat tag.
- Consolidate synonyms and preserve the source wording as aliases.
- Split a broad technique into durable subtopics such as mechanics, timing, spacing, selection, errors, and drills.
- Prefer evidence from more than one source when available.
- Keep excerpts short and necessary for context; paraphrase the article body.
- Avoid asserting that an inferred movement is visible without inspecting nearby video material.
- Relations must point to existing concept IDs and use the supported relation vocabulary.
- Do not delete or overwrite unrelated reviewed material when resolving a candidate.

## Required verification

After Python, model, schema, or content changes, run from the repository root:

```powershell
$env:PYTHONUTF8='1'
.\.venv\Scripts\python.exe -m processors.cli validate --kb table-tennis
.\.venv\Scripts\python.exe -m processors.cli publish --kb table-tennis
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check .
```

After site, types, public data, or reviewed content changes, also run:

```powershell
Set-Location app
npm run build
```

`npm run build` runs Astro diagnostics before the static build. Return to the repository root before running Python commands because the virtual environment is rooted there.

For content changes, verify representative live routes on `http://127.0.0.1:4321/` when the development server is running. Confirm that visual and spoken timestamps are separate controls and that transcript-only evidence does not loop.

## Git and generated-data hygiene

- Respect `.gitignore`; do not force-add private or generated processing inputs.
- Do not commit `media/`, raw/normalized transcripts, derived Codex responses, cookies, credentials, `.env` files, Node modules, or build output.
- Reviewed concept YAML, configuration, processors, tests, documentation, and sanitized publish data are legitimate tracked artifacts.
- Preserve unrelated user changes in a dirty worktree.
- Do not use destructive Git cleanup or reset commands.

## Offline feature boundary

Offline download, preservation, and transcoding are future user-controlled features. They must remain separate from the public site and require explicit user actions, manifest-owned paths, rights/policy checks, storage estimates, and safe cleanup previews. Never place downloaded video in Git or GitHub Pages.

## Definition of done

A change is complete only when its claims are source-grounded, visual windows are honestly classified, private data remains excluded, validation passes, tests and lint pass, Astro reports no diagnostics, the static build succeeds, and the affected local routes render the intended content.

## SHORTCUT PROMPTS
### Common
- "c" continue
- "cp" continue processing the videos: first drain eligible cached transcripts/candidates; if no local work remains, select and ingest the next controlled batch from configured discovery catalogs, subject to backlog priority, source-policy checks, pacing, and the block circuit breaker. Do not start a large scrape while a backlog gate still defers expansion.
- "u" update docs, including the session log, and notes; start with checking the current date and time
- "rlc" - review local changes
- "cm" - provide a commit message for the local changes, list features and state them in past tense as what was done
- "ggg" - go on with the current task and dont stop until it is done
- "p" ponder on your notes for the current problem and update it if you come up with something new
- "v" review all local changes (both staged and unstaged) for possible cleanup and any issues for committing. create a new md about it.

### DOCUMENTATION RULES
- **Keep documentation updated**
- **Maintain `docs/prioritized-backlog-2026-07-15.md` as the consolidated project backlog.** Treat it as the planning source of truth for findings from architecture reviews, legal/platform reviews, content audits, processing runs, and implementation work.
- When a review or implementation pass discovers work, add or update a backlog item with its priority, status, source finding, dependencies, and acceptance criteria. Do not leave actionable findings only in a dated report.
- Before starting a large scrape, extraction batch, or broad refactor, check the backlog and follow its priority order. After completing work, mark the affected items complete, deferred, blocked, or superseded and record the evidence.
- Keep completed items in the backlog’s history/“completed” section when useful; do not silently delete unresolved work. If the backlog filename changes, update this rule and all references in the same change.
- **Keep and maintain a session log md file** with the current date and hour in the file name, and update it before modifying the code (Keep it in Docs/Session Logs)
- **Keep and maintain a lessons learned md file** so you can avoid making the same mistakes
- **Keep the session log and the lessons learned max 500 lines** and start a new when reaching the limit
- **Organize the session log** so that the order of activities with time stamps can be followed
- **Before making code changes check the session log** in many cases the process is going around in cirles, you should be aware of this
- **Whenevery you find code that could be made more efficient, duplicate code refactored into common methods, etc, make a note in a refactorings.md file**
- **Make notes for yourself in a session notes file** with the current date and hour in the file name and session notes in the file name.
