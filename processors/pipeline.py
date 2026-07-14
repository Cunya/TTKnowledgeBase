from __future__ import annotations

from pathlib import Path

import networkx as nx
from rapidfuzz.fuzz import token_set_ratio
from ruamel.yaml import YAML

from .codex_engine import extract_with_codex
from .models import Concept, ExtractionResponse, KnowledgeNavigation, PublishCorpus, Video
from .utils import read_json, read_yaml, sha256_json, write_json, youtube_url

MAX_SPOKEN_SOURCE_MS = 30_000
MAX_CITED_SEGMENT_GAP_MS = 20_000

roundtrip_yaml = YAML()
roundtrip_yaml.preserve_quotes = True
roundtrip_yaml.indent(mapping=2, sequence=4, offset=2)


def load_videos(directory: Path) -> list[Video]:
    return [Video.model_validate(read_json(path)) for path in sorted(directory.glob("*.json"))]


def load_reviewed_concepts(directory: Path) -> list[Concept]:
    concepts: list[Concept] = []
    for path in sorted(directory.glob("*.yaml")):
        data = read_yaml(path)
        if data:
            concepts.append(Concept.model_validate(data))
    return concepts


def extract_video(
    video: Video,
    taxonomy: dict,
    known_concepts: list[dict],
    processors_config: Path,
    output_dir: Path,
    audit_dir: Path,
) -> Path:
    if not video.transcript:
        raise ValueError(f"Video {video.id} has no transcript")
    response, provenance = extract_with_codex(
        video.transcript.segments,
        taxonomy,
        known_concepts,
        processors_config,
        audit_dir,
    )
    payload = {
        "video_id": video.id,
        "response": response.model_dump(mode="json"),
        "provenance": provenance,
    }
    path = output_dir / f"{video.id}.candidates.json"
    write_json(path, payload)
    return path


def build_review_queue(
    derived_dir: Path, queue_path: Path, reviewed_concepts: list[Concept] | None = None
) -> int:
    queue: list[dict] = []
    reviewed_concepts = reviewed_concepts or []
    for path in sorted(derived_dir.glob("*.candidates.json")):
        payload = read_json(path)
        response = ExtractionResponse.model_validate(payload["response"])
        for concept in response.concepts:
            candidate_segments = {
                segment_id
                for evidence in concept.evidence
                for segment_id in evidence.segment_ids
            }
            approved = next(
                (
                    reviewed
                    for reviewed in reviewed_concepts
                    if max(
                        token_set_ratio(concept.canonical_label, label)
                        for label in [reviewed.label, *reviewed.aliases]
                    )
                    >= 60
                    and any(
                        evidence.source.video_id == payload["video_id"]
                        and candidate_segments.intersection(evidence.source.segment_ids)
                        for evidence in reviewed.evidence
                    )
                ),
                None,
            )
            queue.append(
                {
                    "video_id": payload["video_id"],
                    "candidate": concept.model_dump(mode="json"),
                    "decision": "accepted" if approved else "pending",
                    "canonical_concept_id": approved.id if approved else None,
                    "review_notes": "",
                }
            )
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    with queue_path.open("w", encoding="utf-8") as handle:
        roundtrip_yaml.dump({"items": queue}, handle)
    return len(queue)


def validate_graph(concepts: list[Concept]) -> list[str]:
    errors: list[str] = []
    known = {concept.id for concept in concepts}
    graph = nx.DiGraph()
    graph.add_nodes_from(known)
    for concept in concepts:
        for relation in concept.relations:
            if relation.target_concept_id not in known:
                errors.append(f"{concept.id}: unknown relation target {relation.target_concept_id}")
            if relation.relation_type == "prerequisite_of":
                graph.add_edge(concept.id, relation.target_concept_id)
    try:
        cycle = nx.find_cycle(graph)
        if cycle:
            errors.append(f"prerequisite cycle: {cycle}")
    except nx.NetworkXNoCycle:
        pass
    return errors


def validate_review_queue(queue_data: dict, concepts: list[Concept]) -> list[str]:
    """Ensure accepted queue items are represented by their exact cited evidence."""
    errors: list[str] = []
    concept_map = {concept.id: concept for concept in concepts}
    for index, item in enumerate(queue_data.get("items", []), start=1):
        if item.get("decision") != "accepted":
            continue
        canonical_id = item.get("canonical_concept_id")
        canonical = concept_map.get(canonical_id)
        if not canonical:
            errors.append(f"review-queue/{index}: accepted item has unknown canonical concept")
            continue
        candidate_segments = {
            segment_id
            for evidence in item.get("candidate", {}).get("evidence", [])
            for segment_id in evidence.get("segment_ids", [])
        }
        canonical_segments = {
            segment_id
            for evidence in canonical.evidence
            if evidence.source.video_id == item.get("video_id")
            for segment_id in evidence.source.segment_ids
        }
        if not candidate_segments.intersection(canonical_segments):
            errors.append(
                f"review-queue/{index}: accepted item has no cited segment in {canonical_id}"
            )
    return errors


def validate_navigation(
    navigation: KnowledgeNavigation, concepts: list[Concept]
) -> list[str]:
    errors: list[str] = []
    known = {concept.id for concept in concepts}
    referenced: set[str] = set()

    def check_nodes(nodes) -> None:
        for node in nodes:
            for concept_id in node.concept_ids:
                if concept_id not in known:
                    errors.append(f"navigation/{node.id}: unknown concept {concept_id}")
                referenced.add(concept_id)
            check_nodes(node.children)

    check_nodes(navigation.sections)
    for concept_id in sorted(known - referenced):
        errors.append(f"navigation: approved concept is not placed: {concept_id}")
    return errors


def validate_corpus(concepts: list[Concept], videos: list[Video]) -> list[str]:
    errors = validate_graph(concepts)
    video_map = {video.id: video for video in videos}
    segment_map = {
        segment.id: (video.id, segment)
        for video in videos
        if video.transcript
        for segment in video.transcript.segments
    }
    slugs: set[str] = set()
    ids: set[str] = set()
    for concept in concepts:
        if concept.id in ids:
            errors.append(f"duplicate concept id: {concept.id}")
        ids.add(concept.id)
        if concept.slug in slugs:
            errors.append(f"duplicate concept slug: {concept.slug}")
        slugs.add(concept.slug)
        for evidence in concept.evidence:
            source = evidence.source
            video = video_map.get(source.video_id)
            if not video:
                errors.append(f"{concept.id}/{evidence.id}: unknown video {source.video_id}")
                continue
            if video.duration_ms and source.end_ms > video.duration_ms:
                errors.append(f"{concept.id}/{evidence.id}: source ends after video duration")
            if (
                evidence.spoken_context_end_ms
                and video.duration_ms
                and evidence.spoken_context_end_ms > video.duration_ms
            ):
                errors.append(f"{concept.id}/{evidence.id}: spoken context ends after video duration")
            missing = [segment_id for segment_id in source.segment_ids if segment_id not in segment_map]
            if missing:
                errors.append(f"{concept.id}/{evidence.id}: missing segments {missing}")
            mismatched = [
                segment_id
                for segment_id in source.segment_ids
                if segment_id in segment_map and segment_map[segment_id][0] != source.video_id
            ]
            if mismatched:
                errors.append(
                    f"{concept.id}/{evidence.id}: segments belong to another video {mismatched}"
                )
            if source.end_ms - source.start_ms > MAX_SPOKEN_SOURCE_MS:
                errors.append(
                    f"{concept.id}/{evidence.id}: spoken source exceeds "
                    f"{MAX_SPOKEN_SOURCE_MS // 1000} seconds"
                )
            cited_segments = sorted(
                (segment_map[segment_id][1] for segment_id in source.segment_ids if segment_id in segment_map),
                key=lambda segment: segment.start_ms,
            )
            for previous, current in zip(cited_segments, cited_segments[1:], strict=False):
                gap_ms = current.start_ms - previous.end_ms
                if gap_ms > MAX_CITED_SEGMENT_GAP_MS:
                    errors.append(
                        f"{concept.id}/{evidence.id}: cited segments have a "
                        f"{gap_ms / 1000:g}-second gap"
                    )
            if source.url != youtube_url(source.video_id, source.start_ms):
                errors.append(f"{concept.id}/{evidence.id}: noncanonical source URL")
            visual = evidence.visual_source
            if visual:
                visual_video = video_map.get(visual.video_id)
                if not visual_video:
                    errors.append(
                        f"{concept.id}/{evidence.id}: unknown visual video {visual.video_id}"
                    )
                elif visual_video.duration_ms and visual.end_ms > visual_video.duration_ms:
                    errors.append(
                        f"{concept.id}/{evidence.id}: visual source ends after video duration"
                    )
                if visual.url != youtube_url(visual.video_id, visual.start_ms):
                    errors.append(
                        f"{concept.id}/{evidence.id}: noncanonical visual source URL"
                    )
    return errors


def sanitized_video(video: Video) -> Video:
    return video.model_copy(
        update={"transcript": None, "channel_name": video.channel_name.strip()}
    )


def publish(
    concept_dir: Path,
    video_dir: Path,
    output_dir: Path,
    knowledge_base: dict[str, str],
    navigation: dict | None = None,
    include_demo: bool = False,
) -> PublishCorpus:
    videos = load_videos(video_dir)
    excluded_video_ids = {
        video.id for video in videos if video.availability == "demo_fixture" and not include_demo
    }
    concepts = []
    for concept in load_reviewed_concepts(concept_dir):
        if concept.review_status != "approved":
            continue
        public_evidence = [
            evidence
            for evidence in concept.evidence
            if evidence.source.video_id not in excluded_video_ids
        ]
        if public_evidence:
            public_relations = []
            for relation in concept.relations:
                public_sources = [
                    source
                    for source in relation.sources
                    if source.video_id not in excluded_video_ids
                ]
                if public_sources:
                    public_relations.append(
                        relation.model_copy(update={"sources": public_sources})
                    )
            concepts.append(
                concept.model_copy(
                    update={"evidence": public_evidence, "relations": public_relations}
                )
            )
    errors = validate_corpus(concepts, videos)
    parsed_navigation = KnowledgeNavigation.model_validate(navigation) if navigation else None
    if parsed_navigation:
        errors.extend(validate_navigation(parsed_navigation, concepts))
    if errors:
        raise ValueError("Publish validation failed:\n- " + "\n- ".join(errors))
    used_video_ids = {
        evidence.source.video_id for concept in concepts for evidence in concept.evidence
    }
    public_videos = [sanitized_video(video) for video in videos if video.id in used_video_ids]
    corpus = PublishCorpus(
        knowledge_base=knowledge_base,
        concepts=concepts,
        videos=public_videos,
        navigation=parsed_navigation,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "corpus.json", corpus)
    write_json(
        output_dir / "manifest.json",
        {
            "corpus_hash": sha256_json(corpus.model_dump(mode="json")),
            "concept_count": len(concepts),
            "video_count": len(public_videos),
        },
    )
    return corpus
