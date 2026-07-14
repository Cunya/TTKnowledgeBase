# Operating the MVP

For the complete data flow—including which stages are scripted, which require review, how Codex CLI is invoked, and why spoken and visual timestamps are separate—see [How the knowledge-base pipeline works](pipeline.md).

## 1. Prepare

Install Python 3.12+, Node.js 22+, Codex CLI, and dependencies. Authenticate Codex yourself with `codex login`; credentials and session data are never stored in this repository.

## 2. Discover and ingest

```powershell
python -m processors.cli discover https://www.youtube.com/@FreeCoachBradHan
python -m processors.cli ingest VIDEO_URL_1 VIDEO_URL_2
```

Review `data/manifests/discovered-videos.json` and start with a small curated set. Ingest writes normalized metadata and full timed transcripts to local processing data.

## 3. Extract with Codex

```powershell
python -m processors.cli extract-concepts --engine codex
python -m processors.cli build-review-queue
```

Codex runs in an ephemeral, read-only temporary directory using the configured low-cost model. Generated candidates appear under `data/derived/` and are not publishable by default.

## 4. Review

Review `content/kbs/<kb>/annotations/review-queue.yaml`. Approved canonical concepts are stored as individual YAML files under `content/kbs/<kb>/concepts/`. Each concept needs a stable ID/slug, approved status, and at least one evidence item with real segment IDs and a canonical timestamp URL. Use the committed table-tennis demo concepts as templates.

Do not mark a queue item accepted merely because it resembles an existing concept. At least one exact candidate segment must be incorporated into that canonical concept; otherwise leave the item pending or explicitly reject it. Keep each spoken evidence window within 30 seconds and split non-contiguous explanations into separate moments at transcript topic boundaries.

When adding candidates from newly processed videos, preserve existing queue decisions. The current `build-review-queue` command regenerates its output; do not run it over a manually reviewed queue without first arranging a merge or backup strategy.

## 5. Publish and verify

```powershell
python -m processors.cli publish
python -m processors.cli validate
cd app
npm run build
```

Only sanitized `data/publish/` files are copied into the site. Full transcripts, Codex job data, media, authentication state, and rejected/unreviewed candidates are excluded.

## Resilient transcript ingestion

Normal cached ingestion is deliberately slow and sequential:

```powershell
python -m processors.cli ingest --kb table-tennis --request-delay 5 --jitter 2 VIDEO_URLS
```

Existing normalized files are reused without network access. Use `--force` only when a transcript must be refreshed. When YouTube blocks the transcript endpoint, the command stops the batch and writes the next permitted retry time to the gitignored `data/manifests/<kb>/ingest-retries.json` file. Do not immediately rerun a blocked batch.

To import captions supplied by a creator or exported from an authorized source:

```powershell
python -m processors.cli ingest --kb table-tennis --caption-file C:\captions\lesson.vtt VIDEO_URL
```

The file may be VTT, WebVTT, or SRT and is normalized into stable segment IDs. One caption file applies to exactly one URL.

For yt-dlp's current YouTube extraction, configure an installed JavaScript runtime when needed:

```powershell
python -m processors.cli ingest --kb table-tennis --js-runtime node:C:\path\to\node.exe VIDEO_URL
```

Copy `.env.example` to a private `.env` or set its variables in the current shell for optional proxy configuration. A Netscape cookie file can be passed with `--cookie-file`; it must remain outside Git and should use a nonessential account because authenticated scraping can put the account at risk. Proxies and cookies are optional fallbacks, never automatic behavior.

Local transcription is a rights-gated last resort and requires the optional ASR dependency:

```powershell
pip install -e ".[asr]"
python -m processors.cli ingest --kb table-tennis --allow-audio-download --confirm-rights --whisper-model small VIDEO_URL
```

Both flags are mandatory. Audio is downloaded into a temporary directory, transcribed locally, and removed when the operation exits. Do not use this path without authorization to download and process the source.
