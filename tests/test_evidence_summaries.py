import re
from pathlib import Path

from processors.evidence_summaries import (
    build_evidence_summary,
    build_missing_summaries,
    build_stale_summaries,
    write_missing_summaries,
)
from processors.models import Concept
from processors.pipeline import load_reviewed_concepts
from processors.utils import read_yaml

ROOT = Path(__file__).resolve().parents[1]
CONCEPTS = ROOT / "content" / "kbs" / "table-tennis" / "concepts"


def test_summary_is_moment_grounded_and_not_transcript_framed() -> None:
    data = read_yaml(CONCEPTS / "counter-loop.yaml")
    concept = Concept.model_validate(data)
    summary = build_evidence_summary(concept)
    assert summary is not None
    assert not re.search(r"\b(?:speaker|source|evidence|transcript|moments?|examples?)\b", summary, re.I)
    assert "slow" in summary.lower()
    assert concept.short_definition not in summary


def test_missing_summary_inventory_excludes_existing_counter_loop() -> None:
    items = build_missing_summaries(CONCEPTS)
    assert items == []


def test_every_reviewed_concept_has_an_evidence_summary() -> None:
    concepts = load_reviewed_concepts(CONCEPTS)
    assert len(concepts) >= 73
    assert all(concept.evidence_summary for concept in concepts)
    assert sum(bool(concept.evidence_summary_source_hash) for concept in concepts) >= 72
    assert next(concept for concept in concepts if concept.slug == "counter-loop").evidence_summary_source_hash is None


def test_generated_summaries_are_direct_syntheses() -> None:
    for path in CONCEPTS.glob("*.yaml"):
        data = read_yaml(path)
        if data.get("evidence_summary_source_hash"):
            summary = data["evidence_summary"]
            assert not re.search(
                r"\b(?:the )?(?:source|evidence|transcript|speaker|coach)\b",
                summary,
                re.I,
            ), path.name
            assert len(re.findall(r"[.!?](?:\s|$)", summary)) >= 2, path.name
            assert data.get("evidence_summary_generator") in {"codex", "deterministic"}, path.name


def test_editorial_reason_removes_possessive_speaker_reference() -> None:
    concept = Concept.model_validate(read_yaml(CONCEPTS / "compact-explosive-contact-and-stop.yaml"))
    summary = build_evidence_summary(concept)
    assert summary is not None
    assert not re.search(r"\b(?:speaker|coach)\b", summary, re.I)


def test_write_missing_summaries_only_fills_missing_files(tmp_path: Path) -> None:
    source = CONCEPTS / "active-block.yaml"
    target = tmp_path / source.name
    source_text = source.read_text(encoding="utf-8")
    source_text = re.sub(
        r"(?m)^evidence_summary: >-\r?\n(?:^  .*\r?\n?)+(?:^evidence_summary_source_hash:.*\r?\n?)?",
        "",
        source_text,
        count=1,
    )
    target.write_text(source_text, encoding="utf-8")

    written = write_missing_summaries(tmp_path)
    assert written == [target]
    text = target.read_text(encoding="utf-8")
    assert "evidence_summary: >-" in text
    assert "evidence_summary_source_hash:" in text
    assert text.index("evidence_summary:") > text.index("short_definition:")

    written_again = write_missing_summaries(tmp_path)
    assert written_again == []


def test_generated_summary_refreshes_when_reason_changes(tmp_path: Path) -> None:
    source = CONCEPTS / "active-block.yaml"
    target = tmp_path / source.name
    source_text = re.sub(
        r"(?m)^evidence_summary: >-\r?\n(?:^  .*\r?\n?)+(?:^evidence_summary_source_hash:.*\r?\n?)?",
        "",
        source.read_text(encoding="utf-8"),
        count=1,
    )
    target.write_text(source_text, encoding="utf-8")
    write_missing_summaries(tmp_path)
    assert build_stale_summaries(tmp_path) == []

    updated = target.read_text(encoding="utf-8").replace(
        "The speaker introduces a method", "The speaker introduces a more forceful method", 1
    )
    target.write_text(updated, encoding="utf-8")
    assert len(build_stale_summaries(tmp_path)) == 1
    assert write_missing_summaries(tmp_path, refresh_generated=True) == [target]
    assert build_stale_summaries(tmp_path) == []
