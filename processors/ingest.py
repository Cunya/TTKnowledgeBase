from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from importlib.util import find_spec
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import srt
import truststore
import webvtt
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig, WebshareProxyConfig

from .models import Segment, TranscriptOrigin, TranscriptTrack, Video
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
    allow_video_download: bool = False
    rights_confirmed: bool = False
    whisper_model: str = "small"


@dataclass(frozen=True)
class MediaAsrResult:
    video: Video
    manifest: dict


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
        transcript_origin=("youtube_generated" if transcript.is_generated else "youtube_manual"),
        segments=segments,
    )


def transcript_from_caption(
    path: Path,
    video_id: str,
    language: str,
    method: str,
    transcript_origin: TranscriptOrigin | None = None,
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
        transcript_origin=transcript_origin or (
            "supplied" if method == "supplied-caption" else "youtube_manual"
        ),
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
        # yt-dlp does not expose the selected track type in the filename. The
        # normalized origin is therefore conservative until the media-ASR
        # route adds a track-selection manifest of its own.
        return transcript_from_caption(files[0], video_id, language, "yt-dlp-subtitles")


def transcribe_authorized_audio(
    url: str, video_id: str, language: str, options: IngestOptions
) -> TranscriptTrack:
    if not options.allow_audio_download or not options.rights_confirmed:
        raise PermissionError(
            "Local transcription requires --allow-audio-download and --confirm-rights"
        )
    if find_spec("faster_whisper") is None:
        raise RuntimeError(
            'Install the optional ASR dependencies with pip install -e ".[asr]"'
        )
    with tempfile.TemporaryDirectory(prefix="ytkb-audio-") as directory:
        template = str(Path(directory) / "%(id)s.%(ext)s")
        settings = _ydl_options(options)
        settings.update({"format": "bestaudio/best", "outtmpl": template})
        with yt_dlp.YoutubeDL(settings) as ydl:
            info = ydl.extract_info(url, download=True)
            audio_path = Path(ydl.prepare_filename(info))
        return transcribe_authorized_audio_file(audio_path, video_id, language, options)


def transcribe_authorized_audio_file(
    audio_path: Path, video_id: str, language: str, options: IngestOptions
) -> TranscriptTrack:
    if find_spec("faster_whisper") is None:
        raise RuntimeError(
            'Install the optional ASR dependencies with pip install -e ".[asr]"'
        )
    from faster_whisper import WhisperModel

    # Keep the smoke test portable on machines without the CUDA runtime. A
    # later benchmark can add an explicit device/profile choice.
    model = WhisperModel(options.whisper_model, device="cpu", compute_type="int8")
    generated, info = model.transcribe(str(audio_path), language=language)
    segments = []
    for index, item in enumerate(generated):
        text = normalize_text(item.text)
        if text:
            segments.append(
                Segment(
                    id=f"{video_id}:asr:{index:05d}",
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
        transcript_origin="local_asr",
        segments=segments,
    )


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _write_asr_vtt(path: Path, segments: list[Segment]) -> None:
    def timestamp(milliseconds: int) -> str:
        hours, remainder = divmod(milliseconds, 3_600_000)
        minutes, remainder = divmod(remainder, 60_000)
        seconds, milliseconds = divmod(remainder, 1_000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

    lines = ["WEBVTT", ""]
    for segment in segments:
        lines.extend(
            [
                segment.id,
                f"{timestamp(segment.start_ms)} --> {timestamp(segment.end_ms)}",
                segment.text.replace("\n", " "),
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def _download_media_video(
    url: str, media_dir: Path, options: IngestOptions
) -> tuple[Path, dict]:
    media_dir.mkdir(parents=True, exist_ok=True)
    settings = _ydl_options(options)
    settings.update(
        {
            "format": "best[ext=mp4]/best",
            "outtmpl": str(media_dir / "video.%(ext)s"),
            "noplaylist": True,
        }
    )
    with yt_dlp.YoutubeDL(settings) as ydl:
        info = ydl.extract_info(url, download=True)
        prepared = Path(ydl.prepare_filename(info))
    candidates = [prepared, *sorted(media_dir.glob("video.*"))]
    video_path = next((path for path in candidates if path.is_file()), None)
    if video_path is None:
        raise RuntimeError("yt-dlp completed without producing a video file")
    return video_path, info


def _extract_asr_audio(video_path: Path, audio_path: Path) -> dict:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required for the media-ASR smoke test")
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(audio_path),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    return {"command": command, "sample_rate": 16000, "channels": 1, "codec": "pcm_s16le"}


def ingest_media_asr(
    url: str,
    normalized_dir: Path,
    media_root: Path,
    manifest_dir: Path,
    languages: list[str],
    options: IngestOptions,
    *,
    force: bool = False,
    max_video_bytes: int | None = None,
    max_duration_seconds: int | None = None,
) -> MediaAsrResult:
    """Download one private video, retain media, and normalize local ASR output."""
    if not options.allow_video_download:
        raise PermissionError("Media ASR requires --allow-video-download")
    video_id = video_id_from_url(url)
    media_dir = media_root / video_id
    normalized_path = normalized_dir / f"{video_id}.json"
    manifest_path = manifest_dir / f"{video_id}.json"
    if manifest_path.exists() and normalized_path.exists() and not force:
        return MediaAsrResult(
            video=Video.model_validate(read_json(normalized_path)),
            manifest=read_json(manifest_path),
        )

    video_path, metadata = _download_media_video(url, media_dir, options)
    duration_seconds = int(metadata.get("duration") or 0)
    if max_video_bytes is not None and video_path.stat().st_size > max_video_bytes:
        raise ValueError(f"Downloaded video exceeds --max-video-bytes ({max_video_bytes})")
    if max_duration_seconds is not None and duration_seconds > max_duration_seconds:
        raise ValueError(f"Video exceeds --max-duration ({max_duration_seconds}s)")

    audio_path = media_dir / "audio.wav"
    audio_details = _extract_asr_audio(video_path, audio_path)
    try:
        transcript = transcribe_authorized_audio_file(audio_path, video_id, languages[0], options)
    except Exception:
        # Keep both retained artifacts for later operator inspection.
        raise
    vtt_path = media_dir / "asr.vtt"
    json_path = media_dir / "asr.json"
    _write_asr_vtt(vtt_path, transcript.segments)
    source_hash = _sha256_file(video_path)
    audio_hash = _sha256_file(audio_path)
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
    write_json(normalized_path, video)
    write_json(
        json_path,
        {
            "video_id": video_id,
            "transcript_origin": "local_asr",
            "model": options.whisper_model,
            "language": transcript.language_code,
            "segments": [segment.model_dump(mode="json") for segment in transcript.segments],
        },
    )
    manifest = {
        "video_id": video_id,
        "source_url": url,
        "retained_media": True,
        "media_dir": str(media_dir),
        "video_path": str(video_path),
        "audio_path": str(audio_path),
        "subtitle_path": str(vtt_path),
        "asr_json_path": str(json_path),
        "video_sha256": source_hash,
        "audio_sha256": audio_hash,
        "video_bytes": video_path.stat().st_size,
        "duration_ms": video.duration_ms,
        "audio": audio_details,
        "transcript_origin": "local_asr",
        "transcript_provenance": {
            "engine": "faster-whisper",
            "model": options.whisper_model,
            "language": transcript.language_code,
        },
        "created_at": datetime.now(UTC).isoformat(),
    }
    write_json(manifest_path, manifest)
    return MediaAsrResult(video=video, manifest=manifest)


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
