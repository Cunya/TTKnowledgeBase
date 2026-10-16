import json
import subprocess
from pathlib import Path

import pytest

import processors.codex_engine as codex_engine
from processors.codex_engine import (
    CodexTimeoutError,
    adjudicate_candidate_with_codex,
    parse_codex_usage,
)
from processors.models import Segment


@pytest.mark.parametrize("operation", ["extraction", "schema", "summary", "batch_summary", "rephrase"])
def test_all_text_processor_calls_disable_apps_without_changing_profile(tmp_path, monkeypatch, operation):
    config = tmp_path / "processors.yaml"
    config.write_text("codex:\n  default_model: gpt-6-luna\n  reasoning_effort: high\n  timeout_seconds: 1\n", encoding="utf-8")
    audit = tmp_path / "private"
    monkeypatch.setattr(codex_engine, "preflight", lambda _tier: ("codex", "fixture-cli"))
    captured = []

    def checked_command(command, **kwargs):
        assert "features.apps=false" in command
        assert command[command.index("features.apps=false") - 1] == "--config"
        assert command[command.index("--model") + 1] == "gpt-6-luna"
        assert 'model_reasoning_effort="high"' in command
        assert "--ephemeral" in command and command[command.index("--sandbox") + 1] == "read-only"
        assert kwargs["timeout"] == 1
        captured.append(command)
        raise subprocess.TimeoutExpired(command, 1)

    monkeypatch.setattr(codex_engine.subprocess, "run", checked_command)
    with pytest.raises((subprocess.TimeoutExpired, codex_engine.CodexError)):
        if operation == "extraction":
            codex_engine.extract_with_codex([Segment(id="video:00000", video_id="video", text="Keep balance.",
                                                    normalized_text="Keep balance.", start_ms=0, duration_ms=1000)],
                                            {}, [], config, audit)
        elif operation == "schema":
            codex_engine._run_schema_constrained_codex("Review supplied text.", {}, object, config, audit,
                                                       "sha256:fixture", "fixture")
        elif operation == "summary":
            codex_engine.summarize_evidence_with_codex("Balance", ["Keep balance."], config, audit)
        elif operation == "batch_summary":
            codex_engine.summarize_evidence_batch_with_codex(
                [{"id": "balance", "label": "Balance", "reasons": ["Keep balance."]}], config, audit,
            )
        else:
            codex_engine.rephrase_excerpt_with_codex("Keep balance.", "Keep balance.", config, audit)
    assert len(captured) == 1
    if operation == "schema":
        failure = json.loads(next(audit.glob("*.failure.json")).read_text(encoding="utf-8"))
        assert failure["apps_enabled"] is False


def test_parse_codex_usage_uses_final_jsonl_event() -> None:
    stdout = "\n".join(
        [
            '{"type":"item.completed"}',
            '{"type":"turn.completed","usage":{"input_tokens":120,"output_tokens":30}}',
        ]
    )
    assert parse_codex_usage(stdout) == {"input_tokens": 120, "output_tokens": 30}


def test_parse_codex_usage_tolerates_non_json_output() -> None:
    assert parse_codex_usage("diagnostic text") is None


def test_captured_codex_call_emits_heartbeat_after_bounded_wait(monkeypatch) -> None:
    class FakeProcess:
        returncode = 0

        def __init__(self) -> None:
            self.calls = []

        def communicate(self, *, input=None, timeout=None):
            self.calls.append((input, timeout))
            if len(self.calls) == 1:
                raise subprocess.TimeoutExpired(["codex"], timeout)
            return "{}", ""

        def kill(self) -> None:
            raise AssertionError("heartbeat test should finish before the total timeout")

    process = FakeProcess()
    monkeypatch.setattr(codex_engine.subprocess, "Popen", lambda *args, **kwargs: process)
    heartbeats = []

    result = codex_engine._run_captured_with_heartbeat(
        ["codex"],
        "private prompt",
        30,
        lambda: heartbeats.append("heartbeat"),
    )

    assert result.stdout == "{}"
    assert heartbeats == ["heartbeat"]
    assert process.calls[0][0] == "private prompt"
    assert process.calls[1][0] is None


def test_adjudication_timeout_is_audited_as_typed_error(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "processors.yaml"
    config_path.write_text(
        "codex:\n  default_model: test-codex\n  timeout_seconds: 2\n",
        encoding="utf-8",
    )

    prompts = []

    class FakeProcess:
        returncode = -9

        def communicate(self, *, input=None, timeout=None):
            if input is not None:
                prompts.append(input)
            if timeout is not None:
                raise subprocess.TimeoutExpired(
                    ["codex"], timeout, output="partial stdout", stderr="partial stderr"
                )
            return "partial stdout", "partial stderr"

        def kill(self) -> None:
            return None

    monkeypatch.setattr(codex_engine, "preflight", lambda _service_tier: ("codex", "test-1"))
    monkeypatch.setattr(codex_engine.subprocess, "Popen", lambda *args, **kwargs: FakeProcess())

    with pytest.raises(CodexTimeoutError) as raised:
        adjudicate_candidate_with_codex(
            {"candidate_id": "timeout"},
            [
                Segment(
                    id="video:00000",
                    video_id="video",
                    text="A transcript row.",
                    normalized_text="A transcript row.",
                    start_ms=0,
                    duration_ms=1000,
                )
            ],
            [],
            {},
            config_path,
            tmp_path / "audit",
            heartbeat_callback=lambda: None,
        )

    assert raised.value.timeout_seconds == 2
    failure_files = list((tmp_path / "audit").glob("*.adjudication.failure.json"))
    assert len(failure_files) == 1
    failure = json.loads(failure_files[0].read_text(encoding="utf-8"))
    assert failure["error_type"] == "timeout"
    assert failure["timeout_seconds"] == 2
    assert failure["stderr"] == "partial stderr"
    assert "A region on the ball, a region on the racket" in prompts[0]
    assert failure["prompt_version"] == codex_engine.ADJUDICATION_PROMPT_VERSION


def test_shared_transport_preserves_adjudication_success_audit(tmp_path, monkeypatch):
    config = tmp_path / "config.yaml"
    config.write_text("codex:\n  default_model: test-model\n  timeout_seconds: 2\n", encoding="utf-8")
    monkeypatch.setattr(codex_engine, "preflight", lambda _tier: ("codex", "test-cli"))

    def completed(command, **_kwargs):
        path = Path(command[command.index("--output-last-message")+1])
        path.write_text(json.dumps({
            "decision": "reject", "canonical_concept_id": None, "canonical_label": None,
            "definition": None, "concept_type": None, "facets": [], "evidence_type": None,
            "segment_ids": [], "excerpt": None, "reason": "Unsupported.", "confidence": 0.8, "uncertainty": [],
        }), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, '{"usage":{"input_tokens":100,"output_tokens":20}}', "")

    monkeypatch.setattr(codex_engine.subprocess, "run", completed)
    response, provenance = adjudicate_candidate_with_codex({"candidate_id": "fixture"}, [], [], {}, config, tmp_path / "audit")
    assert response.decision == "reject"
    audit_files = list((tmp_path / "audit").glob("*.adjudication.json"))
    assert len(audit_files) == 1
    audit = json.loads(audit_files[0].read_text(encoding="utf-8"))
    assert audit["decision"] == "reject" and audit["selected_segment_ids"] == []
    assert audit["canonical_concept_id"] is None
    assert audit["model"] == provenance["model"] == "test-model"
    assert audit["usage"] == {"input_tokens": 100, "output_tokens": 20}
