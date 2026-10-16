from datetime import UTC, datetime
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from processors.demo import write_demo_video
from processors.inventory import (
    build_inventory_ledger,
    load_inventory_catalog,
    select_ledger_worksets,
)
from processors.models import Concept, PublishCorpus
from processors.utils import read_json, write_json
from processors.workspace import KnowledgeBasePaths


def _paths(tmp_path: Path) -> KnowledgeBasePaths:
    paths = KnowledgeBasePaths(tmp_path, "test-kb", "Test KB", "Test")
    paths.config.mkdir(parents=True)
    paths.content.joinpath("annotations").mkdir(parents=True)
    paths.data("manifests").mkdir(parents=True)
    paths.data("normalized").mkdir(parents=True)
    paths.data("derived").mkdir(parents=True)
    tmp_path.joinpath("app", "src", "data").mkdir(parents=True)
    yaml = YAML()
    with paths.config.joinpath("sources.yaml").open("w", encoding="utf-8") as handle:
        yaml.dump(
            {
                "sources": [
                    {
                        "id": "source-one",
                        "url": "https://www.youtube.com/@SourceOne",
                        "enabled": True,
                    }
                ],
                "videos": [],
            },
            handle,
        )
    return paths


def test_inventory_uses_best_catalog_and_rejects_non_video_placeholders(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    write_json(
        paths.data("manifests") / "discovered-small.json",
        {
            "source_url": "https://www.youtube.com/@SourceOne",
            "videos": [{"id": "abcdefghijk", "title": "First"}],
        },
    )
    write_json(
        tmp_path / "app" / "src" / "data" / "source.json",
        {
            "source_id": "source-one",
            "videos": [
                {"id": "abcdefghijk", "title": "First", "view_count": 2},
                {"id": "zyxwvutsrqp", "title": "Second", "view_count": 9},
                {"id": "UCLdwDMdtrcW_WlhXI0Kli9Q", "title": "Channel placeholder"},
            ],
        },
    )
    write_json(
        paths.data("manifests") / "ingest-retries.json",
        {
            "items": {
                "abcdefghijk": {
                    "attempts": 3,
                    "error_type": "TranscriptsDisabled",
                    "next_retry_at": "2026-08-05T00:00:00+00:00",
                }
            }
        },
    )

    catalog = load_inventory_catalog(paths)
    ledger = build_inventory_ledger(
        paths, write=False, now=datetime(2026, 8, 6, tzinfo=UTC)
    )

    assert set(catalog) == {"abcdefghijk", "zyxwvutsrqp"}
    assert ledger["summary"]["inventory"] == 2
    assert ledger["summary"]["excluded"] == 1
    worksets = select_ledger_worksets(ledger, 10)
    assert worksets["acquisition"] == [
        {
            "id": "zyxwvutsrqp",
            "source_id": "source-one",
            "reason": "eligibility or transcript acquisition is due",
        }
    ]


def test_worksets_round_robin_across_sources() -> None:
    videos = [
        {
            "video_id": f"{source}-{index}",
            "source_ids": [source],
            "view_count": 100 - index,
            "completion_state": "needs_adjudication",
        }
        for source in ("alpha", "beta", "gamma")
        for index in range(4)
    ]
    workset = select_ledger_worksets({"videos": videos}, 0, adjudication_limit=8)

    assert [item["source_id"] for item in workset["adjudication"]] == [
        "alpha",
        "beta",
        "gamma",
        "alpha",
        "beta",
        "gamma",
        "alpha",
        "beta",
    ]
    assert len({item["source_id"] for item in workset["adjudication"]}) == 3


def test_inventory_write_records_history_and_preserves_corrupt_history(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    history_path = paths.data("manifests") / "bucket-history.json"
    build_inventory_ledger(paths, write=False)
    assert not history_path.exists()
    ledger = build_inventory_ledger(paths)
    assert read_json(history_path)["entries"][-1]["at"] == ledger["generated_at"]
    history_path.write_text("{", encoding="utf-8")
    with pytest.warns(RuntimeWarning, match="Could not record private bucket history"):
        build_inventory_ledger(paths)
    assert history_path.read_text(encoding="utf-8") == "{"


def test_inventory_recognizes_adjudicated_citations(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    video = write_demo_video(paths.data("normalized"))
    write_json(paths.data("manifests") / "discovered-test.json", {
        "source_id": "source-one", "videos": [{"id": video.id}],
    })
    write_json(paths.data("derived") / f"{video.id}.candidates.json", {})
    segment = video.transcript.segments[0]
    concept = Concept(
        id="concept-test", slug="test", label="Test", short_definition="Test",
        concept_type="technique", evidence=[{
            "id": "evidence-test", "evidence_type": "explanation", "excerpt": "Test",
            "reason": "Test", "confidence": 0.9,
            "source": {"video_id": video.id, "start_ms": segment.start_ms,
                       "end_ms": segment.end_ms, "url": video.canonical_url,
                       "segment_ids": [segment.id]},
        }],
    )
    item = {"video_id": video.id, "decision": "accepted", "canonical_concept_id": concept.id,
            "candidate": {"evidence": [{"segment_ids": ["original:00001"]}]},
            "adjudicated_segment_ids": [segment.id]}
    with (paths.content / "annotations" / "review-queue.yaml").open("w", encoding="utf-8") as handle:
        YAML().dump({"items": [item]}, handle)
    corpus = PublishCorpus(knowledge_base={"id": paths.id}, concepts=[concept], videos=[video])
    ledger = build_inventory_ledger(paths, corpus, write=False)
    assert ledger["videos"][0]["candidate_counts"]["accepted_unincorporated"] == 0
    assert ledger["videos"][0]["completion_state"] == "complete"


def test_worksets_prioritize_unattempted_and_rotate_away_from_retries() -> None:
    videos = [
        {
            "video_id": f"{source}-{index}",
            "source_ids": [source],
            "view_count": 1000 - index,
            "completion_state": "needs_adjudication",
            "adjudication_history": {
                "pending": 1 if index == 2 else 0,
                "attempts": 0 if index == 2 else index + 1,
                "last_attempt_at": None if index == 2 else f"2026-08-{10 + index:02d}T00:00:00+00:00",
            },
        }
        for source in ("alpha", "beta")
        for index in range(3)
    ]

    workset = select_ledger_worksets({"videos": videos}, 0, adjudication_limit=4)

    assert [item["id"] for item in workset["adjudication"]] == [
        "alpha-2",
        "beta-2",
        "alpha-0",
        "beta-0",
    ]
