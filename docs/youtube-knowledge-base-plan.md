# YouTube Knowledge Base — Product and Implementation Plan

Status: proposed  
Example pilot: table tennis coaching  
Target hosting: GitHub Pages (free, public repository)  
Project scope: generic—usable for any topic, creator, channel, playlist, or hand-picked video collection

## 1. Product vision

Build a source-grounded, concept-centered knowledge base from public YouTube videos. The primary outcome is not a transcript archive: it is a browsable map of the concepts taught across the videos. Each concept has a stable page, a concise definition, aliases, relationships to other concepts, and one or more timestamped demonstration moments that seek the embedded video to the relevant explanation or physical demonstration.

The system collects video metadata and available timed transcripts, preserves the link from every derived statement to its source moment, and publishes multiple views of the resulting knowledge: concept pages, a concept index/map, searchable transcripts, summaries, topic guides, glossaries, comparisons, learning paths, and cross-video connections.

The first pilot should use table tennis coaching videos, including material from [Free Coach Brad Han](https://www.youtube.com/@FreeCoachBradHan). The system must not hard-code table tennis concepts: topic-specific vocabulary, taxonomies, prompts, and editorial corrections belong in configuration/content files.

The coach identity should initially be recorded as unverified metadata (for example, `speaker_display_name: Xiao Han?`) rather than stated as fact. Confirm it from an authoritative channel description, creator profile, or direct statement before publishing it as an identity claim.

## 2. Guiding principles

- Source first: every excerpt, summary point, concept, and generated answer must retain one or more video IDs and time ranges.
- Static publishing: the public site has no server, secrets, database, login, or runtime scraping.
- Processing outside the browser: Python scripts ingest and enrich content locally; GitHub Actions may validate and build it.
- Human review: machine-generated knowledge is marked by status and can be corrected without editing generated files.
- Reproducibility: generated data records processor version, input hash, Codex CLI/model metadata, prompt/schema version, and timestamp.
- Generic core, configurable domain: table tennis is a dataset and taxonomy, not application logic.
- Respectful collection: embed or link to YouTube; do not redistribute video/audio; retain attribution and removal controls.

## 3. Recommended architecture

### Decision

Use **Astro + TypeScript** for the static site and **Python 3.12** for ingestion/analysis processors.

Astro is a good fit because most output is content-heavy static HTML, while interactive islands can support the YouTube player, transcript synchronization, filters, and client-side search. Python has the strongest practical ecosystem for transcript retrieval, text processing, embeddings, and optional speech-to-text.

### Runtime split

```text
YouTube URLs / channel / playlists
              |
              v
     Local Python processors  ----> Codex CLI (`codex exec`)
              |
              v
     versioned JSON + Markdown
              |
              v
      Astro static-site build
              |
              v
         GitHub Pages
```

GitHub Pages serves static files only. The repository and published site should remain comfortably below the documented 1 GB recommendation/limit; Pages also documents a 10-minute deployment timeout and a soft 100 GB/month bandwidth limit. See [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits). Downloaded media is explicitly outside the initial architecture and may be added later as a separate local/private feature.

### Why not a server-side app first

A live scraper/API would require separate hosting, secrets, rate limiting, storage, moderation, and operational cost. It also makes reliable YouTube access harder. A checked-in corpus produces a fast, inspectable, forkable site and keeps the initial hosting genuinely free.

### Recommended library stack

Use maintained libraries for protocol/tool integration and generic infrastructure, while keeping the knowledge/provenance rules in project code. Pin all direct dependencies and test upgrades against captured fixtures because YouTube-facing tools change frequently.

| Requirement | Library/tool | Decision | Notes |
|---|---|---|---|
| Video/channel/playlist metadata | [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) | Adopt | Supports metadata-only extraction, channels/playlists, subtitles, download archives, Python embedding, and later media acquisition. Wrap it behind an adapter because extractor behavior changes. Prefer subprocess usage for archive jobs; its Python API is acceptable for metadata if isolated. |
| Public timed captions | [`youtube-transcript-api`](https://github.com/jdepoix/youtube-transcript-api) | Adopt as first caption adapter | Returns text, start, duration, language, and manual/generated status. It uses an undocumented YouTube interface, so retain `yt-dlp` and supplied VTT/SRT fallbacks. |
| Official YouTube metadata | [`google-api-python-client`](https://github.com/googleapis/google-api-python-client) | Optional | Use only when an API key is configured and repeatable official channel/playlist discovery is valuable. It does not solve downloading third-party captions. |
| Caption parsing | [`webvtt-py`](https://github.com/glut23/webvtt-py) plus Python `srt` | Adopt for supplied/downloaded files | Avoid maintaining custom VTT/SRT parsers. Convert both into the canonical `Segment` model immediately. |
| Local speech-to-text fallback | [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) | Optional, not MVP-critical | Use only for authorized audio processing when captions are unavailable. Preserve word/segment timestamps and record model/settings. |
| Models, validation, JSON Schema | [Pydantic v2](https://docs.pydantic.dev/latest/) | Adopt | One typed model layer should validate files, generate the Codex `--output-schema`, and validate Codex responses again. Avoid maintaining separate hand-written schemas. |
| CLI | [Typer](https://typer.tiangolo.com/) + [Rich](https://rich.readthedocs.io/) | Adopt | Typer provides typed commands/help; Rich provides progress, tables, status, and readable errors. Keep domain services independent of Typer so the later UI can reuse them. |
| Human-edited YAML | [`ruamel.yaml`](https://yaml.dev/doc/ruamel.yaml/) | Adopt | Its round-trip mode preserves comments/formatting in reviewed concept and annotation files. Use safe/round-trip loading, never unsafe object construction. |
| Concept/alias candidate matching | [RapidFuzz](https://rapidfuzz.github.io/RapidFuzz/) | Adopt as candidate generator | Efficiently proposes likely alias matches. Never auto-merge on fuzzy score alone; taxonomy, evidence, and review still decide identity. |
| Sentence boundary assistance | [`pysbd`](https://github.com/nipunsadvilkar/pySBD) | Evaluate on transcript fixtures | Lightweight multilingual rule-based segmentation. Caption timing and original segment IDs remain authoritative. Skip if simple timestamp-aware merging performs as well. |
| Heavy NLP pipeline | [spaCy](https://spacy.io/) | Defer | `PhraseMatcher`/`EntityRuler` could help later with large reviewed vocabularies, but spaCy models are unnecessary for the initial LLM-centered pilot. |
| Concept graph validation/export | [NetworkX](https://networkx.org/) | Adopt narrowly | Use directed graphs for cycle checks, prerequisites, reachability, and JSON export. It is not the source of truth and does not require a graph database. |
| Codex extraction | Installed `codex` executable via Python `subprocess` | Adopt | Use `codex exec`, schema output, read-only/ephemeral isolation, timeouts, and captured results. Do not add an agent framework or shell-wrapper package. |
| Static website | [Astro](https://astro.build/) + TypeScript | Adopt | Static content-first output with small interactive islands for player/search. Avoid a client-heavy SPA for the whole site. |
| Browser search | [MiniSearch](https://github.com/lucaong/minisearch) | Adopt for pilot | Supports in-memory prefix/fuzzy search and field boosting without a server. Generate a compact publishable index and establish a size budget. |
| YouTube playback | Official [IFrame Player API](https://developers.google.com/youtube/iframe_api_reference) | Adopt behind a wrapper | Required for seek/time synchronization. Evaluate [`lite-youtube-embed`](https://github.com/paulirish/lite-youtube-embed) for lazy loading only after verifying its JS API path supports all synchronization needs. |
| Python tests | [pytest](https://docs.pytest.org/) + [Hypothesis](https://hypothesis.readthedocs.io/) | Adopt | Use fixtures for network adapters and property tests for timestamp/source invariants, stable IDs, chunking, and path safety. Tests must not require YouTube or Codex. |
| Future transcoding | FFmpeg/ffprobe executables | Adopt directly | Invoke with argument arrays and parse `ffprobe` JSON/progress output. Prefer direct subprocesses or yt-dlp postprocessors over `ffmpeg-python`; the wrapper still requires an external FFmpeg installation and adds little for fixed profiles. |
| Future local manager API | [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn | Evaluate/adopt when offline phase starts | Good fit for a loopback API and static manager UI. Do not use in-process `BackgroundTasks` as the durable archive queue; persist jobs in SQLite and run them through the shared archive worker. |
| Future local job state | Python `sqlite3` + explicit worker/state machine | Adopt later | A single-user local app does not need Redis, Celery, RabbitMQ, or a distributed task framework. SQLite provides durable queue/manifests when transitions are transactional. |
| Future terminal UI alternative | [Textual](https://textual.textualize.io/) | Optional | Provides a capable terminal UI from the same Python services. Prefer the planned local web manager for nontechnical users; Textual is a fallback if packaging a web UI proves costly. |

Do **not** add LangChain/LlamaIndex for the MVP: transcript batching, `codex exec`, schema validation, caching, and provenance are direct and project-specific. Also avoid a graph database, vector database, Celery/Redis, and a full CMS until corpus size or real usage demonstrates a need.

Suggested dependency groups:

- `core`: Pydantic, Typer, Rich, `ruamel.yaml`, RapidFuzz, `youtube-transcript-api`, `webvtt-py`, `srt`, and NetworkX;
- `youtube-api`: `google-api-python-client` only for users who configure the official API;
- `asr`: `faster-whisper` only for authorized caption fallback;
- `web`: Astro, TypeScript, and MiniSearch in the Node workspace;
- `dev`: pytest, Hypothesis, linters/type checker, and captured fixtures;
- `offline` (future): yt-dlp media options, FFmpeg/ffprobe, FastAPI, Uvicorn, and local-manager assets.

Keep yt-dlp available to the core ingestion environment for metadata/subtitle fallback, but isolate its future media-download configuration behind the `offline` feature and rights gate. Generate lockfiles for Python and Node; do not specify loose unbounded versions in automation.

## 4. Proposed repository layout

```text
/
├── app/                         # Astro website
│   ├── src/components/
│   ├── src/layouts/
│   ├── src/pages/
│   └── public/data/             # build output copied from generated data
├── config/
│   ├── project.yaml             # languages, site name, behavior
│   ├── sources.yaml             # channels, playlists, individual videos
│   ├── processors.yaml          # enabled analysis recipes
│   └── taxonomies/
│       └── table-tennis.yaml    # pilot-specific terms and hierarchy
├── content/
│   ├── annotations/             # reviewed overrides; source of truth for editorial decisions
│   ├── concepts/                # reviewed canonical concepts and relations
│   ├── guides/                  # authored learning paths/articles
│   └── entities/                # reviewed people, terms, organizations
├── data/
│   ├── raw/                     # immutable local source metadata/transcripts; not necessarily public
│   ├── normalized/              # canonical segments/documents
│   ├── derived/                 # generated candidates, summaries, relations, chunks
│   ├── publish/                 # allowlisted, redacted static-site input
│   └── manifests/               # hashes, provenance, failures
├── processors/
│   ├── discover.py
│   ├── fetch_metadata.py
│   ├── fetch_transcripts.py
│   ├── normalize.py
│   ├── analyze.py
│   ├── build_search.py
│   ├── validate.py
│   └── cli.py
├── prompts/                     # version-controlled analysis recipes
├── schemas/                     # JSON Schema/Pydantic contracts
├── tests/
├── docs/
└── .github/workflows/
```

Do not commit downloaded video or audio. Keep a hard boundary between processing data and public site data: only `data/publish/` is copied into the Pages build. Raw transcripts are a policy/copyright decision; if redistribution is undesirable, keep `data/raw/` local/gitignored and publish only short cited excerpts plus derived indexes. CI then builds from a small sanitized fixture/publish corpus, while maintainers generate the real publish corpus locally.

## 5. Data model

Use stable, portable JSON files rather than a database for version 1.

### Core entities

- `SourceCollection`: channel, playlist, or manual URL list; topic tags and inclusion rules.
- `Video`: YouTube ID, canonical URL, title, channel ID/name, publish date, duration, thumbnail, language, availability, attribution, last checked.
- `TranscriptTrack`: language, generated/manual flag, acquisition method, retrieved time, license/policy state.
- `Segment`: stable segment ID, exact text, normalized text, `start_ms`, `duration_ms`, speaker if known, source URL.
- `Chunk`: overlapping semantic unit made from consecutive segments; carries the complete segment/time lineage.
- `Concept`: stable slug/ID, canonical label, aliases, short and detailed definitions, type, taxonomy parents, difficulty, review state, and referenced evidence.
- `ConceptEvidence`: a concept-to-source link with evidence type (`definition`, `explanation`, `demonstration`, `example`, `mistake`, `correction`, or `drill`), video/time span, excerpt, relevance/confidence, and review state.
- `Claim`: concise proposition, confidence/review state, supporting and contradicting source spans.
- `AnalysisArtifact`: summary, outline, FAQ, drill, comparison, glossary entry, etc.; processor and provenance fields.
- `Relation`: typed, directed edge such as `prerequisite_of`, `part_of`, `variation_of`, `contrasts_with`, `used_with`, `causes`, or `corrects`; includes evidence, confidence, and review state. `same_as` is handled by concept resolution/aliasing, and `demonstrates` belongs on `ConceptEvidence` rather than mixing source links into the concept graph.

### Concept identity and merging

Concepts must be stable across processor reruns and across videos. Generate slugs from reviewed canonical names, but assign an immutable ID so renaming a concept does not break links. Extraction first creates `ConceptCandidate` records; a resolver then matches them against existing concepts using exact aliases, the domain taxonomy, normalized terms, and optional semantic similarity. Low-confidence matches remain separate candidates for review rather than being merged automatically.

Examples such as `loop`, `topspin loop`, and `forehand topspin` may be aliases, variants, or distinct concepts depending on context. The system should preserve the phrase used in the source while linking it to a reviewed canonical concept. A concept can belong to several facets (for example stroke, backhand, against backspin, intermediate) rather than one rigid tree.

### Source-link contract

Every derived item must include:

```json
{
  "sources": [
    {
      "video_id": "VIDEO_ID",
      "start_ms": 83400,
      "end_ms": 101200,
      "url": "https://www.youtube.com/watch?v=VIDEO_ID&t=83s",
      "segment_ids": ["VIDEO_ID:00042", "VIDEO_ID:00043"]
    }
  ],
  "generated_by": {
    "processor": "topic_summary",
    "version": "1.0.0",
    "input_hash": "sha256:..."
  },
  "review_status": "unreviewed"
}
```

Store times as integer milliseconds; generate YouTube URLs using whole seconds. Never let an LLM invent timestamps—timestamps are calculated from cited input segments.

## 6. Ingestion and processing pipeline

Expose one idempotent CLI, for example:

```powershell
python -m processors.cli discover --source free-coach-brad-han
python -m processors.cli ingest --new
python -m processors.cli extract-concepts --new --engine codex
python -m processors.cli build-review-queue
python -m processors.cli publish
python -m processors.cli validate
npm --prefix app run build
```

### Stage A — source discovery

Accept:

- individual YouTube video URLs;
- playlist URLs;
- channel handles/URLs;
- a curated YAML list.

Prefer the official YouTube Data API for repeatable channel/playlist metadata when an API key is available. Provide a `yt-dlp` adapter as the local fallback. Persist video IDs immediately so discovery changes do not lose the collection.

### Stage B — metadata

Collect title, channel, dates, description, chapters, duration, thumbnails, language hints, and availability. Refresh mutable fields without overwriting the original acquisition record.

### Stage C — timed transcript acquisition

Adapter priority:

1. User-supplied VTT/SRT transcript for owned or licensed material.
2. `youtube-transcript-api` for public manual/auto captions.
3. `yt-dlp --skip-download --write-subs --write-auto-subs` as a local fallback.
4. Optional local transcription with `faster-whisper` only when caption retrieval fails and the operator has the right to download/process the audio.
5. Record a structured `transcript_unavailable` result rather than silently dropping the video.

The official YouTube `captions.download` endpoint is not a general solution for third-party videos: it requires authorization and permission to edit the video ([official documentation](https://developers.google.com/youtube/v3/docs/captions/download)). `youtube-transcript-api` can return text, start time, and duration for public manual or generated tracks, but it uses an undocumented YouTube interface, warns that cloud-provider IPs may be blocked, and can break when YouTube changes ([project documentation](https://github.com/jdepoix/youtube-transcript-api)). Therefore, run acquisition locally by default; do not make unattended GitHub-hosted scraping a launch requirement.

### Stage D — normalization

- Preserve the raw response unchanged.
- Decode entities and normalize Unicode/whitespace.
- Retain the original language and text alongside any corrected text.
- Merge overly short caption fragments into sentence-like segments without losing original segment IDs.
- Detect repeated captions, music markers, and likely gaps.
- Optionally run punctuation restoration and domain spelling correction as separate, reversible layers.
- Chunk by semantic/sentence boundary with small overlap; aggregate start/end from member segments.

For the pilot, a reviewed alias list should handle recurring terms and names (rubbers, strokes, grips, Chinese names) without rewriting the raw transcript.

### Future feature — offline media preservation and transcoding

This feature is **deferred until after version 1**. It is not part of the MVP, initial repository scaffold, initial CLI, GitHub Actions, pilot acceptance criteria, or definition of done. The first release links to and embeds source videos from YouTube while preserving transcripts, timestamps, metadata, and derived knowledge.

A later release may provide an explicit, opt-in archive command for material the operator is permitted to download and preserve. It should use `yt-dlp` as a replaceable acquisition adapter and FFmpeg/ffprobe for inspection and transcoding.

Archive behavior:

- download individual videos, playlists, channels, or only videos already present in the corpus;
- use a `yt-dlp` download-archive file so reruns skip known video IDs;
- retain metadata JSON, description, thumbnail, chapters, and available subtitles;
- write atomically to a temporary filename, then verify before marking an item complete;
- compute SHA-256 checksums and record size, container, codecs, resolution, frame rate, audio layout, acquisition time, source URL, and tool versions;
- never delete an existing local copy merely because the upstream video becomes unavailable;
- distinguish `available_online`, `removed_upstream`, `private_upstream`, `blocked`, and `archive_missing` states;
- support `--metadata-only`, `--missing`, `--video-id`, and `--dry-run` modes;
- keep original and derivative lifecycles independent so a compact encode can be regenerated without reacquiring the source.

#### Future user-control model

The offline feature should not require users to compose `yt-dlp` or FFmpeg commands. Provide one underlying archive service with two local control surfaces:

1. A simple, scriptable CLI for automation and recovery.
2. A local-only **Offline Manager** web UI for normal use, started with a command such as `python -m processors.cli offline-ui` and opened on `localhost`.

Both surfaces operate on the same config, queue, manifests, and job-state files, so a job started in the UI can be inspected or resumed from the CLI. The public GitHub Pages site remains read-only and cannot initiate downloads. A future portable/local site may show an “available offline” indicator and deep-link into the local manager when it is running.

The Offline Manager should provide:

- first-run setup for archive folder, storage policy, default quality profile, bandwidth limit, and optional backup location;
- collection/video selection with search and filters, plus `select all`, `only missing`, and per-video exclusions;
- plain-language actions: **Estimate**, **Download**, **Pause**, **Resume**, **Retry failed**, **Verify**, **Transcode**, **Open folder**, and **Remove local copy**;
- a preflight summary showing video count, estimated download/output size, available disk space, selected codec/profile, and whether originals will be retained;
- a queue with per-item state, progress, speed, ETA, errors, and a readable retry suggestion;
- archive health showing online/offline availability, checksum status, last verification, original/derivative presence, and backup status;
- bulk policy changes by source, playlist, topic, or selected videos;
- clear separation between removing a compact derivative, removing an original, and forgetting metadata;
- confirmation that names the affected files and reclaimable space before destructive cleanup;
- an activity log and exportable diagnostic report with secrets/cookies redacted.

Use a small explicit state machine such as `not_selected`, `queued`, `downloading`, `downloaded`, `transcoding`, `ready`, `paused`, `failed`, `missing_upstream`, and `verification_failed`. Operations must be resumable and idempotent. Closing the UI must not corrupt a running or partial job; `.part` files and manifests allow safe continuation.

Store user choices in a readable local file such as `config/offline.local.yaml`, excluded from Git because it may contain machine-specific paths. Keep reusable named presets in a tracked example file without personal paths or credentials. Bind the manager to loopback only by default, open no inbound network access, and require an explicit advanced setting before listening on another interface.

Suggested configurable profiles:

| Profile | Purpose | Suggested output |
|---|---|---|
| `original` | Best preservation | Keep downloaded source streams/remux without lossy re-encode where possible |
| `compact` | Good offline coaching/reference copy | MP4, H.265/HEVC or AV1 video, AAC/Opus audio, maximum 720p, quality-targeted encode |
| `compatible` | Broad browser/device playback | MP4, H.264 video, AAC audio, maximum 720p |
| `audio` | Speech review/transcription | Opus or M4A audio only |

AV1/HEVC usually gives smaller files but encodes more slowly and has less universal playback support; H.264 is larger but safest for browsers and older devices. Preserve aspect ratio and source frame rate, avoid upscaling, and use constant-quality encoding rather than a fixed bitrate. Benchmark a small corpus before selecting CRF/CQ defaults. For sports instruction, verify that ball motion and fine racket contact remain legible; an aggressive encode can destroy the detail the archive exists to preserve.

Storage policy should be explicit:

- `preservation`: retain both original and compact derivative;
- `space-saving`: verify the compact derivative, then allow deletion of the original only through a separate, confirmed prune command;
- `metadata-only`: preserve knowledge data and checksums without media.

No automatic prune should be part of ingestion. Generate a report showing projected and actual bytes, compression ratio, failed encodes, checksum status, and orphaned files. For stronger preservation, recommend two verified copies on different devices. Optional private object storage or an external drive can be added later, but is outside the free GitHub Pages deployment.

### Stage E — analysis recipes

The version 1 recipes consume canonical chunks and emit schema-validated artifacts with citations:

- concept candidates: term, contextual definition, aliases, type, broader/narrower concepts, and source spans;
- concept evidence classification: definition, verbal explanation, visual demonstration, example, mistake, correction, or drill;
- concept resolution: attach a candidate to an existing concept, propose a new concept, or queue an ambiguous merge for review;
- relationship extraction: prerequisite, part-of, variation-of, contrasts-with, used-with, causes, and corrects;
- representative-moment ranking so each concept leads with the clearest short demonstration and offers alternative explanations from other videos;
- claims/advice with evidence spans;
- drills, cues, common mistakes, and corrections;
- cross-video agreement, complement, duplication, and contradiction candidates;
- optional extractive highlights that require no LLM.

Video summaries, chapter suggestions, entity catalogs, question cards, translations, and generated learning paths are useful later recipes, but they must not delay the concept/evidence core.

For the MVP, use **Codex CLI** as the concrete LLM extraction engine. The maintainer installs/authenticates Codex locally, and the Python processor invokes `codex exec` non-interactively. Keep a small internal `ExtractionEngine` interface so a direct API or local-model adapter can be added later, but do not build multiple providers before the Codex workflow is proven. A deterministic fixture engine remains for tests.

### Codex CLI execution design

The Python processor is the orchestrator and trust boundary. For each bounded job it creates an input package containing numbered transcript segments, relevant known concepts/taxonomy, a task prompt, and a JSON Schema. It invokes Codex in read-only mode, captures the final structured response, validates it, and only then writes a candidate artifact.

Illustrative invocation (the processor should use subprocess arguments/stdin rather than constructing a shell string):

```powershell
Get-Content -Raw "$jobDir\prompt.md" | codex exec - `
  --cd $jobDir `
  --skip-git-repo-check `
  --model gpt-5.4-mini `
  --sandbox read-only `
  --ephemeral `
  --output-schema "$jobDir\response.schema.json" `
  --output-last-message "$jobDir\response.json" `
  --json
```

MVP requirements:

- preflight with `codex --version` and `codex login status`, and give a clear setup error if unavailable or unauthenticated;
- run locally/manual by default, not in GitHub Actions;
- run with the job directory as the working root, preferably in an OS temporary directory outside the repository, so unrelated files and repository instructions are not accidental context;
- use `--skip-git-repo-check` for that isolated job directory and `--ephemeral` so extraction sessions are not persisted;
- use `--sandbox read-only`; Codex reads only prepared job inputs and cannot modify corpus/content files;
- pass prompts through stdin and subprocess argument arrays to avoid shell quoting/injection problems;
- use `--output-schema` for the final response and validate it again with Pydantic/JSON Schema;
- use `--output-last-message` for the response payload; treat `--json` stdout as JSONL execution/audit events, not as the knowledge artifact;
- write to a unique temporary job directory and atomically promote validated output into `data/derived/`;
- set timeouts, check exit codes, capture stderr, and retain a sanitized failure record that can be retried;
- process jobs sequentially initially; add bounded concurrency only after rate/cost behavior is measured;
- record the Codex CLI version, selected model and reasoning setting, prompt/schema versions, input hash, exit status, and response hash;
- never pass secrets in prompts or commit Codex session/auth files, raw event logs, temporary job inputs, or raw responses;
- do not use `--dangerously-bypass-approvals-and-sandbox` for extraction.

### Cost-aware model policy

Use `gpt-5.4-mini` with low reasoning as the MVP default. OpenAI describes it as its strongest mini model for coding, computer use, and subagents, designed for faster, high-volume workloads. This is a better starting point than a frontier model for repeated transcript batches, while retaining more capability than a nano model for ambiguous concepts, aliases, and relationships ([official model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini)).

Make the policy explicit in `config/processors.yaml`, for example:

```yaml
codex:
  default_model: gpt-5.4-mini
  reasoning_effort: low
  escalation_model: gpt-5.4
  escalation_reasoning_effort: low
  allow_automatic_escalation: false
```

The processor passes the default model explicitly with `--model` rather than silently inheriting a changing personal default. Apply the reasoning setting through a tested Codex profile/config override, record it in the manifest, and fail clearly if the configured model is unavailable to the signed-in account.

Do not automatically send every job to the stronger model. A job becomes an escalation candidate only when deterministic validation fails repeatedly, the model marks it ambiguous/low-confidence, competing candidates cannot be resolved, or the citation check disagrees with the extraction. For the MVP, place these jobs in the human review queue and require an explicit `--retry-escalated` command. This keeps cost predictable and prevents a model from escalating its own workload silently.

Treat `gpt-5.4-nano` as an evaluation candidate only for narrow operations such as evidence-type classification or ranking after concepts are already resolved. Do not use it for primary concept extraction until the golden corpus shows acceptable precision/recall and citation accuracy. Use `gpt-5.4` only for selected difficult jobs; a larger frontier model is unnecessary as the default.

Before processing the pilot corpus, benchmark at least 20 representative chunks with the mini model and review:

- concept precision and missed-concept rate;
- alias/merge mistakes;
- relationship direction accuracy;
- valid and supported segment citations;
- schema failure/retry rate;
- average input/output tokens or available Codex usage metrics;
- reviewer corrections and time saved.

Adopt the cheapest model/settings that pass explicit quality thresholds. Suggested initial gates: at least 90% valid supported citations, no automatic false merges in the reviewed sample, and at least 80% precision for publishable concept candidates. Re-evaluate the chosen alias/profile when models change; do not hard-code price figures because Codex subscription/credit accounting can differ from API token pricing.

Concept extraction should run in two passes. The per-video pass proposes candidates and timestamped evidence without knowledge of the full corpus. The corpus pass deduplicates candidates, resolves aliases, builds relationships, ranks demonstrations, and identifies gaps or conflicting explanations. LLM output is always treated as a proposal; only transcript segment boundaries determine published timestamps.

### LLM extraction contract

Do not ask the model to return free-form articles as the primary artifact. Give it numbered transcript segments containing stable segment IDs and exact start/end times, the current taxonomy, known concepts/aliases, and a narrowly scoped task. Require schema-constrained JSON output containing:

- proposed canonical concept and aliases actually used in the source;
- concise definition grounded in the supplied transcript;
- concept type/facets and difficulty, with confidence;
- cited segment IDs for every definition, claim, relation, and evidence item;
- evidence classification and a short reason;
- proposed relations to known concepts;
- `new`, `match`, or `ambiguous` resolution recommendation;
- uncertainty and missing-context flags rather than guesses.

The processor—not the LLM—looks up cited segment IDs, calculates time ranges, constructs YouTube links, rejects nonexistent citations, and copies the exact supporting excerpt. Reject an item if its cited text does not support it or if it cites segments outside the supplied batch.

Use several focused calls rather than one large “understand this channel” request:

1. Extract candidates and evidence from overlapping per-video chunks.
2. Consolidate duplicate candidates within each video.
3. Resolve candidates against the current concept catalog in bounded batches.
4. Propose cross-video definitions, relationships, conflicts, and representative moments.
5. Run a citation/entailment check with a separate prompt or model pass.

Cache every response by Codex CLI version, model, reasoning setting, prompt version, schema version, input hash, and relevant settings. Use deterministic input ordering, retry only failed/invalid structured output, enforce job/time budgets, and make batches resumable. Store prompt/response audit records locally; publish only approved derived artifacts and non-sensitive provenance. A small reviewed golden dataset should compare model/profile and prompt changes before corpus-wide regeneration.

For visual demonstrations, transcript timing is an initial locator, not proof that the movement is visible at that exact second. Store a wider suggested clip window and allow a reviewer to adjust its start/end while watching the player. Mark evidence as `transcript_inferred` until visually checked and `verified_visual_demo` afterward.

### Stage F — review and validation

- Validate every JSON output against schemas.
- Reject missing/invalid video IDs and time ranges outside video duration.
- Check that derived source spans refer to actual segment IDs.
- Flag unsupported claims, low-confidence entity merges, and contradictory results.
- Overlay human annotations after generation so reruns cannot erase edits.
- Generate a concept-review queue for new candidates, possible duplicates, uncertain aliases, weak definitions, unverified visual demonstrations, and relationship conflicts.
- Make review file-based for version 1: the CLI writes a deterministic queue/report; a reviewer accepts, rejects, merges, renames, or adjusts evidence in tracked YAML under `content/kbs/<kb>/concepts/` and `content/kbs/<kb>/annotations/`; regeneration overlays those decisions. A browser-based editor would require write-capable hosting and is out of scope.
- Publish only `approved` concepts/relations by default. `unreviewed` evidence may appear only when explicitly enabled and visibly labeled; `rejected` items never enter `data/publish/`.
- Generate a QA report: video count, transcript coverage, languages, failures, unreviewed artifacts, broken embeds/links, and stale sources.

## 7. Website experience

### MVP pages

- Home: prominent concept search/browse entry, major concept groups, learning routes, recent additions, and coverage statistics.
- Concepts index: browse alphabetically or by facets such as category, difficulty, prerequisite, source, and review status; include compact cards with definition and best demonstration.
- Concept page: canonical definition, aliases, prerequisite/related concept links, supporting excerpts, and ranked timestamped demonstrations across videos.
- Relationship browse: accessible prerequisite/related-concept lists on concept pages. An interactive graph/map is a later enhancement, not an MVP dependency.
- Library: filter videos by source, topic, level, language, duration, and transcript availability.
- Video page: embedded player, synchronized transcript, outline, summary, concepts, and related moments.
- Search: unified results grouped into concepts, exact transcript moments, videos, and guides; every moment has highlighted context and “play from here.”
- Guides: curated sequences that combine moments from multiple videos.
- About/methodology: provenance, limitations, attribution, correction/removal path, and independence disclaimer.

### Concept-page interaction

The concept page is the central experience. Its first screen should answer: what is this, why does it matter, what should I know first, and where can I see it demonstrated? Selecting a demonstration seeks the embedded player and shows the matching transcript excerpt beside it. Users can move to the previous/next cited moment, switch between creators or explanations, copy a timestamped source link, and open the full video context.

Avoid an undifferentiated tag cloud. Use faceted navigation, aliases, breadcrumbs, prerequisite links, and curated “learn next” relations. Show confidence and review badges unobtrusively, while keeping the exact evidence one click away. URLs should be durable and readable, for example `/concepts/forehand-loop/` and `/concepts/forehand-loop/#demo-videoid-83`.

### Player behavior

For version 1, use the YouTube IFrame Player API. Clicking a transcript line or citation should seek the player to its `start_ms`; transcript highlighting follows player time. Also expose a normal timestamped YouTube link for accessibility and cases where embedding is disabled. Do not autoplay by default.

In the future offline-media phase, introduce a player adapter with `YouTubePlayer` and HTML5 `LocalMediaPlayer` implementations. A separate `build:offline` target could then produce a portable site and generated local-media catalog. Because `file://` playback can be unreliable, that package should include a one-command local server. None of this is required for version 1.

### Search strategy

Start with a generated MiniSearch index because the product needs structured result types, facets, aliases, exact timestamp anchors, and grouping by concept/video. Index title, channel, publishable transcript excerpts, concepts, aliases, and approved analysis artifacts. Keep search local in the browser and lazy-load/shard the index if the corpus becomes large. Pagefind remains a simpler fallback for whole-page search, but is not the primary plan for segment-level results.

Semantic search is a phase-two enhancement: precompute embeddings offline, quantize them, and ship only if download size and browser latency remain acceptable. Lexical search plus aliases is simpler and more transparent for the pilot.

### Accessibility and trust

- Keyboard-operable player/transcript controls and visible focus states.
- Captions/transcripts readable independently of the player.
- Clear labels for auto-generated transcript, machine translation, AI-generated analysis, and human-reviewed content.
- Each insight expands to show the exact supporting excerpt and timestamp.
- A correction/removal link identifies the relevant video and time.

## 8. Build, deployment, and automation

### GitHub Actions

Use separate workflows:

- `ci.yml`: lint, unit tests, schema validation, link/source validation, and Astro build on pull requests.
- `deploy-pages.yml`: build and deploy the static artifact on `main` using GitHub's Pages Actions.
- `refresh.yml` (optional/manual first): discover metadata and open a pull request containing changed generated data.

Avoid scheduled transcript scraping from GitHub Actions at first. Cloud IP blocking and undocumented endpoints make it fragile. A maintainer should run `ingest` locally and submit generated changes. If scheduled refresh is later enabled, use low request rates, caching, retries/backoff, a manual kill switch, and failure artifacts; never use evasion as a core dependency.

### Reproducibility

- Pin Python and Node dependencies with lockfiles.
- Cache by video ID + transcript language + raw transcript hash.
- Reprocess only when input, processor, prompt, taxonomy, or model version changes.
- Provide `make`/Taskfile/npm wrappers that work on Windows, macOS, and Linux.
- Store a corpus manifest so a build can be recreated without contacting YouTube.
- Add a deployment leakage check that fails if raw transcripts, prompt/response audit logs, secrets, or media-like extensions appear in the Pages artifact.
- Future offline phase: store a separate media manifest with relative paths/checksums and record `yt-dlp` and FFmpeg versions; never put machine-specific absolute paths into content data.

## 9. Legal, platform, and editorial safeguards

This needs review before a public corpus launch; it is not legal advice.

- Follow the YouTube Terms of Service, API policies where applicable, creator embedding settings, and applicable copyright/database/privacy rules.
- Prefer embedding and deep-linking for the public site. Never commit video/audio downloads.
- Future offline phase: treat downloading as an operator-controlled archival feature, not an entitlement. Only archive where the operator has permission or another valid legal basis, and account for YouTube's terms and applicable law. Private preservation does not automatically grant redistribution rights.
- Future offline phase: do not publish, sync to public object storage, or bundle archived media into GitHub Pages without documented authorization from the rights holder.
- Treat transcripts as copyrighted source material: publish only what is necessary for search/context, consider short snippets rather than full transcript redistribution, and document the chosen policy.
- Attribute the channel and video on every page; do not imply creator endorsement or affiliation.
- Maintain deny lists, per-video exclusions, and a documented removal/correction process.
- Record whether a transcript is creator-authored, auto-generated, translated, or locally transcribed.
- Do not generate a synthetic coaching authority: summaries must distinguish source advice from project synthesis.
- Confirm names and identities before merging speaker entities, especially across channels.

## 10. Table tennis pilot

The pilot validates the generic system; it does not define the core schema.

### Seed scope

- Add the Free Coach Brad Han channel as a configured source.
- Begin with 10–20 manually selected videos spanning several techniques rather than ingesting the entire channel.
- Record the possible “Xiao Han” identity as an unresolved entity until verified.
- Use English as the UI language while preserving each transcript's source language and available translations.

### Initial taxonomy

- fundamentals: stance, ready position, footwork, timing, recovery;
- strokes: serve, receive, push, flick, drive, loop, block, chop, smash;
- technique dimensions: grip, contact point, racket angle, acceleration, spin, placement;
- tactics: serve patterns, third ball, rally patterns, variation, opponent adaptation;
- practice: multiball, shadow practice, drills, error diagnosis;
- context: forehand/backhand, close/mid/far distance, against backspin/topspin/sidespin, skill level.

Keep this in `config/kbs/table-tennis/taxonomy.yaml`, with aliases such as `loop`/`topspin`, and allow a video moment to have multiple tags. Other topics get independent folders registered in `config/knowledge-bases.yaml`.

### Pilot success checks

- At least 80% of selected captioned videos ingest successfully.
- Every visible derived item opens a valid source moment.
- A user can find a technique across all pilot videos in under three interactions.
- At least 25 reviewed concepts have stable pages, aliases/facets, and at least one timestamped evidence item.
- At least 10 core concepts have a reviewer-verified visual demonstration, not only a transcript-inferred timestamp.
- Users can move from a concept to prerequisites, related techniques, common mistakes, and demonstrations without returning to transcript search.
- At least two useful cross-video concept pages combine evidence from multiple videos.
- A reviewer can correct a name, term, summary, or source span without editing generated files.
- A clean checkout builds and deploys without YouTube access or paid services.

## 11. Delivery phases

### Phase 0 — policy and feasibility spike (1–2 days)

- Confirm the transcript publication policy and attribution/removal wording.
- Test 5 representative pilot videos for captions, languages, timestamp quality, embedding, and acquisition reliability.
- Verify the coach/channel identity only from authoritative evidence; otherwise keep it unresolved.
- Record results in a corpus feasibility report.

Exit: at least three usable timed transcripts and a documented fallback for failures.

### Phase 1 — corpus pipeline (3–5 days)

- Scaffold Python package, configuration, schemas, and CLI.
- Implement discovery, metadata, transcript adapters, normalization, caching, manifests, and validation.
- Implement concept-candidate/evidence schemas and deterministic fixture extraction so concept lineage is designed into the pipeline from the beginning.
- Add fixtures/tests that require no network.

Exit: one command reproducibly creates valid normalized data for the seed set.

### Phase 2 — Codex CLI concept extraction and review (4–7 days)

- Implement the read-only `codex exec` runner and schema-constrained recipes for concept proposal, evidence classification, resolution, relationships, representative-moment ranking, and citation checking.
- Add preflight, subprocess safety, response validation, caching, resumable jobs, failure reporting, and Codex provenance.
- Benchmark `gpt-5.4-mini` at low reasoning on the golden pilot sample; keep escalation manual and verify the quality gates before running the full corpus.
- Add the file-based review queue, reviewed concept/annotation overlays, publish allowlist, provenance, and QA report.
- Review a small pilot set, including manual adjustment of visual-demonstration windows.

Exit: a repeatable command produces a reviewed, publishable concept corpus whose every item has valid segment evidence.

### Phase 3 — concept-first static MVP (4–6 days)

- Scaffold Astro with GitHub Pages base-path support.
- Implement home, concept index/page, relationship lists, library, video/player/transcript, unified search, methodology, and error states.
- Connect concept evidence to exact player seeking and full source context.
- Deploy via Actions and verify the public artifact contains only `data/publish/` data.

Exit: the public Pages URL works from a clean build; approved concepts are browsable and every displayed citation seeks correctly.

### Phase 4 — hardening and expansion

- Improve multilingual support, entity resolution, semantic search (only if justified), incremental refresh, performance, and accessibility.
- Add secondary artifacts such as summaries, drills, question cards, comparisons, learning paths, and an optional interactive concept graph after the concept core is proven.
- Add a second unrelated topic to prove domain independence.
- Measure index/site size and establish thresholds for repository splitting or external object storage.
- Optionally begin the separately scoped offline-media phase: rights gate, shared archive service, CLI, local-only Offline Manager UI, checksums, transcoding profiles, local player adapter, and portable offline build.

## 12. Testing strategy

- Unit: URL/video-ID parsing, timestamp conversion, caption merging, chunk boundaries, hashing, citation URL generation.
- Contract: adapters return the same canonical schema; JSON Schema validation for all artifacts.
- Fixture/integration: captured metadata/transcript samples, including no captions, disabled video, multilingual tracks, Shorts, live archive, deleted/private video, and malformed captions.
- Analysis: golden examples ensure claims cite supplied chunks and timestamps are aggregated rather than generated.
- Concept extraction: golden corpora test candidate extraction, alias resolution, non-merging of ambiguous terms, relationship direction, evidence classification, and stable IDs across reruns.
- UI: player seek behavior (mocked API), transcript sync, base-path routing, keyboard navigation, search, and mobile layout.
- Concept UX: concept search/browse, facet combinations, accessible relationship navigation, durable anchors, and exact seeking for every displayed demonstration.
- End-to-end: clean network-independent build of the checked-in corpus; deployed Pages smoke test.
- Content QA: sampled transcript accuracy, name/term accuracy, citation support, and creator attribution.
- Future offline controls: state-machine transitions, pause/resume after interruption, disk-space guardrails, shared CLI/UI queue state, destructive-action confirmations, loopback-only binding, and redacted diagnostics.

## 13. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| YouTube changes or blocks transcript access | Ingestion fails | Adapter boundary, local-first runs, raw cache, supplied-caption path, structured failures |
| Captions are absent or inaccurate | Poor knowledge quality | Coverage status, optional authorized local ASR, correction overlays, confidence/review labels |
| Copyright/platform concerns | Content removal or project risk | Embed/link media, minimize transcript display, attribution, exclusions, removal process, policy review |
| LLM hallucination or false synthesis | Misleading advice | Schema-constrained output, segment-ID citations, exact excerpts, deterministic timestamping, entailment pass, review states, no-source rejection |
| Codex availability, usage limits, or model changes | Incomplete or non-reproducible extraction | Preflight, response cache, resumable batches, budgets, recorded CLI/model metadata, golden-set evaluation |
| Codex subprocess hangs or returns invalid output | Pipeline stalls or corrupts artifacts | Timeout, exit-code handling, output schema, second validation, temporary files, atomic promotion |
| Extraction agent modifies project data | Corpus corruption | `--sandbox read-only`, processor-owned writes, never bypass sandbox, clean-worktree tests |
| Transcript chunks hide wider context | Duplicate or incorrect concepts | Overlap, per-video consolidation, corpus-resolution pass, uncertainty flags, human review |
| Static bundle/search grows too large | Slow site or Pages limit | Incremental data, compressed/sharded indexes, avoid media, size budgets, split corpus later |
| Future: local media archive consumes excessive disk | Failed or incomplete preservation | Profiles, size estimates, compact derivatives, reports, explicit retention/prune policy |
| Future: transcoding destroys instructional detail | Archive becomes less useful | Retain originals where possible, benchmark motion/detail, quality-targeted encodes, spot checks |
| Future: local drive failure or silent corruption | Preserved source is lost | SHA-256 verification, periodic audit, two copies on different devices |
| Future: archived media is accidentally published | Copyright/platform exposure | Gitignore media, separate offline build, deployment exclusion test, authorization gate |
| Future: offline controls delete or overwrite the wrong files | Data loss | Manifest-owned paths, preview/reclaim estimate, explicit confirmation, no automatic prune, idempotent operations |
| Future: local manager is exposed to the network | Unauthorized archive control | Loopback-only default, no remote access, explicit advanced opt-in, security tests |
| Identity/entity merge is wrong | Misattribution | Unresolved entities, authoritative verification, human review, reversible aliases |
| GitHub Action refresh is unreliable | Stale corpus | Treat refresh as optional; local CLI remains canonical; show `last_checked` |
| Generated changes create noisy diffs | Hard review | Stable ordering/formatting, input hashes, separate raw/derived files, PR summaries |
| Private/raw material leaks into Pages | Copyright or privacy exposure | Publish allowlist, separate `data/publish/`, artifact leakage test, no wildcard copying |

## 14. Decisions to make before implementation

1. Transcript visibility: full transcripts, short indexed excerpts, or local-only full text?
2. Repository visibility: GitHub Pages is free for a public repository on GitHub Free; is public source/data acceptable?
3. Escalation threshold: which validation/quality failures justify an explicit retry with `gpt-5.4`?
4. Languages: source-language only for MVP, or English translation as a first-class derived artifact?
5. Editorial model: maintainer-reviewed publishing, or publish unreviewed output with prominent labels?

Recommended defaults: public repository; no media files in Git or Pages; short excerpts on public pages; full raw transcripts retained locally until policy review; local/manual Codex CLI extraction using `gpt-5.4-mini` with low reasoning, read-only sandboxing, manual escalation, and a deterministic test engine; English UI with source-language evidence for the MVP and translation deferred; and maintainer review for concepts, relations, and claims while publishable transcript excerpts remain clearly labeled by source/type.

Future offline-phase decisions (not blockers for version 1): archive retention policy, codec/compatibility target, storage location, backup strategy, rights/authorization rules, and whether the first offline release ships the CLI and Offline Manager together or stages the UI immediately afterward.

## 15. Definition of done for version 1

- The repository contains documented, tested processors and a reproducible corpus manifest.
- A configured list of videos can be ingested locally without hand-editing generated data.
- The static site deploys free on GitHub Pages and builds without network access from committed publishable data.
- Users can browse, search, filter, play, seek by transcript timestamp, and follow topic connections.
- Concepts—not videos—form the primary browse layer, with stable pages, aliases, facets, prerequisites, and related-concept navigation.
- Every published concept has timestamped supporting evidence; core pilot concepts have at least one reviewer-verified demonstration moment.
- Summaries and structured knowledge expose exact source moments and generation/review status.
- LLM extraction is schema-constrained, cached, reproducible, and unable to publish a concept or relation without valid supporting segment IDs.
- The MVP extraction command preflights Codex, invokes `codex exec` in read-only mode, handles failures safely, and records CLI/model/prompt/schema provenance.
- The default extraction model is the golden-set-approved low-cost model (`gpt-5.4-mini` initially); stronger-model retries are explicit, traceable, and limited to flagged jobs.
- Failures, absent captions, uncertain identities, source languages, and machine-generated text are explicit.
- Human annotations survive regeneration.
- Policy, attribution, correction/removal, limitations, and data provenance are visible on the site.

## 16. Reference starting points

- [GitHub Pages documentation and limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)
- [YouTube Data API: captions.download](https://developers.google.com/youtube/v3/docs/captions/download)
- [YouTube IFrame Player API](https://developers.google.com/youtube/iframe_api_reference)
- [OpenAI Codex documentation](https://developers.openai.com/codex/)
- [`youtube-transcript-api`](https://github.com/jdepoix/youtube-transcript-api)
- [`yt-dlp`](https://github.com/yt-dlp/yt-dlp)
- [Astro deployment to GitHub Pages](https://docs.astro.build/en/guides/deploy/github/)
- [MiniSearch client-side search](https://github.com/lucaong/minisearch)
- [Pagefind static search (fallback)](https://pagefind.app/)
- [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper)
