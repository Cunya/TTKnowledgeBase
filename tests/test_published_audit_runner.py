import json
from copy import deepcopy
from pathlib import Path

import pytest

from processors.codex_engine import CodexError, CodexResponseError
from processors.llm_budget import LLMBudgetExceeded
from processors.published_audit import audit_summary
from processors.published_audit_runner import (
    AUDIT_PROMPT_VERSION,
    machine_summary,
    review_unit_with_codex,
    run_audit_jobs,
    unit_jobs,
)
from processors.utils import read_json


def inputs():
    rows = [{"id": f"video:{i:05d}", "text": "Claim.", "normalized_text": "Claim.",
             "start_ms": i*1000, "duration_ms": 1000} for i in range(9)]
    source = {"video_id": "video", "start_ms": 0, "end_ms": 9000, "url": "https://www.youtube.com/watch?v=video", "segment_ids": [r["id"] for r in rows]}
    concept = {"id": "a", "label": "A", "aliases": [], "short_definition": "Claim.", "concept_type": "technique",
               "evidence": [{"id": "e", "excerpt": "Claim.", "reason": "Claim.", "source": source}], "relations": []}
    dossier = {"concept": concept, "sources": [{"source": source, "video": {"id": "video", "duration_ms": 9000},
               "selected_rows": rows, "context_rows": [], "missing_segment_ids": []}],
               "boundary_flags": {}, "relation_targets": {}}
    audit = {"items": [{"concept_id": "a", "fingerprint": "fresh", "decisions": {
        "field:short_definition": None, "evidence:0:e": None, "visual:0:e": None}}], "structural_errors": []}
    return audit, {"a": dossier}


def config_file(tmp_path: Path):
    path = tmp_path / "config.yaml"
    path.write_text("codex:\n  default_model: test-model\n  timeout_seconds: 2\n  max_segments_per_job: 4\n", encoding="utf-8")
    return path


def test_large_dossier_chunk_coverage_is_bounded_and_unit_complete():
    audit, dossiers = inputs()
    jobs = unit_jobs(audit["items"][0], dossiers["a"], {"max_segments_per_job": 4}, [])
    for unit in ["field:short_definition", "evidence:0:e"]:
        chunks = [j["payload"] for j in jobs if j["unit"] == unit]
        assert len(chunks) == 3
        ids = [r["id"] for chunk in chunks for r in chunk["selected_rows"]]
        assert len(ids) == len(set(ids)) == 9
        assert all(len(chunk["selected_rows"])+len(chunk["context_rows"]) <= 4 for chunk in chunks)
    assert len([job for job in jobs if job["visual"]]) == 1


def test_checkpoint_resume_and_machine_pass_never_approves_editorial_units(tmp_path):
    audit, dossiers = inputs()
    cfg = config_file(tmp_path)
    calls = []

    def reviewer(payload, *_args, **_kwargs):
        calls.append((payload["unit"], payload["chunk"]))
        return {"status": "supported", "note": "Selected rows support the claim.",
                "supporting_segment_ids": [payload["selected_rows"][0]["id"]]}, {"model": "test-model", "prompt_version": AUDIT_PROMPT_VERSION}

    checkpoint = tmp_path / "audit.json"
    report = run_audit_jobs(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint, max_calls=2, reviewer=reviewer)
    assert report["calls"] == 2
    assert report["machine_unit_status"]["needs_footage"] == 1
    resumed = read_json(checkpoint)
    run_audit_jobs(resumed, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint, max_calls=10, reviewer=reviewer)
    assert len(calls) == len(set(calls)) == 6
    assert machine_summary(resumed)["machine_pass_complete"]
    assert not audit_summary(resumed)["complete"]
    assert all(v is None for v in resumed["items"][0]["decisions"].values())
    first = next(job for job in resumed["items"][0]["machine_jobs"].values() if job.get("provenance", {}).get("model"))
    first["provenance"]["prompt_version"] = "outdated"
    assert machine_summary(resumed)["machine_job_status"]["stale"] == 1
    assert not machine_summary(resumed)["machine_pass_complete"]


def test_failed_jobs_and_budget_deferrals_remain_visible_and_retryable(tmp_path):
    audit, dossiers = inputs()
    cfg = config_file(tmp_path)
    checkpoint = tmp_path / "audit.json"

    def failed(*_args, **_kwargs):
        raise CodexError("bounded failure")

    report = run_audit_jobs(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint, max_calls=1, reviewer=failed)
    assert report["machine_job_status"]["failed"] == 1
    before = deepcopy(audit)

    def exhausted(*_args, **_kwargs):
        raise LLMBudgetExceeded("adjudication", 100, {"remaining_tokens": 0}, "daily limit")

    report = run_audit_jobs(audit, dossiers, cfg, tmp_path, tmp_path / "budget.json", checkpoint, max_calls=1, reviewer=exhausted)
    assert report["stopped"] == "budget" and report["calls"] == 0
    assert report["machine_job_status"]["failed"] == 1
    assert report["machine_job_status"]["budget_deferred"] == 1
    assert not machine_summary(audit)["machine_pass_complete"]
    assert before["items"][0]["decisions"] == audit["items"][0]["decisions"]


def test_transport_private_schema_read_only_timeout_model_and_wrong_ids(tmp_path, monkeypatch):
    import processors.codex_engine as engine

    cfg = config_file(tmp_path)
    monkeypatch.setattr(engine, "preflight", lambda _tier: ("codex", "test-cli"))
    commands = []

    def completed(command, **kwargs):
        commands.append(command)
        assert "--ephemeral" in command and command[command.index("--sandbox")+1] == "read-only"
        assert command[command.index("--model")+1] == "test-model"
        assert kwargs["timeout"] == 2
        assert "context_rows" in kwargs["input"]
        assert "Never impose the one-citation rule" in kwargs["input"]
        response_path = Path(command[command.index("--output-last-message")+1])
        response_path.write_text(json.dumps({"status": "supported", "note": "Claim.", "supporting_segment_ids": ["outside:00000"]}), encoding="utf-8")
        return engine.subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(engine.subprocess, "run", completed)
    payload = {"value": "Claim.", "selected_rows": [{"id": "video:00000"}], "context_rows": []}
    with pytest.raises(CodexResponseError, match="outside"):
        review_unit_with_codex(payload, cfg, tmp_path / "private", tmp_path / "budget.json")
    assert len(commands) == 1
    assert len(list((tmp_path / "private").glob("*.published-audit.failure.json"))) == 1
    assert (tmp_path / "budget.json").exists()
