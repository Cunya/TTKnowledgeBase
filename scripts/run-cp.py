"""Run one controlled full cp cycle for a knowledge base."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from processors.utils import read_yaml, write_json  # noqa: E402


def cmd(kb: str, *args: str) -> list[str]:
    return [sys.executable, "-m", "processors.cli", *args, "--kb", kb]

def run(name: str, args: list[str], report: dict) -> int:
    print(f"\n=== {name} ===", flush=True)
    result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    output = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
    if output:
        print(output, flush=True)
    report.setdefault("stages", []).append({
        "name": name,
        "exit_code": result.returncode,
        "output": output[-4000:],
        "exit_class": "success" if result.returncode == 0 else "stage_failed",
    })
    return result.returncode

def selected_batch(kb: str, limit: int) -> list[dict]:
    config = read_yaml(ROOT / "config" / "kbs" / kb / "sources.yaml") or {}
    normalized = ROOT / "data" / "normalized" / kb
    return [item for item in config.get("videos", [])
            if item.get("selected") and item.get("availability") != "members_only"
            and item.get("id") and not (normalized / f"{item['id']}.json").exists()][:limit]

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kb", default="table-tennis")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--no-discover-when-empty", action="store_true")
    args = parser.parse_args()
    report = {"knowledge_base": args.kb, "started_at": datetime.now(UTC).isoformat(), "status": "running"}
    manifest = ROOT / "data" / "manifests" / args.kb / "cp.latest.json"
    try:
        status = run("process-pending before acquisition", cmd(args.kb, "process-pending"), report)
        if status not in (0, 2):
            raise RuntimeError(f"cached triage failed (exit {status}; see stage output)")
        batch = selected_batch(args.kb, args.batch_size)
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
                    filename = f"discovered-{playlist_id}.json" if playlist_id else "discovered-videos.json"
                    manifest = ROOT / "data" / "manifests" / args.kb / filename
                    if manifest.exists():
                        payload = json.loads(manifest.read_text(encoding="utf-8"))
                        discovered.extend(payload.get("videos", []))
            normalized = ROOT / "data" / "normalized" / args.kb
            seen: set[str] = set()
            batch = []
            for item in sorted(discovered, key=lambda value: value.get("view_count") or 0, reverse=True):
                video_id = str(item.get("id", ""))
                if video_id and video_id not in seen and not (normalized / f"{video_id}.json").exists():
                    seen.add(video_id)
                    batch.append(item)
            batch = batch[: args.batch_size]
            report["discovered_batch"] = [{"id": x["id"], "title": x.get("title", "")} for x in batch]
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
        report.update(status="stopped", exit_class="stage_failed", error=str(error))
        print(f"cp stopped safely: {error}", file=sys.stderr)
        return 1
    finally:
        report["finished_at"] = datetime.now(UTC).isoformat()
        write_json(manifest, report)

if __name__ == "__main__":
    raise SystemExit(main())
