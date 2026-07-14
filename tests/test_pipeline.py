from pathlib import Path

from ruamel.yaml import YAML

from processors.demo import write_demo_video
from processors.models import Concept, KnowledgeNavigation
from processors.pipeline import (
    build_review_queue,
    load_reviewed_concepts,
    publish,
    validate_corpus,
    validate_navigation,
    validate_review_queue,
)
from processors.utils import read_yaml, write_json

ROOT = Path(__file__).resolve().parents[1]


def test_review_queue_rebuild_preserves_editorial_decisions(tmp_path: Path) -> None:
    derived = tmp_path / "derived"
    queue_path = tmp_path / "review-queue.yaml"
    candidate = {
        "candidate_id": "candidate-1",
        "canonical_label": "Unreviewed test idea",
        "aliases": [],
        "definition": "A source-grounded test candidate.",
        "concept_type": "technique",
        "facets": [],
        "difficulty": None,
        "resolution": "new",
        "matched_concept_id": None,
        "confidence": 0.8,
        "evidence": [{
            "evidence_type": "explanation",
            "segment_ids": ["video-1:00001"],
            "reason": "The segment explains the idea.",
            "confidence": 0.8,
            "visual_status": "not_visual",
        }],
        "relations": [],
        "uncertainty": [],
    }
    write_json(
        derived / "video-1.candidates.json",
        {"video_id": "video-1", "response": {"concepts": [candidate], "batch_notes": []}},
    )
    yaml = YAML()
    with queue_path.open("w", encoding="utf-8") as handle:
        yaml.dump({"items": [{
            "video_id": "video-1",
            "candidate": candidate,
            "decision": "rejected",
            "canonical_concept_id": None,
            "review_notes": "Duplicate wording.",
        }]}, handle)

    build_review_queue(derived, queue_path)

    rebuilt = read_yaml(queue_path)["items"][0]
    assert rebuilt["decision"] == "rejected"
    assert rebuilt["review_notes"] == "Duplicate wording."


def demo_concepts() -> list[Concept]:
    concepts = load_reviewed_concepts(
        ROOT / "content" / "kbs" / "table-tennis" / "concepts"
    )
    selected = [
        concept
        for concept in concepts
        if any(item.source.video_id == "demoTT00001" for item in concept.evidence)
    ]
    selected_ids = {concept.id for concept in selected}
    return [
        concept.model_copy(
            update={
                "evidence": [
                    item for item in concept.evidence if item.source.video_id == "demoTT00001"
                ],
                "relations": [
                    relation
                    for relation in concept.relations
                    if relation.target_concept_id in selected_ids
                ],
            }
        )
        for concept in selected
    ]


def test_demo_reviewed_corpus_is_valid(tmp_path: Path) -> None:
    normalized = tmp_path / "normalized"
    video = write_demo_video(normalized)
    concepts = demo_concepts()
    assert validate_corpus(concepts, [video]) == []


def test_publish_strips_full_transcript(tmp_path: Path) -> None:
    normalized = tmp_path / "normalized"
    write_demo_video(normalized)
    concept_dir = tmp_path / "concepts"
    concept_dir.mkdir()
    yaml = YAML()
    for concept in demo_concepts():
        with (concept_dir / f"{concept.slug}.yaml").open("w", encoding="utf-8") as handle:
            yaml.dump(concept.model_dump(mode="json"), handle)
    corpus = publish(
        concept_dir,
        normalized,
        tmp_path / "publish",
        {"id": "table-tennis", "name": "Table Tennis", "description": "Test"},
        include_demo=True,
    )
    assert corpus.videos
    assert corpus.videos[0].transcript is None
    assert all(concept.review_status == "approved" for concept in corpus.concepts)


def test_accepted_queue_item_requires_exact_canonical_evidence() -> None:
    concept = demo_concepts()[0]
    queue = {
        "items": [
            {
                "video_id": "demoTT00001",
                "decision": "accepted",
                "canonical_concept_id": concept.id,
                "candidate": {"evidence": [{"segment_ids": ["demoTT00001:99999"]}]},
            }
        ]
    }
    assert "no cited segment" in validate_review_queue(queue, [concept])[0]


def test_navigation_requires_every_approved_concept() -> None:
    concept = demo_concepts()[0]
    navigation = KnowledgeNavigation(
        title="Test", introduction="Test", sections=[]
    )
    assert validate_navigation(navigation, [concept]) == [
        f"navigation: approved concept is not placed: {concept.id}"
    ]


def test_spoken_source_cannot_exceed_thirty_seconds(tmp_path: Path) -> None:
    normalized = tmp_path / "normalized"
    video = write_demo_video(normalized)
    concept = demo_concepts()[0]
    evidence = concept.evidence[0]
    long_source = evidence.source.model_copy(
        update={"end_ms": evidence.source.start_ms + 30_001}
    )
    long_concept = concept.model_copy(
        update={"evidence": [evidence.model_copy(update={"source": long_source})]}
    )
    assert any("spoken source exceeds 30 seconds" in error for error in validate_corpus([long_concept], [video]))
