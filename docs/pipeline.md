# How the knowledge-base pipeline works

This project is a **local, operator-run publishing pipeline**, not a website that scrapes YouTube at request time. Python commands collect and transform source material on the maintainer's computer; Codex CLI proposes structured knowledge; reviewed YAML is the editorial source of truth; Astro builds a read-only static site for GitHub Pages.

## What is automated and what is manual

| Stage | Automated by the repository | Operator or reviewer responsibility |
|---|---|---|
| Source discovery | `yt-dlp` lists channel or playlist videos. | Choose relevant videos and record them in the KB source configuration. |
| Ingestion | Python fetches metadata and available timed captions and assigns stable segment IDs. | Supply video URLs, choose transcript languages, and investigate unavailable/member-only videos. |
| Knowledge extraction | The processor invokes `codex exec` with the transcript, taxonomy, known concepts, and a strict output schema. | Authenticate Codex, choose the configured model, and rerun failed jobs. |
| LLM budget | A private daily token ledger reserves an estimate before each extraction, rephrase, or benchmark call and records reported usage afterward. Exhausted daily or task caps defer work before subprocess execution. | Adjust `llm_budget` in `config/processors.yaml`, inspect `llm-budget --kb <id>`, and decide when deferred work should resume. |
| Candidate resolution | The review-queue builder proposes matches using names, aliases, fuzzy matching, and shared evidence. | Accept, reject, merge, rename, and edit concepts. No candidate becomes public merely because an LLM proposed it. |
| Spoken evidence | Validation checks every approved claim against real transcript segment IDs and canonical YouTube timestamps. | Check that the excerpt supports the editorial wording. |
| Excerpt safety | The deterministic overlap screen flags complete/high-ratio transcript matches; `rephrase-excerpts` or `publish --auto-rephrase-high-overlap` asks the configured low-cost Codex model for an editorial summary and verifies that the rewrite no longer has high overlap. | Review the rewrite when it changes a canonical excerpt; the source metadata and cited timestamps remain unchanged. |
| Visual examples | The data model stores a `visual_source` separately from the spoken `source`. | Locate a nearby movement demonstration, set its window and selection method, and eventually mark it manually verified. This is currently reviewer-assisted, not a finished automatic processor. |
| Publishing | Python validates and sanitizes the reviewed corpus, then copies only allowlisted data into the Astro public folder. | Run the publish command after review. |
| Site build | Astro generates static concept, video, search, and KB pages. | Preview locally and deploy the generated site through GitHub Pages. |

## Study-to-backlog documentation contract

An analysis or study is not complete when its Markdown report is written. The result must be carried through the planning and operator surfaces:

1. Record each actionable finding in `docs/prioritized-backlog-2026-07-15.md` with a priority, status, source study, dependencies, and acceptance criteria. Group related work under the appropriate feature workstream used by the local backlog page.
2. Rebuild the Astro site locally so `/backlog/` renders the updated Markdown source. Verify that the feature summary, item status, and links are present; do not hand-edit generated HTML.
3. Update the relevant operational documentation (`docs/pipeline.md`, `docs/operations.md`, README, or a domain/legal/content findings report) so the recommended process and the backlog item do not diverge.
4. Add a dated entry to the session log and session notes, including the study-to-backlog IDs and verification performed.

The Markdown backlog remains the planning source of truth. The HTML backlog is a generated local operator view and is intentionally excluded from the public GitHub Pages build.

## Data flow

```mermaid
flowchart LR
    Y["YouTube channels and videos"] --> D["discover"]
    D --> M["reviewable video manifest"]
    M --> I["ingest selected URLs"]
    I --> N["local normalized metadata and timed transcripts"]
    N --> C["Codex CLI structured extraction"]
    C --> Q["local candidate files and review queue"]
    Q --> R["reviewed concept YAML"]
    R --> E["high-overlap excerpt guard"]
    E --> V["validate and publish"]
    V --> P["sanitized public corpus"]
    P --> A["Astro static build"]
    A --> G["GitHub Pages"]
```

The raw/normalized transcripts, Codex responses, review media, and offline archives are gitignored. The browser receives only the sanitized corpus under `app/public/data/`.

## Normal operating sequence

Run commands from the repository root with the virtual environment active. Every command accepts `--kb`, so the same pipeline can operate independent knowledge bases.

### 1. Discover a channel

```powershell
python -m processors.cli discover https://www.youtube.com/@GlobalTTStudio --kb table-tennis
```

This writes a local discovery manifest. Discovery does not ingest transcripts or publish anything.

### 2. Select and ingest videos

Record the editorial selection in `config/kbs/<kb>/sources.yaml`, then pass the selected public URLs to ingestion:

```powershell
python -m processors.cli ingest --kb table-tennis `
  https://www.youtube.com/watch?v=VIDEO_ID_1 `
  https://www.youtube.com/watch?v=VIDEO_ID_2
```

`processors/ingest.py` uses `yt-dlp` for video metadata and a cache-first adapter chain for timed captions. It writes one private normalized JSON document per video under `data/normalized/<kb>/`. Each caption receives an ID such as `VIDEO_ID:00042`; later evidence cites these IDs instead of inventing timestamps.

The acquisition order is:

1. reuse an existing normalized video unless `--force` is supplied;
2. import an operator-supplied VTT/SRT when `--caption-file` is supplied;
3. try `youtube-transcript-api`;
4. try subtitle-only `yt-dlp` retrieval;
5. optionally download temporary audio and run `faster-whisper`, but only when both `--allow-audio-download` and `--confirm-rights` are supplied.

Network batches are sequential and paced by `--request-delay` plus randomized `--jitter`. Defaults use 20–40 seconds between uncached videos and cap each invocation at 8 uncached videos. A detected YouTube IP block opens a circuit breaker: ingestion records a private retry entry and stops the batch instead of sending more requests. Retry records use exponential backoff and live under `data/manifests/<kb>/ingest-retries.json`.

Ingestion continues after an individual video fails, retains successful results, and exits nonzero with a failure summary.

Optional proxy, cookie, JavaScript-runtime, and ASR settings are operator controlled. They are never published or committed. Proxy support accepts `--proxy-url` or the `YTKB_YOUTUBE_PROXY_URL` environment variable; the transcript library's Webshare adapter uses `YTKB_WEBSHARE_USERNAME` and `YTKB_WEBSHARE_PASSWORD`. `--cookie-file` is passed only to yt-dlp. `--js-runtime` (or `YTKB_YTDLP_JS_RUNTIME`) configures a supported yt-dlp JavaScript runtime such as `node:C:\\path\\node.exe`. PO-token provider plugins, when independently installed for yt-dlp, remain external operator configuration.

### 3. Extract concept candidates with Codex CLI

```powershell
python -m processors.cli extract-concepts --kb table-tennis --engine codex
```

To process only one normalized video:

```powershell
python -m processors.cli extract-concepts --kb table-tennis --engine codex --video-id VIDEO_ID
```

The Python processor is the caller. It starts `codex exec` as a subprocess using the settings in `config/processors.yaml`. The default profile uses `gpt-5.4-mini`, low reasoning, a strict Pydantic-generated JSON schema, a read-only sandbox, an ephemeral session, and a five-minute timeout. The stronger `gpt-5.4` profile is configured only for an explicit editorial retry; automatic escalation remains disabled. Codex receives transcript text and segment IDs, not downloaded video.

The response is validated before it is saved to `data/derived/<kb>/<video-id>.candidates.json`. The output records the Codex CLI version, model, reasoning setting, prompt/schema versions, and input hash. Invalid output or a failed command does not reach publishing.

### Daily LLM budget and deferral

All Codex-backed production tasks share a local per-knowledge-base ledger at `data/manifests/<kb>/llm-budget.json`. The defaults are configured in `config/processors.yaml`:

```yaml
llm_budget:
  enabled: true
  timezone: Europe/Helsinki
  daily_token_limit: 500000
  task_token_limits:
    extraction: 400000
    rephrase: 100000
    benchmark: 100000
```

The processor estimates prompt plus output tokens before starting Codex. It refuses the call when either the daily total or the task cap would be exceeded, records a deferred event, and lets the CLI continue without producing a partial candidate. Completed calls reconcile the reservation with Codex-reported `input_tokens` and `output_tokens`; when usage is unavailable, the estimate is charged conservatively. The ledger is private and ignored by Git.

Use the status command to see the current day, remaining allowance, per-task usage, calls, and deferrals:

```powershell
python -m processors.cli llm-budget --kb table-tennis
```

To change the allowance, edit `config/processors.yaml` before the next run. Set `enabled: false` only for an explicit operator decision; the default is enabled. Deferred extraction videos are listed in the private `data/manifests/<kb>/llm-deferred.json` record. The budget is a guard against unplanned usage, not a billing estimate, and it does not alter the configured model or reasoning profile.

If the optional auto-rephrase stage reaches its cap, `publish` records the deferral and exits before rebuilding the public corpus. This prevents the budget guard from weakening the excerpt-safety gate.

### 3a. Compare extraction-model output quality before changing the default

The model benchmark is deliberately separate from production extraction. It runs each requested model against a small, deterministic sample of cached transcripts and compares the result with reviewed, transcript-backed evidence:

```powershell
python -m processors.cli benchmark-models --kb table-tennis --sample-size 3
```

By default this compares the configured model with `gpt-5.4-nano`. To choose a different set or fixed videos:

```powershell
python -m processors.cli benchmark-models --kb table-tennis `
  --models gpt-5.4-mini,gpt-5.4-nano `
  --video-ids VIDEO_ID_1,VIDEO_ID_2
```

The report measures strict-schema success, whether evidence cites real input segment IDs, fuzzy overlap with reviewed concept names, and a conservative support proxy that also requires an exact overlap with reviewed evidence for the same video. It records Codex-reported token usage when available. These are screening signals, not automatic approvals; the benchmark writes only ignored files under `data/benchmarks/<kb>/latest.{json,md}` and never changes the production model, review queue, or published corpus. A model rejected by the current Codex account is reported as unavailable rather than scored as low quality.

### 4. Build and review the candidate queue

```powershell
python -m processors.cli build-review-queue --kb table-tennis
```

The generated queue lives at `content/kbs/<kb>/annotations/review-queue.yaml`. It suggests whether a candidate resembles an already reviewed concept, but fuzzy similarity never performs an automatic merge by itself.

An item may remain `accepted` only when at least one of its exact transcript segment IDs is present in evidence for the referenced canonical concept and video. A semantically similar candidate that was not incorporated stays `pending`; similarity alone is not evidence of editorial integration.

Reviewed public knowledge is stored as tracked YAML under `content/kbs/<kb>/concepts/`. An approved evidence item contains:

- `source`: the transcript-backed claim location, including segment IDs;
- optional `spoken_context_end_ms`: a reviewed playback boundary at the next transcript topic transition, without widening the claim citation;
- optional `visual_source`: a different window where the relevant movement is visible;
- `visual_status`: whether the demonstration is absent, inferred, or verified;
- editorial definition, evidence type, confidence, relations, and review status.

### 5. Select visual demonstration windows

Transcript extraction can locate an explanation but cannot prove that a useful movement is visible at that exact moment. For that reason the loop player must not treat `source` as a visual clip.

The current workflow is reviewer-assisted:

1. Start from the transcript evidence timestamp.
2. Inspect nearby video material, including moments immediately before and after the explanation.
3. Prefer a compact live-ball, shadow-stroke, comparison, or drill sequence that visibly demonstrates the specific concept.
4. Store that window as `visual_source`, normally no longer than 15 seconds.
5. Use `selection_method: nearby_visual_inference` until the complete clip has been watched and approved; use `manual_review` only after that check.
6. Keep the spoken `source` unchanged so the knowledge claim remains traceable.

For the forehand-loop pilot, I performed this stage manually with temporary, gitignored low-resolution review copies and timestamped contact sheets. I then edited the reviewed concept YAML with the inferred visual windows. The site loops only `visual_source`; transcript-only evidence is labeled **Play spoken citation** and looping is disabled.

A future processor can propose visual windows using scene/motion analysis and transcript cues, but its output should still remain a review candidate rather than silently becoming verified evidence.

### 6. Validate and publish

```powershell
python -m processors.cli validate --kb table-tennis
python -m processors.cli publish --kb table-tennis
```

For an automatic high-overlap rewrite pass before publishing, opt in explicitly:

```powershell
python -m processors.cli publish --kb table-tennis --auto-rephrase-high-overlap
```

The same stage can be run independently with `rephrase-excerpts`. It calls the configured `gpt-5.4-mini`
profile only for flagged excerpts, never escalates automatically, writes a private rewrite audit under
`data/manifests/<kb>/`, and changes only the canonical `excerpt` field. If Codex is unavailable or a rewrite still
has high overlap, the command fails rather than publishing an unverified result. Static builds and CI do not invoke
the stage implicitly, so they remain deterministic and network-free.

Validation checks concept IDs and slugs, graph targets/cycles, video existence, segment ownership, time bounds, and canonical URLs for both spoken and visual spans. Publishing includes approved concepts only, removes private transcripts from video metadata, excludes demo fixtures by default, and writes:

Spoken evidence is also constrained to a focused window of at most 30 seconds, and citations with gaps greater than 20 seconds must be split into separate evidence moments. Navigation validation requires every approved concept to have at least one topic-tree placement; repeated placements are allowed as explicit cross-listings, with the first placement treated as the primary path.

- `data/publish/kbs/<kb>/corpus.json` and `manifest.json`;
- matching browser-safe files under `app/public/data/kbs/<kb>/`;
- the multi-KB catalog under `app/public/data/catalog.json`.

Only videos referenced by published evidence enter the public corpus.

### 7. Test and build the site

```powershell
python -m pytest
ruff check .
cd app
npm run build
```

`npm run build` runs Astro diagnostics and generates the static site in `app/dist/`. For development:

```powershell
cd app
npm run dev
```

The resulting site has no server-side scraper, database, Codex credentials, or runtime LLM dependency.

## What I did for the current table-tennis corpus

I did call the repository commands manually from Codex's terminal rather than bypassing the pipeline:

1. searched both configured channel catalogs and curated public forehand-loop lessons;
2. added those selections to `sources.yaml`;
3. ran ingestion for the explicit video URLs;
4. ran Codex extraction per video and resumed the batch when a command window expired;
5. built the review queue;
6. reviewed and consolidated candidates into the forehand-loop hub and subtopic YAML files;
7. inspected nearby visual material and added separate inferred demonstration windows;
8. ran validation, publishing, Python tests, Ruff, Astro diagnostics, the static build, and local HTTP checks.

This means the pipeline is repeatable, but it is intentionally not fully unattended. Collection, extraction, validation, and build are scripted; source curation, knowledge approval, and visual-example approval are editorial gates.

As of 2026-07-16, the published table-tennis corpus contains 73 approved concepts, 121 supporting videos, and 1,814 non-demo evidence moments. The review queue contains 1,060 accepted, 139 explicitly deferred, and 1 rejected candidate; no candidates remain pending. The P1-02 cached review pass and controlled follow-up batches continue to incorporate only explicitly accepted matches; the latest two-public-video GlobalTTStudio continuation added 23 accepted candidates and 30 focused evidence moments, while deferred items remain out of the public corpus until reviewed. Every concept participates in the semantic relation graph. Exact accepted-candidate overlap, candidate fingerprints, navigation coverage, the 30-second spoken-window limit, large citation gaps, visual verification state, and public artifact consistency are enforced during validation.

CI uses `validate-published` because private normalized transcripts are intentionally absent from Git. This checks the sanitized corpus model, graph, navigation, evidence windows, visual-review consistency, manifest hash/counts, queue overlap, encoding quality, and byte-for-byte equality between the canonical publish output and Astro public copy. Local maintainers still run the stronger transcript-backed `validate` command before publishing.

Codex extraction does not request a service tier. Omitting the override uses the account's normal/default service and avoids the explicitly accelerated `fast` tier. The model and low reasoning setting remain controlled by `config/processors.yaml`, and automatic escalation remains disabled.

## Automation boundary

GitHub Actions may safely run tests and build already reviewed public data. It should not initially scrape channels, download media, or invoke Codex on a schedule. Those operations are local/manual because YouTube access can be fragile, Codex has authentication and cost implications, and neither LLM proposals nor inferred visual timestamps should publish without review.

Offline video download/transcoding remains a future, user-controlled feature. Any temporary review media or later offline archive stays outside Git and GitHub Pages.
