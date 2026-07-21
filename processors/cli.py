from __future__ import annotations

import hashlib
import os
import random
import shutil
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated
from urllib.parse import parse_qs, urlparse

import typer
from rich.console import Console
from rich.table import Table
from ruamel.yaml import YAML

from .benchmark import render_benchmark_markdown, run_quality_benchmark, select_benchmark_videos
from .boundaries import (
    build_boundary_report,
    build_boundary_review_set,
    render_boundary_report_markdown,
    render_boundary_review_set_markdown,
    validate_boundary_review_set,
)
from .codex_engine import CodexError
from .demo import DEMO_VIDEO_ID, write_demo_video
from .evidence_summaries import (
    build_missing_summaries,
    write_codex_summaries,
    write_missing_summaries,
)
from .ingest import (
    IngestOptions,
    MembersOnlyError,
    TranscriptBlockedError,
    discover_videos,
    fetch_metadata,
    ingest_media_asr,
    ingest_video,
    video_id_from_url,
)
from .llm_budget import LLMBudgetExceeded, LLMTokenBudget
from .models import KnowledgeNavigation, PublishCorpus
from .pipeline import (
    auto_place_generated_concepts,
    build_quality_report,
    build_review_queue,
    extract_video,
    load_reviewed_concepts,
    load_videos,
    process_pending_candidates,
    render_quality_report_markdown,
    rephrase_high_overlap_excerpts,
    validate_corpus,
    validate_navigation,
    validate_published_corpus,
    validate_review_queue,
)
from .pipeline import publish as publish_corpus
from .progress import build_progress_report, write_recent_snapshot
from .review_diagnostics import build_review_diagnostics
from .utils import read_json, read_yaml, sha256_json, write_json
from .workspace import KnowledgeBasePaths, load_knowledge_base

ROOT = Path(__file__).resolve().parents[1]
console = Console()
roundtrip_yaml = YAML()
MEMBERS_ONLY_COOLDOWN = timedelta(days=3)


def retry_window_remaining(entry: dict, now: datetime | None = None) -> timedelta | None:
    """Return the remaining block cooldown, or None when retrying is permitted."""
    value = entry.get("next_retry_at")
    if not value:
        return None
    try:
        retry_at = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=UTC)
    remaining = retry_at - (now or datetime.now(UTC))
    return remaining if remaining.total_seconds() > 0 else None
app = typer.Typer(help="Build source-grounded video knowledge bases.")
KbOption = Annotated[str | None, typer.Option("--kb", help="Knowledge-base ID")]


def kb_paths(kb: str | None) -> KnowledgeBasePaths:
    try:
        return load_knowledge_base(ROOT, kb)
    except ValueError as error:
        raise typer.BadParameter(str(error), param_hint="--kb") from error


def _demo_video_ids(videos: list) -> set[str]:
    """Return synthetic fixture IDs even when private normalized data is absent."""
    return {video.id for video in videos if video.availability == "demo_fixture"} | {
        DEMO_VIDEO_ID
    }


@app.command()
def list_kbs() -> None:
    """List configured knowledge bases."""
    project = read_yaml(ROOT / "config" / "project.yaml")
    registry = read_yaml(ROOT / "config" / "knowledge-bases.yaml")
    table = Table("ID", "Name", "Default")
    for item in registry["knowledge_bases"]:
        if item.get("enabled", True):
            table.add_row(
                item["id"],
                item["name"],
                "yes" if item["id"] == project["default_knowledge_base"] else "",
            )
    console.print(table)


@app.command("llm-budget")
def llm_budget(kb: KbOption = None) -> None:
    """Show the current daily Codex token budget and per-task usage."""
    paths = kb_paths(kb)
    budget = LLMTokenBudget(
        ROOT / "config" / "processors.yaml",
        paths.data("manifests") / "llm-budget.json",
    )
    status = budget.status()
    if not status["enabled"]:
        console.print("[yellow]LLM budget is disabled in config/processors.yaml[/yellow]")
        return
    console.print(
        f"[green]LLM budget[/green] {status['date']} ({status['timezone']}): "
        f"{status['used_tokens']:,}/{status['daily_limit_tokens']:,} tokens used; "
        f"{status['remaining_tokens']:,} remaining"
    )
    table = Table("Task", "Used", "Limit", "Remaining", "Calls", "Deferred")
    for task, item in status["tasks"].items():
        limit = "unlimited" if item["limit_tokens"] is None else f"{item['limit_tokens']:,}"
        remaining = (
            "unlimited"
            if item["remaining_tokens"] is None
            else f"{item['remaining_tokens']:,}"
        )
        table.add_row(
            task,
            f"{item['used_tokens']:,}",
            limit,
            remaining,
            str(item["calls"]),
            str(item["deferred"]),
        )
    console.print(table)


@app.command()
def discover(url: Annotated[str, typer.Argument()], kb: KbOption = None) -> None:
    """Discover videos in a source and save a reviewable manifest."""
    paths = kb_paths(kb)
    with console.status(f"Discovering videos for {paths.name}"):
        videos = discover_videos(url)
    playlist_id = parse_qs(urlparse(url).query).get("list", [None])[0]
    source_key = playlist_id or hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    output_name = f"discovered-{source_key}.json"
    output = paths.data("manifests") / output_name
    write_json(output, {"knowledge_base": paths.id, "source_url": url, "videos": videos})
    console.print(f"[green]Discovered {len(videos)} videos[/green] for {paths.name}")


@app.command("build-evidence-summaries")
def build_evidence_summaries(
    kb: KbOption = None,
    engine: Annotated[
        str,
        typer.Option(help="Summary engine: deterministic or codex"),
    ] = "deterministic",
    write: Annotated[
        bool,
        typer.Option(help="Write summaries into concepts missing evidence_summary"),
    ] = False,
    max_points: Annotated[
        int,
        typer.Option(min=2, max=12, help="Maximum distinct evidence reasons per summary"),
    ] = 8,
    refresh_generated: Annotated[
        bool,
        typer.Option(help="Refresh summaries marked as generated when evidence changed"),
    ] = False,
    model: Annotated[str | None, typer.Option(help="Optional Codex model override")] = None,
) -> None:
    """Build essays from approved evidence reasons.

    The deterministic engine is the default and never calls an LLM. Use
    ``--engine codex --write --refresh-generated`` for coherent LLM synthesis
    with the configured model and daily budget.
    """
    paths = kb_paths(kb)
    if engine not in {"deterministic", "codex"}:
        raise typer.BadParameter("engine must be deterministic or codex")
    if engine == "codex" and not write:
        raise typer.BadParameter("--engine codex requires --write")
    if write:
        if engine == "codex":
            try:
                files = write_codex_summaries(
                    paths.content / "concepts",
                    ROOT / "config" / "processors.yaml",
                    paths.data("manifests") / "summary-audit",
                    paths.data("manifests") / "llm-budget.json",
                    max_points=max_points,
                    refresh_generated=refresh_generated,
                    model_override=model,
                )
            except LLMBudgetExceeded as error:
                console.print(f"[yellow]Summary generation deferred[/yellow]: {error}")
                raise typer.Exit(2) from None
            except CodexError as error:
                raise typer.BadParameter(str(error)) from error
            console.print(f"[green]Wrote {len(files)} Codex evidence summaries[/green]")
            return
        files = write_missing_summaries(
            paths.content / "concepts",
            max_points=max_points,
            refresh_generated=refresh_generated,
        )
        console.print(f"[green]Wrote {len(files)} evidence summaries[/green]")
        return
    previews = build_missing_summaries(paths.content / "concepts", max_points=max_points)
    console.print(f"[yellow]Preview: {len(previews)} concepts need evidence summaries[/yellow]")
    for path, summary in previews:
        console.print(f"[bold]{path.stem}[/bold]: {summary}")


@app.command()
def ingest(
    urls: Annotated[list[str], typer.Argument()],
    languages: Annotated[str, typer.Option()] = "en",
    force: Annotated[bool, typer.Option(help="Refetch an existing normalized video")] = False,
    request_delay: Annotated[
        float, typer.Option(min=0, help="Seconds between uncached videos")
    ] = 20.0,
    jitter: Annotated[float, typer.Option(min=0, help="Random extra delay in seconds")] = 20.0,
    max_network_videos: Annotated[
        int,
        typer.Option(min=1, help="Maximum successful uncached videos in one invocation"),
    ] = 10,
    caption_file: Annotated[
        Path | None, typer.Option(help="Import a local VTT/SRT for one URL")
    ] = None,
    proxy_url: Annotated[
        str | None, typer.Option(help="Explicit operator-supplied HTTP(S) proxy")
    ] = None,
    cookie_file: Annotated[
        Path | None, typer.Option(help="Explicit yt-dlp Netscape cookie file")
    ] = None,
    js_runtime: Annotated[
        str | None, typer.Option(help="yt-dlp runtime, e.g. node:C:\\path\\node.exe")
    ] = None,
    allow_audio_download: Annotated[
        bool, typer.Option(help="Allow temporary audio for local ASR")
    ] = False,
    confirm_rights: Annotated[
        bool, typer.Option(help="Confirm authorization to process source audio")
    ] = False,
    retry_blocked: Annotated[
        bool,
        typer.Option(
            help="Retry during an active block cooldown only after changing VPN/proxy route"
        ),
    ] = False,
    whisper_model: Annotated[str, typer.Option(help="faster-whisper model name")] = "small",
    kb: KbOption = None,
) -> None:
    """Fetch metadata and timed transcripts using cache and controlled fallbacks."""
    paths = kb_paths(kb)
    if caption_file and len(urls) != 1:
        raise typer.BadParameter("--caption-file requires exactly one video URL")
    if caption_file and not caption_file.exists():
        raise typer.BadParameter(f"Caption file does not exist: {caption_file}")
    if cookie_file and not cookie_file.exists():
        raise typer.BadParameter(f"Cookie file does not exist: {cookie_file}")
    if allow_audio_download and not confirm_rights:
        raise typer.BadParameter("--allow-audio-download also requires --confirm-rights")
    options = IngestOptions(
        proxy_url=proxy_url or os.getenv("YTKB_YOUTUBE_PROXY_URL"),
        webshare_username=os.getenv("YTKB_WEBSHARE_USERNAME"),
        webshare_password=os.getenv("YTKB_WEBSHARE_PASSWORD"),
        cookie_file=cookie_file,
        js_runtime=js_runtime or os.getenv("YTKB_YTDLP_JS_RUNTIME"),
        supplied_caption=caption_file,
        allow_audio_download=allow_audio_download,
        rights_confirmed=confirm_rights,
        whisper_model=whisper_model,
    )
    retry_path = paths.data("manifests") / "ingest-retries.json"
    retry_state = (
        read_json(retry_path) if retry_path.exists() else {"knowledge_base": paths.id, "items": {}}
    )
    failures: list[str] = []
    network_attempts = 0
    successful_network_videos = 0
    for index, url in enumerate(urls):
        requested_video_id = video_id_from_url(url)
        cache_path = paths.data("normalized") / f"{requested_video_id}.json"
        needs_network = force or not cache_path.exists()
        if needs_network and successful_network_videos >= max_network_videos:
            console.print(
                f"[yellow]Stopped[/yellow] after {successful_network_videos} successful "
                "uncached video(s); the conservative per-run success budget was reached."
            )
            break
        retry_item = retry_state["items"].get(requested_video_id, {})
        active_retry = retry_window_remaining(retry_item)
        alternate_route = bool(
            options.proxy_url or (options.webshare_username and options.webshare_password)
        )
        if (
            needs_network
            and retry_item.get("classification") == "members_only"
            and active_retry
        ):
            days = max(1, round(active_retry.total_seconds() / 86400))
            console.print(
                f"[yellow]Skipped[/yellow] {requested_video_id}: marked members-only; "
                f"cooldown has about {days} day(s) remaining."
            )
            continue
        if needs_network and active_retry and not retry_blocked and not alternate_route:
            hours = max(1, round(active_retry.total_seconds() / 3600))
            failures.append(url)
            console.print(
                f"[yellow]Skipped[/yellow] {requested_video_id}: YouTube block cooldown has "
                f"about {hours} hour(s) remaining. Change VPN/proxy route and pass "
                "--retry-blocked, or wait for the recorded retry time."
            )
            # A cooldown is scoped to this video/route. Continue with other
            # batch entries rather than letting one blocked item starve the
            # remaining eligible catalog.
            continue
        if index and needs_network and request_delay + jitter > 0:
            time.sleep(request_delay + random.uniform(0, jitter))
        if needs_network:
            network_attempts += 1
        try:
            video = ingest_video(
                url, paths.data("normalized"), languages.split(","), options, force=force
            )
            retry_state["items"].pop(video.id, None)
            if needs_network:
                successful_network_videos += 1
            console.print(f"[green]Saved[/green] {video.id}: {video.title}")
        except Exception as error:
            try:
                video_id = video_id_from_url(url)
            except ValueError:
                video_id = url
            previous = retry_state["items"].get(video_id, {})
            attempts = int(previous.get("attempts", 0)) + 1
            now = datetime.now(UTC)
            if isinstance(error, MembersOnlyError):
                retry_state["items"][video_id] = {
                    "url": url,
                    "attempts": attempts,
                    "last_attempt_at": now.isoformat(),
                    "next_retry_at": (now + MEMBERS_ONLY_COOLDOWN).isoformat(),
                    "error_type": type(error).__name__,
                    "classification": "members_only",
                    "availability": "members_only",
                    "message": str(error)[:1000],
                }
                console.print(
                    f"[yellow]Marked[/yellow] {video_id} as members-only; "
                    "will retry after the three-day cooldown."
                )
                continue
            failures.append(url)
            blocked = isinstance(error, TranscriptBlockedError)
            delay_hours = (
                min(24 * (2 ** (attempts - 1)), 24 * 7)
                if blocked
                else min(0.25 * (2 ** (attempts - 1)), 1)
            )
            retry_state["items"][video_id] = {
                "url": url,
                "attempts": attempts,
                "last_attempt_at": now.isoformat(),
                "next_retry_at": (now + timedelta(hours=delay_hours)).isoformat(),
                "error_type": type(error).__name__,
                "blocked": blocked,
                "message": str(error)[:1000],
            }
            console.print(f"[red]Failed[/red] {url}: {error}")
            if isinstance(error, TranscriptBlockedError):
                console.print(
                    "[yellow]YouTube block detected; stopping this batch to avoid escalation.[/yellow]"
                )
                break
    write_json(retry_path, retry_state)
    write_recent_snapshot(paths)
    if failures:
        console.print(
            f"[red]{len(failures)} video(s) failed; successful videos were retained.[/red]"
        )
        raise typer.Exit(1)


@app.command("ingest-media-asr")
def ingest_media_asr_command(
    url: Annotated[str, typer.Argument(help="One YouTube video URL")],
    languages: Annotated[str, typer.Option()] = "en",
    allow_video_download: Annotated[
        bool, typer.Option(help="Allow retaining a private local video copy for ASR")
    ] = False,
    force: Annotated[bool, typer.Option(help="Rerun the retained-media ASR job")] = False,
    dry_run: Annotated[bool, typer.Option(help="Inspect metadata without downloading media")] = False,
    max_video_bytes: Annotated[
        int, typer.Option(min=1, help="Maximum retained video size in bytes")
    ] = 2_000_000_000,
    max_duration: Annotated[
        int, typer.Option(min=1, help="Maximum video duration in seconds")
    ] = 7_200,
    proxy_url: Annotated[
        str | None, typer.Option(help="Explicit operator-supplied HTTP(S) proxy")
    ] = None,
    cookie_file: Annotated[
        Path | None, typer.Option(help="yt-dlp Netscape cookie file")
    ] = None,
    js_runtime: Annotated[
        str | None, typer.Option(help="yt-dlp runtime, e.g. node:C:\\path\\node.exe")
    ] = None,
    whisper_model: Annotated[str, typer.Option(help="faster-whisper model name")] = "small",
    kb: KbOption = None,
) -> None:
    """Run the one-video retained-media ASR smoke test outside normal ingestion."""
    paths = kb_paths(kb)
    if cookie_file and not cookie_file.exists():
        raise typer.BadParameter(f"Cookie file does not exist: {cookie_file}")
    video_id = video_id_from_url(url)
    options = IngestOptions(
        proxy_url=proxy_url or os.getenv("YTKB_YOUTUBE_PROXY_URL"),
        webshare_username=os.getenv("YTKB_WEBSHARE_USERNAME"),
        webshare_password=os.getenv("YTKB_WEBSHARE_PASSWORD"),
        cookie_file=cookie_file,
        js_runtime=js_runtime or os.getenv("YTKB_YTDLP_JS_RUNTIME"),
        allow_video_download=allow_video_download,
        whisper_model=whisper_model,
    )
    if dry_run:
        metadata = fetch_metadata(url, options)
        duration = int(metadata.get("duration") or 0)
        console.print(
            f"[yellow]Dry run[/yellow] {video_id}: {metadata.get('title') or video_id}; "
            f"duration={duration}s; max_duration={max_duration}s; "
            f"max_video_bytes={max_video_bytes:,}"
        )
        return
    try:
        result = ingest_media_asr(
            url,
            paths.data("normalized") / "asr",
            ROOT / "media" / paths.id,
            paths.data("manifests") / "media-asr",
            languages.split(","),
            options,
            force=force,
            max_video_bytes=max_video_bytes,
            max_duration_seconds=max_duration,
        )
    except (PermissionError, ValueError, RuntimeError) as error:
        raise typer.BadParameter(str(error)) from error
    console.print(
        f"[green]Saved ASR transcript[/green] {result.video.id}: "
        f"{len(result.video.transcript.segments if result.video.transcript else [])} segments; "
        f"retained media at {result.manifest['media_dir']}"
    )


@app.command("extract-concepts")
def extract_concepts(
    video_id: Annotated[str | None, typer.Option()] = None,
    engine: Annotated[str, typer.Option()] = "codex",
    kb: KbOption = None,
) -> None:
    """Extract concept candidates using Codex CLI."""
    if engine != "codex":
        raise typer.BadParameter("Only the Codex engine is implemented")
    paths = kb_paths(kb)
    videos = load_videos(paths.data("normalized"))
    if video_id:
        videos = [video for video in videos if video.id == video_id]
    if not videos:
        raise typer.BadParameter("No matching normalized videos found")
    taxonomy = read_yaml(paths.config / "taxonomy.yaml")
    known = [
        {"id": c.id, "label": c.label, "aliases": c.aliases}
        for c in load_reviewed_concepts(paths.content / "concepts")
    ]
    deferred: list[str] = []
    for index, video in enumerate(videos):
        try:
            path = extract_video(
                video,
                taxonomy,
                known,
                ROOT / "config" / "processors.yaml",
                paths.data("derived"),
                paths.data("manifests"),
                budget_path=paths.data("manifests") / "llm-budget.json",
            )
        except LLMBudgetExceeded as error:
            deferred = [item.id for item in videos[index:]]
            console.print(f"[yellow]Deferred {len(deferred)} extraction task(s)[/yellow]: {error}")
            break
        console.print(f"[green]Saved candidates[/green] {path.name}")
    if deferred:
        write_json(
            paths.data("manifests") / "llm-deferred.json",
            {
                "knowledge_base": paths.id,
                "task": "extraction",
                "deferred_video_ids": deferred,
                "reason": "daily or task LLM token budget exhausted",
                "budget": LLMTokenBudget(
                    ROOT / "config" / "processors.yaml",
                    paths.data("manifests") / "llm-budget.json",
                ).status(),
            },
        )


@app.command("rephrase-excerpts")
def rephrase_excerpts(
    model: Annotated[str | None, typer.Option(help="Optional Codex model override")] = None,
    kb: KbOption = None,
) -> None:
    """Rephrase high-overlap canonical excerpts before publication."""
    paths = kb_paths(kb)
    concepts = load_reviewed_concepts(paths.content / "concepts")
    videos = load_videos(paths.data("normalized"))
    publishing = read_yaml(paths.config / "kb.yaml").get("publishing", {})
    findings: list[dict] = []
    try:
        _, findings = rephrase_high_overlap_excerpts(
            paths.content / "concepts",
            concepts,
            videos,
            ROOT / "config" / "processors.yaml",
            paths.data("manifests"),
            budget_path=paths.data("manifests") / "llm-budget.json",
            model_override=model,
            max_chars=int(publishing.get("excerpt_max_chars", 420)),
        )
        report = {
            "knowledge_base": paths.id,
            "status": "complete",
            "rephrased_count": len(findings),
            "items": findings,
        }
    except LLMBudgetExceeded as error:
        report = {
            "knowledge_base": paths.id,
            "status": "deferred",
            "rephrased_count": 0,
            "items": [],
            "reason": str(error),
            "budget": LLMTokenBudget(
                ROOT / "config" / "processors.yaml",
                paths.data("manifests") / "llm-budget.json",
            ).status(),
        }
        console.print(f"[yellow]Deferred excerpt rephrasing[/yellow]: {error}")
    report_path = paths.data("manifests") / "excerpt-rephrasing.json"
    write_json(report_path, report)
    if report["status"] == "deferred":
        console.print(f"[yellow]Rephrasing deferred[/yellow]; report {report_path}")
    else:
        console.print(
            f"[green]Rephrased {len(findings)} high-overlap excerpt(s)[/green]; report {report_path}"
        )


@app.command("benchmark-models")
def benchmark_models(
    models: Annotated[
        str | None,
        typer.Option(
            help="Comma-separated Codex model IDs; defaults to the configured model and gpt-5.4-nano"
        ),
    ] = None,
    video_ids: Annotated[
        str | None,
        typer.Option(help="Optional comma-separated cached video IDs to benchmark"),
    ] = None,
    sample_size: Annotated[
        int, typer.Option(min=1, help="Number of evidence-rich cached videos when IDs are omitted")
    ] = 3,
    output: Annotated[Path | None, typer.Option(help="Optional JSON report path")] = None,
    markdown_output: Annotated[
        Path | None, typer.Option(help="Optional Markdown report path")
    ] = None,
    kb: KbOption = None,
) -> None:
    """Compare Codex extraction models against reviewed transcript evidence."""
    paths = kb_paths(kb)
    config_path = ROOT / "config" / "processors.yaml"
    processor_config = read_yaml(config_path)["codex"]
    requested_models = [item.strip() for item in (models or "").split(",") if item.strip()]
    if not requested_models:
        requested_models = [processor_config["default_model"], "gpt-5.4-nano"]
    requested_models = list(dict.fromkeys(requested_models))
    all_videos = load_videos(paths.data("normalized"))
    reviewed = load_reviewed_concepts(paths.content / "concepts")
    if video_ids:
        requested_ids = [item.strip() for item in video_ids.split(",") if item.strip()]
        video_map = {video.id: video for video in all_videos}
        missing = [video_id for video_id in requested_ids if video_id not in video_map]
        if missing:
            raise typer.BadParameter(
                f"No normalized videos found for: {', '.join(missing)}", param_hint="--video-ids"
            )
        selected = [video_map[video_id] for video_id in requested_ids]
    else:
        selected = select_benchmark_videos(all_videos, reviewed, sample_size)
    if not selected:
        raise typer.BadParameter("No cached normalized transcripts are available for benchmarking")
    taxonomy = read_yaml(paths.config / "taxonomy.yaml")
    output_dir = paths.data("benchmarks")
    json_path = output or output_dir / "latest.json"
    markdown_path = markdown_output or output_dir / "latest.md"
    report = run_quality_benchmark(
        selected,
        reviewed,
        taxonomy,
        config_path,
        requested_models,
        output_dir,
        budget_path=paths.data("manifests") / "llm-budget.json",
    )
    write_json(json_path, report)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_benchmark_markdown(report, paths.name), encoding="utf-8")
    table = Table(title=f"{paths.name} model quality benchmark")
    table.add_column("Model")
    table.add_column("Runs", justify="right")
    table.add_column("Schema", justify="right")
    table.add_column("Citation IDs", justify="right")
    table.add_column("Supported overlap", justify="right")
    for item in report["summary"]:
        table.add_row(
            item["model"],
            str(item["run_count"]),
            f"{item['schema_valid_rate']:.1%}",
            _format_cli_rate(item["valid_citation_rate"]),
            _format_cli_rate(item["overlap_support_rate"]),
        )
    console.print(table)
    console.print(f"[green]JSON report[/green] {json_path}")
    console.print(f"[green]Markdown report[/green] {markdown_path}")


def _format_cli_rate(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1%}"


@app.command("build-review-queue")
def review_queue(kb: KbOption = None) -> None:
    """Create a deterministic YAML review queue."""
    paths = kb_paths(kb)
    count = build_review_queue(
        paths.data("derived"),
        paths.content / "annotations" / "review-queue.yaml",
        load_reviewed_concepts(paths.content / "concepts"),
    )
    console.print(f"[green]{paths.name}: {count} candidates queued[/green]")


@app.command("process-pending")
def process_pending(
    min_confidence: Annotated[
        float, typer.Option(min=0, max=1, help="Minimum confidence for automatic acceptance")
    ] = 0.85,
    retry_deferred: Annotated[
        bool, typer.Option(help="Re-evaluate previously deferred candidates, including the full backfill")
    ] = False,
    kb: KbOption = None,
) -> None:
    """Triage cached pending candidates before any new scrape."""
    paths = kb_paths(kb)
    concepts = load_reviewed_concepts(paths.content / "concepts")
    counts = process_pending_candidates(
        paths.content / "annotations" / "review-queue.yaml",
        paths.content / "concepts",
        paths.data("normalized"),
        concepts,
        min_confidence=min_confidence,
        retry_deferred=retry_deferred,
    )
    diagnostics_output = ROOT / "app" / "src" / "data" / "generated" / f"{paths.id}-concept-review.json"
    diagnostics = build_review_diagnostics(
        paths.content / "annotations" / "review-queue.yaml",
        paths.content / "concepts",
        diagnostics_output,
    )
    navigation_counts = {"placed": 0, "skipped": 0}
    navigation_path = paths.config / "navigation.yaml"
    if navigation_path.exists():
        navigation = read_yaml(navigation_path)
        navigation_counts = auto_place_generated_concepts(navigation, load_reviewed_concepts(paths.content / "concepts"))
        temporary = navigation_path.with_suffix(".yaml.tmp")
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            roundtrip_yaml.dump(navigation, handle)
        temporary.replace(navigation_path)
    console.print(
        f"[green]Processed pending candidates for {paths.name}[/green]: "
        f"{counts['accepted']} accepted, {counts['deferred']} deferred, "
        f"{counts['rejected']} rejected, {counts['evidence_added']} evidence moments added, "
        f"{counts['concepts_added']} concepts added; diagnostics refreshed "
        f"({diagnostics['total']} deferred candidates); navigation placed "
        f"{navigation_counts['placed']} concepts"
    )


@app.command("build-review-diagnostics")
def review_diagnostics(kb: KbOption = None) -> None:
    """Build the local-only deferred/new-concept diagnostic view data."""
    paths = kb_paths(kb)
    output = ROOT / "app" / "src" / "data" / "generated" / f"{paths.id}-concept-review.json"
    payload = build_review_diagnostics(
        paths.content / "annotations" / "review-queue.yaml",
        paths.content / "concepts",
        output,
    )
    console.print(f"[green]{paths.name}: {payload['total']} deferred candidates diagnosed[/green]")


def refresh_catalog() -> None:
    registry = read_yaml(ROOT / "config" / "knowledge-bases.yaml")
    entries = []
    for item in registry["knowledge_bases"]:
        corpus = ROOT / "data" / "publish" / "kbs" / item["id"] / "corpus.json"
        if corpus.exists() and item.get("enabled", True):
            payload = read_json(corpus)
            entries.append(
                {
                    "id": item["id"],
                    "name": item["name"],
                    "description": item["description"],
                    "concept_count": len(payload["concepts"]),
                    "video_count": len(payload["videos"]),
                }
            )
    catalog = {"knowledge_bases": entries}
    write_json(ROOT / "data" / "publish" / "catalog.json", catalog)
    write_json(ROOT / "app" / "public" / "data" / "catalog.json", catalog)


@app.command()
def publish(
    kb: KbOption = None,
    include_demo: Annotated[bool, typer.Option(help="Publish synthetic fixtures")] = False,
    auto_rephrase_high_overlap: Annotated[
        bool,
        typer.Option(
            help="Run the low-cost Codex rephrase stage before publishing flagged excerpts"
        ),
    ] = False,
) -> None:
    """Build one sanitized static-site corpus and refresh the catalog."""
    paths = kb_paths(kb)
    summary_updates = write_missing_summaries(
        paths.content / "concepts", refresh_generated=True
    )
    if summary_updates:
        console.print(f"[yellow]Refreshed {len(summary_updates)} generated concept summary(ies)[/yellow]")
    if auto_rephrase_high_overlap:
        concepts = load_reviewed_concepts(paths.content / "concepts")
        videos = load_videos(paths.data("normalized"))
        publishing = read_yaml(paths.config / "kb.yaml").get("publishing", {})
        try:
            _, findings = rephrase_high_overlap_excerpts(
                paths.content / "concepts",
                concepts,
                videos,
                ROOT / "config" / "processors.yaml",
                paths.data("manifests"),
                budget_path=paths.data("manifests") / "llm-budget.json",
                max_chars=int(publishing.get("excerpt_max_chars", 420)),
            )
            rephrase_status = "complete"
            rephrase_reason = None
        except LLMBudgetExceeded as error:
            findings = []
            rephrase_status = "deferred"
            rephrase_reason = str(error)
            console.print(f"[yellow]Deferred auto-rephrasing[/yellow]: {error}")
        write_json(
            paths.data("manifests") / "excerpt-rephrasing.json",
            {
                "knowledge_base": paths.id,
                "status": rephrase_status,
                "rephrased_count": len(findings),
                "items": findings,
                **({"reason": rephrase_reason} if rephrase_reason else {}),
            },
        )
        if rephrase_status == "deferred":
            console.print(
                "[yellow]Publication was not started; rerun after the budget resets or is adjusted.[/yellow]"
            )
            raise typer.Exit(2)
        if findings:
            console.print(f"[yellow]Auto-rephrased {len(findings)} high-overlap excerpt(s)[/yellow]")
    output = ROOT / "data" / "publish" / "kbs" / paths.id
    corpus = publish_corpus(
        paths.content / "concepts",
        paths.data("normalized"),
        output,
        {"id": paths.id, "name": paths.name, "description": paths.description},
        navigation=read_yaml(paths.config / "navigation.yaml")
        if (paths.config / "navigation.yaml").exists()
        else None,
        include_demo=include_demo,
    )
    public = ROOT / "app" / "public" / "data" / "kbs" / paths.id
    public.mkdir(parents=True, exist_ok=True)
    shutil.copy2(output / "corpus.json", public / "corpus.json")
    shutil.copy2(output / "manifest.json", public / "manifest.json")
    refresh_catalog()
    progress_path = ROOT / "app" / "src" / "data" / "generated" / f"{paths.id}-progress.json"
    write_json(progress_path, build_progress_report(paths, corpus))
    write_recent_snapshot(paths)
    console.print(f"[green]Published {paths.name}: {len(corpus.concepts)} concepts[/green]")


@app.command("validate-published")
def validate_published(kb: KbOption = None) -> None:
    """Validate committed public artifacts without private transcript files."""
    paths = kb_paths(kb)
    publish_dir = ROOT / "data" / "publish" / "kbs" / paths.id
    corpus_path = publish_dir / "corpus.json"
    manifest_path = publish_dir / "manifest.json"
    public_dir = ROOT / "app" / "public" / "data" / "kbs" / paths.id
    public_corpus_path = public_dir / "corpus.json"
    public_manifest_path = public_dir / "manifest.json"
    required = [corpus_path, manifest_path, public_corpus_path, public_manifest_path]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        raise typer.BadParameter(f"Missing published artifacts: {', '.join(missing)}")

    corpus = PublishCorpus.model_validate(read_json(corpus_path))
    manifest = read_json(manifest_path)
    errors = validate_published_corpus(corpus)
    if corpus_path.read_bytes() != public_corpus_path.read_bytes():
        errors.append("published corpus differs from app/public copy")
    if manifest_path.read_bytes() != public_manifest_path.read_bytes():
        errors.append("published manifest differs from app/public copy")
    if manifest.get("corpus_hash") != sha256_json(corpus.model_dump(mode="json")):
        errors.append("published manifest corpus hash is stale")
    if manifest.get("concept_count") != len(corpus.concepts):
        errors.append("published manifest concept count is stale")
    if manifest.get("video_count") != len(corpus.videos):
        errors.append("published manifest video count is stale")
    queue_path = paths.content / "annotations" / "review-queue.yaml"
    if queue_path.exists():
        normalized_videos = load_videos(paths.data("normalized"))
        demo_ids = _demo_video_ids(normalized_videos)
        errors.extend(
            validate_review_queue(
                read_yaml(queue_path), corpus.concepts, ignored_video_ids=demo_ids
            )
        )
    if errors:
        for error in errors:
            console.print(f"[red]ERROR[/red] {error}")
        raise typer.Exit(1)
    console.print(
        f"[green]{paths.name}: published artifacts valid[/green] "
        f"({len(corpus.concepts)} concepts, {len(corpus.videos)} videos)"
    )


@app.command("report-quality")
def report_quality(
    kb: KbOption = None,
    output: Annotated[Path | None, typer.Option(help="Optional JSON report path")] = None,
    markdown_output: Annotated[
        Path | None, typer.Option(help="Optional Markdown report path")
    ] = None,
) -> None:
    """Report editorial quality signals for a published knowledge base."""
    paths = kb_paths(kb)
    corpus_path = ROOT / "data" / "publish" / "kbs" / paths.id / "corpus.json"
    corpus = PublishCorpus.model_validate(read_json(corpus_path))
    queue_path = paths.content / "annotations" / "review-queue.yaml"
    queue = read_yaml(queue_path) if queue_path.exists() else {}
    report = build_quality_report(corpus, queue)
    report["public_corpus_bytes"] = corpus_path.stat().st_size
    if output:
        write_json(output, report)
    if markdown_output:
        markdown_output.parent.mkdir(parents=True, exist_ok=True)
        markdown_output.write_text(
            render_quality_report_markdown(report, paths.name), encoding="utf-8"
        )
    table = Table(title=f"{paths.name} quality report")
    table.add_column("Signal")
    table.add_column("Count", justify="right")
    for label, key in [
        ("Concepts", "concept_count"),
        ("Published videos", "published_video_count"),
        ("Evidence moments", "evidence_count"),
        ("Distinct excerpts", "distinct_excerpt_count"),
        ("Isolated concepts", "concepts_without_relations"),
        ("Single-source concepts", "single_source_concepts"),
        ("Verified visuals", "verified_visual_count"),
        ("Pending candidates", "pending_candidate_count"),
    ]:
        value = report[key]
        table.add_row(label, str(len(value) if isinstance(value, list) else value))
    console.print(table)


@app.command("report-boundaries")
def report_boundaries(
    kb: KbOption = None,
    output: Annotated[Path | None, typer.Option(help="Optional JSON report path")] = None,
    markdown_output: Annotated[
        Path | None, typer.Option(help="Optional Markdown report path")
    ] = None,
    include_demo: Annotated[bool, typer.Option(help="Include synthetic demo evidence")] = False,
) -> None:
    """Measure caption boundary quality without calling an LLM."""
    paths = kb_paths(kb)
    concepts = load_reviewed_concepts(paths.content / "concepts")
    videos = load_videos(paths.data("normalized"))
    if not include_demo:
        demo_ids = _demo_video_ids(videos)
        videos = [video for video in videos if video.id not in demo_ids]
        concepts = [
            concept.model_copy(
                update={
                    "evidence": [
                        item for item in concept.evidence if item.source.video_id not in demo_ids
                    ]
                }
            )
            for concept in concepts
            if any(item.source.video_id not in demo_ids for item in concept.evidence)
        ]
    report = build_boundary_report(concepts, videos, paths.id)
    json_path = output or paths.data("manifests") / "boundary-report.json"
    write_json(json_path, report)
    if markdown_output:
        markdown_output.parent.mkdir(parents=True, exist_ok=True)
        markdown_output.write_text(
            render_boundary_report_markdown(report, paths.name), encoding="utf-8"
        )
    rates = report["rates"]
    console.print(
        f"[green]{paths.name} boundary report[/green]: "
        f"{report['evaluated_count']}/{report['evidence_count']} evaluated; "
        f"mid-sentence {rates['starts_mid_sentence']:.1%}/{rates['ends_mid_sentence']:.1%}; "
        f"too short {rates['too_short']:.1%}; "
        f"needs context {rates['needs_context']:.1%}"
    )
    console.print(f"[green]JSON report[/green] {json_path}")


@app.command("prepare-boundary-review")
def prepare_boundary_review(
    kb: KbOption = None,
    sample_size: Annotated[int, typer.Option(min=1, help="Number of stratified flagged moments to export")] = 24,
    output: Annotated[Path | None, typer.Option(help="Optional JSON worksheet path")] = None,
    markdown_output: Annotated[Path | None, typer.Option(help="Optional Markdown worksheet path")] = None,
) -> None:
    """Export an undecided, stratified boundary gold-set worksheet."""
    paths = kb_paths(kb)
    concepts = load_reviewed_concepts(paths.content / "concepts")
    videos = load_videos(paths.data("normalized"))
    review_set = build_boundary_review_set(concepts, videos, paths.id, sample_size)
    json_path = output or paths.data("manifests") / "boundary-review.json"
    write_json(json_path, review_set)
    if markdown_output:
        markdown_output.parent.mkdir(parents=True, exist_ok=True)
        markdown_output.write_text(
            render_boundary_review_set_markdown(review_set, paths.name), encoding="utf-8"
        )
    console.print(
        f"[green]{paths.name} boundary review worksheet[/green]: "
        f"{review_set['sample_size']} sampled from {review_set['flagged_pool_size']} flagged moments"
    )
    console.print(f"[green]JSON worksheet[/green] {json_path}")


@app.command("validate-boundary-review")
def validate_boundary_review(
    kb: KbOption = None,
    input_path: Annotated[Path | None, typer.Option(help="Boundary review worksheet JSON path")] = None,
) -> None:
    """Validate an edited boundary worksheet without publishing its decisions."""
    paths = kb_paths(kb)
    json_path = input_path or paths.data("manifests") / "boundary-review.json"
    if not json_path.exists():
        raise typer.BadParameter(f"Boundary review worksheet does not exist: {json_path}")
    review_set = read_json(json_path)
    errors = validate_boundary_review_set(review_set, load_videos(paths.data("normalized")))
    if errors:
        for error in errors:
            console.print(f"[red]{error}[/red]")
        raise typer.Exit(1)
    pending = sum(item.get("review_action") is None for item in review_set.get("items", []))
    console.print(
        f"[green]{paths.name} boundary worksheet valid[/green]: "
        f"{len(review_set.get('items', []))} items, {pending} pending"
    )


@app.command()
def validate(
    kb: KbOption = None,
    include_demo: Annotated[bool, typer.Option(help="Validate synthetic fixtures")] = False,
) -> None:
    """Validate one knowledge base."""
    paths = kb_paths(kb)
    concepts = load_reviewed_concepts(paths.content / "concepts")
    videos = load_videos(paths.data("normalized"))
    if not include_demo:
        demo_ids = _demo_video_ids(videos)
        videos = [video for video in videos if video.id not in demo_ids]
        concepts = [
            concept.model_copy(
                update={
                    "evidence": [
                        item for item in concept.evidence if item.source.video_id not in demo_ids
                    ]
                }
            )
            for concept in concepts
            if any(item.source.video_id not in demo_ids for item in concept.evidence)
        ]
    errors = validate_corpus(concepts, videos)
    navigation_path = paths.config / "navigation.yaml"
    if navigation_path.exists():
        navigation = KnowledgeNavigation.model_validate(read_yaml(navigation_path))
        errors.extend(validate_navigation(navigation, concepts))
    queue_path = paths.content / "annotations" / "review-queue.yaml"
    if queue_path.exists():
        errors.extend(
            validate_review_queue(
                read_yaml(queue_path), concepts, ignored_video_ids=demo_ids
            )
        )
    if errors:
        for error in errors:
            console.print(f"[red]ERROR[/red] {error}")
        raise typer.Exit(1)
    table = Table(title=f"{paths.name} validation")
    table.add_column("Item")
    table.add_column("Count", justify="right")
    table.add_row("Concepts", str(len(concepts)))
    table.add_row("Videos", str(len(videos)))
    table.add_row("Evidence", str(sum(len(c.evidence) for c in concepts)))
    console.print(table)


@app.command()
def demo(kb: KbOption = None) -> None:
    """Install the network-free fixture for a knowledge base and publish it."""
    paths = kb_paths(kb)
    if paths.id != "table-tennis":
        raise typer.BadParameter("A demo fixture is currently available only for table-tennis")
    write_demo_video(paths.data("normalized"))
    publish(paths.id, include_demo=True)


if __name__ == "__main__":
    app()
