from __future__ import annotations

import os
import random
import shutil
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from .benchmark import render_benchmark_markdown, run_quality_benchmark, select_benchmark_videos
from .demo import write_demo_video
from .ingest import (
    IngestOptions,
    TranscriptBlockedError,
    discover_videos,
    ingest_video,
    video_id_from_url,
)
from .models import KnowledgeNavigation, PublishCorpus
from .pipeline import (
    build_quality_report,
    build_review_queue,
    extract_video,
    load_reviewed_concepts,
    load_videos,
    render_quality_report_markdown,
    validate_corpus,
    validate_navigation,
    validate_published_corpus,
    validate_review_queue,
)
from .pipeline import publish as publish_corpus
from .utils import read_json, read_yaml, sha256_json, write_json
from .workspace import KnowledgeBasePaths, load_knowledge_base

ROOT = Path(__file__).resolve().parents[1]
console = Console()


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


@app.command()
def discover(url: Annotated[str, typer.Argument()], kb: KbOption = None) -> None:
    """Discover videos in a source and save a reviewable manifest."""
    paths = kb_paths(kb)
    with console.status(f"Discovering videos for {paths.name}"):
        videos = discover_videos(url)
    output = paths.data("manifests") / "discovered-videos.json"
    write_json(output, {"knowledge_base": paths.id, "source_url": url, "videos": videos})
    console.print(f"[green]Discovered {len(videos)} videos[/green] for {paths.name}")


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
        typer.Option(min=1, help="Maximum uncached videos attempted in one invocation"),
    ] = 8,
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
    for index, url in enumerate(urls):
        requested_video_id = video_id_from_url(url)
        cache_path = paths.data("normalized") / f"{requested_video_id}.json"
        needs_network = force or not cache_path.exists()
        if needs_network and network_attempts >= max_network_videos:
            console.print(
                f"[yellow]Stopped[/yellow] after {network_attempts} uncached video(s); "
                "the conservative per-run request budget was reached."
            )
            break
        active_retry = retry_window_remaining(retry_state["items"].get(requested_video_id, {}))
        alternate_route = bool(
            options.proxy_url or (options.webshare_username and options.webshare_password)
        )
        if needs_network and active_retry and not retry_blocked and not alternate_route:
            hours = max(1, round(active_retry.total_seconds() / 3600))
            failures.append(url)
            console.print(
                f"[yellow]Skipped[/yellow] {requested_video_id}: YouTube block cooldown has "
                f"about {hours} hour(s) remaining. Change VPN/proxy route and pass "
                "--retry-blocked, or wait for the recorded retry time."
            )
            break
        if index and needs_network and request_delay + jitter > 0:
            time.sleep(request_delay + random.uniform(0, jitter))
        if needs_network:
            network_attempts += 1
        try:
            video = ingest_video(
                url, paths.data("normalized"), languages.split(","), options, force=force
            )
            retry_state["items"].pop(video.id, None)
            console.print(f"[green]Saved[/green] {video.id}: {video.title}")
        except Exception as error:
            failures.append(url)
            try:
                video_id = video_id_from_url(url)
            except ValueError:
                video_id = url
            previous = retry_state["items"].get(video_id, {})
            attempts = int(previous.get("attempts", 0)) + 1
            delay_hours = min(24 * (2 ** (attempts - 1)), 24 * 7)
            retry_state["items"][video_id] = {
                "url": url,
                "attempts": attempts,
                "last_attempt_at": datetime.now(UTC).isoformat(),
                "next_retry_at": (datetime.now(UTC) + timedelta(hours=delay_hours)).isoformat(),
                "error_type": type(error).__name__,
                "message": str(error)[:1000],
            }
            console.print(f"[red]Failed[/red] {url}: {error}")
            if isinstance(error, TranscriptBlockedError):
                console.print(
                    "[yellow]YouTube block detected; stopping this batch to avoid escalation.[/yellow]"
                )
                break
    write_json(retry_path, retry_state)
    if failures:
        console.print(
            f"[red]{len(failures)} video(s) failed; successful videos were retained.[/red]"
        )
        raise typer.Exit(1)


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
    for video in videos:
        path = extract_video(
            video,
            taxonomy,
            known,
            ROOT / "config" / "processors.yaml",
            paths.data("derived"),
            paths.data("manifests"),
        )
        console.print(f"[green]Saved candidates[/green] {path.name}")


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
) -> None:
    """Build one sanitized static-site corpus and refresh the catalog."""
    paths = kb_paths(kb)
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
        errors.extend(validate_review_queue(read_yaml(queue_path), corpus.concepts))
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
        demo_ids = {video.id for video in videos if video.availability == "demo_fixture"}
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
        errors.extend(validate_review_queue(read_yaml(queue_path), concepts))
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
