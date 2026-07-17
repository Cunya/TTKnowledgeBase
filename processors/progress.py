"""Build deterministic operator progress snapshots from local artifacts."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime

from .models import PublishCorpus
from .pipeline import load_videos
from .utils import read_json, read_yaml, write_json
from .workspace import KnowledgeBasePaths


def _source_id_for_video(video_config: dict, default_source_id: str) -> str:
    return str(video_config.get("source_id") or default_source_id)


def _discovery_counts(paths: KnowledgeBasePaths, sources: list[dict]) -> dict[str, int]:
    """Read source discovery manifests without making a network request.

    The processor's discovery command writes a manifest with ``source_url``. The
    fallback scan also accepts browser-safe catalog JSON carrying ``source_id`` or
    ``source_url`` so an existing catalog can seed the first generated snapshot.
    """
    counts: dict[str, int] = {}
    manifests = list(paths.data("manifests").glob("discovered*.json"))
    catalog_files = list((paths.root / "app" / "src" / "data").glob("*.json"))
    for source in sources:
        source_id = str(source["id"])
        source_url = str(source.get("url", "")).rstrip("/")
        for path in [*manifests, *catalog_files]:
            try:
                payload = read_json(path)
            except (OSError, ValueError):
                continue
            payload_url = str(payload.get("source_url") or payload.get("channel_url", "")).rstrip("/")
            payload_source = str(payload.get("source_id", ""))
            if payload_source != source_id and payload_url != source_url:
                continue
            videos = payload.get("videos")
            if isinstance(videos, list):
                counts[source_id] = max(counts.get(source_id, 0), len(videos))
    return counts


def write_recent_snapshot(paths: KnowledgeBasePaths) -> None:
    """Refresh the local-only Recent source inventory from normalized videos.

    This is deliberately deterministic and does not call an LLM. Keeping it in
    the processor layer means ingestion and publication cannot silently leave
    the operator's Recent view stale when extraction is deferred.
    """
    videos = load_videos(paths.data("normalized"))
    output = paths.root / "app" / "src" / "data" / "generated" / f"{paths.id}-recent.json"
    write_json(
        output,
        {
            "knowledge_base": paths.id,
            "generated_at": datetime.now(UTC).isoformat(),
            "videos": [video.model_dump(mode="json") for video in videos],
        },
    )


def build_progress_report(paths: KnowledgeBasePaths, corpus: PublishCorpus) -> dict:
    """Return a count-only snapshot for local operator pages.

    All values are derived from source configuration, normalized files, candidate
    files, review decisions, and the sanitized corpus. No LLM is invoked and no
    narrative/editorial status is generated here.
    """
    source_config = read_yaml(paths.config / "sources.yaml") or {}
    sources = source_config.get("sources", [])
    configured_videos = source_config.get("videos", [])
    default_source = str(sources[0]["id"]) if sources else "unassigned"
    source_names = {
        str(source["id"]): str(source.get("observed_channel_name") or source["id"])
        for source in sources
    }
    source_handles = {
        str(source["id"]): str(source.get("url", ""))
        for source in sources
    }
    source_discovered = _discovery_counts(paths, sources)

    normalized_videos = load_videos(paths.data("normalized"))
    normalized_ids = {video.id for video in normalized_videos}
    derived_ids = {
        path.name.removesuffix(".candidates.json")
        for path in paths.data("derived").glob("*.candidates.json")
    }
    queue_path = paths.content / "annotations" / "review-queue.yaml"
    queue_items = (read_yaml(queue_path) or {}).get("items", []) if queue_path.exists() else []
    queue_by_video: defaultdict[str, list[dict]] = defaultdict(list)
    for item in queue_items:
        queue_by_video[str(item.get("video_id", ""))].append(item)
    public_ids = {video.id for video in corpus.videos}
    evidence_by_video: Counter[str] = Counter()
    concepts_by_video: defaultdict[str, set[str]] = defaultdict(set)
    proposed_visual_by_video: Counter[str] = Counter()
    verified_visual_by_video: Counter[str] = Counter()
    for concept in corpus.concepts:
        for evidence in concept.evidence:
            video_id = evidence.source.video_id
            evidence_by_video[video_id] += 1
            concepts_by_video[video_id].add(concept.id)
            if evidence.visual_source:
                if evidence.visual_source.selection_method == "nearby_visual_inference":
                    proposed_visual_by_video[video_id] += 1
                if evidence.visual_status == "verified_visual_demo":
                    verified_visual_by_video[video_id] += 1

    records: list[dict] = []
    inaccessible_ids: list[str] = []
    for source in sources:
        source_id = str(source["id"])
        entries = [
            item for item in configured_videos if _source_id_for_video(item, default_source) == source_id
        ]
        configured_ids = {str(item["id"]) for item in entries}
        eligible_ids = {
            str(item["id"])
            for item in entries
            if item.get("selected", True) and item.get("availability") != "members_only"
        }
        inaccessible = {
            str(item["id"]) for item in entries if item.get("availability") == "members_only"
        }
        inaccessible_ids.extend(sorted(inaccessible))
        source_queue = [item for video_id in configured_ids for item in queue_by_video[video_id]]
        accepted = sum(item.get("decision") == "accepted" for item in source_queue)
        deferred = sum(item.get("decision") == "deferred" for item in source_queue)
        rejected = sum(item.get("decision") == "rejected" for item in source_queue)
        pending = sum(item.get("decision") == "pending" for item in source_queue)
        extracted_ids = eligible_ids & derived_ids
        reviewed_ids = {
            video_id
            for video_id in extracted_ids
            if queue_by_video[video_id] and all(
                item.get("decision") in {"accepted", "rejected"}
                for item in queue_by_video[video_id]
            )
        }
        deferred_video_ids = {
            video_id
            for video_id in configured_ids
            if any(item.get("decision") == "deferred" for item in queue_by_video[video_id])
        }
        published_ids = eligible_ids & public_ids
        record = {
            "id": source_id,
            "name": source_names.get(source_id, source_id),
            "url": source_handles.get(source_id, ""),
            "discovered": source_discovered.get(source_id, max(len(configured_ids), len(eligible_ids))),
            "configured": len(configured_ids),
            "eligible": len(eligible_ids),
            "ingested": len(eligible_ids & normalized_ids),
            "extracted": len(extracted_ids),
            "reviewed": len(reviewed_ids),
            "published": len(published_ids),
            "accepted": accepted,
            "deferred": deferred,
            "rejected": rejected,
            "pending": pending,
            "evidence": sum(evidence_by_video[video_id] for video_id in published_ids),
            "concepts": len({concept_id for video_id in published_ids for concept_id in concepts_by_video[video_id]}),
            "visual_proposed": sum(proposed_visual_by_video[video_id] for video_id in published_ids),
            "visual_verified": sum(verified_visual_by_video[video_id] for video_id in published_ids),
            "published_with_review_backlog": len(published_ids & deferred_video_ids),
            "members_only": len(inaccessible),
            "unselected": max(0, source_discovered.get(source_id, len(configured_ids)) - len(configured_ids)),
        }
        records.append(record)

    queue_counts = Counter(str(item.get("decision", "pending")) for item in queue_items)
    source_concept_sets = {
        record["id"]: set() for record in records
    }
    for concept in corpus.concepts:
        source_ids = {
            next(
                (
                    _source_id_for_video(item, default_source)
                    for item in configured_videos
                    if str(item.get("id")) == evidence.source.video_id
                ),
                default_source,
            )
            for evidence in concept.evidence
        }
        for source_id in source_ids:
            source_concept_sets.setdefault(source_id, set()).add(concept.id)
    totals = {
        "discovered": sum(record["discovered"] for record in records),
        "configured": sum(record["configured"] for record in records),
        "eligible": sum(record["eligible"] for record in records),
        "ingested": sum(record["ingested"] for record in records),
        "extracted": sum(record["extracted"] for record in records),
        "concepts": len(corpus.concepts),
        "published_videos": len(corpus.videos),
        "evidence": sum(len(concept.evidence) for concept in corpus.concepts),
        "visual_proposed": sum(record["visual_proposed"] for record in records),
        "visual_verified": sum(record["visual_verified"] for record in records),
        "accepted": queue_counts["accepted"],
        "deferred": queue_counts["deferred"],
        "rejected": queue_counts["rejected"],
        "pending": queue_counts["pending"],
        "reviewed_videos": sum(record["reviewed"] for record in records),
        "published_with_review_backlog": sum(record["published_with_review_backlog"] for record in records),
        "single_source_concepts": sum(
            len(concept.evidence) > 0
            and len({evidence.source.video_id for evidence in concept.evidence}) == 1
            for concept in corpus.concepts
        ),
    }
    for record in records:
        record["concepts"] = len(source_concept_sets.get(record["id"], set()))
    return {
        "schema_version": 1,
        "knowledge_base": paths.id,
        "generated_at": corpus.generated_at.isoformat(),
        "totals": totals,
        "sources": records,
        "members_only_ids": sorted(inaccessible_ids),
    }
