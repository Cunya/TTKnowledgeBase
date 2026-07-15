from __future__ import annotations

import re
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rapidfuzz.fuzz import token_set_ratio

from .codex_engine import extract_with_codex
from .models import Concept, ExtractionResponse, Video
from .utils import write_json


def _normalise_label(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()


def _best_reviewed_match(label: str, concepts: list[Concept]) -> tuple[Concept | None, int]:
    best: tuple[Concept | None, int] = (None, 0)
    for concept in concepts:
        score = max(
            token_set_ratio(label, candidate)
            for candidate in [concept.label, *concept.aliases]
        )
        if score > best[1]:
            best = (concept, int(score))
    return best


def score_response(
    response: ExtractionResponse,
    video: Video,
    reviewed_concepts: list[Concept],
    *,
    match_threshold: int = 60,
) -> dict[str, Any]:
    """Score one valid extraction against reviewed, transcript-backed evidence.

    This is a precision-oriented proxy, not an automatic editorial decision. A
    name match is only counted as supported when the candidate also cites a
    segment already used by the matched reviewed concept for this video.
    """

    segments = {segment.id for segment in (video.transcript.segments if video.transcript else [])}
    gold_by_id: dict[str, set[str]] = defaultdict(set)
    for concept in reviewed_concepts:
        for evidence in concept.evidence:
            if evidence.source.video_id == video.id:
                gold_by_id[concept.id].update(evidence.source.segment_ids)

    total_references = 0
    valid_references = 0
    overlap_count = 0
    supported_count = 0
    supported_concepts: set[str] = set()
    matched_concepts: set[str] = set()
    duplicate_labels: set[str] = set()
    labels_seen: set[str] = set()

    for candidate in response.concepts:
        label = _normalise_label(candidate.canonical_label)
        if label in labels_seen:
            duplicate_labels.add(label)
        labels_seen.add(label)
        candidate_ids = [segment_id for evidence in candidate.evidence for segment_id in evidence.segment_ids]
        total_references += len(candidate_ids)
        valid_references += sum(segment_id in segments for segment_id in candidate_ids)
        matched, score = _best_reviewed_match(candidate.canonical_label, reviewed_concepts)
        if not matched or score < match_threshold:
            continue
        overlap_count += 1
        matched_concepts.add(matched.id)
        if set(candidate_ids).intersection(gold_by_id.get(matched.id, set())):
            supported_count += 1
            supported_concepts.add(matched.id)

    gold_concepts = set(gold_by_id)
    return {
        "candidate_count": len(response.concepts),
        "duplicate_label_count": len(duplicate_labels),
        "gold_concept_count": len(gold_concepts),
        "matched_concept_count": len(matched_concepts),
        "supported_concept_count": len(supported_concepts),
        "overlapping_candidate_count": overlap_count,
        "supported_overlap_count": supported_count,
        "citation_reference_count": total_references,
        "valid_citation_reference_count": valid_references,
        "valid_citation_rate": (
            round(valid_references / total_references, 4) if total_references else 0.0
        ),
        "overlap_support_rate": (
            round(supported_count / overlap_count, 4) if overlap_count else 0.0
        ),
        "concept_recall_proxy": (
            round(len(supported_concepts) / len(gold_concepts), 4) if gold_concepts else None
        ),
    }


def select_benchmark_videos(
    videos: list[Video], reviewed_concepts: list[Concept], sample_size: int
) -> list[Video]:
    """Pick a deterministic, evidence-rich sample from cached transcripts."""

    eligible = [
        video
        for video in videos
        if video.transcript and video.availability != "demo_fixture" and video.transcript.segments
    ]
    evidence_counts = {
        video.id: sum(
            1
            for concept in reviewed_concepts
            for evidence in concept.evidence
            if evidence.source.video_id == video.id
        )
        for video in eligible
    }
    return sorted(eligible, key=lambda video: (-evidence_counts[video.id], video.id))[:sample_size]


def _usage_total(usage: dict | None, key: str) -> int:
    if not usage:
        return 0
    value = usage.get(key, 0)
    return int(value) if isinstance(value, (int, float)) else 0


def run_quality_benchmark(
    videos: list[Video],
    reviewed_concepts: list[Concept],
    taxonomy: dict,
    config_path: Path,
    models: list[str],
    output_dir: Path,
) -> dict[str, Any]:
    """Run model comparisons and write private per-run audit artifacts."""

    output_dir.mkdir(parents=True, exist_ok=True)
    runs: list[dict[str, Any]] = []
    known = [
        {"id": concept.id, "label": concept.label, "aliases": concept.aliases}
        for concept in reviewed_concepts
    ]
    for model in models:
        model_slug = re.sub(r"[^a-zA-Z0-9_.-]+", "_", model)
        for video in videos:
            started = time.monotonic()
            base = {"model": model, "video_id": video.id, "video_title": video.title}
            try:
                response, provenance = extract_with_codex(
                    video.transcript.segments,  # type: ignore[union-attr]
                    taxonomy,
                    known,
                    config_path,
                    output_dir / "audit" / model_slug,
                    model_override=model,
                )
                metrics = score_response(response, video, reviewed_concepts)
                run = {
                    **base,
                    "status": "ok",
                    "schema_valid": True,
                    "elapsed_seconds": round(time.monotonic() - started, 2),
                    "provenance": provenance,
                    "metrics": metrics,
                }
            except Exception as error:  # benchmark records failures instead of stopping the batch
                run = {
                    **base,
                    "status": "failed",
                    "schema_valid": False,
                    "elapsed_seconds": round(time.monotonic() - started, 2),
                    "error_type": type(error).__name__,
                    "error": str(error)[:2000],
                }
            write_json(
                output_dir / "runs" / f"{model_slug}-{video.id}.json",
                run,
            )
            runs.append(run)

    summary: list[dict[str, Any]] = []
    for model in models:
        model_runs = [run for run in runs if run["model"] == model]
        successful = [run for run in model_runs if run["status"] == "ok"]
        failures = [run for run in model_runs if run["status"] != "ok"]
        failure_reasons = sorted(
            {
                _failure_reason(run.get("error", ""))
                for run in failures
                if run.get("error")
            }
        )
        availability = (
            "available"
            if successful
            else "unsupported in Codex account"
            if any(reason == "model_not_supported" for reason in failure_reasons)
            else "failed"
        )
        metric_values = [run["metrics"] for run in successful]
        summary.append(
            {
                "model": model,
                "availability": availability,
                "failure_reasons": failure_reasons,
                "run_count": len(model_runs),
                "successful_run_count": len(successful),
                "schema_valid_rate": round(len(successful) / len(model_runs), 4)
                if model_runs
                else 0.0,
                "valid_citation_rate": _average(metric_values, "valid_citation_rate"),
                "overlap_support_rate": _average(metric_values, "overlap_support_rate"),
                "concept_recall_proxy": _average(metric_values, "concept_recall_proxy"),
                "candidate_count": _average(metric_values, "candidate_count"),
                "duplicate_label_count": _average(metric_values, "duplicate_label_count"),
                "input_tokens": sum(
                    _usage_total(run.get("provenance", {}).get("usage"), "input_tokens")
                    for run in successful
                ),
                "output_tokens": sum(
                    _usage_total(run.get("provenance", {}).get("usage"), "output_tokens")
                    for run in successful
                ),
                "elapsed_seconds": round(
                    sum(float(run["elapsed_seconds"]) for run in model_runs), 2
                ),
            }
        )
    return {
        "benchmark_version": "1.0.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "video_ids": [video.id for video in videos],
        "videos": [{"id": video.id, "title": video.title} for video in videos],
        "models": models,
        "summary": summary,
        "runs": runs,
        "method": {
            "match_threshold": 60,
            "citation_metric": "candidate evidence segment IDs that exist in the normalized transcript",
            "support_metric": "fuzzy concept-name overlap plus intersection with reviewed evidence segment IDs for this video",
            "warning": "These are screening signals for model selection, not automatic editorial approval.",
        },
    }


def _failure_reason(message: str) -> str:
    lowered = message.casefold()
    if "not supported when using codex with a chatgpt account" in lowered:
        return "model_not_supported"
    if "authentication" in lowered or "login" in lowered:
        return "authentication"
    if "timed out" in lowered or "timeout" in lowered:
        return "timeout"
    return "command_failed"


def _average(values: list[dict[str, Any]], key: str) -> float | None:
    numbers = [value[key] for value in values if isinstance(value.get(key), (int, float))]
    return round(sum(numbers) / len(numbers), 4) if numbers else None


def render_benchmark_markdown(report: dict[str, Any], kb_name: str) -> str:
    lines = [
        f"# {kb_name} Codex extraction quality benchmark",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "This compares extraction models on cached, transcript-backed videos. It does not change the production model, publish candidates, or treat name overlap as editorial approval.",
        "",
        "## Model summary",
        "",
        "| Model | Availability | Runs | Schema-valid | Citation IDs | Supported overlap | Recall proxy | Candidates | Input tokens | Output tokens |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in report["summary"]:
        lines.append(
            f"| `{item['model']}` | {item['availability']} | {item['run_count']} | {item['schema_valid_rate']:.1%} | "
            f"{_format_rate(item['valid_citation_rate'])} | {_format_rate(item['overlap_support_rate'])} | "
            f"{_format_rate(item['concept_recall_proxy'])} | {_format_number(item['candidate_count'])} | "
            f"{item['input_tokens']} | {item['output_tokens']} |"
        )
        if item.get("failure_reasons"):
            lines.append(
                f"  - Failure reason: {', '.join(f'`{reason}`' for reason in item['failure_reasons'])}"
            )
    lines.extend(["", "## Per-video runs", "", "| Model | Video | Status | Candidates | Citation IDs | Support |", "| --- | --- | --- | ---: | ---: | ---: |"])
    for run in report["runs"]:
        metrics = run.get("metrics", {})
        lines.append(
            f"| `{run['model']}` | {run['video_id']} | {run['status']} | "
            f"{_format_number(metrics.get('candidate_count'))} | "
            f"{_format_rate(metrics.get('valid_citation_rate'))} | "
            f"{_format_rate(metrics.get('overlap_support_rate'))} |"
        )
    lines.extend(
        [
            "",
            "## How to read this",
            "",
            "- **Schema-valid** means the CLI returned the strict Pydantic extraction schema.",
            "- **Citation IDs** measures whether proposed evidence points to real segments in the input transcript.",
            "- **Supported overlap** is a conservative precision proxy: the candidate label overlaps a reviewed concept and cites at least one segment already approved for that concept in this video.",
            "- **Recall proxy** counts distinct reviewed concepts supported by the sample; it is not a complete-recall claim because the sample is small and the reviewed corpus is incomplete.",
            "- Token totals are usage values reported by Codex when available; they are not a billing estimate for a Codex subscription.",
            "",
            "## Method",
            "",
            f"Videos: {', '.join(f'`{video_id}`' for video_id in report['video_ids'])}",
            "",
            report["method"]["warning"],
        ]
    )
    return "\n".join(lines) + "\n"


def _format_rate(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1%}"


def _format_number(value: float | int | None) -> str:
    return "n/a" if value is None else f"{value:.1f}" if isinstance(value, float) else str(value)
