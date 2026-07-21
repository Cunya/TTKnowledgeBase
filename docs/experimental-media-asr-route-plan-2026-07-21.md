# Experimental media download and ASR route

Status: implemented smoke test, local-only experiment
Scope: optional per-video processing for authorized source material

## Purpose

Add a separate acquisition route for videos whose captions are missing, incomplete, poorly timed, or worth independently verifying. The route downloads a local video, extracts audio locally, generates timed subtitles with automatic speech recognition (ASR), and sends the resulting normalized transcript through the existing candidate and review pipeline. For the initial implementation, the downloaded video is retained in the private ignored media workspace; cleanup and deletion controls are a later phase.

This is an alternate input, not a replacement for the normal caption-first path. It must never run automatically during ordinary `cp` processing and must never place video, audio, raw ASR output, or downloaded media in the public artifact.

## Hard boundaries

- Record the source URL, operator, time, retained-media state, and allowed media actions in a private manifest before downloading.
- Do not defeat authentication, DRM, geographic restrictions, rate limits, or platform blocks. Cookies and proxy settings remain operator-supplied and private.
- Keep media under the ignored `media/<kb>/<video-id>/` workspace, never under `data/publish/` or `app/public/`.
- Use a bounded storage estimate, duration/file-size limits, a per-run video cap, and paced requests. Do not delete the downloaded video in the initial implementation; cleanup previews, retention selection, and safe deletion are deferred follow-up features.
- Preserve the public boundary: publish only reviewed authored summaries, short evidence, source links, timestamps, and standard embeds.

## Proposed route

1. **Select and authorize**
   - Accept explicit video URLs or a reviewed configured workset; do not expand a whole channel implicitly.
   - Show the estimated storage and expected network volume before starting.

2. **Acquire and retain video**
   - Use the existing paced downloader adapter with a media-specific timeout and bounded retries.
   - Save source metadata, exact URL, format, duration, byte count, checksum, and downloader provenance beside the temporary file.
   - Fail closed when the requested format, duration, or size is not acceptable.

3. **Extract audio**
   - Use a pinned `ffmpeg` invocation to produce a temporary mono, speech-oriented PCM stream while retaining the original video for timestamp verification.
   - Record the media and audio checksums, sample rate, channel layout, extraction command version, and duration drift.
   - Retain the extracted audio alongside the video for the initial experiment. Audio deletion is part of the deferred cleanup feature set.

4. **Generate ASR subtitles**
   - Run a locally installed, pinned ASR engine such as `faster-whisper` with a configured model, language, VAD, and word-timestamp setting.
   - Write private WebVTT plus structured JSON containing segment IDs, start/end milliseconds, recognized text, model/version, language, decoding options, and per-segment confidence where available.
   - Use a distinct provenance namespace, for example `VIDEO_ID:asr:00042`, so ASR segments cannot be confused with creator captions or YouTube captions.
   - Mark locally generated subtitles explicitly as `transcript_origin: local_asr` (and retain the ASR model/provenance). Do not rely on a generic `is_generated` flag alone: downloaded YouTube automatic captions should be represented as `transcript_origin: youtube_generated`, while downloaded/manual captions use `youtube_manual` (and supplied files use `supplied`).

5. **Normalize and compare**
   - Feed the ASR VTT through the same normalization and boundary machinery as ordinary captions.
   - If another caption source exists, align both streams by time and produce a private comparison report: coverage, duration drift, token/word disagreement, numbers/names/spin terms, and low-confidence spans.
   - Treat disagreement as a review signal, not as automatic evidence that ASR or captions are correct. Build a small manually checked gold set for each language/model.

6. **Extract and review**
   - Run Codex extraction against the selected transcript source and record the transcript-origin hash in candidate provenance.
   - Allow ASR to discover candidate concepts and moments, including for videos with no captions, but keep all new evidence pending until a reviewer checks the source interval.
   - For an approved ASR-backed evidence item, record transcript origin and ASR review state (`unreviewed`, `spot_checked`, or `reviewed`) and require the cited ASR segment IDs to validate against the private normalized transcript.
   - Manual review must verify important names, numbers, spin labels, negations, and boundaries against the downloaded audio/video. Transcript confidence alone is not approval.

7. **Clean up**
   - Keep the downloaded video and its provenance manifest for the initial experiment so reviewers can inspect the complete source locally.
   - Later add a manifest-owned cleanup preview listing video, audio, VTT, JSON, comparison reports, and disk usage, followed by explicit operator-controlled deletion or retention actions for both video and audio.
   - Preserve failed-run diagnostics and never infer deletion from process completion or failure.

## Implemented smoke-test data model and CLI

- Added `transcript_origin` to normalized transcript metadata with an explicit origin enum (`supplied`, `youtube_manual`, `youtube_generated`, `local_asr`) so local ASR is distinguishable from subtitles downloaded from YouTube.
- The smoke test records ASR model, language, source hashes, retained-media paths, and provenance in a private per-video manifest. Review-state enforcement and caption comparison remain later phases.
- Add an explicit route rather than overloading the current caption fallback, for example:

  ```powershell
  python -m processors.cli ingest-media-asr --kb table-tennis `
    --allow-video-download `
    --whisper-model small VIDEO_URL
  ```

- Keep ordinary `ingest` unchanged. A separate command or explicit `--transcript-source asr` is safer than silently replacing available captions.
- Added `--dry-run`, `--max-video-bytes`, and `--max-duration` controls. Defer `--cleanup-preview`, deletion, and retention/expiry controls until after the initial retained-media experiment.
- Extend validation so ASR-backed citations require valid ASR segment IDs, a matching normalized input hash, a recorded model/provenance record, and the required review state.

## Experimental evaluation

Start with one authorized video as a smoke test. Verify download retention, audio extraction, ASR subtitle generation, explicit `local_asr` provenance, and private/public boundary handling before expanding to a 10–20-video gold set spanning clear speech, music/noise, multiple speakers, long lessons, missing captions, and known caption errors. Measure:

- transcript word error rate on a manually transcribed sample;
- timestamp drift and meaningful boundary coverage;
- recognition of table-tennis terms, names, numbers, negations, and spin labels;
- candidate citation validity and reviewer correction rate;
- extraction quality versus the caption path on videos with both sources;
- network time, CPU/GPU time, disk usage, failure/retry rate, and retained-media inventory; evaluate cleanup success after cleanup controls exist.

The route should remain experimental until it improves verified transcript usefulness without creating unacceptable acquisition, rights, storage, or review cost. A better WER alone is insufficient if boundaries or technical terminology remain unreliable.

## Rollout gates

1. Implement a dry-run manifest and storage gate.
2. Implement media acquisition with retained private video and no publishing integration.
3. Add audio extraction and pinned ASR output with provenance.
4. Run a one-video smoke test, then the gold-set comparison and reviewer dashboard locally.
5. Permit ASR-backed candidates, but not automatic canonical promotion.
6. After the evaluation, make a deliberate decision about limited production use; do not enable it in the monitor or scheduler by default.

## Acceptance criteria

- The normal caption path remains unchanged and cache-first.
- No media or raw ASR transcript reaches Git, `data/publish/`, `app/public/`, or GitHub Pages.
- Every download has a bounded resource policy, provenance, and an explicit retained-media state. Cleanup outcome is deferred until cleanup controls are implemented.
- ASR-only videos can enter extraction with stable private segment IDs and can be reviewed without inventing timestamps.
- ASR-backed evidence cannot become approved or public without the required transcript and boundary review.
- A reproducible experiment report compares ASR with available captions and records a go/no-go decision.
