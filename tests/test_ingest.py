import pytest

from processors.ingest import discover_videos, transcript_from_caption, video_id_from_url


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=4", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ],
)
def test_video_id_from_url(value: str, expected: str) -> None:
    assert video_id_from_url(value) == expected


def test_invalid_video_url() -> None:
    with pytest.raises(ValueError):
        video_id_from_url("https://example.com/nope")


def test_discover_videos_prioritizes_view_count(monkeypatch) -> None:
    class FakeYoutubeDL:
        def __init__(self, options):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def extract_info(self, url, download=False):
            return {
                "entries": [
                    {"id": "low", "title": "Low", "view_count": 10},
                    {"id": "unknown", "title": "Unknown"},
                    {"id": "high", "title": "High", "view_count": 100},
                ]
            }

    monkeypatch.setattr("processors.ingest.yt_dlp.YoutubeDL", FakeYoutubeDL)
    assert [item["id"] for item in discover_videos("https://example.com/channel")] == [
        "high",
        "low",
        "unknown",
    ]


def test_supplied_vtt_is_normalized(tmp_path) -> None:
    caption = tmp_path / "lesson.vtt"
    caption.write_text(
        "WEBVTT\n\n00:00:01.000 --> 00:00:03.500\n  Start below the ball.  \n",
        encoding="utf-8",
    )

    track = transcript_from_caption(caption, "dQw4w9WgXcQ", "en", "supplied-caption")

    assert track.acquisition_method == "supplied-caption"
    assert track.segments[0].id == "dQw4w9WgXcQ:00000"
    assert track.segments[0].start_ms == 1000
    assert track.segments[0].duration_ms == 2500
    assert track.segments[0].normalized_text == "Start below the ball."


def test_supplied_srt_is_normalized(tmp_path) -> None:
    caption = tmp_path / "lesson.srt"
    caption.write_text(
        "1\n00:00:02,000 --> 00:00:04,000\nBrush forward and upward.\n",
        encoding="utf-8",
    )

    track = transcript_from_caption(caption, "dQw4w9WgXcQ", "en", "supplied-caption")

    assert track.segments[0].start_ms == 2000
    assert track.segments[0].duration_ms == 2000
