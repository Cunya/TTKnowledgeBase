"""Run one controlled full cp cycle for a knowledge base."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from processors.inventory import build_inventory_ledger, select_ledger_worksets  # noqa: E402
from processors.run_lock import KnowledgeBaseRunLock, RunAlreadyActive  # noqa: E402
from processors.utils import read_yaml, set_current_process_idle_priority, write_json  # noqa: E402
from processors.workspace import load_knowledge_base, processing_is_paused  # noqa: E402

STAGE_TIMEOUTS_SECONDS = {
    "discover": 20 * 60,
    "ingest": 45 * 60,
    "adjudication": 60 * 60,
    "default": 45 * 60,
}
STAGE_HEARTBEAT_SECONDS = 15


def cmd(kb: str, *args: str) -> list[str]:
    return [sys.executable, "-m", "processors.cli", *args, "--kb", kb]


def stage_timeout_seconds(name: str) -> int:
    if name.startswith("discover "):
        return STAGE_TIMEOUTS_SECONDS["discover"]
    if name.startswith("ingest "):
        return STAGE_TIMEOUTS_SECONDS["ingest"]
    if "retry batch" in name or name.startswith("process pending"):
        return STAGE_TIMEOUTS_SECONDS["adjudication"]
    return STAGE_TIMEOUTS_SECONDS["default"]


def stage_description(name: str) -> str:
    descriptions = {
        "small fair retry batch for unclear candidates": "Review unclear candidate proposals against their transcript evidence",
        "build review queue": "Rebuild the editorial review queue from current candidates",
        "refresh summaries": "Write missing evidence summaries for reviewed concepts",
        "publish reviewed corpus": "Validate and copy reviewed content into the local site",
        "ingest selected acquisition batch": "Fetch metadata and timed captions for selected videos",
    }
    if name.startswith("discover "):
        return f"Refresh the configured video catalog for {name.removeprefix('discover ')}"
    if name.startswith("extract cached "):
        return f"Create private candidate proposals from cached video {name.removeprefix('extract cached ')}"
    if name.startswith("extract "):
        return f"Create private candidate proposals from video {name.removeprefix('extract ')}"
    return descriptions.get(name, "Run the current processing stage")


def processor_creation_flags() -> int:
    return getattr(subprocess, "IDLE_PRIORITY_CLASS", 0)


def enabled_sources(kb: str) -> list[dict[str, str]]:
    config = read_yaml(ROOT / "config" / "kbs" / kb / "sources.yaml") or {}
    return [
        {"id": str(source["id"]), "url": str(source["url"])}
        for source in config.get("sources", []) or []
        if isinstance(source, dict)
        and source.get("enabled", True)
        and source.get("id")
        and source.get("url")
    ]


def planned_stage_total(completed: int, cached_count: int, retry: bool, batch_count: int) -> int:
    """Count the stage invocations this cycle will make."""
    extracted_count = cached_count + batch_count
    return completed + cached_count + int(retry) + int(batch_count > 0) + batch_count + 1 + int(extracted_count > 0) + 2


def set_stage_total(report: dict, manifest: Path, total: int) -> None:
    report["stage_total"] = max(total, len(report.get("stages", [])) + 1)
    write_json(manifest, report)


def terminate_process_tree(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill.exe", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
    else:
        try:
            os.kill(pid, 9)
        except ProcessLookupError:
            pass


def run(name: str, args: list[str], report: dict) -> int:
    stage_index = len(report.get("stages", [])) + 1
    stage_total = max(int(report.get("stage_total") or stage_index), stage_index)
    stage_label = f"Stage {stage_index}/{stage_total}"
    print(f"\n=== {name} ===", flush=True)
    description = stage_description(name)
    print(f"{stage_label}: {description}.", flush=True)
    print(f"Stage purpose: {description}.", flush=True)
    started_monotonic = time.monotonic()
    child_env = os.environ.copy()
    child_env["PYTHONUNBUFFERED"] = "1"
    result = subprocess.Popen(
        args,
        cwd=ROOT,
        env=child_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        creationflags=processor_creation_flags(),
    )
    timeout_seconds = stage_timeout_seconds(name)
    timed_out = False
    captured: list[str] = [
        f"=== {name} ===\n",
        f"{stage_label}: {description}.\n",
        f"Stage purpose: {description}.\n",
    ]

    def timeout_stage() -> None:
        nonlocal timed_out
        timed_out = True
        message = (
            f"TIMEOUT: {name} exceeded the {timeout_seconds // 60}-minute stage limit; "
            "terminating its process tree."
        )
        print(message, flush=True)
        captured.append(message + "\n")
        terminate_process_tree(result.pid)

    timeout_timer = threading.Timer(timeout_seconds, timeout_stage)
    timeout_timer.daemon = True
    timeout_timer.start()
    heartbeat_stop = threading.Event()

    def heartbeat_stage() -> None:
        while not heartbeat_stop.wait(STAGE_HEARTBEAT_SECONDS):
            elapsed = round(time.monotonic() - started_monotonic)
            message = (
                f"[stage] No new output yet; current work is to {description.lower()} "
                f"({elapsed}s elapsed; {stage_label})."
            )
            print(message, flush=True)
            captured.append(message + "\n")

    heartbeat_thread = threading.Thread(target=heartbeat_stage, daemon=True)
    heartbeat_thread.start()
    try:
        if result.stdout is not None:
            for line in result.stdout:
                print(line, end="", flush=True)
                captured.append(line)
        result.wait()
    finally:
        timeout_timer.cancel()
        heartbeat_stop.set()
        heartbeat_thread.join(timeout=1)
    return_code = 124 if timed_out else result.returncode
    output = "".join(captured).strip()
    if timed_out:
        exit_class = "timeout"
    elif return_code == 0:
        exit_class = "success"
    elif return_code == 2:
        exit_class = "deferred"
        report.setdefault("warnings", []).append(f"{name} deferred work (exit 2)")
    else:
        exit_class = "stage_failed"
    elapsed_seconds = round(time.monotonic() - started_monotonic, 1)
    completion = (
        f"[stage] Finished: {description} in {elapsed_seconds}s "
        f"({exit_class.replace('_', ' ')}; {stage_label})."
    )
    print(completion, flush=True)
    captured.append(completion + "\n")
    output = "".join(captured).strip()
    report.setdefault("stages", []).append({
        "name": name,
        "stage_index": stage_index,
        "stage_total": stage_total,
        "exit_code": return_code,
        "output": output[-4000:],
        "exit_class": exit_class,
        "timeout_seconds": timeout_seconds,
        "duration_seconds": elapsed_seconds,
    })
    return return_code

def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer") from error
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def has_local_work(workset: dict) -> bool:
    return any(workset.get(stage) for stage in ("extraction", "adjudication", "acquisition"))


def main() -> int:
    set_current_process_idle_priority()
    parser = argparse.ArgumentParser()
    parser.add_argument("--kb", default="table-tennis")
    parser.add_argument("--batch-size", type=positive_int, default=10)
    parser.add_argument("--no-discover-when-empty", action="store_true")
    args = parser.parse_args()
    try:
        paths = load_knowledge_base(ROOT, args.kb)
    except ValueError as error:
        parser.error(str(error))
    if processing_is_paused(paths.data("manifests")):
        print("Processing is paused for the published-content audit; no cycle started.", flush=True)
        return 2
    manifest = ROOT / "data" / "manifests" / args.kb / "cp.latest.json"
    lock = KnowledgeBaseRunLock(ROOT / "data" / "manifests" / args.kb / "cp.lock")
    try:
        lock.acquire()
    except RunAlreadyActive as error:
        skipped = {
            "knowledge_base": args.kb,
            "status": "skipped",
            "exit_class": "overlap",
            "reason": str(error),
            "attempted_at": datetime.now(UTC).isoformat(),
            "pid": os.getpid(),
        }
        skipped_path = manifest.with_name(f"cp.skipped.{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}.{os.getpid()}.json")
        write_json(skipped_path, skipped)
        print(f"cp skipped safely: {error}", file=sys.stderr)
        return 10
    report = {
        "knowledge_base": args.kb,
        "pid": os.getpid(),
        "started_at": datetime.now(UTC).isoformat(),
        "status": "running",
    }
    try:
        ledger = build_inventory_ledger(paths)
        workset = select_ledger_worksets(ledger, args.batch_size * 4, 50)
        report["inventory_before"] = ledger["summary"]
        report["workset"] = workset
        write_json(manifest, report)
        cached = [item["id"] for item in workset["extraction"]]
        report["cached_unextracted"] = cached
        initial_has_local_work = has_local_work(workset)
        if initial_has_local_work:
            initial_catalog = {item["video_id"]: item for item in ledger.get("videos", [])}
            initial_batch = [initial_catalog[item["id"]] for item in workset["acquisition"]]
            set_stage_total(
                report,
                manifest,
                planned_stage_total(0, len(cached), bool(workset["adjudication"]), len(initial_batch)),
            )
        elif args.no_discover_when_empty:
            set_stage_total(report, manifest, planned_stage_total(0, 0, False, 0))
        else:
            set_stage_total(report, manifest, len(enabled_sources(args.kb)) + planned_stage_total(0, 0, False, 0))
        for video_id in cached:
            status = run(f"extract cached {video_id}", cmd(args.kb, "extract-concepts", "--video-id", video_id), report)
            if status not in (0, 2):
                raise RuntimeError(f"cached extraction failed (exit {status}; see stage output)")
        if workset["adjudication"]:
            status = run(
                "small fair retry batch for unclear candidates",
                cmd(
                    args.kb,
                    "process-pending",
                    "--retry-deferred",
                    "--max-adjudication-attempts",
                    "2",
                    "--max-candidates",
                    str(args.batch_size),
                    "--video-ids",
                    ",".join(item["id"] for item in workset["adjudication"]),
                ),
                report,
            )
            if status not in (0, 2):
                raise RuntimeError(f"cached triage failed (exit {status}; see stage output)")
        discovery_attempted = False
        if not has_local_work(workset):
            if args.no_discover_when_empty:
                report["discovery_skipped"] = "disabled by command-line option"
            else:
                discovery_attempted = True
                report["discovery_attempted"] = True
                for source in enabled_sources(args.kb):
                    status = run(
                        f"discover {source['id']}",
                        cmd(args.kb, "discover", source["url"]),
                        report,
                    )
                    if status != 0:
                        raise RuntimeError(
                            f"discovery failed for {source['id']} (exit {status}; see stage output)"
                        )
                ledger = build_inventory_ledger(paths)
                workset = select_ledger_worksets(ledger, args.batch_size * 4, 50)
                report["inventory_after_discovery"] = ledger["summary"]
                report["workset"] = workset
                write_json(manifest, report)
        catalog = {item["video_id"]: item for item in ledger.get("videos", [])}
        batch = [catalog[item["id"]] for item in workset["acquisition"]]
        if discovery_attempted:
            set_stage_total(report, manifest, planned_stage_total(len(report.get("stages", [])), 0, False, len(batch)))
        report["discovered_inventory_count"] = ledger["summary"]["inventory"]
        report["discovered_unprocessed_count"] = len(batch)
        report["selected_batch"] = [
            {
                "id": item["video_id"],
                "source_id": item.get("source_id"),
                "title": item.get("title", ""),
                "reason": "eligibility or transcript acquisition is due",
            }
            for item in batch
        ]
        report["discovered_batch"] = report["selected_batch"] if discovery_attempted else []
        if batch:
            urls = [str(item.get("url") or f"https://www.youtube.com/watch?v={quote(str(item['video_id']))}") for item in batch]
            status = run("ingest selected acquisition batch", cmd(args.kb, "ingest", *urls), report)
            if status not in (0, 1):
                raise RuntimeError(f"ingest failed (exit {status}; see stage output)")
            if status == 1:
                report.setdefault("warnings", []).append(
                    "ingest reported item failures; successful videos were retained"
                )
            for item in batch:
                video_id = str(item["video_id"])
                if (ROOT / "data" / "normalized" / args.kb / f"{video_id}.json").exists():
                    status = run(f"extract {video_id}", cmd(args.kb, "extract-concepts", "--video-id", video_id), report)
                    if status not in (0, 2):
                        raise RuntimeError(f"extraction failed (exit {status}; see stage output)")
        newly_extracted_ids = [*cached, *(str(item["video_id"]) for item in batch)]
        final_stages = [("build review queue", ("build-review-queue",))]
        if newly_extracted_ids:
            final_stages.append(
                (
                    "process pending after extraction",
                    (
                        "process-pending",
                        "--max-adjudication-attempts",
                        "2",
                        "--max-candidates",
                        str(args.batch_size),
                        "--video-ids",
                        ",".join(newly_extracted_ids),
                    ),
                )
            )
        final_stages.extend(
            [
                ("publish reviewed corpus", ("publish",)),
            ]
        )
        for name, stage in final_stages:
            status = run(name, cmd(args.kb, *stage), report)
            if status not in (0, 2):
                raise RuntimeError(f"{name} failed (exit {status}; see stage output)")
        report["status"] = "completed_with_warnings" if report.get("warnings") else "completed"
        report["exit_class"] = "partial" if report.get("warnings") else "success"
        return 0
    except Exception as error:
        timed_out = any(stage.get("exit_class") == "timeout" for stage in report.get("stages", []))
        report.update(status="stopped", exit_class="timeout" if timed_out else "stage_failed", error=str(error))
        print(f"cp stopped safely: {error}", file=sys.stderr)
        return 1
    finally:
        try:
            report["finished_at"] = datetime.now(UTC).isoformat()
            try:
                paths = load_knowledge_base(ROOT, args.kb)
                report["inventory_after"] = build_inventory_ledger(paths)["summary"]
            except Exception as ledger_error:
                report["inventory_refresh_error"] = str(ledger_error)
            write_json(manifest, report)
        finally:
            lock.release()

if __name__ == "__main__":
    raise SystemExit(main())
