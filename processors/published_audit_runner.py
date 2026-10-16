"""Bounded machine proposals for every unit in the exhaustive editorial audit."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import Field

from .codex_engine import CodexError, CodexResponseError, _run_schema_constrained_codex
from .llm_budget import LLMBudgetExceeded
from .models import StrictModel
from .utils import read_yaml, sha256_json, write_json

AUDIT_PROMPT_VERSION = "1.0.1"


class AuditUnitProposal(StrictModel):
    status: Literal["supported", "needs_fix", "needs_footage", "uncertain"]
    note: str = Field(min_length=1)
    supporting_segment_ids: list[str]


def review_unit_with_codex(
    payload: dict, config_path: Path, audit_dir: Path, budget_path: Path,
    heartbeat_callback: Callable[[], None] | None = None,
) -> tuple[dict, dict]:
    prompt = """Audit one existing published review unit. Return only the supplied JSON schema.
This is an error-finding proposal, never approval or a canonical edit.
Check every clause of the unit's prose and its topic mapping, necessary object/role/context
conditions, unsupported facets/difficulty/attribution, review-scaffolding prose, duplicate topics,
selected-caption completeness, citation timing, and relations when applicable.
Preserve the actual object described; its surface, position in space and motion mechanics are different topics.
Use only selected_rows as claim support. context_rows and other article text are NOT evidence.
For evidence units, all excerpt/reason clauses must be supported by this citation, not another video.
Review ONLY value for the specified unit. A field:evidence_summary or definition is article prose:
it may synthesize selected support from several citations/videos. Never impose the one-citation rule
on these fields. Labels/aliases are not evidence excerpts; do not flag their wording solely because
a separate citation needs repair. A citation need only be a supported, relevant example of the
article topic; it does not need to establish every clause of the article's broader definition.
Review scaffolding means editorial/model-process language in article prose, excerpts or reasons,
not a spoken introduction in the captions. Never propose deleting original caption rows.
For field/relations units, this may be one of several source chunks. Use supported only if this
chunk supports the ENTIRE unit. Use needs_fix for a demonstrable contradiction, wrong topic,
missing necessary qualifier, review-scaffolding, bad timestamp or source metadata inconsistency.
Use uncertain if support is absent/partial, caption quality is ambiguous, identity requires an
authoritative source, or this chunk cannot establish the complete claim; absence in one chunk is
not proof that the whole article is unsupported. Editorial classifications with no empirical claim
may be supported; technical/difficulty/conditions facets need actual support.
Boundary flags are review signals, not automatic factual errors. Preserve meaningful short moments.
Never invent a segment ID, timestamp, quotation, identity, or visual verification.
If a visual fact is required, use needs_footage. You have not watched any footage.
Supply exact selected supporting IDs for a supported substantive unit; an empty alias/facet list
has no substantive claim. Explain findings and needed repairs in note, without pretending to repair.
""" + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    input_hash = sha256_json({"prompt": prompt, "prompt_version": AUDIT_PROMPT_VERSION})
    schema = AuditUnitProposal.model_json_schema()
    allowed = {row["id"] for row in payload["selected_rows"]}
    if allowed:
        schema["properties"]["supporting_segment_ids"]["items"]["enum"] = sorted(allowed)
    else:
        schema["properties"]["supporting_segment_ids"]["maxItems"] = 0
    response, provenance = _run_schema_constrained_codex(
        prompt, schema, AuditUnitProposal, config_path, audit_dir,
        input_hash, AUDIT_PROMPT_VERSION, operation="published-audit", task="adjudication",
        budget_path=budget_path, heartbeat_callback=heartbeat_callback,
    )
    proposal = response.model_dump(mode="json")
    invalid = set(proposal["supporting_segment_ids"]) - allowed
    error = None
    if invalid:
        error = "Audit cited IDs outside its exact selected rows"
    elif proposal["status"] == "supported" and payload["value"] and not proposal["supporting_segment_ids"]:
        error = "Supported substantive audit unit has no selected supporting IDs"
    if error:
        write_json(audit_dir / f"{input_hash.removeprefix('sha256:')}.published-audit.failure.json",
                   {**provenance, "error": error, "proposal": proposal})
        raise CodexResponseError(error, provenance)
    write_json(audit_dir / f"{input_hash.removeprefix('sha256:')}.published-audit.json",
               {**provenance, "proposal": proposal})
    return proposal, provenance


def unit_jobs(item: dict, dossier: dict, config: dict, labels: list[dict]) -> list[dict]:
    """Split large articles by source rows; no unit or source chunk is silently dropped."""
    jobs = []
    cap = max(1, int(config.get("max_segments_per_job", 80)))
    selected_cap = max(1, cap - min(8, cap // 4))
    concept = dossier["concept"]
    for unit, editorial in item["decisions"].items():
        if editorial is not None:
            continue
        kind, key, *_ = unit.split(":", 2)
        if kind == "field":
            value = concept[key]
            sources = dossier["sources"][:len(concept["evidence"])]
        elif kind in {"evidence", "visual"}:
            value = concept["evidence"][int(key)]
            sources = [dossier["sources"][int(key)]]
        else:
            value = concept["relations"][int(key)]
            offset = len(concept["evidence"]) + sum(len(r["sources"]) for r in concept["relations"][:int(key)])
            sources = dossier["sources"][offset:offset+len(value["sources"])]
        selected = {row["id"]: row for source in sources for row in source["selected_rows"]}
        context = {row["id"]: row for source in sources for row in source["context_rows"] if row["id"] not in selected}
        rows = [selected[k] for k in sorted(selected)]
        chunks = [rows[i:i+selected_cap] for i in range(0, len(rows), selected_cap)] or [[]]
        if kind == "visual":
            chunks = [[]]
        for index, chunk in enumerate(chunks):
            payload = {
                "unit": unit, "value": value,
                "article": {k: concept[k] for k in ("id", "label", "short_definition", "concept_type")},
                "selected_rows": chunk,
                "context_rows": [context[k] for k in sorted(context)][:cap-len(chunk)],
                "source_metadata": {source["source"]["video_id"]: source["video"] for source in sources},
                "source_spans": [source["source"] for source in sources],
                "missing_segment_ids": [sid for source in sources for sid in source["missing_segment_ids"]],
                "boundary_flags": dossier["boundary_flags"],
                "topic_overlap_candidates": dossier.get("topic_overlap_candidates", []),
                "relation_targets": dossier["relation_targets"] if kind == "relation" else {},
                "existing_article_labels": labels if unit in {"field:label", "field:aliases"} else [],
                "chunk": index+1, "chunks": len(chunks), "total_selected_rows": len(rows),
            }
            job_id = sha256_json({"fingerprint": item["fingerprint"], "payload": payload,
                                  "config": config, "prompt_version": AUDIT_PROMPT_VERSION})
            jobs.append({"id": job_id, "unit": unit, "payload": payload, "visual": kind == "visual"})
    return jobs


def run_audit_jobs(
    audit: dict, dossiers: dict[str, dict], config_path: Path, audit_dir: Path,
    budget_path: Path, checkpoint_path: Path, *, max_calls: int,
    retry_failed: bool = False, reviewer: Callable = review_unit_with_codex,
    progress: Callable[[str], None] | None = None,
) -> dict:
    """Checkpoint private proposals per call, leaving editorial decisions untouched."""
    config = read_yaml(config_path)["codex"]
    labels = [{"id": d["concept"]["id"], "label": d["concept"]["label"], "aliases": d["concept"]["aliases"]}
              for _, d in sorted(dossiers.items())]
    plan = []
    for item in audit["items"]:
        jobs = unit_jobs(item, dossiers[item["concept_id"]], config, labels)
        item["machine_job_ids"] = [job["id"] for job in jobs]
        saved = item.setdefault("machine_jobs", {})
        for job in jobs:
            if job["id"] not in saved:
                saved[job["id"]] = {"unit": job["unit"], "status": "pending", "attempts": 0}
            if job["visual"]:
                saved[job["id"]].update(status="done", proposal={
                    "status": "needs_footage", "note": "Full-clip inspection is required; no footage was watched.",
                    "supporting_segment_ids": [],
                }, provenance={"method": "no_footage_inspected"})
            plan.append((item, job))
    write_json(checkpoint_path, audit)
    calls = 0
    for item, job in plan:
        saved = item["machine_jobs"][job["id"]]
        if saved["status"] == "done" or (saved["status"] == "failed" and not retry_failed):
            continue
        if calls >= max_calls:
            break
        message = f"{item['concept_id']} / {job['unit']} / source chunk {job['payload']['chunk']}/{job['payload']['chunks']}"
        if progress:
            progress(message)
        try:
            proposal, provenance = reviewer(
                job["payload"], config_path, audit_dir, budget_path,
                heartbeat_callback=(lambda message=message: progress(f"Waiting: {message}")) if progress else None,
            )
        except LLMBudgetExceeded as error:
            saved.update(status="budget_deferred", error=str(error))
            write_json(checkpoint_path, audit)
            return {"calls": calls, "stopped": "budget", **machine_summary(audit)}
        except (CodexError, ValueError) as error:
            saved.update(status="failed", error=str(error), provenance=getattr(error, "provenance", {}))
        else:
            saved.update(status="done", proposal=proposal, provenance=provenance)
            saved.pop("error", None)
        calls += 1
        saved["attempts"] += 1
        saved["updated_at"] = datetime.now(UTC).isoformat()
        write_json(checkpoint_path, audit)
    return {"calls": calls, "stopped": "call_limit" if calls >= max_calls else "no_pending_jobs", **machine_summary(audit)}


def machine_summary(audit: dict) -> dict:
    jobs = Counter()
    units = Counter()
    for item in audit["items"]:
        grouped = {}
        for job_id in item.get("machine_job_ids", []):
            job = item["machine_jobs"][job_id]
            if item["decisions"].get(job["unit"]) is not None:
                continue
            current = job
            if job["status"] == "done" and job.get("provenance", {}).get("method") != "no_footage_inspected" and job.get("provenance", {}).get("prompt_version") != AUDIT_PROMPT_VERSION:
                current = {**job, "status": "stale"}
            jobs[current["status"]] += 1
            grouped.setdefault(job["unit"], []).append(current)
        for chunks in grouped.values():
            states = {chunk["status"] for chunk in chunks}
            if states != {"done"}:
                units["failed" if "failed" in states else "pending"] += 1
                continue
            verdicts = {chunk["proposal"]["status"] for chunk in chunks}
            state = "needs_fix" if "needs_fix" in verdicts else (
                "needs_footage" if "needs_footage" in verdicts else (
                    "proposed_supported" if "supported" in verdicts else "uncertain"
                )
            )
            units[state] += 1
    return {"machine_job_status": dict(jobs), "machine_unit_status": dict(units),
            "machine_pass_complete": not any(value is None for item in audit["items"] for value in item["decisions"].values())
            or (bool(jobs) and set(jobs) == {"done"}),
            "source_metadata_findings": len(audit.get("source_metadata_findings", []))}
