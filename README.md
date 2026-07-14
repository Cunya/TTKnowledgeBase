# YouTube Knowledge Base

A source-grounded, concept-first platform for multiple independent knowledge bases generated from timestamped YouTube transcripts. The first configured KB covers table tennis. The MVP uses local Python processors and Codex CLI for structured extraction, then publishes a static Astro site to GitHub Pages.

The current published table-tennis corpus contains 70 approved concepts, metadata for 42 source videos, and 950 evidence moments. The review queue contains 383 accepted, 59 pending, and 1 rejected candidate after a 100-proposal editorial batch consolidated 99 grounded proposals. Spoken evidence is limited to focused 30-second windows; accepted candidates must be traceable to exact segment IDs in canonical content.

## Quick start

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m processors.cli demo --kb table-tennis
python -m processors.cli validate --kb table-tennis
cd app
npm install
npm run dev
```

The committed demo corpus works without network access or Codex. For real table-tennis videos, edit `config/kbs/table-tennis/sources.yaml`, then run `ingest --kb table-tennis` and `extract-concepts --kb table-tennis --engine codex`. Generated candidates require review before `publish --kb table-tennis` includes them.

Ingestion is cache-first and supports paced requests, block-aware retry records, yt-dlp subtitle fallback, supplied VTT/SRT files, optional operator-provided proxy/cookie settings, and explicitly rights-gated local transcription. See [operations](docs/operations.md#resilient-transcript-ingestion) for the controls and safety boundaries.

Normal publishing and validation exclude synthetic demo fixtures. Use `demo --kb table-tennis` for the network-free fixture, or pass `--include-demo` explicitly when validating fixture output.

Each KB is registered in `config/knowledge-bases.yaml` and owns matching folders under `config/kbs/` and `content/kbs/`. Private processing data and published corpora are also isolated by KB ID. Run `python -m processors.cli list-kbs` to inspect the registry.

To add another topic, add its registry entry, copy `config/kbs/table-tennis/` as a starting point, and create `content/kbs/<new-id>/concepts/`. All processing commands accept `--kb <new-id>`; publishing adds that corpus to the site catalog and generates isolated `/kb/<new-id>/` routes.

See [how the pipeline works](docs/pipeline.md) for the automated and manual stages, commands, data lineage, and visual-timestamp workflow. See [the implementation plan](docs/youtube-knowledge-base-plan.md) for architecture, policy, and future offline-media scope.

## Publish with GitHub Pages

The repository includes separate CI and Pages deployment workflows. GitHub builds only the committed sanitized corpus in `app/public/data/`; it does not ingest YouTube, download media, run Codex, or require private transcripts.

1. Commit the reviewed source and sanitized public data.
2. Push the `main` branch to GitHub.
3. In **Settings → Pages**, select **GitHub Actions** as the source.
4. Run **Deploy GitHub Pages** manually or let the push to `main` trigger it.

For the configured repository, the project URL will be:

```text
https://cunya.github.io/TTKnowledgeBase/
```

Astro derives `/TTKnowledgeBase` from `GITHUB_REPOSITORY` during Actions builds, while local development continues to use `/`. The workflow scans the generated site for raw transcript collections, media, cookies, environment files, and credential-like strings before upload.

Before committing a new corpus, run the release checks from the repository root:

```powershell
$env:PYTHONUTF8='1'
.\.venv\Scripts\python.exe -m processors.cli validate --kb table-tennis
.\.venv\Scripts\python.exe -m processors.cli publish --kb table-tennis
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check .
Set-Location app
npm run build
```
