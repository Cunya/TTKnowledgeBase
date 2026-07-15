from datetime import UTC, datetime, timedelta

from processors.cli import retry_window_remaining


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
