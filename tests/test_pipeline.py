from pathlib import Path

from ruamel.yaml import YAML

from processors.demo import write_demo_video
from processors.models import Concept
from processors.pipeline import load_reviewed_concepts, publish, validate_corpus

ROOT = Path(__file__).resolve().parents[1]


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
