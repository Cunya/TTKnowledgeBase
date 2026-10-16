import re
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from processors.evidence_summaries import (
    _editorial_reason,
    _write_summary_file,
    build_evidence_summary,
    build_missing_summaries,
    build_stale_summaries,
    evidence_summary_source_hash,
    write_missing_summaries,
)
from processors.models import Concept
from processors.pipeline import load_reviewed_concepts
from processors.utils import read_yaml

ROOT = Path(__file__).resolve().parents[1]
CONCEPTS = ROOT / "content" / "kbs" / "table-tennis" / "concepts"


def test_cleanup_does_not_create_causal_relationship() -> None:
    result = _editorial_reason(
        "Keep the racket close to the body, with the coach noting that the ball is fast."
    )
    assert "because" not in result
    assert "ball is fast" in result


@pytest.mark.parametrize("engine", ["deterministic", "codex"])
def test_summary_command_respects_audit_pause(tmp_path, monkeypatch, engine) -> None:
    from typer.testing import CliRunner

    import processors.cli as cli

    class Paths:
        content = tmp_path / "content"

        def data(self, _name):
            return tmp_path

    monkeypatch.setattr(cli, "kb_paths", lambda _kb: Paths())
    monkeypatch.setattr(cli, "processing_is_paused", lambda _path: True)
    def unexpected_writer(*args, **kwargs):
        pytest.fail("Paused summary writer was called")
    monkeypatch.setattr(cli, "write_missing_summaries", unexpected_writer)
    monkeypatch.setattr(cli, "write_codex_summaries", unexpected_writer)
    result = CliRunner().invoke(cli.app, ["build-evidence-summaries", "--write", "--engine", engine])
    assert result.exit_code != 0
    assert "paused" in result.output


@pytest.mark.parametrize("engine", ["deterministic", "codex"])
def test_summary_command_cannot_write_through_active_lock(tmp_path, monkeypatch, engine) -> None:
    from typer.testing import CliRunner

    import processors.cli as cli
    from processors.run_lock import KnowledgeBaseRunLock, RunAlreadyActive

    class Paths:
        content = tmp_path / "content"

        def data(self, _name):
            return tmp_path

    monkeypatch.setattr(cli, "kb_paths", lambda _kb: Paths())
    monkeypatch.setattr(cli, "processing_is_paused", lambda _path: False)
    def unexpected_writer(*args, **kwargs):
        pytest.fail("Contended summary writer was called")
    monkeypatch.setattr(cli, "write_missing_summaries", unexpected_writer)
    monkeypatch.setattr(cli, "write_codex_summaries", unexpected_writer)
    with KnowledgeBaseRunLock(tmp_path / "cp.lock"):
        result = CliRunner().invoke(cli.app, ["build-evidence-summaries", "--write", "--engine", engine])
    assert isinstance(result.exception, RunAlreadyActive)


def test_codex_summary_rejection_keeps_original(tmp_path, monkeypatch) -> None:
    import processors.evidence_summaries as summaries
    import processors.published_repair as repair
    from processors.codex_engine import CodexError
    from processors.demo import write_demo_video

    target = tmp_path / "active-block.yaml"
    write_summary_fixture(target)
    video = write_demo_video(tmp_path / "normalized")
    data = read_yaml(target)
    evidence = data["evidence"][0]
    evidence["source"] = {
        "video_id": video.id, "start_ms": 12000, "end_ms": 16200,
        "url": f"https://www.youtube.com/watch?v={video.id}&t=12s",
        "segment_ids": [video.transcript.segments[0].id],
    }
    evidence["review_status"] = "approved"
    evidence["visual_source"] = None
    evidence["spoken_context_start_ms"] = None
    evidence["spoken_context_end_ms"] = None
    data["evidence"] = [evidence]
    with target.open("w", encoding="utf-8") as handle:
        YAML().dump(data, handle)
    original = target.read_bytes()
    concept = Concept.model_validate(read_yaml(target))
    monkeypatch.setattr(summaries, "summarize_evidence_batch_with_codex", lambda *a, **k: (
        {concept.id: "Always attack with maximum power regardless of the incoming ball. This universal instruction applies to every possible stroke and serve."}, {}
    ))
    def reject(payload, *args, **kwargs):
        assert payload["selected_rows"]
        assert "field:evidence_summary" in payload["units"]
        return {"units": [{"key": "field:evidence_summary", "status": "needs_fix"}]}, {}
    monkeypatch.setattr(repair, "verify_article_with_codex", reject)
    with pytest.raises(CodexError, match="independent source verification"):
        summaries.write_codex_summaries(
            tmp_path, ROOT / "config/processors.yaml", tmp_path, tmp_path / "budget.json",
            videos=[video],
        )
    assert target.read_bytes() == original


def write_summary_fixture(target: Path) -> None:
    data = read_yaml(CONCEPTS / "active-block.yaml")
    for field in ("evidence_summary", "evidence_summary_source_hash", "evidence_summary_generator"):
        data.pop(field, None)
    with target.open("w", encoding="utf-8") as stream:
        YAML().dump(data, stream)


def test_summary_is_moment_grounded_and_not_transcript_framed() -> None:
    data = read_yaml(CONCEPTS / "counter-loop.yaml")
    concept = Concept.model_validate(data)
    summary = build_evidence_summary(concept)
    assert summary is not None
    assert not re.search(r"\b(?:speaker|source|evidence|transcript|moments?|examples?)\b", summary, re.I)
    assert "slow" in summary.lower()
    assert concept.short_definition not in summary
    assert "brings together" not in summary
    assert "preserving the relevant" not in summary
    assert "Additional points" not in summary


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
            assert len(re.findall(r"[.!?](?:\s|$)", summary)) >= 1, path.name
            assert data.get("evidence_summary_generator") in {"codex", "deterministic"}, path.name


def test_summary_falls_back_to_definition_instead_of_publishing_review_rationale() -> None:
    concept = Concept.model_validate(read_yaml(CONCEPTS / "counter-loop.yaml"))
    concept = concept.model_copy(update={"evidence": [concept.evidence[0].model_copy(update={
        "review_status": "approved",
        "reason": "The selected contiguous span matches the supplied existing concept.",
    })]})
    assert build_evidence_summary(concept) == concept.short_definition
    changed = concept.model_copy(update={"short_definition": "A corrected source-grounded definition."})
    assert evidence_summary_source_hash(changed) != evidence_summary_source_hash(concept)
    concept = concept.model_copy(update={"evidence": [concept.evidence[0].model_copy(update={
        "review_status": "unreviewed",
    })]})
    assert build_evidence_summary(concept) is None


def test_editorial_reason_removes_possessive_speaker_reference() -> None:
    concept = Concept.model_validate(read_yaml(CONCEPTS / "compact-explosive-contact-and-stop.yaml"))
    concept = concept.model_copy(
        update={
            "review_status": "approved",
            "evidence": [
                item.model_copy(update={"review_status": "approved"})
                for item in concept.evidence
            ],
        }
    )
    summary = build_evidence_summary(concept)
    assert summary is not None
    assert not re.search(r"\b(?:speaker|coach)\b", summary, re.I)


def test_write_missing_summaries_only_fills_missing_files(tmp_path: Path) -> None:
    source = CONCEPTS / "active-block.yaml"
    target = tmp_path / source.name
    write_summary_fixture(target)

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
    write_summary_fixture(target)
    write_missing_summaries(tmp_path)
    assert build_stale_summaries(tmp_path) == []

    data = read_yaml(target)
    data["evidence"][0]["reason"] += " Additional reviewed explanation."
    with target.open("w", encoding="utf-8") as stream:
        YAML().dump(data, stream)
    assert len(build_stale_summaries(tmp_path)) == 1
    assert write_missing_summaries(tmp_path, refresh_generated=True) == [target]
    assert build_stale_summaries(tmp_path) == []


@pytest.mark.parametrize("existing", [
    "", "evidence_summary: old summary\n  continued here.\n",
    'evidence_summary: "old summary\n  continued here."\n',
    "evidence_summary: >-\n  old summary\n  continued here.\n",
    "evidence_summary: |-\n  old summary\n  continued here.\n",
])
def test_summary_write_preserves_multiline_definition_and_other_fields(tmp_path: Path, existing: str) -> None:
    target = tmp_path / "concept.yaml"
    target.write_text(
        "short_definition: A definition that continues\n  onto the next line.\n" + existing
        + "evidence_summary_source_hash:\n  sha256:old\nevidence_summary_generator:\n  deterministic\n"
        + "concept_type: concept\nfacets:\n  category: [fundamentals]\n",
        encoding="utf-8",
    )
    before = read_yaml(target)
    _write_summary_file(target, "A new reviewed summary.", "sha256:test", generator="deterministic")
    after = read_yaml(target)
    assert after["short_definition"] == before["short_definition"]
    assert after["concept_type"] == before["concept_type"]
    assert after["facets"] == before["facets"]
    assert after["evidence_summary"] == "A new reviewed summary."
    assert after["evidence_summary_source_hash"] == "sha256:test"
    assert target.read_text(encoding="utf-8").count("evidence_summary:") == 1
