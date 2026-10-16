from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

from pydantic import ValidationError

from .llm_budget import LLMTokenBudget
from .models import (
    CandidateAdjudicationResponse,
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
ADJUDICATION_PROMPT_VERSION = "1.1.2"


class CodexError(RuntimeError):
    pass


class CodexTimeoutError(CodexError):
    """A Codex call exceeded its bounded per-call timeout."""

    def __init__(self, message: str, provenance: dict, timeout_seconds: int) -> None:
        super().__init__(message)
        self.provenance = provenance
        self.timeout_seconds = timeout_seconds


class CodexResponseError(CodexError):
    """A model response was returned but failed the requested response schema."""

    def __init__(self, message: str, provenance: dict) -> None:
        super().__init__(message)
        self.provenance = provenance


def _run_captured_with_heartbeat(
    command: list[str],
    prompt: str,
    timeout: int,
    heartbeat_callback: Callable[[], None],
    *,
    heartbeat_interval: int = 15,
) -> subprocess.CompletedProcess[str]:
    """Capture Codex output while allowing a caller to report bounded progress."""
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    pending_input: str | None = prompt
    elapsed = 0
    while True:
        remaining = max(1, timeout - elapsed)
        wait_for = min(heartbeat_interval, remaining)
        try:
            stdout, stderr = process.communicate(input=pending_input, timeout=wait_for)
            return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
        except subprocess.TimeoutExpired as error:
            pending_input = None
            elapsed += wait_for
            if elapsed >= timeout:
                process.kill()
                stdout, stderr = process.communicate()
                raise subprocess.TimeoutExpired(
                    command, timeout, output=stdout, stderr=stderr
                ) from error
            heartbeat_callback()


def _captured_text(value: object) -> str:
    """Normalize partial subprocess output before writing a private audit record."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


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
            "--config",
            "notify=[]",
            "--config",
            "features.apps=false",
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
                "apps_enabled": False,
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


def adjudicate_candidate_with_codex(
    candidate: dict,
    segments: list[Segment],
    known_concepts: list[dict],
    taxonomy: dict,
    config_path: Path,
    audit_dir: Path,
    *,
    model_override: str | None = None,
    budget_path: Path | None = None,
    task: str = "adjudication",
    heartbeat_callback: Callable[[], None] | None = None,
) -> tuple[CandidateAdjudicationResponse, dict]:
    """Use Codex CLI to make one transcript-grounded semantic queue decision."""
    segment_lines = "\n".join(
        f"[{segment.id}] {segment.start_ms}-{segment.end_ms}ms: {segment.normalized_text}"
        for segment in segments
    )
    prompt = f"""Semantically adjudicate one proposed knowledge-base concept against exact transcript text.

Rules:
- Return only data matching the supplied JSON Schema.
- Accept only when the exact selected segment IDs directly support the final excerpt and reason.
- An accepted publication span must be one contiguous topic moment no longer than 30 seconds.
- Rewrite the excerpt and reason so they describe only the selected span; do not retain claims from omitted locations.
- Preserve every necessary qualifier (grip, incoming/outgoing ball, spin, depth, player role, and conditions) in definitions and excerpts; never turn conditional advice into a universal instruction.
- Distinguish the player's outgoing shot from the opponent's incoming ball. Shared vocabulary alone does not establish the same concept.
- Preserve the object being described. A region on the ball, a region on the racket, spatial contact position, and hand or force mechanics are different topics; shared contact vocabulary does not justify mapping one to another.
- Every clause of the excerpt must be supported by the selected IDs, not merely nearby context. Include the supporting rows or omit that clause.
- For accepted decisions, the reason is reader-facing knowledge about the technique, not a review justification. Omit supplied-concept comparisons, segment IDs, span duration, and validation commentary.
- New definitions and facets must be supported by the selected rows; omit facets that are merely inferred from the proposal.
- Write definitions as neutral descriptions of the technique; omit speaker-reporting prose and preserve whether the advice handles incoming spin or generates outgoing spin.
- Editorial advice identifies issues to recheck; it is not transcript evidence and cannot justify accepting an unsupported claim.
- Use accept_existing only when one supplied concept is the same durable topic, and copy its exact ID.
- Use create_new only for a distinct durable wiki topic, never for a moment-specific paraphrase or duplicate.
- Use reject when the proposal is unsupported, generic, redundant, or misclassified.
- Use defer only when the supplied transcript is genuinely insufficient for a defensible decision.
- Cite only supplied segment IDs. Reject/defer decisions must return no segment IDs.
- A transcript cannot verify a visual demonstration.

Candidate proposal:
{json.dumps(candidate, ensure_ascii=False, indent=2)}

Possible existing concepts:
{json.dumps(known_concepts, ensure_ascii=False, indent=2)}

Allowed taxonomy and facet vocabulary:
{json.dumps(taxonomy, ensure_ascii=False, indent=2)}

Exact cited rows plus bounded nearby context:
{segment_lines}
"""
    schema = CandidateAdjudicationResponse.model_json_schema()
    input_hash = sha256_json(
        {
            "candidate": candidate,
            "segments": [segment.model_dump(mode="json") for segment in segments],
            "known_concepts": known_concepts,
            "taxonomy": taxonomy,
            "prompt_version": ADJUDICATION_PROMPT_VERSION,
        }
    )
    response, provenance = _run_schema_constrained_codex(
        prompt, schema, CandidateAdjudicationResponse, config_path, audit_dir,
        input_hash, ADJUDICATION_PROMPT_VERSION, model_override=model_override,
        budget_path=budget_path, task=task, heartbeat_callback=heartbeat_callback,
    )
    audit_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        audit_dir / f"{input_hash.removeprefix('sha256:')}.adjudication.json",
        {
            **provenance,
            "decision": response.decision,
            "selected_segment_ids": response.segment_ids,
            "canonical_concept_id": response.canonical_concept_id,
        },
    )
    return response, provenance


def _run_schema_constrained_codex(
    prompt: str,
    schema: dict,
    response_model: type,
    config_path: Path,
    audit_dir: Path,
    input_hash: str,
    prompt_version: str,
    *,
    operation: str = "adjudication",
    model_override: str | None = None,
    budget_path: Path | None = None,
    task: str = "adjudication",
    heartbeat_callback: Callable[[], None] | None = None,
) -> tuple:
    """Shared read-only, schema-constrained, bounded and budgeted CLI transport."""
    config = read_yaml(config_path)["codex"]
    service_tier = config.get("service_tier")
    executable, cli_version = preflight(service_tier)
    model = model_override or config["default_model"]
    reasoning = config.get("reasoning_effort", "low")
    timeout = int(config.get("timeout_seconds", 300))
    budget = LLMTokenBudget(config_path, budget_path) if budget_path else None
    reservation = budget.reserve(task, prompt, input_hash=input_hash) if budget else None
    with tempfile.TemporaryDirectory(prefix=f"ytkb-{operation}-") as temporary:
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
            "--config",
            "notify=[]",
            "--config",
            "features.apps=false",
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
            try:
                if heartbeat_callback is None:
                    result = subprocess.run(
                        command,
                        input=prompt,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=timeout,
                    )
                else:
                    result = _run_captured_with_heartbeat(
                        command,
                        prompt,
                        timeout,
                        heartbeat_callback,
                    )
            except subprocess.TimeoutExpired as error:
                partial_stdout = _captured_text(error.output)
                partial_stderr = _captured_text(error.stderr)
                usage = parse_codex_usage(partial_stdout)
                provenance = {
                    "cli_version": cli_version,
                    "model": model,
                    "reasoning_effort": reasoning,
                    "apps_enabled": False,
                    "prompt_version": prompt_version,
                    "schema_version": SCHEMA_VERSION,
                    "input_hash": input_hash,
                    "exit_code": None,
                    "usage": usage,
                    "timeout_seconds": timeout,
                }
                audit_dir.mkdir(parents=True, exist_ok=True)
                write_json(
                    audit_dir / f"{input_hash.removeprefix('sha256:')}.{operation}.failure.json",
                    {
                        **provenance,
                        "error_type": "timeout",
                        "error": f"Codex {operation} timed out after {timeout} seconds",
                        "stderr": partial_stderr[-4000:],
                        "stdout": partial_stdout[-8000:],
                    },
                )
                raise CodexTimeoutError(
                    f"Codex {operation} timed out after {timeout} seconds",
                    provenance,
                    timeout,
                ) from error
            usage = parse_codex_usage(result.stdout)
            provenance = {
                "cli_version": cli_version,
                "model": model,
                "reasoning_effort": reasoning,
                "apps_enabled": False,
                "prompt_version": prompt_version,
                "schema_version": SCHEMA_VERSION,
                "input_hash": input_hash,
                "exit_code": result.returncode,
                "usage": usage,
            }
            if result.returncode != 0 or not response_path.exists():
                audit_dir.mkdir(parents=True, exist_ok=True)
                write_json(
                    audit_dir / f"{input_hash.removeprefix('sha256:')}.{operation}.failure.json",
                    {
                        **provenance,
                        "stderr": result.stderr[-4000:],
                        "stdout": result.stdout[-8000:],
                    },
                )
                raise CodexError(result.stderr.strip() or f"Codex returned no {operation}")
            response_text = response_path.read_text(encoding="utf-8")
            try:
                response = response_model.model_validate_json(response_text)
            except ValidationError as error:
                audit_dir.mkdir(parents=True, exist_ok=True)
                write_json(
                    audit_dir / f"{input_hash.removeprefix('sha256:')}.{operation}.failure.json",
                    {
                        **provenance,
                        "error_type": "response_schema_validation",
                        "error": str(error),
                        "response": response_text[:12000],
                    },
                )
                raise CodexResponseError(
                    f"Codex {operation} response failed schema validation: {error}",
                    provenance,
                ) from error
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
            "--config",
            "notify=[]",
            "--config",
            "features.apps=false",
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
                "apps_enabled": False,
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
            "--config",
            "notify=[]",
            "--config",
            "features.apps=false",
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
                "apps_enabled": False,
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
            "--config",
            "notify=[]",
            "--config",
            "features.apps=false",
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
                "apps_enabled": False,
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
