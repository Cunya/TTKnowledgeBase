# MomentGraph

Current released checkpoint (2026-10-21 20h): **367/380 articles supported**; **13 remain** (10 pending,3 classified footage). Units:3582/4191 supported,600 pending,9 classified needs_footage. All35 actual proposed visual windows remain unverified. Zero structural/source-metadata findings;6overlap reviews remain. Control before power retained all33records,18actual citation completions and localconditions. Five full Luna/high calls plus two targeted calls passed40units,retaining36unchanged positive proofs. Source-primary review and guarded application passed. Fullrelease passed332tests(108.93s),Ruff,monitorchecks,validators and zero-diagnostic638pageAstrobuild. Exact40unit publicparity,1817article/1806TOCprose,380controls,67fresh toggles and25relationsbothdirections passed. Browser verification unavailable because local browser use is disabled in Work settings. Normal processing remains paused; nofootageapproval. See [control repair receipt](editorial-control-before-power-2026-10-21-20.md).

2026-10-21 20h released checkpoint:366/380articles supported;11pending+3classifiedfootage=14remaining.3542/4192units supported,641pending,9classifiedneeds_footage;all35actualvisualwindows unverified. Zero structural/source-metadatafindings,fiveoverlapreviews. Ready position source repair retained29approvedexamples and preserved both moved instructions in reviewed destinations; originalrecords remain archived in YAML,unrelatedunreviewed/demo records preserved. Whole15unitBodyrotation check plus36unchangedReadyproofs andexactprimary review passed. Fullrelease4328terminal0:332tests116.65s,Ruff,monitorchecks,validators,zeroAstro638pages. Exact77record public parity,1817article/1807TOCprose,380controls,67fresh toggles and25relationsbothdirections passed. Normalprocessingpaused,nofootageapproval. Evidence:[retention receipt](editorial-ready-retention-2026-10-21-20.md).

Visual inventory correction (2026-10-21 18h): all 35 current proposed visual windows remain unverified: nine already classified needs_footage plus 26 visual units in pending articles. Nine is a ledger-status subtotal, not the complete footage scope. Preserve every window; complete actual clip viewing is required before visual approval. Evidence: private media/audit-full-visual-inventory-2026-10-21-18.json. Current released article/unit counts remain unchanged.

Current full-audit checkpoint (2026-10-21 18h): 365/380 articles supported; 12 pending articles and three classified footage articles remain (15 total). Units: 3505/4193 supported, 679 pending, nine classified needs_footage; the complete visual inventory is 35 unverified windows, including 26 in pending articles. Zero structural/source-metadata findings; five overlap reviews remain. Short-ball receive decisions retained all28records with23bounded citation completions, local wording, an actual length-based relation source and removal of unsupported difficulty. Five full Luna/high calls plus one targeted three-unit check passed all35units with32unchanged positives retained. Full release passed332tests(292.82s),Ruff,nine monitor tests,validators and zero-diagnostic638pageAstro build; exact public35units,1817article/1807TOC prose,380controls and67fresh toggles passed. Browser confirmed28moments,oneplayer,disabledloop and valid parent route. Ready position has36/38 private units supported after4full calls plus one targeted wording check; two placement findings remain, with all31records preserved. P1-56 corrects reversed incoming relation labels; all380rendered sections/25relations pass both graph directions and the actual parent route says has part. Normalprocessing stayspaused; nofootageapproval. Evidence: [18h session](docs/Session%20Logs/2026-10-21-18.md), [receive receipt](docs/editorial-short-receive-2026-10-21-18.md). Older checkpoints below are historical.

MomentGraph is a source-grounded knowledge extraction engine for video. It turns timestamped YouTube transcripts into browsable, wiki-style knowledge bases: concepts are organized into hierarchies, related ideas are linked, and every claim points back to a precise source moment.

The repository is currently named `TTKnowledgeBase`, but the product name is **MomentGraph**. Table tennis is the first knowledge base; the processors and site are designed to support additional domains without hard-coded table-tennis assumptions.

## What it provides

- Concept-first wiki pages instead of flat transcript summaries.
- Hierarchies for shots, mechanics, timing, errors, tactics, and drills.
- Per-video table-of-contents pages with linear, timestamped sections.
- Cross-video concept pages with multiple supporting moments where available.
- Separate spoken citations and visual demonstrations. A transcript citation is not treated as proof that the movement is visible.
- YouTube links and standard embeds, with looping reserved for reviewed visual windows.
- File-based review queues and canonical YAML so editorial decisions remain inspectable and versionable.
- Independent knowledge bases isolated by KB ID, configuration, content, private processing data, and published routes.

Table-tennis corpus counts are generated by the processor during `publish` from local artifacts rather than edited by the LLM or maintained by hand. Run `python -m processors.cli publish --kb table-tennis` and inspect the local operator dashboard at `/progress/` for the current snapshot.

The [September 2026 specification review](docs/specification-gaps-and-issues-2026-09-19.md) records repaired validation/publication defects and the remaining product, editorial, and privacy gaps, with actions tracked in the consolidated backlog.

## Table Tennis knowledge base

Table tennis is the first production knowledge base in MomentGraph. It is a source-grounded study guide for learning strokes, movement, timing, tactics, and practice methods from instructional video. The content is organized as a wiki rather than as a list of transcript summaries.

Browse the [published table-tennis knowledge base](https://cunya.github.io/TTKnowledgeBase/kb/table-tennis/) or open the local version at `http://127.0.0.1:4321/kb/table-tennis/` during development.

### Sources and scope

The initial source set is deliberately focused on two public YouTube channels:

- **TT SpinMaster** (`@FreeCoachBradHan`, formerly configured as FreeCoachBradHan). The channel's coach attribution remains provisional; the repository does not assert an independently verified identity.
- **GlobalTTStudio** (`@GlobalTTStudio`). Some configured entries are members-only or otherwise unavailable and are tracked as ineligible rather than retried indefinitely.

The current collection emphasizes forehand-loop learning while also covering related table-tennis fundamentals: backhand and forehand strokes, serves and receive, spin, contact point, spacing, body coordination, weight transfer, recovery, errors, strategies, and drills. Source selection is recorded in `config/kbs/table-tennis/sources.yaml`; public availability and processing state are tracked separately from editorial approval.

### Knowledge structure

The table-tennis navigation uses a depth-aware topic tree. The main branches include:

```text
Table tennis
├── Shots and strokes
│   ├── Push
│   │   ├── Forehand
│   │   └── Backhand
│   ├── Counter
│   │   ├── Forehand
│   │   └── Backhand
│   ├── Loop
│   │   ├── Forehand
│   │   └── Backhand
│   └── Block
│       ├── Forehand
│       └── Backhand
├── Serves and receive
├── Training and drills
├── Tactics and strategies
└── Mechanics, timing, spacing, and recovery
```

Shot-related concepts live beneath the relevant shot family, with durable subtopics such as mechanics, timing, contact, spacing, selection, common errors, and drills. A concept may be cross-listed when it genuinely belongs to more than one learning path, while its canonical YAML file remains the single editorial source of truth.

### Evidence and video moments

Each concept page combines a concise editorial explanation with traceable evidence:

- **Spoken source** - a short transcript-backed citation with real segment IDs and a YouTube timestamp. It supports what the instructor says.
- **Visual source** - a separately selected nearby window where the movement is actually visible. It may be inferred or manually verified and is the only source eligible for looping.
- **Video moment** - a focused, repeatable clip grouped by meaning, with a link back to the source video and the corresponding concept.

Per-video pages provide a chronological table of contents so a long lesson can be studied linearly. Concept pages collect moments from multiple videos when the corpus contains supporting evidence, making it possible to compare explanations and demonstrations without turning the site into a transcript mirror.

### Editorial boundaries

Codex CLI proposes concepts, evidence groupings, and wording from supplied transcripts; it does not approve public knowledge. Reviewed concept YAML under `content/kbs/table-tennis/concepts/` is required before publication. Transcript excerpts are kept short and high-overlap text is rephrased or deferred. Visual windows are never marked verified from transcript text alone, and unavailable or removed source videos are not bypassed.

The table-tennis KB therefore remains useful even as the source catalog changes: it preserves original summaries, relationships, source links, and timestamps without copying a complete video transcript or hosting a public video archive.

## Architecture

```text
YouTube channel / supplied captions
              |
              v
     processors/ (Python CLI)
       discovery -> ingestion -> normalization
              |
              v
     Codex CLI extraction (local, budgeted)
              |
              v
     private candidates + deterministic review queue
              |
              v
     reviewed content/kbs/<kb>/concepts/*.yaml
              |
              v
     validate -> publish -> app/public/data/
              |
              v
     Astro static site -> GitHub Pages
```

The public site is a static artifact. GitHub Actions does not scrape YouTube, run Codex, download media, or require private transcripts. Only sanitized publish data is copied into `app/public/data/`.

## Repository map

- `processors/` - discovery, paced ingestion, Codex extraction, review-queue, validation, publishing, and budget controls.
- `config/knowledge-bases.yaml` - registered knowledge bases.
- `config/kbs/<kb>/` - sources, taxonomy, and KB settings.
- `config/processors.yaml` - Codex model/profile and LLM budget settings.
- `content/kbs/<kb>/concepts/` - reviewed canonical concept YAML, the editorial source of truth.
- `content/kbs/<kb>/annotations/` - file-based review decisions and notes.
- `data/normalized/` - private timed transcripts and metadata; generated and ignored.
- `data/derived/` - private Codex candidates; generated and ignored.
- `data/publish/` - sanitized publish output.
- `app/` - Astro site and static build.
- `app/public/data/` - browser-safe corpus data only.
- `media/` - temporary review media or future offline media; always ignored.

## Quick start

Prerequisites: Python 3.12+, Node.js 22+, and the Codex CLI for real extraction. The committed demo corpus can be built without network access or Codex.

```powershell
git clone https://github.com/cunya/TTKnowledgeBase.git
Set-Location TTKnowledgeBase

py -3.12 -m venv .venv
$env:PYTHONUTF8='1'
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

Set-Location app
npm install
npm run dev
```

Open `http://127.0.0.1:4321/`. The local operator dashboard is available at `/dashboard/`; it links to progress, backlog, pipeline, diagnostics, and review workspaces. `/human-review/` is an optional source-grounded advisory/override workspace; Codex CLI remains the normal decision path. These operator routes are intentionally removed from production builds.

On Windows, `start.bat` at the repository root stops any existing verified project monitor and Astro server, starts a fresh processor monitor, verifies `http://127.0.0.1:4322/`, and then runs the Astro development server in the foreground. Ctrl+C runs cleanup for both services; Windows may ask you to confirm terminating the batch job.

To run the network-free fixture path from the repository root:

```powershell
$env:PYTHONUTF8='1'
.\.venv\Scripts\python.exe -m processors.cli demo --kb table-tennis
.\.venv\Scripts\python.exe -m processors.cli validate --kb table-tennis
```

## Normal content pipeline

Run commands from the repository root with the checked virtual environment:

```powershell
$env:PYTHONUTF8='1'

# 1. Discover metadata; discovery alone does not ingest or publish anything.
.\.venv\Scripts\python.exe -m processors.cli discover CHANNEL_OR_PLAYLIST_URL --kb table-tennis

# 2. Ingest a small, curated batch of videos.
.\.venv\Scripts\python.exe -m processors.cli ingest --kb table-tennis VIDEO_URL_1 VIDEO_URL_2

# 3. Extract transcript-grounded concept candidates with Codex CLI.
.\.venv\Scripts\python.exe -m processors.cli extract-concepts --kb table-tennis --engine codex --video-id VIDEO_ID

# 4. Build and inspect the review queue.
.\.venv\Scripts\python.exe -m processors.cli build-review-queue --kb table-tennis
.\.venv\Scripts\python.exe -m processors.cli process-pending --kb table-tennis
.\.venv\Scripts\python.exe -m processors.cli build-inventory-ledger --kb table-tennis

# 5. After Codex semantic adjudication, validate and publish.
.\.venv\Scripts\python.exe -m processors.cli validate --kb table-tennis
.\.venv\Scripts\python.exe -m processors.cli publish --kb table-tennis
```

**Codex-first accuracy gate (2026-08-12):** `process-pending` now uses schema-constrained Codex CLI for the semantic accept/match/create/reject decision. Deterministic code separately requires a contiguous supported span, controlled facet vocabulary, complete timestamp envelopes, real segment IDs, and recorded model provenance. The 4,775 evidence moments and 460 concepts created by the previous heuristic path are quarantined and excluded from publication until Codex re-adjudicates them. See [the whole-project review](docs/project-review-2026-08-12-11.md).

`process-pending` refreshes the local `/concept-review/` diagnostics snapshot automatically. Queue rebuilds preserve decisions using candidate content hashes as well as video/candidate IDs, including distinct proposals with colliding extraction IDs. Bounded review batches favor fewer prior attempts, then the oldest attempt; deferred work remains retryable. Exact same-topic citations are retained once, and semantic review explicitly preserves grip, conditions, and incoming/outgoing roles; selected excerpt clauses must be supported by the cited rows. The monitor selects unclear-candidate videos fairly across sources; while all three sources have work, a 50-video pool rotates across them instead of exhausting one source first, but each automatic adjudication stage selects and processes at most 10 candidate decisions. Live adjudication output names the current pass (`x/10`), the eligible proposals in the selected videos, and the full adjudication backlog (`full adjudication backlog: remaining/starting-total`), so the backlog trend is visible across runs. Adjudication checkpoints the queue and changed concepts after every 10 completed candidates, so a stage timeout preserves prior progress. Codex deferrals remain automated work for a later bounded pass. `build-inventory-ledger` writes the private, gitignored per-video eligibility/completion ledger used by the orchestrator and operator dashboards.

Human input is optional advice or an explicit override, not the default queue. When desired, pause the processor loop after its active cycle finishes and open `http://127.0.0.1:4321/human-review/` to inspect exact cited rows and add an audited decision. The workspace never verifies a visual demonstration.

Ingestion honors each KB's ordered `language.transcript_priority` setting. It prefers an exact source-caption code such as `en`, then falls back to a regional source track such as `en-US` only when the exact code is unavailable; translation-language listings are not treated as source captions.

The `cp` workflow drains eligible cached transcripts and Codex-adjudication candidates before generating another small run batch. It first tries configured batch-history entries that still need acquisition, then continues automatically from unseen discovery-catalog entries only after extraction, adjudication, and acquisition worksets are empty. The configured video list is not the complete processing history or the videos selected for the current run. Every run obeys the prioritized backlog, pacing, source-policy checks, token budget, and block circuit breaker.

For the unattended/local full cycle, run the shared orchestrator from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\run-cp.py --kb table-tennis
```

It refreshes pending work, generates and processes the next small run batch, rebuilds review diagnostics, writes eligible evidence summaries, and publishes the reviewed corpus. When configured batch-history entries are exhausted and no extraction, adjudication, or acquisition work remains, it discovers enabled sources and chooses the most-viewed unseen videos where view counts are available; those continuation videos are not appended to `sources.yaml`. The private run manifest records the actual cached, configured, and discovered selections. The Windows Task Scheduler entry runs this workflow daily at 21:00 Europe/Helsinki time. For an interactive start/stop loop with live output and local budget reset, run `node scripts/processor-monitor.mjs` and open `http://127.0.0.1:4322/`.

The monitor remembers the last applied cooldown per knowledge base across restarts. Press Enter in the cooldown field to save/apply it without starting a stopped loop; Start/Stop are enabled only when applicable. The monitor streams stage output while work is running. Each stage is labeled `Stage x/y` for its position in the cycle, explains its purpose, emits a privacy-safe no-new-output heartbeat every 15 seconds, and records its elapsed duration when it finishes, so long quiet periods remain understandable. The processor workload runs at Windows idle CPU priority so it yields to interactive applications; the monitor UI remains normal priority. Discovery is limited to 20 minutes, ingestion and other stages to 45 minutes, and each ten-candidate semantic-adjudication stage to 60 minutes; a timeout is recorded explicitly and Windows Stop terminates nested processor workers as well as the parent. A single five-minute Codex adjudication timeout is isolated to that candidate, which is deferred with a private audit record so the rest of the ten-candidate batch can continue. Queue and changed-concept checkpoints occur every 10 completed adjudications.

Every study or review also updates the canonical Markdown backlog, the generated local `/backlog/` view, and the relevant project documentation before it is considered complete. See [the study-to-backlog documentation contract](docs/pipeline.md#study-to-backlog-documentation-contract).

Every published claim must cite real transcript segment IDs. Candidate JSON is a proposal, not public knowledge, and must be reviewed into canonical concept YAML. Spoken windows are kept short and focused; visual windows are separate and remain non-looping until a reviewer confirms that the footage actually demonstrates the concept.

## Codex model and daily budget

Codex-backed extraction, adjudication/auditing, rephrasing, and benchmarking use the configured low-cost profile (`gpt-6-luna`, high reasoning by default), explicitly selected by the operator on 2026-10-15. Automatic escalation is disabled. Historical results retain their original model provenance. All of these tasks share an adjustable local budget in `config/processors.yaml`:

```yaml
llm_budget:
  enabled: true
  timezone: Europe/Helsinki
  daily_token_limit: 90000000
  task_token_limits:
    extraction: 24000000
    adjudication: 60000000
    rephrase: 2000000
    benchmark: 2000000
    summary: 8000000
```

Check the private per-KB ledger with:

```powershell
.\.venv\Scripts\python.exe -m processors.cli llm-budget --kb table-tennis
```

The ledger and deferral records are ignored under `data/manifests/<kb>/`. A conservative estimate is reserved before a Codex call and reconciled afterward. When a daily or task limit is reached, new work is deferred instead of started. The local `/progress/` page shows usage, remaining allowance, calls, and deferrals; this section is not published.

## Source and platform safeguards

Ingestion is cache-first, sequential, and deliberately paced. Existing normalized transcripts are reused without network access. Each invocation targets up to 10 successful uncached videos; failed or cooling-down entries are skipped without consuming that success target, within a limited candidate window. When a source blocks transcript requests, the processor records a cooldown and stops rather than repeatedly retrying the same route. Cookies, proxy settings, credentials, raw transcripts, Codex audit data, and downloaded media are private and never belong in Git or GitHub Pages.

The public product is an independent study guide: original summaries, short attributed excerpts, source links, timestamps, and standard YouTube embeds. It is not a transcript mirror, video archive, or replacement player. Review [the legal/platform findings](docs/legal-review-youtube-2026-07-15.md) and [the precedent study](docs/youtube-knowledge-project-precedents-2026-07-15.md) before expanding acquisition or changing public content policy.

## GitHub Pages deployment

The repository includes validation and Pages deployment workflows. GitHub Pages publishes the committed sanitized corpus only.

1. Review and publish the local corpus.
2. Run the release checks below.
3. Commit and push the reviewed source and sanitized data to `main`.
4. In **Settings -> Pages**, select **GitHub Actions** as the source.
5. Run the deployment workflow or let the push trigger it.

For this repository, the project URL is:

```text
https://cunya.github.io/TTKnowledgeBase/
```

Astro derives the project base path from `GITHUB_REPOSITORY` during Actions builds; local development uses `/`. Production builds remove every operator route, including dashboard, progress, backlog, pipeline, diagnostics, review, human-review, source-discovery, research, and ASR pages, along with their navigation links.

## Multi-KB workflow

To add another topic:

1. Register it in `config/knowledge-bases.yaml`.
2. Copy `config/kbs/table-tennis/` to `config/kbs/<new-id>/` and replace its sources/taxonomy.
3. Create `content/kbs/<new-id>/concepts/` and its annotations directory.
4. Run every processor command with `--kb <new-id>`.
5. Validate and publish; the site will generate isolated `/kb/<new-id>/` routes.

Shared processors and site routes must remain domain-neutral. Domain terminology belongs in the KB taxonomy and reviewed content, not in generic pipeline code.

## Offline scope

Downloading, preserving, and transcoding source videos are future, user-controlled features. They are not part of the public MVP. A future offline mode must be a separate local-only tool with explicit rights/policy checks, manifest-owned paths, storage estimates, safe cleanup previews, and no GitHub Pages or public object-storage output. Keep the current public build source-linked and media-free.

## Release checks

Run these checks before publishing a new corpus or site change:

```powershell
$env:PYTHONUTF8='1'
.\.venv\Scripts\python.exe -m processors.cli validate --kb table-tennis
.\.venv\Scripts\python.exe -m processors.cli publish --kb table-tennis
.\.venv\Scripts\python.exe -m processors.cli validate-published --kb table-tennis
.\.venv\Scripts\python.exe -m processors.cli report-quality --kb table-tennis
.\.venv\Scripts\pytest.exe
.\.venv\Scripts\ruff.exe check .

Set-Location app
npm run build
```

For the complete data lineage, scripted-versus-LLM responsibilities, review gates, timestamp rules, and troubleshooting, see:

- [Pipeline documentation](docs/pipeline.md)
- [Operations guide](docs/operations.md)
- [Source video progress](docs/source-video-progress.md)
- [Exhaustive source-completion plan](docs/exhaustive-source-completion-plan-2026-08-05.md)
- [Prioritized backlog](docs/prioritized-backlog-2026-07-15.md)
- [Moment-boundary analysis study](docs/moment-boundary-analysis-study-2026-07-16.md)
- [Architecture and product plan](docs/youtube-knowledge-base-plan.md)

Published-content repairs now use the [complete audit workflow](docs/full-published-audit-workflow-2026-10-14.md) and [coverage report](docs/full-published-audit-coverage-2026-10-14.md), tracked under P1-50. Every article/citation/relation/visual claim is inventoried; changed inputs reopen reviews. Processing is paused for the full audit at the operator's request.

The latest reviewed audit checkpoint is **361/380 supported articles, 16 pending, 3 need footage**. The latest two-article batch and dependency reviews passed the full release gate and exact public/prose/control checks; actual-browser show-all verification also passed. All19remaining articles and9footage clips remain in scope; normal processing stays paused. See the [current coverage report](docs/full-published-audit-coverage-2026-10-14.md) and consolidated backlog.

Checkpoint at 2026-10-15 11:00 EEST: 23 supported / 354 pending articles among 377 eligible articles (176 supported / 4,325 pending units); two excluded originals retained in history. Ten additional articles were repaired and reviewed in this continuation. Repair contract 1.0.8 removes prior confidence/approval from independent verifier targets. The ordinary release gate passed at 10:58 EEST: reviewed/published validation, 203 Python tests, nine monitor tests, Ruff, zero Astro errors/warnings/hints and 635 built pages. Full semantic/visual audit completion remains blocked; processing stays paused. See the [continuation record](docs/automated-published-repair-study-2026-10-14.md#full-audit-continuation--2026-10-15).

The full-audit runner executes private semantic checks with resumable per-call checkpoints: run-published-audit --kb table-tennis --max-calls 10. Final campaign verification uses verify-release.ps1 -Kb table-tennis -RequireFullAudit; pending/fix/footage/metadata/stale work blocks it. Machine findings require independent editorial review before canonical changes or approval.

The default article path is now `plan-published-repairs --kb table-tennis --max-calls 20 --max-articles 10`: audit existing values first with complete citation proofs. Clean articles are not drafted again. Use `--repair-confirmed` for one targeted repair of confirmed failures and separate verification of changed claims; there is no automatic reducer/revision loop. Oversized proofs, unresolved semantics and footage stay explicit exceptions. The CLI refuses more than 20 calls per invocation and releases the KB lock after its article/call batch. Use `--concept-ids ID_1,ID_2` for controlled selection. Import staged exact plan/fingerprint-bound primary reviews with repeatable `--primary-review-file PATH --max-calls 0`; this makes zero model calls and grants no public approval. An imported rejection blocks application. Every new coverage-first plan requires an exact final primary-review artifact before application; changed plans need a fresh review. Unwatched visual claims stay needs_footage and cannot be approved by this source-only import. Existing valid terminal plans/call provenance are retained. Apply explicit reviewed IDs with the existing `apply-published-repairs` command; archives, transactions, freshness and full release gates remain mandatory.

`plan-duration-quarantines` and `plan-summary-format-repairs` prepare mechanical exclusions or exact boilerplate deletion without model calls or semantic audit credit. Normal processing honors the saved audit pause; publication does not regenerate summaries or auto-rephrase while paused. New Codex evidence acceptance receives a separate selected-source verification before canonical incorporation. No repair automation marks unwatched footage verified.

Repair efficiency update (2026-10-15 12:34 EEST): contract 1.1.0 adds stage-specific caches, dependency-checked unit verification reuse, targeted revisions and compact model inputs. All 377 articles / 4,501 units retain exact source coverage in the read-only compaction check; serialized draft inputs shrink 49.5%. Billed-token/runtime savings remain unmeasured. Two GPT-6 Luna controls still falsely accepted the known unsupported hand referent, so primary review remains required and processing stays paused. Coverage remains 23 supported / 354 pending. See [operations](docs/operations.md#audit-efficiency-follow-up).

Luna effort checkpoint (2026-10-15 12:44 EEST): current fixed effort is **high**, following the operator's request and official reviewer guidance. High alone did not fix the known false acceptance; verifier policy 1.1.1 adds general incomplete-clause referent checks. The revised high-effort pair rejected the bad claim and retained the supported control. Broad accuracy remains unproven; see [operations](docs/operations.md#luna-reviewer-effort-and-referent-check--2026-10-15-1244).

Processor transport update (2026-10-15 19:27 EEST): all supplied-text Codex jobs opt out of Apps per invocation, avoiding an unnecessary connector startup dependency. New private provenance records the opt-out; global settings and GPT-6 Luna/high remain unchanged. All 231 Python tests and Ruff pass; live retry/startup measurements and final idle release gate await the current campaign’s completion. See [operations](docs/operations.md#processor-apps-opt-out--2026-10-15-1927).

Account quota protection is configured in `llm_budget.account_quota`: default 80% cutoff, with the five-hour cutoff exempt during the final 10 minutes before reset. Weekly limits and local token budgets still apply. See [operations](docs/operations.md#account-quota-cutoff).

### Audit throughput

Reviewed difficulty-only removal can now generate private plans with zero model calls. Batch application reuses checked snapshots and faster value-checked archives; advisory overlap changes retain unchanged claim reviews while leaving overlap review pending. Use completed batches of 20–30 reviewed corrections with one full release gate. [Operations](docs/operations.md#throughput-implementation--2026-10-16-1426-eest) explains the commands and safeguards. The full corpus audit remains open; benchmark application speed separately from semantic clearance.

Current audit ledger:135/377 articles supported;242 remain pending. The latest two-article batch corrected drive-boundary wording and loop-specific weight loading. One spacing/jamming overlap remains unresolved. See the [current session checkpoint](docs/Session%20Logs/2026-10-16-19.md), [operations](docs/operations.md) and [original benchmark evidence](docs/audit-benchmark20-2026-10-16.md). Full corpus/footage clearance remains open;normal processing stays paused.




The [field-proof selection checkpoint](docs/audit-field-proof-selection-2026-10-17-14.md) records the bounded large-article repair path and its real Luna/high pilot. Final verification and primary review remain mandatory.


Audit checkpoint 2026-10-17 18:26 EEST: Resumed saved GPT-6 Luna/high finite jobs; applied complete source/primary-reviewed backspin timing and under-ball contact corrections. Coverage170/377 supported,207 pending;1331/4377 units supported,3046 pending,one overlap advisory. Retained valid conditional hook-serving warning; unsupported loose-grip relation archived. Broader timing topic moved to fundamentals. Source/visual guards retained; no footage approval. Small planner fix permits rejected private quarantine reauthoring only with exact primary findings; regression confirms no automatic retry or stale approval. Focused126 repair/CLI tests and Ruff passed; full release pending. Quota16%five-hour/16%weekly permits work; normal processing paused. Evidence: media/audit-under-ball-bounce-repair-2026-10-17-18.log and current session.


Latest audit checkpoint:172/377articles cleared,205remaining,1367/4374units supported. Balltracking/rhythm complete primary-reviewed corrections applied;normal processingpaused. See docs/Session Logs/2026-10-17-18.md.


Latest audit checkpoint:174/377articles cleared,203remaining;1410/4362units supported. Reviewed backswing/serve repairs applied with two actual spoken-source extensions;normal processingpaused. See docs/Session Logs/2026-10-17-19.md.


Latest audit checkpoint:175/377articles cleared,202remaining;1437/4360units supported. Full reviewed spacing correction applied;normal processingpaused. See docs/Session Logs/2026-10-17-20.md.


Latest audit checkpoint:176/377articles cleared,201remaining;1466/4356units supported. Backhand body coordination reviewed;normalprocessingpaused. See docs/Session Logs/2026-10-17-20.md.


Latest audit checkpoint:177/377articles cleared,200remaining;1480/4354units supported. Ballfeel reviewed;normalprocessingpaused. See docs/Session Logs/2026-10-17-20.md.


Retention recheck:all16historicalflags resolved (11supportedcurrent,5corrected). Fullaudit remains177/377cleared,200pending;normalprocessingpaused. See docs/Session Logs/2026-10-17-21.md.
