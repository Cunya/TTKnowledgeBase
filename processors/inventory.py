"""Build the private per-video eligibility and completion ledger."""

from __future__ import annotations

import re
import warnings
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .bucket_history import record_bucket_history
from .models import PublishCorpus
from .pipeline import candidate_citation_ids, load_videos
from .utils import read_json, read_yaml, write_json
from .workspace import KnowledgeBasePaths

YOUTUBE_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
def _normalized_url(value: object) -> str:
    return str(value or "").rstrip("/").removesuffix("/videos")


def _catalog_payloads(paths: KnowledgeBasePaths) -> list[tuple[Path, dict[str, Any]]]:
    files = [
        *paths.data("manifests").glob("discovered*.json"),
        *(paths.root / "app" / "src" / "data").glob("*.json"),
    ]
    payloads: list[tuple[Path, dict[str, Any]]] = []
    for path in files:
        try:
            payload = read_json(path)
        except (OSError, ValueError):
            continue
        if isinstance(payload, dict) and isinstance(payload.get("videos"), list):
            payloads.append((path, payload))
    return payloads


def load_inventory_catalog(paths: KnowledgeBasePaths) -> dict[str, dict[str, Any]]:
    """Return the best local discovery catalog per enabled source, deduplicated by ID."""
    config = read_yaml(paths.config / "sources.yaml") or {}
    sources = [source for source in config.get("sources", []) if source.get("enabled", True)]
    payloads = _catalog_payloads(paths)
    records: dict[str, dict[str, Any]] = {}
    for source in sources:
        source_id = str(source["id"])
        source_url = _normalized_url(source.get("url"))
        matches: list[tuple[Path, dict[str, Any], list[dict[str, Any]]]] = []
        for path, payload in payloads:
            payload_url = _normalized_url(payload.get("source_url") or payload.get("channel_url"))
            if str(payload.get("source_id") or "") != source_id and payload_url != source_url:
                continue
            valid = [
                item
                for item in payload["videos"]
                if isinstance(item, dict) and YOUTUBE_VIDEO_ID.fullmatch(str(item.get("id", "")))
            ]
            matches.append((path, payload, valid))
        if not matches:
            continue
        path, payload, videos = max(matches, key=lambda match: len(match[2]))
        for item in videos:
            video_id = str(item["id"])
            record = records.setdefault(
                video_id,
                {
                    "video_id": video_id,
                    "title": str(item.get("title") or video_id),
                    "url": str(item.get("url") or f"https://www.youtube.com/watch?v={video_id}"),
                    "view_count": int(item.get("view_count") or 0),
                    "source_ids": [],
                    "inventory_provenance": [],
                },
            )
            if source_id not in record["source_ids"]:
                record["source_ids"].append(source_id)
            record["view_count"] = max(record["view_count"], int(item.get("view_count") or 0))
            record["inventory_provenance"].append(
                {
                    "source_id": source_id,
                    "catalog": str(path.relative_to(paths.root)),
                    "discovered_at": payload.get("discovered_at") or payload.get("generated_at"),
                }
            )

    # Configuration is provenance, not the current run selection. It is only a fallback
    # for a valid historical ID absent from the currently retained catalogs.
    default_source = str(sources[0]["id"]) if sources else "unassigned"
    for item in config.get("videos", []):
        video_id = str(item.get("id") or "")
        if not YOUTUBE_VIDEO_ID.fullmatch(video_id):
            continue
        source_id = str(item.get("source_id") or default_source)
        record = records.setdefault(
            video_id,
            {
                "video_id": video_id,
                "title": str(item.get("title") or video_id),
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "view_count": 0,
                "source_ids": [source_id],
                "inventory_provenance": [{"source_id": source_id, "catalog": f"config/kbs/{paths.id}/sources.yaml", "discovered_at": None}],
            },
        )
        record["configured_batch_history"] = True
        if item.get("availability") == "members_only":
            record["configured_availability"] = "members_only"
    return records


def _parse_deadline(value: object) -> datetime | None:
    try:
        result = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    return result.replace(tzinfo=UTC) if result.tzinfo is None else result


def _adjudication_history(items: list[dict[str, Any]]) -> dict[str, Any]:
    attempts = [int(item.get("adjudication_attempts") or 0) for item in items]
    timestamps = [
        parsed
        for parsed in (_parse_deadline(item.get("last_adjudicated_at")) for item in items)
        if parsed is not None
    ]
    return {
        "pending": sum(item.get("decision") in {None, "pending"} for item in items),
        "deferred": sum(item.get("decision") == "deferred" for item in items),
        "attempts": max(attempts, default=0),
        "last_attempt_at": max(timestamps).isoformat() if timestamps else None,
    }


def _retry_classification(retry: dict[str, Any], now: datetime) -> tuple[str, str, str]:
    classification = str(retry.get("classification") or "")
    error_type = str(retry.get("error_type") or "")
    message = str(retry.get("message") or "").lower()
    attempts = int(retry.get("attempts") or 0)
    deadline = _parse_deadline(retry.get("next_retry_at"))
    if classification == "members_only" or "membersonly" in error_type.lower():
        return "members_only", "ineligible", "members-only video"
    if retry.get("blocked") is True and deadline and deadline > now:
        return "retryable_failure", "unknown", "route-wide access block is cooling down"
    if (error_type == "TranscriptsDisabled" or "subtitles are disabled" in message) and attempts >= 3:
        return "public", "no_usable_subtitles", "source subtitles repeatedly reported disabled"
    if ("unavailable" in error_type.lower() or "video unavailable" in message) and attempts >= 3:
        return "unavailable", "unknown", "video repeatedly reported unavailable"
    return "retryable_failure", "unknown", "acquisition failure remains retryable"


def build_inventory_ledger(
    paths: KnowledgeBasePaths,
    corpus: PublishCorpus | None = None,
    *,
    write: bool = True,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Derive one durable, private state record for every known source video."""
    now = now or datetime.now(UTC)
    records = load_inventory_catalog(paths)
    normalized = {video.id: video for video in load_videos(paths.data("normalized"))}
    derived_paths = {
        path.name.removesuffix(".candidates.json"): path
        for path in paths.data("derived").glob("*.candidates.json")
    }
    queue_path = paths.content / "annotations" / "review-queue.yaml"
    queue_items = (read_yaml(queue_path) or {}).get("items", []) if queue_path.exists() else []
    queue_by_video: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in queue_items:
        queue_by_video[str(item.get("video_id") or "")].append(item)
    retry_path = paths.data("manifests") / "ingest-retries.json"
    retries = (read_json(retry_path).get("items") or {}) if retry_path.exists() else {}

    if corpus is None:
        corpus_path = paths.root / "data" / "publish" / "kbs" / paths.id / "corpus.json"
        if corpus_path.exists():
            corpus = PublishCorpus.model_validate(read_json(corpus_path))
    public_ids: set[str] = set()
    moments: Counter[str] = Counter()
    incorporated: set[tuple[str, str, str]] = set()
    if corpus:
        public_ids = {video.id for video in corpus.videos}
        for concept in corpus.concepts:
            for evidence in concept.evidence:
                moments[evidence.source.video_id] += 1
                for segment_id in evidence.source.segment_ids:
                    incorporated.add((concept.id, evidence.source.video_id, segment_id))

    source_counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
    output_records: list[dict[str, Any]] = []
    for video_id, base in records.items():
        video = normalized.get(video_id)
        retry = retries.get(video_id) or {}
        availability = "public" if video else "unknown"
        caption_status = "selected_source_track" if video and video.transcript else "unknown"
        eligibility_reason = "usable normalized source-caption track exists" if video else "not audited yet"
        if base.get("configured_availability") == "members_only":
            availability, caption_status, eligibility_reason = "members_only", "ineligible", "members-only in source configuration"
        elif retry and not video:
            availability, caption_status, eligibility_reason = _retry_classification(retry, now)

        items = queue_by_video.get(video_id, [])
        decisions = Counter(str(item.get("decision") or "pending") for item in items)
        adjudication_history = _adjudication_history(items)
        accepted_unincorporated = 0
        for item in items:
            if item.get("decision") != "accepted":
                continue
            concept_id = str(item.get("canonical_concept_id") or "")
            segment_ids = candidate_citation_ids(item)
            if not any((concept_id, video_id, segment_id) in incorporated for segment_id in segment_ids):
                accepted_unincorporated += 1

        derived = video_id in derived_paths
        if availability in {"members_only", "unavailable"} or caption_status == "no_usable_subtitles":
            completion_state = "excluded"
            completion_reason = eligibility_reason
        elif not video:
            deadline = _parse_deadline(retry.get("next_retry_at"))
            if deadline and deadline > now:
                completion_state = "retry_wait"
                completion_reason = f"retry after {deadline.isoformat()}"
            else:
                completion_state = "needs_acquisition"
                completion_reason = "eligibility or transcript acquisition is due"
        elif not derived:
            completion_state = "needs_extraction"
            completion_reason = "normalized transcript exists but candidate artifact is missing"
        elif (
            decisions["pending"]
            or decisions["deferred"]
            or decisions["human_review"]
            or accepted_unincorporated
        ):
            completion_state = "needs_adjudication"
            completion_reason = "Codex semantic decisions or canonical incorporation remain"
        else:
            completion_state = "complete"
            completion_reason = "all extracted candidates have final incorporated decisions"

        record = {
            **base,
            "availability": availability,
            "caption_eligibility": caption_status,
            "selected_language": (video.transcript.language_code if video and video.transcript else None),
            "available_source_tracks": ([video.transcript.language_code] if video and video.transcript else []),
            "normalized": bool(video),
            "extracted": derived,
            "candidate_counts": {
                "total": len(items),
                "pending": decisions["pending"],
                "deferred": decisions["deferred"],
                "accepted": decisions["accepted"],
                "rejected": decisions["rejected"],
                "human_review": decisions["human_review"],
                "accepted_unincorporated": accepted_unincorporated,
            },
            "adjudication_history": adjudication_history,
            "published": video_id in public_ids,
            "public_moments": moments[video_id],
            "retry": ({key: retry.get(key) for key in ("attempts", "classification", "error_type", "blocked", "last_attempt_at", "next_retry_at") if retry.get(key) is not None} if retry else None),
            "completion_state": completion_state,
            "completion_reason": completion_reason,
            "human_review_required": False,
        }
        output_records.append(record)
        for source_id in base["source_ids"]:
            source_counts[source_id]["inventory"] += 1
            source_counts[source_id][completion_state] += 1

    output_records.sort(key=lambda item: (item["source_ids"][0], -item["view_count"], item["video_id"]))
    states = Counter(item["completion_state"] for item in output_records)
    availability_counts = Counter(item["availability"] for item in output_records)
    caption_counts = Counter(item["caption_eligibility"] for item in output_records)
    candidate_totals: Counter[str] = Counter()
    for item in output_records:
        candidate_totals.update(item["candidate_counts"])
    eligible_total = len(output_records) - states["excluded"]
    automation_triaged = states["complete"]
    ledger = {
        "schema_version": 2,
        "knowledge_base": paths.id,
        "generated_at": now.isoformat(),
        "summary": {
            "inventory": len(output_records),
            "published": sum(item["published"] for item in output_records),
            "eligible_total": eligible_total,
            "eligible_complete": states["complete"],
            "fully_processed_percent": round(states["complete"] / eligible_total * 100, 1) if eligible_total else 100.0,
            "automation_triaged": automation_triaged,
            "automation_triaged_percent": round(automation_triaged / eligible_total * 100, 1) if eligible_total else 100.0,
            "automated_work_remaining": states["needs_acquisition"] + states["needs_extraction"] + states["needs_adjudication"],
            "human_review_videos": 0,
            "retry_wait": states["retry_wait"],
            "excluded": states["excluded"],
            "states": dict(states),
            "availability": dict(availability_counts),
            "captions": dict(caption_counts),
            "candidates": dict(candidate_totals),
            "sources": {source_id: dict(counts) for source_id, counts in source_counts.items()},
        },
        "videos": output_records,
    }
    if write:
        write_json(paths.data("manifests") / "inventory-ledger.json", ledger)
        try:
            record_bucket_history(paths.data("manifests"), ledger, now=now)
        except (OSError, ValueError, TypeError) as error:
            warnings.warn(f"Could not record private bucket history: {error}", RuntimeWarning, stacklevel=2)
    return ledger


def select_source_balanced(
    items: list[dict[str, Any]], limit: int
) -> list[dict[str, Any]]:
    """Select a deterministic round-robin batch across primary source IDs."""
    if limit <= 0:
        return []
    buckets: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        source_ids = item.get("source_ids") or ["unassigned"]
        buckets[str(source_ids[0])].append(item)
    for bucket in buckets.values():
        bucket.sort(key=_work_priority)
    source_ids = sorted(buckets)
    selected: list[dict[str, Any]] = []
    indexes = {source_id: 0 for source_id in source_ids}
    while len(selected) < limit:
        added = False
        for source_id in source_ids:
            index = indexes[source_id]
            if index >= len(buckets[source_id]):
                continue
            selected.append(buckets[source_id][index])
            indexes[source_id] += 1
            added = True
            if len(selected) >= limit:
                break
        if not added:
            break
    return selected


def _work_priority(item: dict[str, Any]) -> tuple[int, int, str, int, str]:
    """Prioritize untouched/older adjudication work before repeated retries."""
    history = item.get("adjudication_history") or {}
    pending = int(history.get("pending") or 0)
    attempts = int(history.get("attempts") or 0)
    last_attempt = str(history.get("last_attempt_at") or "")
    return (
        0 if pending else 1,
        attempts,
        last_attempt,
        -int(item.get("view_count") or 0),
        str(item.get("video_id") or ""),
    )


def select_ledger_worksets(
    ledger: dict[str, Any], acquisition_limit: int, adjudication_limit: int = 50,
    extraction_limit: int = 50,
) -> dict[str, list[dict[str, str]]]:
    """Select deterministic cache-first batches that rotate fairly across sources."""
    videos = ledger.get("videos", [])
    extraction_items = select_source_balanced(
        [item for item in videos if item.get("completion_state") == "needs_extraction"],
        extraction_limit,
    )
    extraction = [
        {
            "id": item["video_id"],
            "source_id": str((item.get("source_ids") or ["unassigned"])[0]),
            "reason": "normalized transcript is missing candidate extraction",
        }
        for item in extraction_items
    ]
    adjudication_items = select_source_balanced(
        [item for item in videos if item.get("completion_state") == "needs_adjudication"],
        adjudication_limit,
    )
    adjudication = [
        {
            "id": item["video_id"],
            "source_id": str((item.get("source_ids") or ["unassigned"])[0]),
            "reason": "extracted candidates still have retryable decisions",
        }
        for item in adjudication_items
    ]
    acquisition_items = select_source_balanced(
        [item for item in videos if item.get("completion_state") == "needs_acquisition"],
        acquisition_limit,
    )
    acquisition = [
        {
            "id": item["video_id"],
            "source_id": str((item.get("source_ids") or ["unassigned"])[0]),
            "reason": item.get("completion_reason", "transcript acquisition is due"),
        }
        for item in acquisition_items
    ]
    return {"extraction": extraction, "adjudication": adjudication, "acquisition": acquisition}
