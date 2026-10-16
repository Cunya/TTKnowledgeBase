import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import processors.cli as cli_module
from processors.cli import (
    adjudication_progress_position,
    block_cooldown_remaining,
    print_adjudication_progress,
    retry_window_remaining,
)
from processors.workspace import KnowledgeBasePaths


def test_retry_window_reports_active_cooldown() -> None:
    now = datetime(2026, 7, 15, tzinfo=UTC)
    remaining = retry_window_remaining(
        {"next_retry_at": (now + timedelta(hours=6)).isoformat()}, now
    )

    assert remaining == timedelta(hours=6)


def test_validate_include_demo_with_review_queue(tmp_path: Path, monkeypatch) -> None:
    paths = KnowledgeBasePaths(tmp_path, "test-kb", "Test", "Test")
    annotations = paths.content / "annotations"
    annotations.mkdir(parents=True)
    (annotations / "review-queue.yaml").write_text("items: []\n", encoding="utf-8")
    monkeypatch.setattr(cli_module, "kb_paths", lambda _kb: paths)
    cli_module.validate("test-kb", include_demo=True)


def test_retry_window_allows_expired_or_invalid_entries() -> None:
    now = datetime(2026, 7, 15, tzinfo=UTC)

    assert retry_window_remaining({"next_retry_at": (now - timedelta(seconds=1)).isoformat()}, now) is None
    assert retry_window_remaining({"next_retry_at": "not-a-date"}, now) is None
    assert retry_window_remaining({}, now) is None


def test_block_cooldown_is_route_wide_and_uses_longest_active_window() -> None:
    now = datetime(2026, 7, 15, tzinfo=UTC)
    state = {
        "items": {
            "one": {"blocked": True, "next_retry_at": (now + timedelta(hours=2)).isoformat()},
            "two": {"blocked": True, "next_retry_at": (now + timedelta(hours=6)).isoformat()},
            "members": {"blocked": False, "next_retry_at": (now + timedelta(hours=24)).isoformat()},
        }
    }
    assert block_cooldown_remaining(state, now) == timedelta(hours=6)


def test_adjudication_progress_keeps_selected_set_total() -> None:
    assert adjudication_progress_position(
        {
            "index": 3,
            "total": 10,
            "backlog_total": 405,
            "backlog_remaining": 402,
            "full_backlog_total": 5893,
            "full_backlog_remaining": 5890,
        }
    ) == "3/10 selected this pass (eligible in selected videos: 405; full adjudication backlog: 5890/5893)"


def test_adjudication_heartbeat_names_the_video(capsys) -> None:
    print_adjudication_progress(
        {
            "event": "candidate_heartbeat",
            "index": 2,
            "total": 10,
            "backlog_total": 405,
            "backlog_remaining": 403,
            "video_id": "video-123",
            "candidate_id": "concept-serve",
            "elapsed_seconds": 30,
        }
    )

    output = capsys.readouterr().out
    assert "video video-123" in output
    assert "configured language model" in output
    assert "video=unknown" not in output


def test_non_blocking_video_errors_do_not_trigger_route_wide_stop() -> None:
    now = datetime(2026, 7, 15, tzinfo=UTC)
    state = {
        "items": {
            "unavailable": {
                "blocked": False,
                "error_type": "VideoUnavailableError",
                "next_retry_at": (now + timedelta(hours=6)).isoformat(),
            },
            "members": {
                "blocked": False,
                "classification": "members_only",
                "next_retry_at": (now + timedelta(days=3)).isoformat(),
            },
        }
    }
    assert block_cooldown_remaining(state, now) is None


def test_ingest_rejects_invalid_url_before_network_access() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "processors.cli", "ingest", "not-a-youtube-url", "--kb", "table-tennis"],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Could not determine a YouTube video ID" in result.stderr
