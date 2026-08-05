# Codex CLI usage in MomentGraph

This project uses the Codex CLI as a local, controlled proposal engine. It does not let Codex edit canonical public knowledge directly. Python prepares the input, invokes `codex exec` with a constrained task, validates the response, and stores the private result for review.

## Role in the pipeline

```text
private timed transcript
        |
        v
Python builds a bounded prompt and JSON schema
        |
        v
codex exec  ---> private candidate/audit response
        |
        v
schema validation, provenance, review queue
        |
        v
reviewed concept YAML ---> validate ---> publish
```

Codex output is always a proposal. A candidate becomes public only after it is represented in reviewed YAML under `content/kbs/<kb>/concepts/`, has supported evidence, and passes the processor validators.

## Extraction

Run commands from the repository root with the checked virtual environment:

```powershell
$env:PYTHONUTF8='1'
.\.venv\Scripts\python.exe -m processors.cli extract-concepts `
  --kb table-tennis `
  --engine codex `
  --video-id VIDEO_ID
```

The Python processor supplies Codex with:

- the selected knowledge-base taxonomy;
- known reviewed concepts for matching and consolidation;
- private timed transcript segments and stable segment IDs;
- the required structured response schema;
- source-grounding and editorial safety instructions.

The extraction prompt requires Codex to cite only supplied segment IDs. It must not invent timestamps, quotations, coaches, source attribution, or visual demonstrations. Visual evidence is separate from spoken transcript evidence and remains `transcript_inferred` until a reviewer watches the footage.

Private extraction artifacts are written below `data/derived/<kb>/` and are not publishable. They may contain transcript context, model responses, prompts, schemas, and audit metadata.

## Candidate review

Build the file-based queue and process eligible cached candidates:

```powershell
.\.venv\Scripts\python.exe -m processors.cli build-review-queue --kb table-tennis
.\.venv\Scripts\python.exe -m processors.cli process-pending --kb table-tennis
```

Automatic review can accept only candidates meeting the configured source-grounding and editorial rules. Ambiguous candidates remain deferred. The review queue is not a substitute for canonical editorial review; inspect and correct promoted YAML before release.

## Evidence summaries and rephrasing

Deterministic summaries are the normal low-cost path:

```powershell
.\.venv\Scripts\python.exe -m processors.cli build-evidence-summaries `
  --kb table-tennis `
  --engine deterministic `
  --write
```

Codex may be used for reviewed summary prose when explicitly chosen:

```powershell
.\.venv\Scripts\python.exe -m processors.cli build-evidence-summaries `
  --kb table-tennis `
  --engine codex `
  --write
```

Generated summaries carry a source hash and generator marker. Deterministic summaries may be refreshed by publishing; Codex-generated summaries require an explicit refresh decision. Summary prompts prohibit transcript-reporting language, unsupported claims, bullets, and long quotations.

High-overlap excerpts can be rephrased through the configured Codex profile, but source IDs, timestamps, and source metadata remain unchanged:

```powershell
.\.venv\Scripts\python.exe -m processors.cli rephrase-excerpts --kb table-tennis
```

## Model, profile, and budget controls

The model and execution profile come from `config/processors.yaml`. Commands must use that configured default. Do not silently switch to a more expensive model, enable automatic escalation, or bypass the configured execution wrapper.

Extraction, rephrasing, summaries, and benchmarks use the private per-KB LLM budget. Inspect it with:

```powershell
.\.venv\Scripts\python.exe -m processors.cli llm-budget --kb table-tennis
```

Before a Codex call, the processor reserves an estimate. Afterward it reconciles reported usage. If a daily or task limit is exhausted, work is deferred before subprocess execution. The ledger under `data/manifests/<kb>/` is private and must not be published.

## Auditability and failure behavior

Each Codex-backed operation is:

- local and operator-triggered;
- read-only with respect to canonical reviewed content;
- schema-constrained;
- time-bounded by the calling pipeline stage;
- recorded with task, model/profile, prompt/schema provenance, and response metadata;
- subject to deterministic validation before it can enter review.

The processor preserves failed and deferred work for inspection. A failed Codex call must not be treated as an approved concept. Retry only after inspecting the failure and respecting the configured budget and source locks.

The unattended cycle is:

```powershell
.\.venv\Scripts\python.exe scripts\run-cp.py --kb table-tennis
```

The local processor monitor runs this orchestrator without overlapping cycles. A YouTube transcript block is treated as route-wide: the circuit breaker stops before further network access while the block cooldown is active. Non-blocking video errors remain per-video and do not stop unaffected work.

## Publish gate

Codex artifacts are private. Before publishing, run:

```powershell
.\.venv\Scripts\python.exe -m processors.cli validate --kb table-tennis
.\.venv\Scripts\python.exe -m processors.cli publish --kb table-tennis
.\.venv\Scripts\python.exe -m processors.cli validate-published --kb table-tennis
```

For a release gate, also run pytest, Ruff, and the Astro build. Public output may contain reviewed concepts, short source-grounded excerpts, timestamps, links, sanitized evidence, and approved visual metadata. It must not contain raw transcripts, Codex audit data, prompts, credentials, cookies, downloaded media, or offline archives.

## Operator checklist

1. Check the backlog and current monitor manifest before starting a batch.
2. Confirm the per-KB budget and source/block status.
3. Use the configured model/profile and explicit `--kb`.
4. Inspect deferred, accepted, and rejected candidate decisions.
5. Review canonical concept YAML, especially taxonomy placement and visual status.
6. Validate and publish only after the editorial gate passes.
7. Keep private transcripts, derived responses, audit data, and media out of Git and the public site.
