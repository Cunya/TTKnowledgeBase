from datetime import UTC, datetime
from pathlib import Path

from ruamel.yaml import YAML

from processors.inventory import (
    build_inventory_ledger,
    load_inventory_catalog,
    select_ledger_worksets,
)
from processors.utils import write_json
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
        {"id": "zyxwvutsrqp", "reason": "eligibility or transcript acquisition is due"}
    ]
