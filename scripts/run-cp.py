"""Run one controlled full cp cycle for a knowledge base."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from processors.inventory import build_inventory_ledger, select_ledger_worksets  # noqa: E402
from processors.utils import read_yaml, write_json  # noqa: E402
from processors.workspace import load_knowledge_base  # noqa: E402

STAGE_TIMEOUTS_SECONDS = {
    "discover": 20 * 60,
    "ingest": 45 * 60,
    "default": 45 * 60,
}


def cmd(kb: str, *args: str) -> list[str]:
    return [sys.executable, "-m", "processors.cli", *args, "--kb", kb]


def stage_timeout_seconds(name: str) -> int:
    if name.startswith("discover "):
        return STAGE_TIMEOUTS_SECONDS["discover"]
    if name.startswith("ingest "):
        return STAGE_TIMEOUTS_SECONDS["ingest"]
    return STAGE_TIMEOUTS_SECONDS["default"]


def active_members_only_ids(kb: str) -> set[str]:
    retry_path = ROOT / "data" / "manifests" / kb / "ingest-retries.json"
    if not retry_path.exists():
        return set()
    try:
        payload = json.loads(retry_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    now = datetime.now(UTC)
    active: set[str] = set()
    for video_id, item in (payload.get("items") or {}).items():
        if item.get("classification") != "members_only":
            continue
        try:
            retry_at = datetime.fromisoformat(str(item.get("next_retry_at")))
        except (TypeError, ValueError):
            continue
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=UTC)
        if retry_at > now:
            active.add(str(video_id))
    return active


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
    print(f"\n=== {name} ===", flush=True)
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
    )
    timeout_seconds = stage_timeout_seconds(name)
    timed_out = False
    captured: list[str] = []

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
    try:
        if result.stdout is not None:
            for line in result.stdout:
                print(line, end="", flush=True)
                captured.append(line)
        result.wait()
    finally:
        timeout_timer.cancel()
    return_code = 124 if timed_out else result.returncode
    output = "".join(captured).strip()
    report.setdefault("stages", []).append({
        "name": name,
        "exit_code": return_code,
        "output": output[-4000:],
        "exit_class": "timeout" if timed_out else ("success" if return_code == 0 else "stage_failed"),
        "timeout_seconds": timeout_seconds,
    })
    return return_code

def selected_batch(kb: str, limit: int) -> list[dict]:
    config = read_yaml(ROOT / "config" / "kbs" / kb / "sources.yaml") or {}
    normalized = ROOT / "data" / "normalized" / kb
    members_only_cooldown = active_members_only_ids(kb)
    return [item for item in config.get("videos", [])
            if item.get("selected") and item.get("availability") != "members_only"
            and item.get("id") and str(item["id"]) not in members_only_cooldown
            and not (normalized / f"{item['id']}.json").exists()][:limit]


def cached_unextracted(kb: str) -> list[str]:
    normalized = ROOT / "data" / "normalized" / kb
    derived = ROOT / "data" / "derived" / kb
    extracted_ids = {path.name.removesuffix(".candidates.json") for path in derived.glob("*.candidates.json")}
    return sorted(path.stem for path in normalized.glob("*.json") if path.stem not in extracted_ids)


def catalog_videos(kb: str) -> list[dict]:
    """Load existing local discovery catalogs for controlled expansion."""
    paths = [
        *(ROOT / "data" / "manifests" / kb).glob("discovered*.json"),
        *(ROOT / "app" / "src" / "data").glob("*.json"),
    ]
    videos: list[dict] = []
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        entries = payload.get("videos") if isinstance(payload, dict) else None
        if isinstance(entries, list):
            videos.extend(item for item in entries if isinstance(item, dict))
    return videos

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kb", default="table-tennis")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--no-discover-when-empty", action="store_true")
    args = parser.parse_args()
    report = {"knowledge_base": args.kb, "started_at": datetime.now(UTC).isoformat(), "status": "running"}
    manifest = ROOT / "data" / "manifests" / args.kb / "cp.latest.json"
    try:
        paths = load_knowledge_base(ROOT, args.kb)
        ledger = build_inventory_ledger(paths)
        workset = select_ledger_worksets(ledger, args.batch_size * 4, 50)
        report["inventory_before"] = ledger["summary"]
        report["workset"] = workset
        write_json(manifest, report)

        if workset["adjudication"]:
            status = run(
                "bounded deferred adjudication before acquisition",
                cmd(
                    args.kb,
                    "process-pending",
                    "--retry-deferred",
                    "--max-adjudication-attempts",
                    "2",
                    "--video-ids",
                    ",".join(item["id"] for item in workset["adjudication"]),
                ),
                report,
            )
            if status not in (0, 2):
                raise RuntimeError(f"cached triage failed (exit {status}; see stage output)")
        cached = [item["id"] for item in workset["extraction"]]
        report["cached_unextracted"] = cached
        for video_id in cached:
            status = run(f"extract cached {video_id}", cmd(args.kb, "extract-concepts", "--video-id", video_id), report)
            if status not in (0, 2):
                raise RuntimeError(f"cached extraction failed (exit {status}; see stage output)")
        catalog = {item["video_id"]: item for item in ledger.get("videos", [])}
        batch = [catalog[item["id"]] for item in workset["acquisition"]]
        report["selected_batch"] = []
        report["discovered_inventory_count"] = ledger["summary"]["inventory"]
        report["discovered_unprocessed_count"] = len(batch)
        report["discovered_batch"] = [
            {"id": item["video_id"], "title": item.get("title", ""), "reason": "eligibility or transcript acquisition is due"}
            for item in batch
        ]
        if batch:
            urls = [str(item.get("url") or f"https://www.youtube.com/watch?v={quote(str(item['video_id']))}") for item in batch]
            status = run("ingest ledger acquisition workset", cmd(args.kb, "ingest", *urls), report)
            if status not in (0, 1):
                raise RuntimeError(f"ingest failed (exit {status}; see stage output)")
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
                        "--video-ids",
                        ",".join(newly_extracted_ids),
                    ),
                )
            )
        final_stages.extend(
            [
                ("refresh summaries", ("build-evidence-summaries", "--write")),
                ("publish reviewed corpus", ("publish",)),
            ]
        )
        for name, stage in final_stages:
            status = run(name, cmd(args.kb, *stage), report)
            if status not in (0, 2):
                raise RuntimeError(f"{name} failed (exit {status}; see stage output)")
        report["status"] = "completed"
        return 0
    except Exception as error:
        timed_out = any(stage.get("exit_class") == "timeout" for stage in report.get("stages", []))
        report.update(status="stopped", exit_class="timeout" if timed_out else "stage_failed", error=str(error))
        print(f"cp stopped safely: {error}", file=sys.stderr)
        return 1
    finally:
        report["finished_at"] = datetime.now(UTC).isoformat()
        try:
            paths = load_knowledge_base(ROOT, args.kb)
            report["inventory_after"] = build_inventory_ledger(paths)["summary"]
        except Exception as ledger_error:
            report["inventory_refresh_error"] = str(ledger_error)
        write_json(manifest, report)

if __name__ == "__main__":
    raise SystemExit(main())
