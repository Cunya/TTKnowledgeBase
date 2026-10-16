import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("run_cp", ROOT / "scripts" / "run-cp.py")
assert SPEC and SPEC.loader
run_cp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(run_cp)


def test_stage_timeout_covers_adjudication_batch() -> None:
    assert run_cp.stage_timeout_seconds("small fair retry batch for unclear candidates") == 3600
    assert run_cp.stage_timeout_seconds("process pending after extraction") == 3600
    assert run_cp.stage_timeout_seconds("ingest selected acquisition batch") == 2700


def test_quiet_stage_reports_plain_language_heartbeat(monkeypatch) -> None:
    monkeypatch.setattr(run_cp, "STAGE_HEARTBEAT_SECONDS", 0.05)
    report: dict = {}
    status = run_cp.run(
        "quiet stage",
        [sys.executable, "-c", "import time; time.sleep(.2)"],
        report,
    )

    assert status == 0
    output = report["stages"][0]["output"]
    assert "Stage 1/1: Run the current processing stage." in output
    assert "Stage purpose: Run the current processing stage." in output
    assert "[stage] No new output yet; current work is to" in output
    assert "[stage] Finished: Run the current processing stage" in output
    assert report["stages"][0]["stage_index"] == 1
    assert report["stages"][0]["stage_total"] == 1
    assert report["stages"][0]["duration_seconds"] >= 0


def test_processor_children_use_the_lowest_windows_priority_class() -> None:
    assert run_cp.processor_creation_flags() == getattr(subprocess, "IDLE_PRIORITY_CLASS", 0)


def test_enabled_sources_excludes_disabled_expansion_candidates() -> None:
    sources = run_cp.enabled_sources("table-tennis")

    assert {source["id"] for source in sources} == {
        "free-coach-brad-han",
        "global-tt-studio",
        "pingsunday-xiaohan-playlist",
    }


def test_discovery_waits_until_local_worksets_are_empty() -> None:
    assert run_cp.has_local_work({"extraction": [], "adjudication": [{}], "acquisition": []})
    assert not run_cp.has_local_work({"extraction": [], "adjudication": [], "acquisition": []})


def test_run_classifies_deferred_stage() -> None:
    report: dict = {}
    status = run_cp.run(
        "deferred test",
        [sys.executable, "-c", "raise SystemExit(2)"],
        report,
    )

    assert status == 2
    assert report["stages"][0]["exit_class"] == "deferred"
    assert report["warnings"] == ["deferred test deferred work (exit 2)"]


def test_audit_pause_refuses_cycle_without_overwriting_runtime_state(tmp_path, monkeypatch):
    from processors.workspace import KnowledgeBasePaths

    paths = KnowledgeBasePaths(tmp_path, "paused-kb", "Paused", "Fixture")
    manifest = paths.data("manifests")
    manifest.mkdir(parents=True)
    (manifest / "published-audit-pause.json").write_text("{}", encoding="utf-8")
    latest = manifest / "cp.latest.json"
    latest.write_text('{"status":"completed"}', encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["run-cp.py", "--kb", paths.id])
    monkeypatch.setattr(run_cp, "load_knowledge_base", lambda *_args: paths)
    assert run_cp.main() == 2
    assert latest.read_text(encoding="utf-8") == '{"status":"completed"}'
    assert not (manifest / "cp.lock").exists()
