from __future__ import annotations

from collections import Counter
from pathlib import Path

import networkx as nx
from rapidfuzz.fuzz import token_set_ratio
from ruamel.yaml import YAML

from .codex_engine import extract_with_codex
from .models import Concept, ExtractionResponse, KnowledgeNavigation, PublishCorpus, Video
from .utils import read_json, read_yaml, sha256_json, write_json, youtube_url

MAX_SPOKEN_SOURCE_MS = 30_000
MAX_CITED_SEGMENT_GAP_MS = 20_000
MOJIBAKE_MARKERS = ("\ufffd", "Â", "â€", "â†", "ðŸ")

roundtrip_yaml = YAML()
roundtrip_yaml.preserve_quotes = True
roundtrip_yaml.indent(mapping=2, sequence=4, offset=2)
roundtrip_yaml.width = 4096


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
    model_override: str | None = None,
) -> Path:
    if not video.transcript:
        raise ValueError(f"Video {video.id} has no transcript")
    response, provenance = extract_with_codex(
        video.transcript.segments,
        taxonomy,
        known_concepts,
        processors_config,
        audit_dir,
        model_override=model_override,
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
    existing_items: dict[tuple[str, str], dict] = {}
    if queue_path.exists():
        existing_queue = read_yaml(queue_path) or {}
        existing_items = {
            (item.get("video_id", ""), item.get("candidate", {}).get("candidate_id", "")): item
            for item in existing_queue.get("items", [])
            if item.get("video_id") and item.get("candidate", {}).get("candidate_id")
        }
    for path in sorted(derived_dir.glob("*.candidates.json")):
        payload = read_json(path)
        response = ExtractionResponse.model_validate(payload["response"])
        for concept in response.concepts:
            candidate_payload = concept.model_dump(mode="json")
            candidate_hash = sha256_json(candidate_payload).removeprefix("sha256:")
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
            item = {
                "video_id": payload["video_id"],
                "candidate": candidate_payload,
                "candidate_hash": candidate_hash,
                "decision": "accepted" if approved else "pending",
                "canonical_concept_id": approved.id if approved else None,
                "review_notes": "",
            }
            existing = existing_items.get((payload["video_id"], concept.candidate_id))
            if existing:
                existing_hash = existing.get("candidate_hash")
                if isinstance(existing_hash, dict):
                    existing_hash = existing_hash.get("sha256")
                if isinstance(existing_hash, str):
                    existing_hash = existing_hash.removeprefix("sha256:")
                if not existing_hash:
                    existing_hash = sha256_json(existing.get("candidate", {})).removeprefix(
                        "sha256:"
                    )
                if existing_hash == candidate_hash:
                    item["candidate"] = existing.get("candidate", candidate_payload)
                    item["candidate_hash"] = existing.get("candidate_hash", candidate_hash)
                    item.update(
                        decision=existing.get("decision", item["decision"]),
                        canonical_concept_id=existing.get(
                            "canonical_concept_id", item["canonical_concept_id"]
                        ),
                        review_notes=existing.get("review_notes", ""),
                    )
                else:
                    item["review_notes"] = "Candidate content changed; previous decision requires review."
            queue.append(item)
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


def validate_corpus(
    concepts: list[Concept], videos: list[Video], *, require_transcript_segments: bool = True
) -> list[str]:
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
            if require_transcript_segments:
                missing = [
                    segment_id for segment_id in source.segment_ids if segment_id not in segment_map
                ]
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
                if (
                    visual.selection_method == "manual_review"
                    and evidence.visual_status != "verified_visual_demo"
                ):
                    errors.append(
                        f"{concept.id}/{evidence.id}: manually reviewed visual is not verified"
                    )
                if (
                    visual.selection_method == "nearby_visual_inference"
                    and evidence.visual_status == "verified_visual_demo"
                ):
                    errors.append(
                        f"{concept.id}/{evidence.id}: inferred visual cannot be verified"
                    )
            elif evidence.visual_status == "verified_visual_demo":
                errors.append(
                    f"{concept.id}/{evidence.id}: verified visual has no visual source"
                )
    return errors


def validate_published_corpus(corpus: PublishCorpus) -> list[str]:
    """Validate the sanitized artifact without requiring private transcripts."""
    errors = validate_corpus(
        corpus.concepts, corpus.videos, require_transcript_segments=False
    )
    if corpus.navigation:
        errors.extend(validate_navigation(corpus.navigation, corpus.concepts))
    errors.extend(validate_text_encoding(corpus.model_dump(mode="json")))
    return errors


def validate_text_encoding(value, path: str = "corpus") -> list[str]:
    """Find common UTF-8/Windows-1252 mojibake in public strings."""
    errors: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            errors.extend(validate_text_encoding(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(validate_text_encoding(item, f"{path}[{index}]"))
    elif isinstance(value, str) and any(marker in value for marker in MOJIBAKE_MARKERS):
        errors.append(f"{path}: possible encoding corruption")
    return errors


def build_quality_report(corpus: PublishCorpus, queue_data: dict | None = None) -> dict:
    """Return editorial quality metrics without treating warnings as validity errors."""
    evidence = [item for concept in corpus.concepts for item in concept.evidence]
    source_counts = {
        concept.id: len({item.source.video_id for item in concept.evidence})
        for concept in corpus.concepts
    }
    excerpt_counts = Counter(item.excerpt for item in evidence)
    visual_methods = Counter(
        item.visual_source.selection_method
        for item in evidence
        if item.visual_source is not None
    )
    related_ids = {
        concept_id
        for concept in corpus.concepts
        for concept_id in (
            [concept.id, *(relation.target_concept_id for relation in concept.relations)]
            if concept.relations
            else []
        )
    }
    pending = [
        item for item in (queue_data or {}).get("items", []) if item.get("decision") == "pending"
    ]
    return {
        "concept_count": len(corpus.concepts),
        "published_video_count": len(corpus.videos),
        "evidence_count": len(evidence),
        "distinct_excerpt_count": len(excerpt_counts),
        "moments_with_repeated_excerpt": sum(
            count for count in excerpt_counts.values() if count > 1
        ),
        "concepts_without_relations": sorted(
            concept.id for concept in corpus.concepts if concept.id not in related_ids
        ),
        "single_source_concepts": sorted(
            concept_id for concept_id, count in source_counts.items() if count == 1
        ),
        "evidence_outliers": [
            {"concept_id": concept.id, "label": concept.label, "evidence_count": len(concept.evidence)}
            for concept in sorted(corpus.concepts, key=lambda item: len(item.evidence), reverse=True)
            if len(concept.evidence) > 30
        ],
        "visual_sources": dict(sorted(visual_methods.items())),
        "verified_visual_count": sum(
            item.visual_status == "verified_visual_demo" for item in evidence
        ),
        "pending_candidate_count": len(pending),
        "pending_by_video": dict(sorted(Counter(item["video_id"] for item in pending).items())),
        "public_corpus_bytes": None,
    }


def render_quality_report_markdown(report: dict, title: str) -> str:
    """Render a compact, reviewable Markdown companion to the JSON report."""
    rows = [
        ("Concepts", report["concept_count"]),
        ("Published videos", report["published_video_count"]),
        ("Evidence moments", report["evidence_count"]),
        ("Distinct excerpts", report["distinct_excerpt_count"]),
        ("Isolated concepts", len(report["concepts_without_relations"])),
        ("Single-source concepts", len(report["single_source_concepts"])),
        ("Verified visuals", report["verified_visual_count"]),
        ("Pending candidates", report["pending_candidate_count"]),
        ("Public corpus bytes", report["public_corpus_bytes"]),
    ]
    lines = [f"# {title} quality report", "", "| Signal | Count |", "|---|---:|"]
    lines.extend(f"| {label} | {value} |" for label, value in rows)
    lines.extend(["", "## Evidence outliers", ""])
    if report["evidence_outliers"]:
        lines.extend(
            f"- {item['label']}: {item['evidence_count']} moments"
            for item in report["evidence_outliers"]
        )
    else:
        lines.append("- None")
    lines.extend(["", "## Remaining quality work", ""])
    lines.append(
        f"- {report['visual_sources'].get('nearby_visual_inference', 0)} proposed visual clips still require manual review."
    )
    lines.append(
        f"- {len(report['single_source_concepts'])} concepts still have evidence from only one source video."
    )
    lines.append(
        f"- {report['moments_with_repeated_excerpt']} moments share excerpt text with another moment."
    )
    return "\n".join(lines) + "\n"


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
