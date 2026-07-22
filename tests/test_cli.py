from datetime import UTC, datetime, timedelta

from processors.cli import block_cooldown_remaining, retry_window_remaining


def test_retry_window_reports_active_cooldown() -> None:
    now = datetime(2026, 7, 15, tzinfo=UTC)
    remaining = retry_window_remaining(
        {"next_retry_at": (now + timedelta(hours=6)).isoformat()}, now
    )

    assert remaining == timedelta(hours=6)


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
