"""Deterministic boundary analysis for transcript-backed evidence moments.

This module deliberately operates on normalized caption segments only.  It can
propose a more natural playback boundary and flag moments for review, but it
does not invent timestamps or change the public corpus by itself.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from statistics import median
from typing import Any

from .models import Concept, Segment, Video
from .utils import youtube_url

MAX_UNIT_GAP_MS = 1_200
MAX_UNIT_DURATION_MS = 15_000
MAX_CITED_SEGMENT_GAP_MS = 20_000
MAX_SOURCE_DURATION_MS = 30_000
TOO_SHORT_MS = 4_000

_TERMINAL_RE = re.compile(r"[.!?](?:[\"'’”»)}\]]+)?$")


@dataclass(frozen=True)
class CaptionUnit:
    """A derived sentence-like unit that retains its caption segment IDs."""

    segment_ids: tuple[str, ...]
    start_ms: int
    end_ms: int
    text: str


@dataclass(frozen=True)
class BoundaryAssessment:
    """Deterministic boundary findings for one cited segment cluster."""

    segment_ids: tuple[str, ...]
    start_ms: int
    end_ms: int
    snapped_start_ms: int
    snapped_end_ms: int
    flags: tuple[str, ...]
    boundary_confidence: float
    reason: str

    @property
    def needs_context(self) -> bool:
        return "needs_context" in self.flags


def _is_terminal(text: str) -> bool:
    return bool(_TERMINAL_RE.search(text.strip()))


def _merge_allowed(previous: Segment, current: Segment, unit: list[Segment]) -> bool:
    """Return whether two neighboring cues belong to one sentence-like unit."""
    if current.start_ms - previous.end_ms > MAX_UNIT_GAP_MS:
        return False
    if current.end_ms - unit[0].start_ms > MAX_UNIT_DURATION_MS:
        return False
    # A terminal cue is a strong boundary.  Otherwise captions often split a
    # sentence over several cues without punctuation, so the small gap is enough
    # evidence to merge them conservatively.
    return not _is_terminal(previous.text)


def derive_caption_units(segments: list[Segment]) -> list[CaptionUnit]:
    """Merge nearby non-terminal caption cues into bounded sentence-like units."""
    ordered = sorted(segments, key=lambda item: (item.start_ms, item.id))
    if not ordered:
        return []
    units: list[CaptionUnit] = []
    current: list[Segment] = [ordered[0]]
    for segment in ordered[1:]:
        if _merge_allowed(current[-1], segment, current):
            current.append(segment)
            continue
        units.append(
            CaptionUnit(
                segment_ids=tuple(item.id for item in current),
                start_ms=current[0].start_ms,
                end_ms=current[-1].end_ms,
                text=" ".join(item.normalized_text for item in current),
            )
        )
        current = [segment]
    units.append(
        CaptionUnit(
            segment_ids=tuple(item.id for item in current),
            start_ms=current[0].start_ms,
            end_ms=current[-1].end_ms,
            text=" ".join(item.normalized_text for item in current),
        )
    )
    return units


def _largest_contiguous_group(segments: list[Segment]) -> list[Segment]:
    groups: list[list[Segment]] = []
    current: list[Segment] = []
    for segment in segments:
        if not current:
            current = [segment]
            continue
        first = current[0]
        previous = current[-1]
        if (
            segment.start_ms - previous.end_ms > MAX_CITED_SEGMENT_GAP_MS
            or segment.end_ms - first.start_ms > MAX_SOURCE_DURATION_MS
        ):
            groups.append(current)
            current = [segment]
        else:
            current.append(segment)
    groups.append(current)
    return max(groups, key=lambda group: (len(group), group[-1].end_ms - group[0].start_ms))


def assess_boundary(video: Video, segment_ids: list[str]) -> BoundaryAssessment | None:
    """Assess a cited span without changing its claim-supporting IDs.

    ``start_ms``/``end_ms`` are the conservative cited interval.  The snapped
    interval is a proposal for a complete caption unit and is never published by
    this function.  Callers can defer flagged candidates for review.
    """
    if not video.transcript:
        return None
    by_id = {segment.id: segment for segment in video.transcript.segments}
    selected = sorted(
        {segment_id: by_id[segment_id] for segment_id in segment_ids if segment_id in by_id}.values(),
        key=lambda segment: (segment.start_ms, segment.id),
    )
    if not selected:
        return None
    group = _largest_contiguous_group(selected)
    cited_ids = tuple(segment.id for segment in group)
    start_ms = group[0].start_ms
    end_ms = min(
        group[-1].end_ms,
        start_ms + MAX_SOURCE_DURATION_MS,
        video.duration_ms or group[-1].end_ms,
    )

    units = derive_caption_units(video.transcript.segments)
    unit_by_segment = {
        segment_id: unit for unit in units for segment_id in unit.segment_ids
    }
    first_unit = unit_by_segment.get(group[0].id)
    last_unit = unit_by_segment.get(group[-1].id)
    starts_mid_sentence = bool(first_unit and group[0].id != first_unit.segment_ids[0])
    ends_mid_sentence = bool(last_unit and group[-1].id != last_unit.segment_ids[-1])
    snapped_start_ms = first_unit.start_ms if starts_mid_sentence and first_unit else start_ms
    snapped_end_ms = last_unit.end_ms if ends_mid_sentence and last_unit else end_ms
    if snapped_end_ms - snapped_start_ms > MAX_SOURCE_DURATION_MS:
        snapped_start_ms, snapped_end_ms = start_ms, end_ms

    flags: list[str] = []
    if starts_mid_sentence:
        flags.append("starts_mid_sentence")
    if ends_mid_sentence:
        flags.append("ends_mid_sentence")
    if end_ms - start_ms < TOO_SHORT_MS:
        flags.append("too_short")
    if any(flag in flags for flag in ("starts_mid_sentence", "ends_mid_sentence", "too_short")):
        flags.append("needs_context")

    confidence = 1.0
    if starts_mid_sentence or ends_mid_sentence:
        confidence -= 0.2
    if "too_short" in flags:
        confidence -= 0.25
    confidence = max(0.0, round(confidence, 2))
    if flags:
        reason = (
            f"Caption-only review: cited span is {(end_ms - start_ms) / 1000:.1f}s; "
            f"proposed complete-unit span is {(snapped_end_ms - snapped_start_ms) / 1000:.1f}s."
        )
    else:
        reason = "Caption-only span aligns to complete derived units and meets the duration threshold."
    return BoundaryAssessment(
        segment_ids=cited_ids,
        start_ms=start_ms,
        end_ms=end_ms,
        snapped_start_ms=snapped_start_ms,
        snapped_end_ms=snapped_end_ms,
        flags=tuple(flags),
        boundary_confidence=confidence,
        reason=reason,
    )


def _percent(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


def build_boundary_report(concepts: list[Concept], videos: list[Video], knowledge_base: str) -> dict:
    """Measure boundary quality over reviewed evidence using only local captions."""
    video_map = {video.id: video for video in videos}
    flags = Counter()
    durations: list[int] = []
    samples: list[dict] = []
    evaluated = 0
    unavailable = 0
    for concept in concepts:
        for evidence in concept.evidence:
            video = video_map.get(evidence.source.video_id)
            assessment = assess_boundary(video, evidence.source.segment_ids) if video else None
            if assessment is None:
                unavailable += 1
                continue
            evaluated += 1
            duration_ms = assessment.end_ms - assessment.start_ms
            durations.append(duration_ms)
            flags.update(assessment.flags)
            if assessment.flags and len(samples) < 50:
                samples.append(
                    {
                        "concept_id": concept.id,
                        "evidence_id": evidence.id,
                        "video_id": evidence.source.video_id,
                        "start_ms": assessment.start_ms,
                        "end_ms": assessment.end_ms,
                        "duration_ms": duration_ms,
                        "snapped_start_ms": assessment.snapped_start_ms,
                        "snapped_end_ms": assessment.snapped_end_ms,
                        "flags": list(assessment.flags),
                        "boundary_confidence": assessment.boundary_confidence,
                    }
                )
    sorted_durations = sorted(durations)
    p90_index = min(len(sorted_durations) - 1, round((len(sorted_durations) - 1) * 0.9)) if sorted_durations else 0
    return {
        "knowledge_base": knowledge_base,
        "generated_at": datetime.now(UTC).isoformat(),
        "method": "caption_only_sentence_like_units_v1",
        "thresholds": {
            "unit_gap_ms": MAX_UNIT_GAP_MS,
            "unit_duration_ms": MAX_UNIT_DURATION_MS,
            "too_short_ms": TOO_SHORT_MS,
            "max_source_duration_ms": MAX_SOURCE_DURATION_MS,
        },
        "evidence_count": evaluated + unavailable,
        "evaluated_count": evaluated,
        "unavailable_count": unavailable,
        "flag_counts": dict(sorted(flags.items())),
        "rates": {
            "starts_mid_sentence": _percent(flags["starts_mid_sentence"], evaluated),
            "ends_mid_sentence": _percent(flags["ends_mid_sentence"], evaluated),
            "too_short": _percent(flags["too_short"], evaluated),
            "needs_context": _percent(flags["needs_context"], evaluated),
        },
        "duration_ms": {
            "min": min(durations) if durations else None,
            "median": median(durations) if durations else None,
            "p90": sorted_durations[p90_index] if sorted_durations else None,
            "max": max(durations) if durations else None,
        },
        "flagged_samples": samples,
    }


def build_boundary_review_set(
    concepts: list[Concept], videos: list[Video], knowledge_base: str, sample_size: int = 24
) -> dict[str, Any]:
    """Build a deterministic, stratified review set from flagged evidence.

    The output contains no transcript text and no automatic decisions. It is an
    operator worksheet: a reviewer must choose ``keep``, ``merge``, ``split``,
    or ``defer`` after inspecting the cited interval and proposed context.
    Selection is stable for the same corpus and deliberately covers different
    flag types before filling the remaining slots by evidence ID.
    """
    if sample_size < 1:
        raise ValueError("sample_size must be at least 1")
    video_map = {video.id: video for video in videos}
    buckets: dict[str, list[dict[str, Any]]] = {key: [] for key in (
        "starts_mid_sentence", "ends_mid_sentence", "too_short", "needs_context"
    )}
    seen: set[str] = set()
    for concept in sorted(concepts, key=lambda item: item.id):
        for evidence in sorted(concept.evidence, key=lambda item: item.id):
            video = video_map.get(evidence.source.video_id)
            assessment = assess_boundary(video, evidence.source.segment_ids) if video else None
            if not assessment or not assessment.flags or evidence.id in seen:
                continue
            seen.add(evidence.id)
            item = {
                "id": evidence.id,
                "concept_id": concept.id,
                "video_id": evidence.source.video_id,
                "source_segment_ids": list(assessment.segment_ids),
                "source_start_ms": assessment.start_ms,
                "source_end_ms": assessment.end_ms,
                "source_url": youtube_url(evidence.source.video_id, assessment.start_ms),
                "proposed_start_ms": assessment.snapped_start_ms,
                "proposed_end_ms": assessment.snapped_end_ms,
                "flags": list(assessment.flags),
                "boundary_confidence": assessment.boundary_confidence,
                "review_action": None,
                "reviewer": None,
                "reviewed_at": None,
                "review_notes": "",
            }
            bucket = next(
                (flag for flag in ("starts_mid_sentence", "ends_mid_sentence", "too_short", "needs_context")
                 if flag in assessment.flags),
                "needs_context",
            )
            buckets[bucket].append(item)
    for items in buckets.values():
        items.sort(key=lambda item: (item["video_id"], item["source_start_ms"], item["id"]))
    keys = [key for key in buckets if buckets[key]]
    selected: list[dict[str, Any]] = []
    quota = max(1, sample_size // max(1, len(keys)))
    for key in keys:
        selected.extend(buckets[key][:quota])
    remaining = [item for key in keys for item in buckets[key] if item not in selected]
    remaining.sort(key=lambda item: (item["video_id"], item["source_start_ms"], item["id"]))
    selected.extend(remaining[: max(0, sample_size - len(selected))])
    selected = selected[:sample_size]
    return {
        "schema_version": 1,
        "knowledge_base": knowledge_base,
        "generated_at": datetime.now(UTC).isoformat(),
        "method": "deterministic_stratified_boundary_review_v1",
        "review_actions": ["keep", "merge", "split", "defer"],
        "sample_size": len(selected),
        "flagged_pool_size": sum(len(items) for items in buckets.values()),
        "items": selected,
    }


def render_boundary_review_set_markdown(review_set: dict[str, Any], title: str) -> str:
    """Render review instructions and metadata without transcript text."""
    lines = [
        f"# {title} boundary gold-set worksheet",
        "",
        f"Generated: `{review_set['generated_at']}`  ",
        f"Method: `{review_set['method']}`  ",
        f"Flagged pool: **{review_set['flagged_pool_size']}**; review sample: **{review_set['sample_size']}**",
        "",
        "This worksheet is intentionally undecided. Inspect each cited interval and its proposed complete-unit context, then record one action in the JSON file: `keep`, `merge`, `split`, or `defer`. Keep the cited segment IDs unchanged; a playback-context expansion is not new claim support.",
        "",
        "| Evidence | Video | Flags | Cited interval | Proposed interval | Review |",
        "|---|---|---|---:|---:|---|",
    ]
    for item in review_set["items"]:
        cited = f"{item['source_start_ms']}–{item['source_end_ms']}"
        proposed = f"{item['proposed_start_ms']}–{item['proposed_end_ms']}"
        lines.append(
            f"| `{item['id']}` | `{item['video_id']}` | {', '.join(item['flags'])} | {cited} | {proposed} | pending |"
        )
    lines.extend([
        "",
        "## Review contract",
        "",
        "- `keep`: the cited interval is already meaningful and complete.",
        "- `merge`: adjacent caption units should be included as playback context; preserve the original citation IDs.",
        "- `split`: the citation contains separate ideas; identify the split in reviewer notes and keep each claim supported by its own IDs.",
        "- `defer`: the interval needs audio/context or source inspection before publication.",
        "- A second boundary report should be generated only after decisions are recorded and validated; pending items are not a reduction result.",
        "",
    ])
    return "\n".join(lines)


def validate_boundary_review_set(review_set: dict[str, Any], videos: list[Video]) -> list[str]:
    """Validate reviewer edits without applying them to canonical evidence."""
    errors: list[str] = []
    allowed = set(review_set.get("review_actions", []))
    video_map = {video.id: video for video in videos}
    seen: set[str] = set()
    for index, item in enumerate(review_set.get("items", [])):
        label = f"items[{index}]"
        item_id = str(item.get("id", ""))
        if not item_id or item_id in seen:
            errors.append(f"{label}: duplicate or missing evidence id")
        seen.add(item_id)
        action = item.get("review_action")
        if action is not None and action not in allowed:
            errors.append(f"{label}: unsupported review action {action!r}")
        video = video_map.get(str(item.get("video_id", "")))
        if not video or not video.transcript:
            errors.append(f"{label}: normalized transcript is unavailable")
            continue
        segment_ids = item.get("source_segment_ids", [])
        known_ids = {segment.id for segment in video.transcript.segments}
        unknown = [segment_id for segment_id in segment_ids if segment_id not in known_ids]
        if unknown:
            errors.append(f"{label}: unknown source segment IDs: {', '.join(unknown)}")
        start_ms = int(item.get("proposed_start_ms", 0))
        end_ms = int(item.get("proposed_end_ms", 0))
        if start_ms < 0 or end_ms <= start_ms:
            errors.append(f"{label}: proposed bounds are not an increasing positive span")
        if end_ms - start_ms > MAX_SOURCE_DURATION_MS:
            errors.append(f"{label}: proposed span exceeds the 30-second limit")
        if video.duration_ms and end_ms > video.duration_ms:
            errors.append(f"{label}: proposed end exceeds source video duration")
    return errors


def render_boundary_report_markdown(report: dict, title: str) -> str:
    """Render a compact report without transcript text or private captions."""
    rates = report["rates"]
    duration = report["duration_ms"]
    lines = [
        f"# {title} moment-boundary report",
        "",
        f"Generated: `{report['generated_at']}`  ",
        f"Method: `{report['method']}`",
        "",
        "## Coverage",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Evidence records | {report['evidence_count']} |",
        f"| Evaluated with local captions | {report['evaluated_count']} |",
        f"| Missing local transcript | {report['unavailable_count']} |",
        f"| Starts mid-sentence | {rates['starts_mid_sentence']:.1%} |",
        f"| Ends mid-sentence | {rates['ends_mid_sentence']:.1%} |",
        f"| Too short (<4s) | {rates['too_short']:.1%} |",
        f"| Needs context/review | {rates['needs_context']:.1%} |",
        "",
        "## Duration distribution",
        "",
        "| Statistic | Milliseconds |",
        "|---|---:|",
        f"| Minimum | {duration['min'] or 'n/a'} |",
        f"| Median | {duration['median'] or 'n/a'} |",
        f"| 90th percentile | {duration['p90'] or 'n/a'} |",
        f"| Maximum | {duration['max'] or 'n/a'} |",
        "",
        "## Interpretation",
        "",
        "- This is a script-only baseline; it proposes snapped unit bounds but does not alter reviewed evidence.",
        "- Flagged moments should be reviewed for merge, context expansion, split, or defer actions.",
        "- Any future audio or semantic pass must preserve cited segment IDs and the 30-second maximum.",
        "",
    ]
    return "\n".join(lines)
