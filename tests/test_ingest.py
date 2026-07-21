import pytest

from processors.ingest import (
    IngestOptions,
    MembersOnlyError,
    discover_videos,
    ingest_media_asr,
    is_members_only_error,
    transcript_from_caption,
    video_id_from_url,
)
from processors.models import Segment, TranscriptTrack


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


@pytest.mark.parametrize(
    "message",
    [
        "Join this channel to get access to members-only content",
        "This video is only available to members",
    ],
)
def test_members_only_errors_are_classified(message: str) -> None:
    assert is_members_only_error(RuntimeError(message))


def test_members_only_error_is_distinct() -> None:
    error = MembersOnlyError("members-only video")
    assert isinstance(error, RuntimeError)


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


def test_media_asr_retains_artifacts_and_marks_local_origin(tmp_path, monkeypatch) -> None:
    video_id = "dQw4w9WgXcQ"
    video_path = tmp_path / "media" / video_id / "video.mp4"

    def fake_download(url, media_dir, options):
        media_dir.mkdir(parents=True)
        video_path.write_bytes(b"video-bytes")
        return video_path, {
            "id": video_id,
            "title": "ASR smoke test",
            "duration": 4,
            "channel_id": "channel",
            "channel": "Channel",
        }

    def fake_audio(video, audio):
        audio.write_bytes(b"audio-bytes")
        return {"sample_rate": 16000, "channels": 1, "codec": "pcm_s16le"}

    def fake_transcribe(audio, current_video_id, language, options):
        return TranscriptTrack(
            video_id=current_video_id,
            language=language,
            language_code=language,
            is_generated=True,
            acquisition_method="faster-whisper:tiny",
            transcript_origin="local_asr",
            segments=[
                Segment(
                    id=f"{current_video_id}:asr:00000",
                    video_id=current_video_id,
                    text="Start below the ball.",
                    normalized_text="Start below the ball.",
                    start_ms=1000,
                    duration_ms=1500,
                )
            ],
        )

    monkeypatch.setattr("processors.ingest._download_media_video", fake_download)
    monkeypatch.setattr("processors.ingest._extract_asr_audio", fake_audio)
    monkeypatch.setattr("processors.ingest.transcribe_authorized_audio_file", fake_transcribe)

    result = ingest_media_asr(
        f"https://www.youtube.com/watch?v={video_id}",
        tmp_path / "normalized",
        tmp_path / "media",
        tmp_path / "manifests",
        ["en"],
        IngestOptions(allow_video_download=True),
    )

    assert result.video.transcript.transcript_origin == "local_asr"
    assert result.video.transcript.segments[0].id == f"{video_id}:asr:00000"
    assert video_path.exists()
    assert (video_path.parent / "audio.wav").exists()
    assert (video_path.parent / "asr.vtt").exists()
    assert result.manifest["retained_media"] is True
    assert result.manifest["transcript_origin"] == "local_asr"
