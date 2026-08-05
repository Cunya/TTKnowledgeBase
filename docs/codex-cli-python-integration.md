# Calling Codex CLI from Python

This document describes the Python-to-Codex CLI integration pattern used by MomentGraph. It is intentionally about subprocess integration and operational safeguards, not about the project’s knowledge-base content model.

## Basic pattern

Python should treat Codex CLI as a bounded external process:

1. Locate and preflight the executable.
2. Build the prompt and the JSON Schema separately.
3. Create an ephemeral temporary job directory.
4. Invoke `codex exec` with a list of arguments, never a shell string.
5. Send the prompt through standard input.
6. Capture structured output, diagnostics, and exit status.
7. Validate the output file against the same schema.
8. Record version, model, input hash, usage, and exit metadata.
9. Delete temporary files automatically when the call ends.

## Preflight

The project checks both installation and authentication before starting work:

```python
import shutil
import subprocess

executable = shutil.which("codex")
if not executable:
    raise RuntimeError("Codex CLI is not installed or is not on PATH")

version = subprocess.run(
    [executable, "--version"],
    capture_output=True,
    text=True,
    timeout=20,
    check=False,
)
if version.returncode != 0:
    raise RuntimeError(version.stderr.strip() or "Codex version check failed")

login = subprocess.run(
    [executable, "login", "status"],
    capture_output=True,
    text=True,
    timeout=20,
    check=False,
)
if login.returncode != 0:
    raise RuntimeError("Codex CLI is not authenticated")
```

The actual project implementation is `processors/codex_engine.py:30-49`. Preflight failures are raised before reserving or spending model budget.

## Constructing the command

Use an argument list so paths and values are not reinterpreted by a shell:

```python
command = [
    executable,
    "exec",
    "-",                         # read the prompt from stdin
    "--cd", str(job_dir),
    "--skip-git-repo-check",
    "--model", model,
    "--config", f'model_reasoning_effort="{reasoning}"',
    "--sandbox", "read-only",
    "--ephemeral",
    "--output-schema", str(schema_path),
    "--output-last-message", str(response_path),
    "--json",
]
```

Important properties:

- `-` makes standard input the prompt source.
- `--cd` gives the subprocess a temporary working directory.
- `--sandbox read-only` prevents the task from mutating the workspace.
- `--ephemeral` avoids durable session state for the job.
- `--output-schema` constrains the response format.
- `--output-last-message` provides a machine-readable response file.
- `--json` makes CLI event output parseable for usage and diagnostics.

Do not build this command as a single string, use `shell=True`, interpolate untrusted text into a shell command, or allow the model to choose its own executable, model, sandbox, or profile.

## Temporary files and schemas

The project writes prompt and schema files using `TemporaryDirectory`:

```python
import json
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory(prefix="codex-job-") as temporary:
    job_dir = Path(temporary)
    schema_path = job_dir / "response.schema.json"
    response_path = job_dir / "response.json"
    schema_path.write_text(
        json.dumps(response_model.model_json_schema(), indent=2),
        encoding="utf-8",
    )
    # invoke Codex while job_dir exists
```

Keep prompts, schemas, and response files in the temporary directory unless an audit record explicitly requires a sanitized copy. Never place credentials, cookies, raw transcripts, or private prompts in a public output directory.

## Running and capturing output

The project uses a bounded `subprocess.run` call:

```python
result = subprocess.run(
    command,
    input=prompt,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=timeout_seconds,
    check=False,
)
```

Use a timeout from configuration, not an unlimited wait. Capture both stdout and stderr because stdout can contain usage events while stderr explains authentication, schema, or process failures. `errors="replace"` prevents a diagnostic encoding error from hiding the actual subprocess result; the original audit should still be treated as potentially lossy.

A successful process is not enough. Require all of the following:

```python
if result.returncode != 0:
    raise RuntimeError(result.stderr.strip() or "Codex exited unsuccessfully")
if not response_path.exists():
    raise RuntimeError("Codex returned no structured response")

response = ResponseModel.model_validate_json(
    response_path.read_text(encoding="utf-8")
)
```

## Provenance and audit records

Record enough information to reproduce or explain the call without publishing its private input:

```python
provenance = {
    "cli_version": cli_version,
    "model": model,
    "reasoning_effort": reasoning,
    "prompt_version": prompt_version,
    "schema_version": schema_version,
    "input_hash": input_hash,
    "exit_code": result.returncode,
    "usage": parse_usage(result.stdout),
}
```

On failure, store bounded stderr/stdout tails in a private audit directory. Limit captured diagnostics so a provider or subprocess cannot create an unbounded audit file. Do not store the full prompt or response in a public artifact.

## Budget reservation

For model-backed work, the project reserves an estimated budget before execution and finalizes it after parsing reported usage:

```python
reservation = budget.reserve(task_name, prompt, input_hash=input_hash)
usage = None
try:
    result = subprocess.run(...)
    usage = parse_usage(result.stdout)
    provenance["budget"] = reservation.finish(usage)
finally:
    # If finish was not already called in the success path:
    if reservation_active:
        reservation.finish(usage)
```

The real implementation ensures finalization also occurs on exceptions. A budget limit must defer work before starting Codex; it must not be bypassed by retries or a model override.

## Failure categories

Handle these separately:

- executable missing: installation/configuration failure;
- login failure: authentication failure;
- timeout: bounded process failure; retain audit context;
- non-zero exit: inspect stderr and CLI event output;
- missing response file: protocol failure;
- invalid JSON/schema: model or integration contract failure;
- valid response rejected by editorial validation: proposal quality failure;
- budget refusal: expected deferral, not a subprocess failure.

Retry only when the failure is retryable and the retry remains within the configured budget. A stronger model or automatic escalation requires an explicit operator decision and provenance.

## Project references

- Implementation: `processors/codex_engine.py`
- Model/profile configuration: `config/processors.yaml`
- Budget implementation: `processors/llm_budget.py`
- Pipeline entry points: `processors/cli.py` and `scripts/run-cp.py`
- Higher-level usage and content safeguards: `docs/codex-cli-usage.md`
