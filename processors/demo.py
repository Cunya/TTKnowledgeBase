from __future__ import annotations

from pathlib import Path

from .models import Segment, TranscriptTrack, Video
from .utils import write_json

DEMO_VIDEO_ID = "demoTT00001"


def write_demo_video(output_dir: Path) -> Video:
    video_id = DEMO_VIDEO_ID
    segments = [
        Segment(
            id=f"{video_id}:00000",
            video_id=video_id,
            text="Start in a balanced ready position.",
            normalized_text="Start in a balanced ready position.",
            start_ms=12000,
            duration_ms=4200,
        ),
        Segment(
            id=f"{video_id}:00001",
            video_id=video_id,
            text="Keep your knees bent and your weight on the front of your feet.",
            normalized_text="Keep your knees bent and your weight on the front of your feet.",
            start_ms=16200,
            duration_ms=5800,
        ),
        Segment(
            id=f"{video_id}:00002",
            video_id=video_id,
            text="Return to this position after every stroke.",
            normalized_text="Return to this position after every stroke.",
            start_ms=22000,
            duration_ms=4300,
        ),
        Segment(
            id=f"{video_id}:00003",
            video_id=video_id,
            text="For the forehand loop, brush the upper back of the ball and accelerate forward and up.",
            normalized_text="For the forehand loop, brush the upper back of the ball and accelerate forward and up.",
            start_ms=41000,
            duration_ms=7200,
        ),
        Segment(
            id=f"{video_id}:00004",
            video_id=video_id,
            text="Contact the ball in front of your body near the top of the bounce.",
            normalized_text="Contact the ball in front of your body near the top of the bounce.",
            start_ms=48200,
            duration_ms=6100,
        ),
        Segment(
            id=f"{video_id}:00005",
            video_id=video_id,
            text="If contact is late, the stroke loses space and consistency.",
            normalized_text="If contact is late, the stroke loses space and consistency.",
            start_ms=54300,
            duration_ms=5100,
        ),
    ]
    video = Video(
        id=video_id,
        title="Table Tennis Fundamentals: Ready Position and Forehand Loop",
        canonical_url=f"https://www.youtube.com/watch?v={video_id}",
        channel_id="demo-channel",
        channel_name="Demonstration Coach",
        duration_ms=90000,
        thumbnail_url="https://i.ytimg.com/vi/demoTT00001/hqdefault.jpg",
        language="en",
        availability="demo_fixture",
        transcript=TranscriptTrack(
            video_id=video_id,
            language="English",
            language_code="en",
            is_generated=False,
            acquisition_method="fixture",
            segments=segments,
        ),
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / f"{video_id}.json", video)
    return video
