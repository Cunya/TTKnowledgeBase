# ASR-assisted audio boundary verification — 2026-07-21

## Decision

Use local ASR as a private audio-timing signal for boundary review, not as a replacement transcript or source of public citations.

The reviewed caption segment IDs remain authoritative for claim support. ASR may propose or validate playback boundaries around those segments, especially when captions begin or end mid-sentence.

## Proposed workflow

1. Select flagged boundary cases from `report-boundaries` (`starts_mid_sentence`, `ends_mid_sentence`, `too_short`, and `needs_context`) plus a small clean control sample.
2. Run the retained-media ASR route with word timestamps and confidence values. Keep the ASR transcript, word alignment, and assessment manifest private.
3. Align normalized caption text to nearby ASR words using time-constrained token matching. Record the first/last aligned word, leading/trailing speech padding, pauses, and confidence.
4. Classify the result as an audio-boundary issue, a caption segmentation issue, a likely topic/context transition, or inconclusive. Low ASR confidence, overlap, music, or disagreement defers the item.
5. Let a reviewer choose `keep`, `merge`, `split`, or `defer`. A reviewed result may update playback context or the cited segment set; ASR timestamps alone never update canonical evidence.

## Guardrails

- Do not publish ASR text, word timings, confidence data, or downloaded media.
- Do not use ASR wording as independent evidence for a knowledge claim.
- Do not widen a claim merely because speech continues; a continued voice may introduce a new topic.
- Keep the existing 30-second evidence limit and segment provenance checks.
- Calibrate thresholds on a reviewed gold set before using automatic proposals. Start with the existing boundary worksheet rather than the whole corpus.

## Expected value

For the one-video ASR test, local ASR tracked the YouTube captions closely enough to support boundary triage: approximately 3% word-level disagreement, near-identical total coverage, and useful word-level timing potential. YouTube captions remain preferable for citation text and segment identity; ASR adds an independent audio-onset/audio-offset check.
