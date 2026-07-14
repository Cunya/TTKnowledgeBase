from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from .models import ExtractionResponse, Segment
from .utils import read_yaml, sha256_json, write_json

PROMPT_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0.0"


class CodexError(RuntimeError):
    pass


def preflight(service_tier: str = "flex") -> tuple[str, str]:
    executable = shutil.which("codex")
    if not executable:
        raise CodexError("Codex CLI is not installed or is not on PATH")
    version = subprocess.run([executable, "--version"], capture_output=True, text=True, timeout=20)
    if version.returncode != 0:
        raise CodexError(version.stderr.strip() or "Could not read Codex CLI version")
    login = subprocess.run(
        [executable, "-c", f'service_tier="{service_tier}"', "login", "status"],
        capture_output=True,
        text=True,
        timeout=20,
    )
    if login.returncode != 0:
        raise CodexError("Codex CLI is not authenticated. Run `codex login` first.")
    return executable, version.stdout.strip()


def build_prompt(segments: list[Segment], taxonomy: dict, known_concepts: list[dict]) -> str:
    segment_lines = "\n".join(
        f"[{segment.id}] {segment.start_ms}-{segment.end_ms}ms: {segment.normalized_text}"
        for segment in segments
    )
    return f"""You extract a source-grounded concept knowledge base from a transcript batch.

Rules:
- Return only data matching the supplied JSON Schema.
- Cite only segment IDs present below. Every concept needs evidence.
- Do not invent timestamps; cite segment IDs only.
- Prefer concrete teachable concepts over generic words.
- Preserve terms used by the speaker as aliases.
- Mark uncertain identity/merges as ambiguous.
- A visual demonstration is transcript_inferred unless a human has verified it.

Taxonomy:
{json.dumps(taxonomy, ensure_ascii=False, indent=2)}

Known concepts:
{json.dumps(known_concepts, ensure_ascii=False, indent=2)}

Transcript segments:
{segment_lines}
"""


def extract_with_codex(
    segments: list[Segment],
    taxonomy: dict,
    known_concepts: list[dict],
    config_path: Path,
    audit_dir: Path,
) -> tuple[ExtractionResponse, dict]:
    config = read_yaml(config_path)["codex"]
    service_tier = config.get("service_tier", "flex")
    executable, cli_version = preflight(service_tier)
    model = config["default_model"]
    reasoning = config.get("reasoning_effort", "low")
    timeout = int(config.get("timeout_seconds", 300))
    schema = ExtractionResponse.model_json_schema()
    prompt = build_prompt(segments, taxonomy, known_concepts)
    input_hash = sha256_json({"segments": [s.model_dump() for s in segments], "prompt": prompt})

    with tempfile.TemporaryDirectory(prefix="ytkb-codex-") as temporary:
        job_dir = Path(temporary)
        prompt_path = job_dir / "prompt.md"
        schema_path = job_dir / "response.schema.json"
        response_path = job_dir / "response.json"
        prompt_path.write_text(prompt, encoding="utf-8")
        schema_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
        command = [
            executable,
            "exec",
            "-",
            "--cd",
            str(job_dir),
            "--skip-git-repo-check",
            "--model",
            model,
            "--config",
            f'model_reasoning_effort="{reasoning}"',
            "--config",
            f'service_tier="{service_tier}"',
            "--sandbox",
            "read-only",
            "--ephemeral",
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(response_path),
            "--json",
        ]
        result = subprocess.run(
            command,
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        provenance = {
            "cli_version": cli_version,
            "model": model,
            "reasoning_effort": reasoning,
            "prompt_version": PROMPT_VERSION,
            "schema_version": SCHEMA_VERSION,
            "input_hash": input_hash,
            "exit_code": result.returncode,
        }
        if result.returncode != 0 or not response_path.exists():
            audit_dir.mkdir(parents=True, exist_ok=True)
            write_json(
                audit_dir / f"{input_hash.removeprefix('sha256:')}.failure.json",
                {
                    **provenance,
                    "stderr": result.stderr[-4000:],
                    "stdout": result.stdout[-8000:],
                },
            )
            raise CodexError(result.stderr.strip() or "Codex returned no response")
        response = ExtractionResponse.model_validate_json(response_path.read_text(encoding="utf-8"))
        return response, provenance
