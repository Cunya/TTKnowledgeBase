from pathlib import Path
from types import SimpleNamespace

import pytest
from ruamel.yaml import YAML

import processors.pipeline as pipeline_module
from processors.codex_engine import CodexResponseError, CodexTimeoutError
from processors.demo import DEMO_VIDEO_ID, write_demo_video
from processors.models import (
    CandidateAdjudicationResponse,
    Concept,
    ConceptRelation,
    ExtractionResponse,
    KnowledgeNavigation,
    PublishCorpus,
    Segment,
    TranscriptTrack,
    Video,
    VisualSpan,
)
from processors.pipeline import (
    auto_place_generated_concepts,
    build_quality_report,
    build_review_queue,
    extract_video,
    find_high_overlap_excerpts,
    load_reviewed_concepts,
    longest_contiguous_overlap,
    process_pending_candidates,
    publish,
    render_quality_report_markdown,
    rephrase_high_overlap_excerpts,
    validate_corpus,
    validate_navigation,
    validate_published_corpus,
    validate_review_queue,
    validate_text_encoding,
)
from processors.utils import read_json, read_yaml, write_json

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def mock_external_support_verifier(monkeypatch):
    def verify(payload, *_args, **_kwargs):
        if "field:label" in payload["units"]:
            assert "field:concept_type" in payload["units"]
        return {"units": [{"key": key, "status": "supported", "note": "Fixture selected support checked.",
                           "supporting_segment_ids": unit["allowed_segment_ids"][:1]}
                          for key, unit in payload["units"].items()]}, {"method": "fixture_verifier"}
    monkeypatch.setattr(pipeline_module, "verify_article_with_codex", verify)


def test_extraction_uses_configured_overlapping_segment_batches(
    tmp_path: Path, monkeypatch
) -> None:
    video_id = "chunkvideo1"
    segments = [
        Segment(
            id=f"{video_id}:{index:05d}",
            video_id=video_id,
            text=f"Segment {index}.",
            normalized_text=f"Segment {index}.",
            start_ms=index * 1_000,
            duration_ms=1_000,
        )
        for index in range(10)
    ]
    video = Video(
        id=video_id,
        title="Chunking fixture",
        canonical_url=f"https://www.youtube.com/watch?v={video_id}",
        duration_ms=10_000,
        transcript=TranscriptTrack(
            video_id=video_id,
            language="English",
            language_code="en",
            is_generated=False,
            acquisition_method="fixture",
            segments=segments,
        ),
    )
    config_path = tmp_path / "processors.yaml"
    config_path.write_text(
        "codex:\n  max_segments_per_job: 4\n  overlap_segments: 1\n",
        encoding="utf-8",
    )
    calls: list[list[str]] = []

    def fake_extract(batch, *_args, **_kwargs):
        calls.append([segment.id for segment in batch])
        return ExtractionResponse(concepts=[], batch_notes=[]), {"input_hash": f"batch-{len(calls)}"}

    monkeypatch.setattr(pipeline_module, "extract_with_codex", fake_extract)
    extract_video(
        video,
        {},
        [],
        config_path,
        tmp_path / "derived",
        tmp_path / "audit",
    )

    assert [len(batch) for batch in calls] == [4, 4, 4, 1]
    assert calls[0][-1] == calls[1][0]
    payload = read_json(tmp_path / "derived" / f"{video_id}.candidates.json")
    assert payload["provenance"]["batch_count"] == 4


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
    assert len(rebuilt["candidate_hash"]) == 64

    # Distinct proposals can reuse an extraction ID within the same video.
    duplicate = candidate | {"definition": "A different source-grounded proposal with the same ID."}
    write_json(
        derived / "video-1.candidates.json",
        {"video_id": "video-1", "response": {"concepts": [candidate, duplicate], "batch_notes": []}},
    )
    accepted = rebuilt | {
        "decision": "accepted", "adjudication_attempts": 4,
        "adjudication_provenance": {"model": "test-model", "input_hash": "exact-input"},
        "manual_review_history": [{"note": "Keep this decision."}],
    }
    rejected = {
        "video_id": "video-1", "candidate": duplicate, "decision": "rejected",
        "review_notes": "Different proposal rejected.", "adjudication_attempts": 2,
    }
    with queue_path.open("w", encoding="utf-8") as handle:
        yaml.dump({"items": [rejected, accepted]}, handle)
    for _ in range(2):
        build_review_queue(derived, queue_path)
        first, second = read_yaml(queue_path)["items"]
        assert first["decision"] == "accepted"
        assert first["adjudication_attempts"] == 4
        assert first["adjudication_provenance"] == accepted["adjudication_provenance"]
        assert first["manual_review_history"] == accepted["manual_review_history"]
        assert second["decision"] == "rejected"
        assert second["adjudication_attempts"] == 2

    changed = candidate | {"definition": "Materially changed candidate content."}
    write_json(
        derived / "video-1.candidates.json",
        {"video_id": "video-1", "response": {"concepts": [changed], "batch_notes": []}},
    )
    build_review_queue(derived, queue_path)
    changed_item = read_yaml(queue_path)["items"][0]
    assert changed_item["decision"] == "pending"
    assert changed_item["canonical_concept_id"] is None
    assert "content changed" in changed_item["review_notes"]

    # Even an exact label and segment match cannot supply a review decision.
    matching = demo_concepts()[0].model_copy(update={
        "label": changed["canonical_label"],
        "evidence": [demo_concepts()[0].evidence[0].model_copy(update={
            "source": demo_concepts()[0].evidence[0].source.model_copy(update={
                "video_id": "video-1", "segment_ids": ["video-1:00001"],
            }),
        })],
    })
    build_review_queue(derived, tmp_path / "fresh-queue.yaml", [matching])
    assert read_yaml(tmp_path / "fresh-queue.yaml")["items"][0]["decision"] == "pending"


def test_legacy_human_candidate_returns_to_codex_deferred_queue(tmp_path: Path) -> None:
    queue_path = tmp_path / "review-queue.yaml"
    concept_dir = tmp_path / "concepts"
    normalized_dir = tmp_path / "normalized"
    concept_dir.mkdir()
    write_demo_video(normalized_dir)
    yaml = YAML()
    with queue_path.open("w", encoding="utf-8") as handle:
        yaml.dump(
            {
                "items": [
                    {
                        "video_id": DEMO_VIDEO_ID,
                        "candidate": {
                            "candidate_id": "candidate-1",
                            "canonical_label": "Ambiguous idea",
                            "definition": "A deliberately ambiguous candidate.",
                            "resolution": "ambiguous",
                            "matched_concept_id": None,
                            "confidence": 0.4,
                            "evidence": [
                                {
                                    "segment_ids": [f"{DEMO_VIDEO_ID}:00000"],
                                }
                            ],
                        },
                        "decision": "human_review",
                        "adjudication_attempts": 1,
                    }
                ]
            },
            handle,
        )

    counts = process_pending_candidates(
        queue_path,
        concept_dir,
        normalized_dir,
        [],
        retry_deferred=True,
        max_adjudication_attempts=2,
        adjudicator=lambda _candidate, _segments, _options: (
            CandidateAdjudicationResponse(
                decision="defer",
                canonical_concept_id=None,
                canonical_label=None,
                definition=None,
                concept_type=None,
                facets=[],
                evidence_type=None,
                segment_ids=[],
                excerpt=None,
                reason="The supplied rows are insufficient for a durable concept.",
                confidence=0.6,
                uncertainty=["Topic identity remains unclear."],
            ),
            {"model": "test-codex", "input_hash": "sha256:test"},
        ),
    )

    item = read_yaml(queue_path)["items"][0]
    assert counts["deferred"] == 1
    assert counts["human_review"] == 0
    assert item["decision"] == "deferred"
    assert item["adjudication_method"] == "codex_cli_semantic_review_v1"
    assert item["adjudication_attempts"] == 2


def test_codex_adjudication_adds_only_its_exact_supported_span(tmp_path: Path) -> None:
    queue_path = tmp_path / "review-queue.yaml"
    concept_dir = tmp_path / "concepts"
    normalized_dir = tmp_path / "normalized"
    concept_dir.mkdir()
    video = write_demo_video(normalized_dir)
    concept = next(item for item in demo_concepts() if item.id == "concept-ready-position")
    yaml = YAML()
    with (concept_dir / f"{concept.slug}.yaml").open("w", encoding="utf-8") as handle:
        document = concept.model_dump(mode="json")
        document["review_status"] = "unreviewed"
        yaml.dump(document, handle)
    with queue_path.open("w", encoding="utf-8") as handle:
        yaml.dump(
            {
                "items": [
                    {
                        "video_id": video.id,
                        "candidate_hash": "candidate-hash",
                        "candidate": {
                            "candidate_id": "focused-ready-position",
                            "canonical_label": "Ready position",
                            "definition": "A balanced stance before the next stroke.",
                            "confidence": 0.95,
                            "evidence": [
                                {
                                    "segment_ids": [f"{video.id}:00000", f"{video.id}:00003"],
                                    "visual_status": "not_visual",
                                }
                            ],
                        },
                        "decision": "pending",
                    }
                ]
            },
            handle,
        )

    counts = process_pending_candidates(
        queue_path,
        concept_dir,
        normalized_dir,
        [concept],
        adjudicator=lambda _candidate, _segments, _options: (
            CandidateAdjudicationResponse(
                decision="accept_existing",
                canonical_concept_id=concept.id,
                canonical_label=None,
                definition=None,
                concept_type=None,
                facets=[],
                evidence_type="explanation",
                segment_ids=[f"{video.id}:00000"],
                excerpt="Use a balanced ready position before the next stroke.",
                reason="The selected row directly instructs the balanced starting stance.",
                confidence=0.96,
                uncertainty=[],
            ),
            {
                "model": "test-codex",
                "input_hash": "sha256:test",
                "prompt_version": "test",
                "schema_version": "test",
            },
        ),
    )

    updated = load_reviewed_concepts(concept_dir)[0]
    added = next(item for item in updated.evidence if item.id.endswith("-codex-reviewed"))
    assert counts["accepted"] == 1
    assert counts["concepts_restored"] == 1
    assert updated.review_status == "approved"
    assert updated.generated_by.processor == "codex_semantic_adjudication"
    assert added.source.segment_ids == [f"{video.id}:00000"]
    assert added.source.start_ms == 12_000
    assert added.source.end_ms == 16_200
    assert "balanced starting stance" in added.reason
    queue_item = read_yaml(queue_path)["items"][0]
    assert queue_item["adjudicated_segment_ids"] == [f"{video.id}:00000"]


def test_schema_failed_codex_response_is_deferred_and_batch_continues(tmp_path: Path) -> None:
    queue_path = tmp_path / "review-queue.yaml"
    concept_dir = tmp_path / "concepts"
    normalized_dir = tmp_path / "normalized"
    concept_dir.mkdir()
    video = write_demo_video(normalized_dir)
    concept = next(item for item in demo_concepts() if item.id == "concept-ready-position")
    yaml = YAML()
    with (concept_dir / f"{concept.slug}.yaml").open("w", encoding="utf-8") as handle:
        yaml.dump(concept.model_dump(mode="json"), handle)
    candidate = {
        "candidate_id": "schema-failure",
        "canonical_label": "Ready position",
        "definition": "A balanced stance before the next stroke.",
        "resolution": "match",
        "matched_concept_id": concept.id,
        "confidence": 0.95,
        "evidence": [{"segment_ids": [f"{video.id}:00000"]}],
    }
    second = candidate | {"candidate_id": "continues-after-failure"}
    with queue_path.open("w", encoding="utf-8") as handle:
        yaml.dump(
            {
                "items": [
                    {"video_id": video.id, "candidate": candidate, "decision": "pending"},
                    {"video_id": video.id, "candidate": second, "decision": "pending"},
                ]
            },
            handle,
        )

    calls = 0
    progress_events = []

    def adjudicator(_candidate, _segments, _options):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise CodexResponseError(
                "only accept_existing may provide canonical_concept_id",
                {"model": "test-codex", "input_hash": "sha256:bad-response"},
            )
        return (
            CandidateAdjudicationResponse(
                decision="accept_existing",
                canonical_concept_id=concept.id,
                canonical_label=None,
                definition=None,
                concept_type=None,
                facets=[],
                evidence_type="explanation",
                segment_ids=[f"{video.id}:00000"],
                excerpt="Use a balanced ready position before the next stroke.",
                reason="The selected row directly instructs the balanced starting stance.",
                confidence=0.96,
                uncertainty=[],
            ),
            {"model": "test-codex", "input_hash": "sha256:good-response"},
        )

    counts = process_pending_candidates(
        queue_path,
        concept_dir,
        normalized_dir,
        [concept],
        adjudicator=adjudicator,
        progress_callback=progress_events.append,
    )

    items = read_yaml(queue_path)["items"]
    assert calls == 2
    assert counts["deferred"] == 1
    assert counts["accepted"] == 1
    assert items[0]["decision"] == "deferred"
    assert "failed schema validation" in items[0]["adjudication_reason"]
    assert items[0]["adjudication_provenance"]["input_hash"] == "sha256:bad-response"
    assert items[1]["decision"] == "accepted"
    assert [event["event"] for event in progress_events] == [
        "candidate_started",
        "candidate_finished",
        "candidate_started",
        "candidate_finished",
    ]
    assert all("excerpt" not in event and "reason" not in event for event in progress_events)


def test_codex_timeout_is_deferred_and_batch_continues(tmp_path: Path) -> None:
    queue_path = tmp_path / "review-queue.yaml"
    concept_dir = tmp_path / "concepts"
    normalized_dir = tmp_path / "normalized"
    concept_dir.mkdir()
    video = write_demo_video(normalized_dir)
    concept = next(item for item in demo_concepts() if item.id == "concept-ready-position")
    yaml = YAML()
    with (concept_dir / f"{concept.slug}.yaml").open("w", encoding="utf-8") as handle:
        yaml.dump(concept.model_dump(mode="json"), handle)
    candidate = {
        "candidate_id": "timeout-first",
        "canonical_label": "Ready position",
        "definition": "A balanced stance before the next stroke.",
        "resolution": "match",
        "matched_concept_id": concept.id,
        "confidence": 0.95,
        "evidence": [{"segment_ids": [f"{video.id}:00000"]}],
    }
    second = candidate | {"candidate_id": "continues-after-timeout"}
    with queue_path.open("w", encoding="utf-8") as handle:
        yaml.dump(
            {
                "items": [
                    {"video_id": video.id, "candidate": candidate, "decision": "pending"},
                    {"video_id": video.id, "candidate": second, "decision": "pending"},
                ]
            },
            handle,
        )

    calls = 0

    def adjudicator(_candidate, _segments, _options):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise CodexTimeoutError(
                "Codex adjudication timed out after 300 seconds",
                {"model": "test-codex", "input_hash": "sha256:timeout"},
                300,
            )
        return (
            CandidateAdjudicationResponse(
                decision="accept_existing",
                canonical_concept_id=concept.id,
                canonical_label=None,
                definition=None,
                concept_type=None,
                facets=[],
                evidence_type="explanation",
                segment_ids=[f"{video.id}:00000"],
                excerpt="Use a balanced ready position before the next stroke.",
                reason="The selected row directly instructs the balanced starting stance.",
                confidence=0.96,
                uncertainty=[],
            ),
            {"model": "test-codex", "input_hash": "sha256:accepted"},
        )

    counts = process_pending_candidates(
        queue_path,
        concept_dir,
        normalized_dir,
        [concept],
        adjudicator=adjudicator,
    )

    items = read_yaml(queue_path)["items"]
    assert calls == 2
    assert counts["deferred"] == 1
    assert counts["accepted"] == 1
    assert items[0]["decision"] == "deferred"
    assert "timed out after 300 seconds" in items[0]["adjudication_reason"]
    assert items[0]["adjudication_provenance"]["input_hash"] == "sha256:timeout"
    assert items[1]["decision"] == "accepted"


def test_bounded_adjudication_rotates_retries_without_starving_deferred(tmp_path: Path) -> None:
    queue_path = tmp_path / "review-queue.yaml"
    concept_dir = tmp_path / "concepts"
    concept_dir.mkdir()
    normalized_dir = tmp_path / "normalized"
    video = write_demo_video(normalized_dir)
    items = [
        {
            "video_id": video.id,
            "candidate": {
                "candidate_id": candidate_id, "canonical_label": "Ready position",
                "evidence": [{"segment_ids": [f"{video.id}:00000"]}],
            },
            "decision": decision, "adjudication_attempts": attempts,
        }
        for candidate_id, decision, attempts in [
            ("repeated", "deferred", 1), ("untouched", "pending", 0),
        ]
    ]
    with queue_path.open("w", encoding="utf-8") as handle:
        YAML().dump({"items": items}, handle)
    selected = []
    advice = []
    items[0]["manual_review_history"] = [{"notes": "Check incoming versus outgoing ball."}]
    items[0]["review_notes"] = "Check incoming versus outgoing ball."
    with queue_path.open("w", encoding="utf-8") as handle:
        YAML().dump({"items": items}, handle)

    def adjudicator(candidate, _segments, _options):
        selected.append(candidate["candidate_id"])
        advice.append(candidate.get("editorial_advice"))
        return CandidateAdjudicationResponse(
            decision="defer", canonical_concept_id=None, canonical_label=None,
            definition=None, concept_type=None, facets=[], evidence_type=None,
            segment_ids=[], excerpt=None, reason="Needs further source support.",
            confidence=0.5, uncertainty=[],
        ), {"model": "test-model"}

    for _ in range(3):
        process_pending_candidates(
            queue_path, concept_dir, normalized_dir, [], adjudicator=adjudicator,
            retry_deferred=True, max_candidates=1,
        )
    assert selected == ["untouched", "repeated", "untouched"]
    assert advice == [None, "Check incoming versus outgoing ball.", None]
    assert all("editorial_advice" not in item["candidate"] for item in read_yaml(queue_path)["items"])
    assert [item["adjudication_attempts"] for item in read_yaml(queue_path)["items"]] == [2, 2]


def test_adjudication_checkpoint_preserves_each_ten_candidates(tmp_path: Path) -> None:
    queue_path = tmp_path / "review-queue.yaml"
    concept_dir = tmp_path / "concepts"
    normalized_dir = tmp_path / "normalized"
    concept_dir.mkdir()
    video = write_demo_video(normalized_dir)
    concept = next(item for item in demo_concepts() if item.id == "concept-ready-position")
    yaml = YAML()
    with (concept_dir / f"{concept.slug}.yaml").open("w", encoding="utf-8") as handle:
        yaml.dump(concept.model_dump(mode="json"), handle)
    items = [
        {
            "video_id": video.id,
            "candidate": {
                "candidate_id": f"checkpoint-{index:02d}",
                "canonical_label": "Ready position",
                "evidence": [{"segment_ids": [f"{video.id}:00000"]}],
            },
            "decision": "pending",
        }
        for index in range(11)
    ]
    with queue_path.open("w", encoding="utf-8") as handle:
        yaml.dump({"items": items}, handle)

    calls = 0
    progress_events: list[dict] = []

    def adjudicator(_candidate, _segments, _options):
        nonlocal calls
        calls += 1
        if calls == 11:
            raise RuntimeError("stop after the first checkpoint")
        return (
            CandidateAdjudicationResponse(
                decision="accept_existing",
                canonical_concept_id=concept.id,
                canonical_label=None,
                definition=None,
                concept_type=None,
                facets=[],
                evidence_type="explanation",
                segment_ids=[f"{video.id}:00000"],
                excerpt="Use a balanced ready position before the next stroke.",
                reason="The selected row directly instructs the balanced starting stance.",
                confidence=0.96,
                uncertainty=[],
            ),
            {"model": "test-codex", "input_hash": "sha256:checkpoint"},
        )

    with pytest.raises(RuntimeError, match="stop after the first checkpoint"):
        process_pending_candidates(
            queue_path,
            concept_dir,
            normalized_dir,
            [concept],
            adjudicator=adjudicator,
            progress_callback=progress_events.append,
        )

    persisted_items = read_yaml(queue_path)["items"]
    assert [item["decision"] for item in persisted_items[:10]] == ["accepted"] * 10
    assert persisted_items[10]["decision"] == "pending"
    persisted_concept = load_reviewed_concepts(concept_dir)[0]
    assert sum(item.id.endswith("-codex-reviewed") for item in persisted_concept.evidence) == 1
    checkpoint = next(event for event in progress_events if event["event"] == "checkpoint")
    assert checkpoint["event"] == "checkpoint"
    assert checkpoint["index"] == 10
    assert checkpoint["total"] == 11
    assert checkpoint["batch"] == 1
    assert checkpoint["batch_total"] == 2
    assert checkpoint["backlog_total"] == 11
    assert checkpoint["backlog_remaining"] == 1
    assert checkpoint["full_backlog_total"] == 11
    assert checkpoint["full_backlog_remaining"] == 1


@pytest.mark.parametrize("candidate_count", [0, 9, 10, 11, 20])
@pytest.mark.parametrize("outcome", ["accept_existing", "defer", "reject", "restore", "blocked_restore", "duplicate", "create_new", "distinct_span", "verification_failure"])
def test_adjudication_writes_only_changed_files_once_per_batch(
    tmp_path: Path, monkeypatch, candidate_count: int, outcome: str
) -> None:
    queue_path = tmp_path / "review-queue.yaml"
    concept_dir = tmp_path / "concepts"
    normalized_dir = tmp_path / "normalized"
    concept_dir.mkdir()
    video = write_demo_video(normalized_dir)
    concepts = demo_concepts()
    concept = next(item for item in concepts if item.id == "concept-ready-position")
    if outcome in {"restore", "blocked_restore"}:
        concept = concept.model_copy(update={"review_status": "unreviewed"})
        if outcome == "restore":
            concept = concept.model_copy(update={"relations": [r.model_copy(update={"review_status": "unreviewed"}) for r in concept.relations]})
        concepts = [concept if item.id == concept.id else item for item in concepts]
    yaml = YAML()
    for item in concepts:
        with (concept_dir / f"{item.slug}.yaml").open("w", encoding="utf-8") as handle:
            yaml.dump(item.model_dump(mode="json"), handle)
    items = [
        {
            "video_id": video.id,
            "candidate": {
                "candidate_id": "repeated" if outcome == "duplicate" else f"candidate-{index}",
                "canonical_label": "Ready position",
                "evidence": [{"segment_ids": [f"{video.id}:00000"]}],
            },
            "decision": "pending",
        }
        for index in range(candidate_count)
    ]
    with queue_path.open("w", encoding="utf-8") as handle:
        yaml.dump({"items": items}, handle)
    original_files = {
        path: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in [queue_path, *concept_dir.glob("*.yaml")]
    }
    replacements: list[Path] = []
    replace = pipeline_module.replace_with_retry

    def record_replace(source, target):
        replacements.append(target)
        replace(source, target)

    monkeypatch.setattr(pipeline_module, "replace_with_retry", record_replace)
    if outcome == "verification_failure":
        def unsupported(payload, *_args, **_kwargs):
            return {"units": [{"key": key, "status": "needs_fix", "note": "Unsupported clause.",
                               "supporting_segment_ids": []} for key in payload["units"]]}, {}
        monkeypatch.setattr(pipeline_module, "verify_article_with_codex", unsupported)
    calls = 0
    new_concept_id = "concept-balanced-starting-stance"

    def adjudicator(_candidate, _segments, _options):
        nonlocal calls
        calls += 1
        decision = outcome if outcome in {"defer", "reject"} else "accept_existing"
        if outcome == "create_new" and calls == 1:
            decision = "create_new"
        accepts = decision not in {"defer", "reject"}
        return (
            CandidateAdjudicationResponse(
                decision=decision,
                canonical_concept_id=(
                    (new_concept_id if outcome == "create_new" else concept.id)
                    if decision == "accept_existing" else None
                ),
                canonical_label="Balanced starting stance" if decision == "create_new" else None,
                definition=(
                    "A balanced stance prepares the player to move before the next stroke."
                    if decision == "create_new" else None
                ),
                concept_type="technique" if decision == "create_new" else None,
                facets=[],
                evidence_type="explanation" if accepts else None,
                segment_ids=[f"{video.id}:00001" if outcome == "distinct_span" and calls % 2 == 0
                             else f"{video.id}:00000"] if accepts else [],
                excerpt="Use a balanced ready position before the next stroke." if accepts else None,
                reason="The selected row directly instructs the balanced starting stance.",
                confidence=0.96,
                uncertainty=[],
            ),
            {"model": "test-codex", "input_hash": "sha256:persistence"},
        )

    counts = process_pending_candidates(
        queue_path, concept_dir, normalized_dir, concepts, adjudicator=adjudicator
    )

    batch_count = (candidate_count + 9) // 10
    assert calls == candidate_count
    assert replacements.count(queue_path) == batch_count
    accepts = outcome not in {"defer", "reject", "verification_failure", "blocked_restore"}
    changed_path = concept_dir / (
        "balanced-starting-stance.yaml" if outcome == "create_new" else f"{concept.slug}.yaml"
    )
    assert replacements.count(changed_path) == (batch_count if accepts else 0)
    for path, original in original_files.items():
        if path not in replacements:
            assert (path.read_bytes(), path.stat().st_mtime_ns) == original
    assert set(replacements) <= {queue_path, changed_path}
    persisted = read_yaml(queue_path)["items"]
    expected_decision = "accepted" if accepts else ("rejected" if outcome == "reject" else "deferred")
    assert [item["decision"] for item in persisted] == [expected_decision] * candidate_count
    assert all(item["adjudication_attempts"] == 1 for item in persisted)
    assert counts["considered"] == candidate_count
    if accepts and candidate_count:
        updated = next(item for item in load_reviewed_concepts(concept_dir) if item.id == (
            new_concept_id if outcome == "create_new" else concept.id
        ))
        added = [item for item in updated.evidence if "-codex-reviewed" in item.id]
        assert len(added) == (min(candidate_count, 2) if outcome == "distinct_span" else 1)
        assert counts["evidence_added"] == len(added)
        assert {tuple(item.source.segment_ids) for item in added} == (
            {(f"{video.id}:00000",), (f"{video.id}:00001",)}
            if outcome == "distinct_span" and candidate_count > 1
            else {(f"{video.id}:00000",)}
        )
        assert updated.review_status == "approved"
        assert counts["concepts_restored"] == int(outcome == "restore")
        assert counts["concepts_added"] == int(outcome == "create_new")


def test_validation_rejects_duplicate_citations_but_keeps_distinct_visual_windows(tmp_path: Path) -> None:
    video = write_demo_video(tmp_path)
    concept = next(c for c in demo_concepts() if c.id == "concept-ready-position")
    original = concept.evidence[0]
    duplicate = original.model_copy(update={"id": "duplicate-citation"})
    concept = concept.model_copy(update={"evidence": [original, duplicate]})
    assert any("duplicate spoken citation" in error for error in validate_corpus([concept], [video]))
    visual = VisualSpan(
        video_id=video.id, start_ms=12000, end_ms=14000,
        url=f"https://www.youtube.com/watch?v={video.id}&t=12s",
        selection_method="nearby_visual_inference",
        note="Synthetic separate visual window for duplicate-citation validation.",
    )
    duplicate = duplicate.model_copy(update={"visual_source": visual, "visual_status": "transcript_inferred"})
    concept = concept.model_copy(update={"evidence": [original, duplicate]})
    assert not any("duplicate spoken citation" in error for error in validate_corpus([concept], [video]))


def test_editorial_corrections_preserve_scope_and_quarantine_wrong_topic() -> None:
    folder = ROOT / "content/kbs/table-tennis/concepts"
    forearm = read_yaml(folder / "forearm-forward-drive.yaml")
    assert "penhold" in forearm["short_definition"].lower()
    half_long = read_yaml(folder / "half-long-ball.yaml")
    definition = half_long["short_definition"].lower()
    assert any(phrase in definition for phrase in (
        "just clears the end line", "just goes past the end line",
    ))
    assert "first bounce" in definition or "bounces once" in definition
    defensive = read_yaml(folder / "defensive-block-against-long-fast-serves.yaml")
    assert "distance" not in defensive["facets"]
    assert "level" not in defensive["facets"]
    half_high = read_yaml(folder / "half-high-ball-as-an-attack-opportunity.yaml")
    assert all(evidence["review_status"] == "unreviewed" for evidence in half_high["evidence"]
               if evidence["source"]["video_id"] == "8EoTrLShMWQ" and "-codex-reviewed" in evidence["id"])
    ready = read_yaml(folder / "ready-position.yaml")
    moment = next(e for e in ready["evidence"]
                  if e["id"] == "JLGqLr-9-2w-concept-ready-position-codex-reviewed")
    assert "JLGqLr-9-2w:00055" in moment["source"]["segment_ids"]
    assert moment["source"]["end_ms"] == 188233


def test_validation_rejects_source_that_truncates_cited_segment() -> None:
    video = write_demo_video(Path(".pytest_cache") / "source-envelope-demo")
    concept = next(item for item in demo_concepts() if item.id == "concept-ready-position")
    evidence = next(
        item for item in concept.evidence if item.source.video_id == DEMO_VIDEO_ID
    )
    truncated = evidence.source.model_copy(update={"end_ms": evidence.source.end_ms - 1})
    changed = concept.model_copy(
        update={"evidence": [evidence.model_copy(update={"source": truncated})]}
    )
    assert any(
        "source ends before its last cited segment" in error
        for error in validate_corpus([changed], [video])
    )


def test_high_overlap_rephrase_preserves_source_metadata() -> None:
    concept = next(
        concept
        for concept in demo_concepts()
        if any("demoTT00001:00000" in item.source.segment_ids for item in concept.evidence)
    )
    evidence_index = next(
        index
        for index, item in enumerate(concept.evidence)
        if "demoTT00001:00000" in item.source.segment_ids
    )
    evidence = concept.evidence[evidence_index]
    direct = evidence.model_copy(update={"excerpt": "Start in a balanced ready position."})
    evidence_items = list(concept.evidence)
    evidence_items[evidence_index] = direct
    concept = concept.model_copy(update={"evidence": evidence_items})
    video = write_demo_video(Path(".pytest_cache") / "rephrase-demo")

    findings = find_high_overlap_excerpts([concept], [video], min_words=5)
    assert findings and findings[0]["complete_match"] is True
    assert longest_contiguous_overlap(direct.excerpt, video.transcript.segments[0].text) == 6

    updated, rewritten = rephrase_high_overlap_excerpts(
        Path("."),
        [concept],
        [video],
        Path("config/processors.yaml"),
        Path(".pytest_cache"),
        min_words=5,
        rephrase=lambda _excerpt, _transcript, _limit: (
            "Begin in a stable ready stance.",
            {"model": "test"},
        ),
        persist=False,
    )
    assert len(rewritten) == 1
    assert updated[0].evidence[evidence_index].excerpt == "Begin in a stable ready stance."
    assert updated[0].evidence[evidence_index].source == evidence.source


def test_rephrase_rejection_preserves_canonical_bytes(tmp_path, monkeypatch) -> None:
    video = write_demo_video(tmp_path / "normalized")
    concept = next(c for c in demo_concepts() if any(
        video.transcript.segments[0].id in e.source.segment_ids for e in c.evidence
    ))
    evidence = next(e for e in concept.evidence if video.transcript.segments[0].id in e.source.segment_ids)
    concept = concept.model_copy(update={"evidence": [evidence.model_copy(update={
        "excerpt": video.transcript.segments[0].text
    })]})
    target = tmp_path / f"{concept.slug}.yaml"
    original = b"canonical content must remain unchanged"
    target.write_bytes(original)
    def reject(payload, *args, **kwargs):
        assert payload["units"]["evidence:0:rewrite"]["allowed_segment_ids"] == evidence.source.segment_ids
        return {"units": [{"key": "evidence:0:rewrite", "status": "needs_fix"}]}, {}
    monkeypatch.setattr(pipeline_module, "verify_article_with_codex", reject)
    with pytest.raises(ValueError, match="independent source verification"):
        rephrase_high_overlap_excerpts(
            tmp_path, [concept], [video], ROOT / "config/processors.yaml", tmp_path,
            min_words=5, rephrase=lambda *_: (
                "Always attack every serve with maximum forehand power.", {}
            ),
        )
    assert target.read_bytes() == original


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
                    relation.model_copy(update={
                        "sources": [source for source in relation.sources
                                    if source.video_id == DEMO_VIDEO_ID],
                    })
                    for relation in concept.relations
                    if relation.target_concept_id in selected_ids
                    and any(source.video_id == DEMO_VIDEO_ID for source in relation.sources)
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
    assert validate_published_corpus(corpus) == []
    report = build_quality_report(corpus)
    assert report["concept_count"] == len(corpus.concepts)
    assert report["evidence_count"] == sum(len(concept.evidence) for concept in corpus.concepts)
    assert "# Table Tennis quality report" in render_quality_report_markdown(
        report | {"public_corpus_bytes": 123}, "Table Tennis"
    )


def test_relation_citations_use_the_evidence_validation_contract(tmp_path: Path) -> None:
    video = write_demo_video(tmp_path / "normalized")
    concept = demo_concepts()[0].model_copy(deep=True)
    source = concept.evidence[0].source
    relation = ConceptRelation(
        relation_type="used_with", target_concept_id=concept.id,
        sources=[source.model_copy(update={"segment_ids": ["invented:00000"]})],
        confidence=0.9,
    )
    concept.relations = [relation]
    assert any("relation/" in error and "missing segments" in error
               for error in validate_corpus([concept], [video]))
    relation.sources = []
    assert any("approved relation has no source" in error
               for error in validate_corpus([concept], [video]))
    relation.review_status = "unreviewed"
    relation.target_concept_id = "unreviewed-target"
    assert validate_corpus([concept], [video]) == []


def test_published_validation_rejects_private_and_unreviewed_content(tmp_path: Path) -> None:
    video = write_demo_video(tmp_path / "normalized")
    concept = demo_concepts()[0].model_copy(update={"review_status": "unreviewed"})
    corpus = PublishCorpus(knowledge_base={"id": "test"}, concepts=[concept], videos=[video])
    errors = validate_published_corpus(corpus)
    assert any("private transcript" in error for error in errors)
    assert any("published concept is not approved" in error for error in errors)


def test_publish_keeps_visual_and_relation_videos_and_only_approved_relations(tmp_path: Path) -> None:
    normalized = tmp_path / "normalized"
    video = write_demo_video(normalized)
    concept = demo_concepts()[0].model_copy(deep=True)
    visual_video = video.model_copy(update={"id": "visualvideo", "transcript": None})
    relation_video = video.model_copy(deep=True)
    relation_video.id = "relationvid"
    relation_video.transcript.video_id = relation_video.id
    for segment in relation_video.transcript.segments:
        segment.video_id = relation_video.id
        segment.id = segment.id.replace(video.id, relation_video.id)
    write_json(normalized / "visual.json", visual_video)
    write_json(normalized / "relation.json", relation_video)
    concept.evidence[0].visual_status = "transcript_inferred"
    concept.evidence[0].visual_source = VisualSpan(
        video_id=visual_video.id, start_ms=0, end_ms=1000,
        url=f"https://www.youtube.com/watch?v={visual_video.id}&t=0s",
        selection_method="nearby_visual_inference", note="Unverified test window.",
    )
    source = concept.evidence[0].source.model_copy(update={
        "video_id": relation_video.id,
        "url": concept.evidence[0].source.url.replace(video.id, relation_video.id),
        "segment_ids": [item.replace(video.id, relation_video.id)
                        for item in concept.evidence[0].source.segment_ids],
    })
    relation = ConceptRelation(
        relation_type="used_with", target_concept_id=concept.id,
        sources=[source], confidence=0.9,
    )
    concept.relations = [relation, relation.model_copy(update={"review_status": "unreviewed"})]
    concept_dir = tmp_path / "concepts"
    concept_dir.mkdir()
    with (concept_dir / "concept.yaml").open("w", encoding="utf-8") as handle:
        YAML().dump(concept.model_dump(mode="json"), handle)
    corpus = publish(concept_dir, normalized, tmp_path / "publish",
                     {"id": "test", "name": "Test"}, include_demo=True)
    assert {item.id for item in corpus.videos} == {video.id, visual_video.id, relation_video.id}
    assert len(corpus.concepts[0].relations) == 1
    assert validate_published_corpus(corpus) == []


def test_text_encoding_validation_finds_mojibake() -> None:
    assert validate_text_encoding({"label": "broken â€“ dash"}) == [
        "corpus.label: possible encoding corruption"
    ]


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


def test_accepted_queue_item_accepts_exact_adjudicated_span() -> None:
    concept = demo_concepts()[0]
    queue = {
        "items": [
            {
                "video_id": "demoTT00001",
                "decision": "accepted",
                "canonical_concept_id": concept.id,
                "candidate": {"evidence": [{"segment_ids": ["demoTT00001:99999"]}]},
                "adjudicated_segment_ids": ["demoTT00001:00004"],
            }
        ]
    }
    assert validate_review_queue(queue, [concept]) == []


def test_published_queue_validation_uses_reviewed_demo_evidence() -> None:
    concept = next(concept for concept in demo_concepts() if concept.id == "concept-ready-position")
    queue = {
        "items": [
            {
                "video_id": DEMO_VIDEO_ID,
                "decision": "accepted",
                "canonical_concept_id": concept.id,
                "candidate": {"evidence": [{"segment_ids": [f"{DEMO_VIDEO_ID}:00000"]}]},
            }
        ]
    }
    assert validate_review_queue(queue, [concept]) == []


def test_navigation_requires_every_approved_concept() -> None:
    concept = demo_concepts()[0]
    navigation = KnowledgeNavigation(
        title="Test", introduction="Test", sections=[]
    )
    assert validate_navigation(navigation, [concept]) == [
        f"navigation: approved concept is not placed: {concept.id}"
    ]


def test_auto_navigation_skips_weak_or_ambiguous_matches() -> None:
    navigation = {
        "sections": [
            {"id": "loop", "label": "Loop", "description": "Topspin attacks.", "concept_ids": []},
            {"id": "push", "label": "Push", "description": "Backspin control strokes.", "concept_ids": []},
        ]
    }
    concept = SimpleNamespace(
        id="concept-ambiguous",
        label="Ball selection",
        short_definition="Choose the right response to the incoming ball.",
        evidence_summary="A decision depends on timing and placement.",
        concept_type="tactic",
        generated_by=SimpleNamespace(processor="automatic_candidate_review"),
    )
    assert auto_place_generated_concepts(navigation, [concept]) == {
        "placed": 0,
        "skipped": 1,
        "holding": 0,
    }
    assert all(not node["concept_ids"] for node in navigation["sections"])


def test_auto_navigation_holds_ambiguous_generated_concept() -> None:
    navigation = {
        "sections": [
            {"id": "serve", "label": "Serve", "description": "Serve mechanics.", "concept_ids": []},
            {
                "id": "editorial-placement-review",
                "label": "Needs editorial placement",
                "description": "Awaiting a human navigation choice.",
                "concept_ids": [],
            },
        ]
    }
    concept = SimpleNamespace(
        id="concept-ambiguous",
        label="Ball selection",
        short_definition="Choose the right response to the incoming ball.",
        evidence_summary="A decision depends on timing and placement.",
        concept_type="tactic",
        generated_by=SimpleNamespace(processor="codex_semantic_adjudication"),
    )
    assert auto_place_generated_concepts(navigation, [concept]) == {
        "placed": 1,
        "skipped": 0,
        "holding": 1,
    }
    assert navigation["sections"][1]["concept_ids"] == [concept.id]


def test_auto_navigation_places_unambiguous_codex_concept() -> None:
    navigation = {
        "sections": [
            {"id": "serve", "label": "Serve", "description": "Serve mechanics.", "concept_ids": []},
        ]
    }
    concept = SimpleNamespace(
        id="concept-close-serve-toss",
        label="Keep the serve toss close to the body",
        short_definition="Keep the serve toss close to the body for precise contact.",
        evidence_summary="Keep the serve toss close to the body before contact.",
        concept_type="fundamentals",
        generated_by=SimpleNamespace(processor="codex_semantic_adjudication"),
    )
    assert auto_place_generated_concepts(navigation, [concept]) == {
        "placed": 1,
        "skipped": 0,
        "holding": 0,
    }
    assert navigation["sections"][0]["concept_ids"] == [concept.id]


def test_auto_navigation_uses_evidence_when_summary_is_missing() -> None:
    navigation = {
        "sections": [
            {
                "id": "backhand-loop-family",
                "label": "Backhand loop",
                "description": "Backhand stroke mechanics.",
                "concept_ids": [],
            },
            {
                "id": "forehand-loop-family",
                "label": "Forehand loop",
                "description": "Forehand stroke mechanics.",
                "concept_ids": [],
            },
        ]
    }
    concept = SimpleNamespace(
        id="concept-backswing-direction",
        label="Backswing direction after looping",
        aliases=[],
        short_definition="Keep the racket moving backward after looping backspin.",
        evidence_summary=None,
        concept_type="stroke",
        facets={},
        evidence=[
            SimpleNamespace(
                excerpt="After looping, your backswing goes backwards, not downwards.",
                reason="This backhand loop correction keeps the racket travelling backwards.",
            )
        ],
        generated_by=SimpleNamespace(processor="codex_semantic_adjudication"),
    )
    assert auto_place_generated_concepts(navigation, [concept]) == {
        "placed": 1,
        "skipped": 0,
        "holding": 0,
    }
    assert navigation["sections"][0]["concept_ids"] == [concept.id]


def test_navigation_keeps_audited_concepts_under_semantic_parents() -> None:
    navigation = read_yaml(ROOT / "config" / "kbs" / "table-tennis" / "navigation.yaml")
    paths: dict[str, list[str]] = {}

    def walk(nodes: list[dict], parent_path: tuple[str, ...] = ()) -> None:
        for node in nodes:
            path = parent_path + (node.get("label", node.get("id", "")),)
            for concept_id in node.get("concept_ids", []) or []:
                paths.setdefault(concept_id, []).append(" > ".join(path))
            walk(node.get("children", []) or [], path)

    walk(navigation["sections"])
    expected = {
        "concept-close-step": "Footwork and spacing",
        "concept-backhand-system-body-led-ripping": "Backhand loop",
        "concept-flat-hit-swing-size-control": "Drive",
        "concept-open-shoulder-and-pivot-for-forehand-transition": "Footwork and spacing",
        "concept-post-shot-recovery-to-ready-position": "Footwork and spacing",
        "concept-rhythm-spacing-and-recovery-for-backhand-rip": "Footwork and spacing",
        "concept-forearm-position-relative-to-the-elbow": "Movement and contact fundamentals",
        "concept-push-flick-close-distance-control": "Timing and spacing",
    }
    for concept_id, parent in expected.items():
        assert any(parent in path for path in paths[concept_id]), concept_id


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
