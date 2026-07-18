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

All Codex-backed tasks share an adjustable daily token budget. The configured total and per-task caps live in `config/processors.yaml` under `llm_budget`; usage is kept in the private, gitignored `data/manifests/<kb>/llm-budget.json`. A call is estimated before `codex exec` starts, and extraction, rephrasing, or benchmarking is deferred when the daily or task cap would be exceeded. Inspect the current allowance with:

```powershell
python -m processors.cli llm-budget --kb table-tennis
```

Deferred extraction work is recorded in `data/manifests/<kb>/llm-deferred.json` and can be resumed on a later day or after adjusting the config. This ledger counts conservative token units reported by Codex (or the pre-call estimate when usage is unavailable); it is not a billing estimate.

The local `/recent/` view orders lessons and connected concepts by `ingested_at`, so a newly processed older YouTube lesson appears as a recent addition. Both `ingest` and `publish` write a local-only normalized-video snapshot, allowing newly ingested videos with no extracted concepts yet to appear as **Awaiting extraction/review** without an LLM or manual edit. New normalized videos record this timestamp directly; legacy cached videos use their normalized-file modification time as a transparent fallback. The original YouTube publication date remains displayed separately.

When `publish --auto-rephrase-high-overlap` reaches the budget, publication stops rather than silently shipping excerpts that still require rephrasing. Run the command again after the daily reset or after deliberately increasing the configured allowance.

To compare a cheaper model before changing `config/processors.yaml`, run the isolated quality benchmark on cached transcripts:

```powershell
python -m processors.cli benchmark-models --kb table-tennis --sample-size 3
```

Read `data/benchmarks/table-tennis/latest.md`. If a model is unavailable through the current Codex account, the report labels it unavailable; that is a capability result, not a quality score.

## 4. Review

Review `content/kbs/<kb>/annotations/review-queue.yaml`. Approved canonical concepts are stored as individual YAML files under `content/kbs/<kb>/concepts/`. Each concept needs a stable ID/slug, approved status, and at least one evidence item with real segment IDs and a canonical timestamp URL. Use the committed table-tennis demo concepts as templates.

Do not mark a queue item accepted merely because it resembles an existing concept. At least one exact candidate segment must be incorporated into that canonical concept; otherwise leave the item pending or explicitly reject it. Keep each spoken evidence window within 30 seconds and split non-contiguous explanations into separate moments at transcript topic boundaries.

Run the caption-only boundary baseline when reviewing moment quality:

```powershell
python -m processors.cli report-boundaries --kb table-tennis `
  --markdown-output docs/moment-boundary-report-table-tennis-YYYY-MM-DD.md
```

This measures sentence-boundary and short-window flags from cached captions without using Codex. New candidates flagged by the same assessment are deferred by `process-pending`; review them as merge, context, split, or defer actions before acceptance. The proposed snapped interval is playback guidance only until the reviewer records an approved boundary.

When adding candidates from newly processed videos, `build-review-queue` regenerates deterministic candidate content while preserving existing decisions, canonical mappings, and review notes by video and candidate ID. Review the diff after a rebuild, especially if extraction was rerun and candidate IDs may have changed.

For a cached review batch, use the conservative P1-02 triage command before scraping anything else:

```powershell
python -m processors.cli process-pending --kb table-tennis
```

It incorporates high-confidence matches and can create a new canonical concept when the extractor explicitly marks it `new`, the confidence and definition gates pass, it is not a near-duplicate, and its cited transcript span validates. Ambiguous, weak, duplicate, and invalid candidates remain `deferred`. Use `process-pending --retry-deferred` to backfill candidates deferred by earlier runs.

The `cp` shortcut follows the same order: finish eligible cached transcripts and candidates first; when no local work remains, continue with the next small, controlled discovery/ingestion batch. It must still obey the prioritized backlog, acquisition-policy checks, pacing limits, and block circuit breaker. A cleared local queue does not authorize bypassing an active “no large scrape” gate.

For a safe Windows Task Scheduler entry point, run:

```powershell
Set-Location D:\Code\AIAssistedProjects\TTKnowledgeBase
.\scripts\run-daily-processing.ps1 -Kb table-tennis -DryRun
.\scripts\run-daily-processing.ps1 -Kb table-tennis
```

The wrapper uses a private per-KB lock, writes `data/manifests/<kb>/daily-processing.latest.json`, and exits with code `10` when another run is active. It only runs `process-pending`; it does not scrape, commit, push, deploy, or publish unreviewed knowledge. The current local Task Scheduler registration runs daily at 21:00 Europe/Helsinki time; recreate it manually with `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ...` if the workstation task is lost.

The `cm` shortcut is message-only: review the current local changes and return a suggested commit message with completed features written in past tense. Do not stage files, run `git commit`, or create a commit; the operator commits manually.

## Study and backlog synchronization

Treat every architecture, legal/platform, content, pipeline, or quality study as an input to the project backlog. Before closing the study:

- add or update its actionable findings in `docs/prioritized-backlog-2026-07-15.md`, including priority, status, source study, dependencies, and acceptance criteria;
- rebuild the local site and verify `/backlog/`, which generates the feature-oriented HTML view from that Markdown file; and
- update the relevant process or findings documentation and the dated session log/notes.

The Markdown file is canonical; the HTML page is a generated local management view and is not published to GitHub Pages. If a study produces no actionable work, record that conclusion in the study and session notes instead of creating an empty backlog item.

## 5. Publish and verify

```powershell
python -m processors.cli publish --auto-rephrase-high-overlap
python -m processors.cli validate
python -m processors.cli validate-published
python -m processors.cli report-quality --output docs/quality-report-table-tennis.json --markdown-output docs/quality-report-table-tennis.md
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

The CLI enforces that cooldown before making another request. After changing to a genuinely different VPN or proxy route, pass `--retry-blocked` once to test the new route. Do not use the flag to retry the same blocked IP. Supplying `--proxy-url` or configured Webshare credentials also counts as an alternate route.

Prevention defaults are deliberately conservative: uncached videos are spaced by 20 seconds plus up to 20 seconds of random jitter, and one invocation attempts at most 8 uncached videos. Cached videos do not consume that budget. Do not defeat the cap by immediately launching repeated batches; leave a substantial break between runs. There is no universally safe request rate, especially on shared VPN or datacenter exits whose reputation is affected by other users. For sustained ingestion, use an operator-controlled rotating residential proxy and retain the same pacing.

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
