from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from .llm_budget import LLMTokenBudget
from .models import (
    EvidenceSummaryBatchResponse,
    EvidenceSummaryResponse,
    ExcerptRewriteResponse,
    ExtractionResponse,
    Segment,
)
from .utils import read_yaml, sha256_json, write_json

PROMPT_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0.0"
REPHRASE_PROMPT_VERSION = "1.0.0"
SUMMARY_PROMPT_VERSION = "1.0.0"
BATCH_SUMMARY_PROMPT_VERSION = "1.0.0"


class CodexError(RuntimeError):
    pass


def preflight(service_tier: str | None = None) -> tuple[str, str]:
    executable = shutil.which("codex")
    if not executable:
        raise CodexError("Codex CLI is not installed or is not on PATH")
    version = subprocess.run([executable, "--version"], capture_output=True, text=True, timeout=20)
    if version.returncode != 0:
        raise CodexError(version.stderr.strip() or "Could not read Codex CLI version")
    login_command = [executable]
    if service_tier:
        login_command.extend(["-c", f'service_tier="{service_tier}"'])
    login_command.extend(["login", "status"])
    login = subprocess.run(
        login_command,
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
    model_override: str | None = None,
    *,
    budget_path: Path | None = None,
    task: str = "extraction",
) -> tuple[ExtractionResponse, dict]:
    config = read_yaml(config_path)["codex"]
    service_tier = config.get("service_tier")
    executable, cli_version = preflight(service_tier)
    model = model_override or config["default_model"]
    reasoning = config.get("reasoning_effort", "low")
    timeout = int(config.get("timeout_seconds", 300))
    schema = ExtractionResponse.model_json_schema()
    prompt = build_prompt(segments, taxonomy, known_concepts)
    input_hash = sha256_json({"segments": [s.model_dump() for s in segments], "prompt": prompt})
    budget = LLMTokenBudget(config_path, budget_path) if budget_path else None
    reservation = (
        budget.reserve(task, prompt, input_hash=input_hash) if budget else None
    )

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
            "--sandbox",
            "read-only",
            "--ephemeral",
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(response_path),
            "--json",
        ]
        if service_tier:
            command[command.index("--sandbox"):command.index("--sandbox")] = [
                "--config",
                f'service_tier="{service_tier}"',
            ]
        usage: dict | None = None
        try:
            result = subprocess.run(
                command,
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
            usage = parse_codex_usage(result.stdout)
            provenance = {
                "cli_version": cli_version,
                "model": model,
                "reasoning_effort": reasoning,
                "prompt_version": PROMPT_VERSION,
                "schema_version": SCHEMA_VERSION,
                "input_hash": input_hash,
                "exit_code": result.returncode,
                "usage": usage,
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
            response = ExtractionResponse.model_validate_json(
                response_path.read_text(encoding="utf-8")
            )
            if reservation:
                provenance["budget"] = reservation.finish(usage)
            return response, provenance
        except Exception:
            if reservation:
                reservation.finish(usage)
            raise


def parse_codex_usage(stdout: str) -> dict | None:
    """Extract the final token-usage object from Codex JSONL when available."""
    usage = None
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        candidate = event.get("usage")
        if not candidate and isinstance(event.get("turn"), dict):
            candidate = event["turn"].get("usage")
        if isinstance(candidate, dict):
            usage = candidate
    return usage


def summarize_evidence_with_codex(
    concept_label: str,
    reasons: list[str],
    config_path: Path,
    audit_dir: Path,
    *,
    model_override: str | None = None,
    max_chars: int = 1600,
    budget_path: Path | None = None,
    task: str = "summary",
) -> tuple[str, dict]:
    """Turn reviewed evidence reasons into a coherent editorial paragraph."""
    config = read_yaml(config_path)["codex"]
    service_tier = config.get("service_tier")
    executable, cli_version = preflight(service_tier)
    model = model_override or config["default_model"]
    reasoning = config.get("reasoning_effort", "low")
    timeout = int(config.get("timeout_seconds", 300))
    prompt = f"""Write a coherent English knowledge-base summary for the concept below.

Rules:
- Return only data matching the supplied JSON Schema.
- Write one cohesive paragraph of 2–4 complete sentences, not a list of fragments.
- Synthesize the ideas and their relationships; do not copy labels or concatenate source notes.
- Do not mention the speaker, coach, source, transcript, evidence, moments, examples, or this prompt.
- Do not use quotation marks and do not reproduce transcript wording.
- Add no claim that is not supported by the supplied reviewed reasons.
- Keep the result under {max_chars} characters.

Concept:
{concept_label}

Reviewed editorial reasons:
{json.dumps(reasons, ensure_ascii=False, indent=2)}
"""
    schema = EvidenceSummaryResponse.model_json_schema()
    input_hash = sha256_json(
        {
            "concept_label": concept_label,
            "reasons": reasons,
            "prompt_version": SUMMARY_PROMPT_VERSION,
            "max_chars": max_chars,
        }
    )
    budget = LLMTokenBudget(config_path, budget_path) if budget_path else None
    reservation = budget.reserve(task, prompt, input_hash=input_hash) if budget else None
    with tempfile.TemporaryDirectory(prefix="ytkb-summary-") as temporary:
        job_dir = Path(temporary)
        schema_path = job_dir / "response.schema.json"
        response_path = job_dir / "response.json"
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
            "--sandbox",
            "read-only",
            "--ephemeral",
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(response_path),
            "--json",
        ]
        if service_tier:
            command[command.index("--sandbox") : command.index("--sandbox")] = [
                "--config",
                f'service_tier="{service_tier}"',
            ]
        usage: dict | None = None
        try:
            result = subprocess.run(
                command,
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
            usage = parse_codex_usage(result.stdout)
            provenance = {
                "cli_version": cli_version,
                "model": model,
                "reasoning_effort": reasoning,
                "prompt_version": SUMMARY_PROMPT_VERSION,
                "schema_version": SCHEMA_VERSION,
                "input_hash": input_hash,
                "exit_code": result.returncode,
                "usage": usage,
            }
            if result.returncode != 0 or not response_path.exists():
                audit_dir.mkdir(parents=True, exist_ok=True)
                write_json(
                    audit_dir / f"{input_hash.removeprefix('sha256:')}.summary.failure.json",
                    {**provenance, "stderr": result.stderr[-4000:], "stdout": result.stdout[-8000:]},
                )
                raise CodexError(result.stderr.strip() or "Codex returned no summary")
            response = EvidenceSummaryResponse.model_validate_json(
                response_path.read_text(encoding="utf-8")
            )
            if len(response.summary) > max_chars:
                raise CodexError("Codex returned a summary longer than the configured limit")
            if reservation:
                provenance["budget"] = reservation.finish(usage)
            audit_dir.mkdir(parents=True, exist_ok=True)
            write_json(
                audit_dir / f"{input_hash.removeprefix('sha256:')}.summary.json",
                {**provenance, "output_chars": len(response.summary)},
            )
            return response.summary.strip(), provenance
        except Exception:
            if reservation:
                reservation.finish(usage)
            raise


def summarize_evidence_batch_with_codex(
    concepts: list[dict],
    config_path: Path,
    audit_dir: Path,
    *,
    model_override: str | None = None,
    max_chars: int = 1600,
    budget_path: Path | None = None,
    task: str = "summary",
) -> tuple[dict[str, str], dict]:
    """Synthesize several concepts in one Codex call to reduce overhead."""
    config = read_yaml(config_path)["codex"]
    service_tier = config.get("service_tier")
    executable, cli_version = preflight(service_tier)
    model = model_override or config["default_model"]
    reasoning = config.get("reasoning_effort", "low")
    timeout = int(config.get("timeout_seconds", 300))
    prompt = f"""Write coherent English knowledge-base summaries for every concept below.

Rules:
- Return exactly one summary for every supplied concept ID, matching the JSON Schema.
- Each summary must be one cohesive paragraph of 2–4 complete sentences, not a list.
- Synthesize the ideas and their relationships; do not concatenate source notes.
- Do not mention the speaker, coach, source, transcript, evidence, moments, examples, or this prompt.
- Do not use quotation marks or reproduce transcript wording.
- Add no claim that is not supported by that concept's reviewed reasons.
- Keep each summary under {max_chars} characters.

Concepts and their reviewed editorial reasons:
{json.dumps(concepts, ensure_ascii=False, indent=2)}
"""
    schema = EvidenceSummaryBatchResponse.model_json_schema()
    input_hash = sha256_json(
        {
            "concepts": concepts,
            "prompt_version": BATCH_SUMMARY_PROMPT_VERSION,
            "max_chars": max_chars,
        }
    )
    budget = LLMTokenBudget(config_path, budget_path) if budget_path else None
    reservation = budget.reserve(task, prompt, input_hash=input_hash) if budget else None
    with tempfile.TemporaryDirectory(prefix="ytkb-summary-batch-") as temporary:
        job_dir = Path(temporary)
        schema_path = job_dir / "response.schema.json"
        response_path = job_dir / "response.json"
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
            "--sandbox",
            "read-only",
            "--ephemeral",
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(response_path),
            "--json",
        ]
        if service_tier:
            command[command.index("--sandbox") : command.index("--sandbox")] = [
                "--config",
                f'service_tier="{service_tier}"',
            ]
        usage: dict | None = None
        try:
            result = subprocess.run(
                command,
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
            usage = parse_codex_usage(result.stdout)
            provenance = {
                "cli_version": cli_version,
                "model": model,
                "reasoning_effort": reasoning,
                "prompt_version": BATCH_SUMMARY_PROMPT_VERSION,
                "schema_version": SCHEMA_VERSION,
                "input_hash": input_hash,
                "exit_code": result.returncode,
                "usage": usage,
                "concept_ids": [item["concept_id"] for item in concepts],
            }
            if result.returncode != 0 or not response_path.exists():
                audit_dir.mkdir(parents=True, exist_ok=True)
                write_json(
                    audit_dir / f"{input_hash.removeprefix('sha256:')}.summary-batch.failure.json",
                    {**provenance, "stderr": result.stderr[-4000:], "stdout": result.stdout[-8000:]},
                )
                raise CodexError(result.stderr.strip() or "Codex returned no summary batch")
            response = EvidenceSummaryBatchResponse.model_validate_json(
                response_path.read_text(encoding="utf-8")
            )
            expected = {item["concept_id"] for item in concepts}
            received = [item.concept_id for item in response.summaries]
            if set(received) != expected or len(received) != len(expected):
                raise CodexError("Codex summary batch did not return exactly one item per concept")
            if any(len(item.summary) > max_chars for item in response.summaries):
                raise CodexError("Codex returned a summary longer than the configured limit")
            if reservation:
                provenance["budget"] = reservation.finish(usage)
            audit_dir.mkdir(parents=True, exist_ok=True)
            write_json(
                audit_dir / f"{input_hash.removeprefix('sha256:')}.summary-batch.json",
                {**provenance, "output_chars": sum(len(item.summary) for item in response.summaries)},
            )
            return {item.concept_id: item.summary.strip() for item in response.summaries}, provenance
        except Exception:
            if reservation:
                reservation.finish(usage)
            raise


def rephrase_excerpt_with_codex(
    excerpt: str,
    transcript_text: str,
    config_path: Path,
    audit_dir: Path,
    *,
    model_override: str | None = None,
    max_chars: int = 420,
    budget_path: Path | None = None,
    task: str = "rephrase",
) -> tuple[str, dict]:
    """Ask the configured Codex profile to turn a source excerpt into an editorial summary."""
    config = read_yaml(config_path)["codex"]
    service_tier = config.get("service_tier")
    executable, cli_version = preflight(service_tier)
    model = model_override or config["default_model"]
    reasoning = config.get("reasoning_effort", "low")
    timeout = int(config.get("timeout_seconds", 300))
    prompt = f"""Rewrite one public knowledge-base evidence excerpt as an original editorial summary.

Rules:
- Return only data matching the supplied JSON Schema.
- Do not quote the speaker and do not use quotation marks.
- Preserve the source-grounded meaning, but use new wording and sentence structure.
- Add no claims that are not supported by the transcript excerpt.
- Keep the result concise and at most {max_chars} characters.
- This is an editorial summary, not a transcript or a dialogue.

Current public excerpt:
{excerpt}

Cited transcript context:
{transcript_text}
"""
    schema = ExcerptRewriteResponse.model_json_schema()
    input_hash = sha256_json(
        {
            "excerpt": excerpt,
            "transcript_text": transcript_text,
            "prompt_version": REPHRASE_PROMPT_VERSION,
            "max_chars": max_chars,
        }
    )
    budget = LLMTokenBudget(config_path, budget_path) if budget_path else None
    reservation = (
        budget.reserve(task, prompt, input_hash=input_hash) if budget else None
    )
    with tempfile.TemporaryDirectory(prefix="ytkb-rephrase-") as temporary:
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
            "--sandbox",
            "read-only",
            "--ephemeral",
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(response_path),
            "--json",
        ]
        if service_tier:
            command[command.index("--sandbox") : command.index("--sandbox")] = [
                "--config",
                f'service_tier="{service_tier}"',
            ]
        usage: dict | None = None
        try:
            result = subprocess.run(
                command,
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
            usage = parse_codex_usage(result.stdout)
            provenance = {
                "cli_version": cli_version,
                "model": model,
                "reasoning_effort": reasoning,
                "prompt_version": REPHRASE_PROMPT_VERSION,
                "schema_version": SCHEMA_VERSION,
                "input_hash": input_hash,
                "exit_code": result.returncode,
                "usage": usage,
            }
            if result.returncode != 0 or not response_path.exists():
                audit_dir.mkdir(parents=True, exist_ok=True)
                write_json(
                    audit_dir / f"{input_hash.removeprefix('sha256:')}.rephrase.failure.json",
                    {
                        **provenance,
                        "stderr": result.stderr[-4000:],
                        "stdout": result.stdout[-8000:],
                    },
                )
                raise CodexError(result.stderr.strip() or "Codex returned no rephrase")
            response = ExcerptRewriteResponse.model_validate_json(
                response_path.read_text(encoding="utf-8")
            )
            if len(response.excerpt) > max_chars:
                raise CodexError("Codex returned an excerpt longer than the configured limit")
            audit_dir.mkdir(parents=True, exist_ok=True)
            if reservation:
                provenance["budget"] = reservation.finish(usage)
            write_json(
                audit_dir / f"{input_hash.removeprefix('sha256:')}.rephrase.json",
                {**provenance, "output_chars": len(response.excerpt)},
            )
            return response.excerpt, provenance
        except Exception:
            if reservation:
                reservation.finish(usage)
            raise
