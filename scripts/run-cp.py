"""Run one controlled full cp cycle for a knowledge base."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from processors.utils import read_yaml, write_json  # noqa: E402

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
    return [item for item in config.get("videos", [])
            if item.get("selected") and item.get("availability") != "members_only"
            and item.get("id") and not (normalized / f"{item['id']}.json").exists()][:limit]


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
        status = run("process-pending before acquisition", cmd(args.kb, "process-pending"), report)
        if status not in (0, 2):
            raise RuntimeError(f"cached triage failed (exit {status}; see stage output)")
        cached = cached_unextracted(args.kb)
        report["cached_unextracted"] = cached
        for video_id in cached:
            status = run(f"extract cached {video_id}", cmd(args.kb, "extract-concepts", "--video-id", video_id), report)
            if status not in (0, 2):
                raise RuntimeError(f"cached extraction failed (exit {status}; see stage output)")
        # Supply a larger candidate window because ingest now targets successful
        # uncached videos rather than limiting total attempts. This lets failed
        # or cooling-down entries be skipped without shrinking the work batch.
        batch = selected_batch(args.kb, args.batch_size * 4)
        report["selected_batch"] = [{"id": x["id"], "title": x.get("title", "")} for x in batch]
        if batch:
            urls = [f"https://www.youtube.com/watch?v={quote(str(x['id']))}" for x in batch]
            status = run("ingest selected batch", cmd(args.kb, "ingest", *urls), report)
            if status not in (0, 1):
                raise RuntimeError(f"ingest failed (exit {status}; see stage output)")
            for item in batch:
                if (ROOT / "data" / "normalized" / args.kb / f"{item['id']}.json").exists():
                    status = run(f"extract {item['id']}", cmd(args.kb, "extract-concepts", "--video-id", str(item["id"])), report)
                    if status not in (0, 2):
                        raise RuntimeError(f"extraction failed (exit {status}; see stage output)")
        elif not args.no_discover_when_empty:
            discovered: list[dict] = []
            for source in (read_yaml(ROOT / "config" / "kbs" / args.kb / "sources.yaml") or {}).get("sources", []):
                if source.get("enabled"):
                    status = run(f"discover {source['id']}", cmd(args.kb, "discover", str(source["url"])), report)
                    if status != 0:
                        raise RuntimeError(f"discovery failed (exit {status}; see stage output)")
                    playlist_id = parse_qs(urlparse(str(source["url"])).query).get("list", [None])[0]
                    source_key = playlist_id or hashlib.sha256(str(source["url"]).encode("utf-8")).hexdigest()[:12]
                    filename = f"discovered-{source_key}.json"
                    discovery_manifest = ROOT / "data" / "manifests" / args.kb / filename
                    if discovery_manifest.exists():
                        payload = json.loads(discovery_manifest.read_text(encoding="utf-8"))
                        discovered.extend(payload.get("videos", []))
            discovered.extend(catalog_videos(args.kb))
            normalized = ROOT / "data" / "normalized" / args.kb
            seen: set[str] = set()
            batch = []
            for item in sorted(discovered, key=lambda value: value.get("view_count") or 0, reverse=True):
                video_id = str(item.get("id", ""))
                if video_id and video_id not in seen and not (normalized / f"{video_id}.json").exists():
                    seen.add(video_id)
                    batch.append(item)
            batch = batch[: args.batch_size * 4]
            report["discovered_inventory_count"] = len({str(item.get("id")) for item in discovered if item.get("id")})
            report["discovered_unprocessed_count"] = len(batch)
            report["discovered_batch"] = [{"id": x["id"], "title": x.get("title", "")} for x in batch]
            print(
                f"Discovered inventory: {report['discovered_inventory_count']} unique; "
                f"eligible unprocessed window: {report['discovered_unprocessed_count']}",
                flush=True,
            )
            if batch:
                urls = [str(x.get("url") or f"https://www.youtube.com/watch?v={quote(str(x['id']))}") for x in batch]
                status = run("ingest discovered batch", cmd(args.kb, "ingest", *urls), report)
                if status not in (0, 1):
                    raise RuntimeError(f"ingest failed (exit {status}; see stage output)")
                for item in batch:
                    if (normalized / f"{item['id']}.json").exists():
                        status = run(f"extract {item['id']}", cmd(args.kb, "extract-concepts", "--video-id", str(item["id"])), report)
                        if status not in (0, 2):
                            raise RuntimeError(f"extraction failed (exit {status}; see stage output)")
        for name, stage in (("process-pending after extraction", ("process-pending",)), ("build review queue", ("build-review-queue",)), ("refresh summaries", ("build-evidence-summaries", "--write")), ("publish reviewed corpus", ("publish",))):
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
        write_json(manifest, report)

if __name__ == "__main__":
    raise SystemExit(main())
