from datetime import UTC, datetime, timedelta
from pathlib import Path

from processors.bucket_history import HISTORY_LIMIT, record_bucket_history
from processors.utils import read_json, write_json

NOW = datetime(2026, 10, 12, 10, tzinfo=UTC)


def ledger(at: datetime, accepted: int = 12) -> dict:
    return {
        "generated_at": at.isoformat(),
        "summary": {"states": {"complete": 3, "needs_adjudication": 7}, "candidates": {"accepted": accepted}},
    }


def test_history_records_unchanged_counts_without_a_browser(tmp_path: Path) -> None:
    record_bucket_history(tmp_path, ledger(NOW - timedelta(days=1)), now=NOW - timedelta(days=1))
    record_bucket_history(tmp_path, ledger(NOW), now=NOW)
    entries = read_json(tmp_path / "bucket-history.json")["entries"]
    assert len(entries) == 2
    assert entries[0]["stages"] == entries[1]["stages"]
    assert entries[0]["decisions"] == entries[1]["decisions"]
    assert entries[1]["decisions"]["accepted"] == 12
    assert entries[1]["stages"]["adjudication"] == 7


def test_history_recovers_only_real_latest_manifest_observations(tmp_path: Path) -> None:
    before = ledger(NOW - timedelta(days=1, minutes=5), 10)
    after = ledger(NOW - timedelta(days=1), 11)
    write_json(tmp_path / "cp.latest.json", {
        "started_at": before["generated_at"], "inventory_before": before["summary"],
        "finished_at": after["generated_at"], "inventory_after": after["summary"],
    })
    for _ in range(2):
        record_bucket_history(tmp_path, ledger(NOW), now=NOW)
    entries = read_json(tmp_path / "bucket-history.json")["entries"]
    assert [entry["at"] for entry in entries] == [before["generated_at"], after["generated_at"], NOW.isoformat()]
    assert [entry["decisions"]["accepted"] for entry in entries] == [10, 11, 12]
    assert all(set(entry) == {"at", "stages", "decisions"} for entry in entries)


def test_history_keeps_one_boundary_anchor_and_all_recent_observations(tmp_path: Path) -> None:
    for days in [10, 8, 6, 4, 2, 0]:
        at = NOW - timedelta(days=days)
        record_bucket_history(tmp_path, ledger(at), now=at)
    entries = read_json(tmp_path / "bucket-history.json")["entries"]
    assert [entry["at"] for entry in entries] == [
        (NOW - timedelta(days=days)).isoformat() for days in [8, 6, 4, 2, 0]
    ]


def test_history_cap_preserves_coverage_endpoints(tmp_path: Path) -> None:
    entries = [
        {"at": (NOW - timedelta(minutes=minute)).isoformat(), "stages": {"complete": minute}, "decisions": {}}
        for minute in range(HISTORY_LIMIT + 100)
    ]
    write_json(tmp_path / "bucket-history.json", {"version": 1, "entries": entries})
    record_bucket_history(tmp_path, ledger(NOW), now=NOW)
    retained = read_json(tmp_path / "bucket-history.json")["entries"]
    assert len(retained) == HISTORY_LIMIT
    assert retained[0]["at"] == entries[-1]["at"]
    assert retained[-1]["at"] == NOW.isoformat()
    assert [entry["at"] for entry in retained] == sorted(entry["at"] for entry in retained)


def test_history_ignores_invalid_and_future_observations(tmp_path: Path) -> None:
    write_json(tmp_path / "bucket-history.json", {"entries": [
        {"at": "invalid"},
        {"at": (NOW + timedelta(days=1)).isoformat(), "stages": {}, "decisions": {}},
        {"at": "2026-10-11T00:00:00", "stages": {}, "decisions": {}},
    ]})
    record_bucket_history(tmp_path, ledger(NOW), now=NOW)
    assert len(read_json(tmp_path / "bucket-history.json")["entries"]) == 1
