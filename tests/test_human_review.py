from pathlib import Path

import pytest
from ruamel.yaml import YAML

from processors.human_review import apply_human_review_decision, list_human_review
from processors.pipeline import load_reviewed_concepts
from processors.utils import read_yaml, write_json
from processors.workspace import KnowledgeBasePaths

yaml = YAML()


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.dump(payload, handle)


def _paths(tmp_path: Path) -> KnowledgeBasePaths:
    paths = KnowledgeBasePaths(tmp_path, "test-kb", "Test KB", "Test")
    paths.config.mkdir(parents=True)
    paths.content.joinpath("concepts").mkdir(parents=True)
    paths.content.joinpath("annotations").mkdir(parents=True)
    paths.data("normalized").mkdir(parents=True)
    paths.data("derived").mkdir(parents=True)
    paths.data("manifests").mkdir(parents=True)
    tmp_path.joinpath("app", "src", "data").mkdir(parents=True)
    _write_yaml(
        paths.config / "sources.yaml",
        {
            "sources": [{"id": "coach", "url": "https://www.youtube.com/@Coach", "enabled": True}],
            "videos": [{"id": "abcdefghijk", "source_id": "coach"}],
        },
    )
    write_json(
        paths.data("normalized") / "abcdefghijk.json",
        {
            "id": "abcdefghijk",
            "title": "Source lesson",
            "canonical_url": "https://www.youtube.com/watch?v=abcdefghijk",
            "channel_name": "Coach",
            "duration_ms": 30_000,
            "transcript": {
                "video_id": "abcdefghijk",
                "language": "English",
                "language_code": "en",
                "is_generated": False,
                "acquisition_method": "test",
                "segments": [
                    {"id": "abcdefghijk:00000", "video_id": "abcdefghijk", "text": "Stay balanced before the return.", "normalized_text": "Stay balanced before the return.", "start_ms": 1_000, "duration_ms": 5_000},
                    {"id": "abcdefghijk:00001", "video_id": "abcdefghijk", "text": "This lets you move either way.", "normalized_text": "This lets you move either way.", "start_ms": 6_000, "duration_ms": 5_000},
                ],
            },
        },
    )
    _write_yaml(
        paths.content / "concepts" / "ready-position.yaml",
        {
            "id": "concept-ready-position",
            "slug": "ready-position",
            "label": "Ready position",
            "short_definition": "A balanced stance used to prepare for the next ball.",
            "concept_type": "technique",
            "evidence": [
                {
                    "id": "existing",
                    "evidence_type": "explanation",
                    "excerpt": "Prepare in balance.",
                    "reason": "Existing reviewed support.",
                    "confidence": 0.9,
                    "visual_status": "not_visual",
                    "source": {"video_id": "abcdefghijk", "start_ms": 1000, "end_ms": 6000, "url": "https://www.youtube.com/watch?v=abcdefghijk&t=1s", "segment_ids": ["abcdefghijk:00000"]},
                }
            ],
        },
    )
    candidate = {
        "candidate_id": "concept-ready-position",
        "canonical_label": "Ready position",
        "aliases": [],
        "definition": "A balanced position that prepares the player to move for the next ball.",
        "concept_type": "technique",
        "facets": [],
        "difficulty": "beginner",
        "resolution": "match",
        "matched_concept_id": "concept-ready-position",
        "confidence": 0.8,
        "evidence": [{"evidence_type": "explanation", "segment_ids": ["abcdefghijk:00000", "abcdefghijk:00001"], "reason": "The coach connects balance with movement readiness.", "confidence": 0.85, "visual_status": "verified_visual_demo"}],
        "relations": [],
        "uncertainty": ["Below automatic confidence threshold"],
    }
    _write_yaml(
        paths.content / "annotations" / "review-queue.yaml",
        {"items": [{"video_id": "abcdefghijk", "candidate": candidate, "candidate_hash": "abc123", "decision": "human_review", "canonical_concept_id": None, "review_notes": "Human review required.", "adjudication_attempts": 2}]},
    )
    return paths


def _decision(action: str) -> dict:
    return {
        "video_id": "abcdefghijk",
        "candidate_id": "concept-ready-position",
        "candidate_hash": "abc123",
        "action": action,
        "target_concept_id": "concept-ready-position",
        "notes": "The cited lines directly support this existing concept.",
        "confirm_source": True,
        "confirm_concept": True,
    }


def test_list_human_review_returns_bounded_source_context(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    result = list_human_review(paths, limit=50)
    assert result["limit"] == 5
    assert result["total"] == 1
    assert len(result["items"][0]["context_segments"]) == 2
    assert all(segment["cited"] for segment in result["items"][0]["context_segments"])


def test_optional_advice_lists_deferred_and_keep_preserves_automation(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    queue_path = paths.content / "annotations" / "review-queue.yaml"
    queue = read_yaml(queue_path)
    queue["items"][0]["decision"] = "deferred"
    _write_yaml(queue_path, queue)

    listed = list_human_review(paths)
    result = apply_human_review_decision(paths, _decision("keep"))
    queue_item = read_yaml(queue_path)["items"][0]

    assert listed["items"][0]["decision"] == "deferred"
    assert result["decision"] == "deferred"
    assert queue_item["decision"] == "deferred"
    assert queue_item["manual_review_history"][0]["action"] == "keep"


def test_accept_existing_adds_exact_source_and_audit_history(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    result = apply_human_review_decision(paths, _decision("accept_existing"))
    concept = load_reviewed_concepts(paths.content / "concepts")[0]
    added = next(value for value in concept.evidence if "human-reviewed" in value.id)
    queue_item = read_yaml(paths.content / "annotations" / "review-queue.yaml")["items"][0]
    assert result["decision"] == "accepted"
    assert added.source.segment_ids == ["abcdefghijk:00000", "abcdefghijk:00001"]
    assert added.source.start_ms == 1000 and added.source.end_ms == 11000
    assert added.visual_status == "transcript_inferred"
    assert queue_item["decision"] == "accepted"
    assert queue_item["manual_review_history"][0]["action"] == "accept_existing"


def test_reject_changes_only_queue_and_stale_hash_is_rejected(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    before = (paths.content / "concepts" / "ready-position.yaml").read_text(encoding="utf-8")
    result = apply_human_review_decision(paths, _decision("reject"))
    assert result["decision"] == "rejected"
    assert (paths.content / "concepts" / "ready-position.yaml").read_text(encoding="utf-8") == before
    with pytest.raises(ValueError, match="changed or was already resolved"):
        apply_human_review_decision(paths, _decision("reject") | {"candidate_hash": "stale"})


def test_accept_requires_both_editorial_confirmations(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    with pytest.raises(ValueError, match="Confirm both"):
        apply_human_review_decision(paths, _decision("accept_existing") | {"confirm_source": False})
    assert read_yaml(paths.content / "annotations" / "review-queue.yaml")["items"][0]["decision"] == "human_review"


def test_accept_new_creates_reviewed_source_backed_concept(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    queue_path = paths.content / "annotations" / "review-queue.yaml"
    queue = read_yaml(queue_path)
    candidate = queue["items"][0]["candidate"]
    candidate.update(
        candidate_id="concept-balanced-recovery",
        canonical_label="Balanced recovery",
        definition="Returning to a balanced position after moving so the player can respond to the next ball.",
        resolution="new",
        matched_concept_id=None,
    )
    queue["items"][0]["candidate_hash"] = "new123"
    _write_yaml(queue_path, queue)
    decision = _decision("accept_new") | {
        "candidate_id": "concept-balanced-recovery",
        "candidate_hash": "new123",
        "target_concept_id": "",
    }

    result = apply_human_review_decision(paths, decision)
    created = paths.content / "concepts" / "balanced-recovery.yaml"
    concept = next(
        value
        for value in load_reviewed_concepts(paths.content / "concepts")
        if value.id == "concept-balanced-recovery"
    )
    queue_item = read_yaml(queue_path)["items"][0]

    assert created.exists()
    assert result["canonical_concept_id"] == "concept-balanced-recovery"
    assert concept.evidence[-1].source.segment_ids == [
        "abcdefghijk:00000",
        "abcdefghijk:00001",
    ]
    assert queue_item["decision"] == "accepted"
    assert queue_item["manual_review_history"][-1]["target_concept_id"] == concept.id
