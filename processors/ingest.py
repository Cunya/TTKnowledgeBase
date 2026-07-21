from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import srt
import truststore
import webvtt
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig, WebshareProxyConfig

from .models import Segment, TranscriptTrack, Video
from .utils import normalize_text, read_json, write_json

truststore.inject_into_ssl()


class TranscriptBlockedError(RuntimeError):
    """Stop a batch when YouTube starts rejecting transcript requests."""


class MembersOnlyError(RuntimeError):
    """The source reports that the requested video is members-only."""


def is_members_only_error(error: BaseException) -> bool:
    message = str(error).lower()
    return any(
        marker in message
        for marker in (
            "members-only",
            "members only",
            "available to channel members",
            "only available to members",
            "join this channel",
            "join the channel",
        )
    )


@dataclass(frozen=True)
class IngestOptions:
    proxy_url: str | None = None
    webshare_username: str | None = None
    webshare_password: str | None = None
    cookie_file: Path | None = None
    js_runtime: str | None = None
    supplied_caption: Path | None = None
    allow_audio_download: bool = False
    rights_confirmed: bool = False
    whisper_model: str = "small"


def video_id_from_url(value: str) -> str:
    if len(value) == 11 and "/" not in value:
        return value
    parsed = urlparse(value)
    if parsed.hostname in {"youtu.be", "www.youtu.be"}:
        return parsed.path.strip("/").split("/")[0]
    if parsed.hostname and "youtube.com" in parsed.hostname:
        if parsed.path == "/watch":
            ids = parse_qs(parsed.query).get("v", [])
            if ids:
                return ids[0]
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2 and parts[0] in {"shorts", "embed", "live"}:
            return parts[1]
    raise ValueError(f"Could not determine a YouTube video ID from: {value}")


def _ydl_options(options: IngestOptions) -> dict:
    result: dict = {"quiet": True, "noplaylist": True}
    if options.proxy_url:
        result["proxy"] = options.proxy_url
    if options.cookie_file:
        result["cookiefile"] = str(options.cookie_file)
    js_runtime = options.js_runtime
    if not js_runtime and shutil.which("node"):
        js_runtime = f"node:{shutil.which('node')}"
    if js_runtime:
        runtime, _, path = js_runtime.partition(":")
        result["js_runtimes"] = {runtime: {"path": path or None}}
    return result


def fetch_metadata(url: str, options: IngestOptions | None = None) -> dict:
    settings = _ydl_options(options or IngestOptions())
    settings.update({"skip_download": True})
    try:
        with yt_dlp.YoutubeDL(settings) as ydl:
            metadata = ydl.sanitize_info(ydl.extract_info(url, download=False))
    except Exception as error:
        if is_members_only_error(error):
            raise MembersOnlyError(str(error)) from error
        raise
    availability = str(metadata.get("availability") or "").lower()
    if availability in {"members_only", "subscriber_only"}:
        raise MembersOnlyError(f"Video availability reported as {availability}")
    return metadata


def discover_videos(url: str) -> list[dict]:
    """Discover video IDs from a channel or playlist without downloading media."""
    options = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": True,
        "ignoreerrors": True,
        "nocheckcertificate": True,
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        result = ydl.extract_info(url, download=False)
    entries = (result or {}).get("entries") or []
    videos = [
        {
            "id": entry.get("id"),
            "title": entry.get("title") or entry.get("id"),
            "url": entry.get("url")
            if str(entry.get("url", "")).startswith("http")
            else f"https://www.youtube.com/watch?v={entry.get('id')}",
            "view_count": entry.get("view_count"),
        }
        for entry in entries
        if entry and entry.get("id")
    ]
    return sorted(
        videos,
        key=lambda video: (
            video["view_count"] is None,
            -(int(video["view_count"]) if video["view_count"] is not None else 0),
        ),
    )


def _proxy_config(options: IngestOptions):
    if options.webshare_username and options.webshare_password:
        return WebshareProxyConfig(options.webshare_username, options.webshare_password)
    if options.proxy_url:
        return GenericProxyConfig(http_url=options.proxy_url, https_url=options.proxy_url)
    return None


def fetch_transcript(
    video_id: str, languages: list[str], options: IngestOptions
) -> TranscriptTrack:
    try:
        api = YouTubeTranscriptApi(proxy_config=_proxy_config(options))
        transcript_list = api.list(video_id)
        transcript = transcript_list.find_transcript(languages)
        fetched = transcript.fetch()
    except Exception as error:
        message = str(error).lower()
        if (
            "blocking requests from your ip" in message
            or "requestblocked" in message
            or "ipblocked" in message
        ):
            raise TranscriptBlockedError(str(error)) from error
        raise
    segments = []
    for index, snippet in enumerate(fetched):
        text = normalize_text(snippet.text)
        if text:
            segments.append(
                Segment(
                    id=f"{video_id}:{index:05d}",
                    video_id=video_id,
                    text=snippet.text,
                    normalized_text=text,
                    start_ms=round(snippet.start * 1000),
                    duration_ms=max(1, round(snippet.duration * 1000)),
                )
            )
    return TranscriptTrack(
        video_id=video_id,
        language=transcript.language,
        language_code=transcript.language_code,
        is_generated=transcript.is_generated,
        acquisition_method="youtube-transcript-api",
        segments=segments,
    )


def transcript_from_caption(
    path: Path, video_id: str, language: str, method: str
) -> TranscriptTrack:
    def vtt_seconds(value: str) -> float:
        parts = value.replace(",", ".").split(":")
        return sum(float(part) * (60**index) for index, part in enumerate(reversed(parts)))

    suffix = path.suffix.lower()
    if suffix == ".srt":
        entries = [
            (item.start.total_seconds(), (item.end - item.start).total_seconds(), item.content)
            for item in srt.parse(path.read_text(encoding="utf-8-sig"))
        ]
    elif suffix in {".vtt", ".webvtt"}:
        entries = [
            (
                vtt_seconds(caption.start),
                vtt_seconds(caption.end) - vtt_seconds(caption.start),
                caption.text,
            )
            for caption in webvtt.read(str(path))
        ]
    else:
        raise ValueError("Supplied captions must use .vtt, .webvtt, or .srt")
    segments = []
    for index, (start, duration, raw_text) in enumerate(entries):
        text = normalize_text(raw_text.replace("\n", " "))
        if text:
            segments.append(
                Segment(
                    id=f"{video_id}:{index:05d}",
                    video_id=video_id,
                    text=raw_text,
                    normalized_text=text,
                    start_ms=round(start * 1000),
                    duration_ms=max(1, round(duration * 1000)),
                )
            )
    if not segments:
        raise ValueError(f"Caption file contains no usable cues: {path}")
    return TranscriptTrack(
        video_id=video_id,
        language=language,
        language_code=language,
        is_generated=False,
        acquisition_method=method,
        segments=segments,
    )


def fetch_yt_dlp_subtitles(
    url: str, video_id: str, languages: list[str], options: IngestOptions
) -> TranscriptTrack:
    with tempfile.TemporaryDirectory(prefix="ytkb-subs-") as directory:
        output = str(Path(directory) / "%(id)s.%(ext)s")
        settings = _ydl_options(options)
        settings.update(
            {
                "skip_download": True,
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": languages,
                "subtitlesformat": "vtt",
                "outtmpl": output,
            }
        )
        with yt_dlp.YoutubeDL(settings) as ydl:
            ydl.download([url])
        files = list(Path(directory).glob(f"{video_id}*.vtt"))
        if not files:
            raise RuntimeError("yt-dlp returned no matching subtitle track")
        language = next((code for code in languages if f".{code}." in files[0].name), languages[0])
        return transcript_from_caption(files[0], video_id, language, "yt-dlp-subtitles")


def transcribe_authorized_audio(
    url: str, video_id: str, language: str, options: IngestOptions
) -> TranscriptTrack:
    if not options.allow_audio_download or not options.rights_confirmed:
        raise PermissionError(
            "Local transcription requires --allow-audio-download and --confirm-rights"
        )
    try:
        from faster_whisper import WhisperModel
    except ImportError as error:
        raise RuntimeError(
            'Install the optional ASR dependencies with pip install -e ".[asr]"'
        ) from error
    with tempfile.TemporaryDirectory(prefix="ytkb-audio-") as directory:
        template = str(Path(directory) / "%(id)s.%(ext)s")
        settings = _ydl_options(options)
        settings.update({"format": "bestaudio/best", "outtmpl": template})
        with yt_dlp.YoutubeDL(settings) as ydl:
            info = ydl.extract_info(url, download=True)
            audio_path = Path(ydl.prepare_filename(info))
        model = WhisperModel(options.whisper_model, device="auto", compute_type="int8")
        generated, info = model.transcribe(str(audio_path), language=language)
        segments = []
        for index, item in enumerate(generated):
            text = normalize_text(item.text)
            if text:
                segments.append(
                    Segment(
                        id=f"{video_id}:{index:05d}",
                        video_id=video_id,
                        text=item.text,
                        normalized_text=text,
                        start_ms=round(item.start * 1000),
                        duration_ms=max(1, round((item.end - item.start) * 1000)),
                    )
                )
        return TranscriptTrack(
            video_id=video_id,
            language=info.language,
            language_code=info.language,
            is_generated=True,
            acquisition_method=f"faster-whisper:{options.whisper_model}",
            segments=segments,
        )


def ingest_video(
    url: str,
    output_dir: Path,
    languages: list[str],
    options: IngestOptions | None = None,
    *,
    force: bool = False,
) -> Video:
    options = options or IngestOptions()
    video_id = video_id_from_url(url)
    cached = output_dir / f"{video_id}.json"
    if cached.exists() and not force:
        return Video.model_validate(read_json(cached))
    metadata = fetch_metadata(url, options)
    if options.supplied_caption:
        transcript = transcript_from_caption(
            options.supplied_caption, video_id, languages[0], "supplied-caption"
        )
    else:
        try:
            transcript = fetch_transcript(video_id, languages, options)
        except Exception as primary_error:
            if is_members_only_error(primary_error):
                raise MembersOnlyError(str(primary_error)) from primary_error
            try:
                transcript = fetch_yt_dlp_subtitles(url, video_id, languages, options)
            except Exception as subtitle_error:
                if is_members_only_error(subtitle_error):
                    raise MembersOnlyError(str(subtitle_error)) from subtitle_error
                if options.allow_audio_download:
                    transcript = transcribe_authorized_audio(url, video_id, languages[0], options)
                else:
                    raise primary_error from None
    duration_seconds = metadata.get("duration") or 0
    video = Video(
        id=video_id,
        title=metadata.get("title") or video_id,
        canonical_url=f"https://www.youtube.com/watch?v={video_id}",
        channel_id=metadata.get("channel_id") or "",
        channel_name=metadata.get("channel") or metadata.get("uploader") or "",
        duration_ms=round(duration_seconds * 1000),
        published_at=metadata.get("upload_date"),
        ingested_at=datetime.now(UTC),
        thumbnail_url=metadata.get("thumbnail"),
        language=transcript.language_code,
        transcript=transcript,
    )
    write_json(cached, video)
    return video
