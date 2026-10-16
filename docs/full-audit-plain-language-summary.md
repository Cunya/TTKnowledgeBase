# What the full audit does and why

The full audit checks whether every published article accurately reflects its cited video transcripts. We found that some articles added details the source did not establish, mixed different instructions together, or attached evidence to the wrong topic.

## What we do

For each article, we:

- Check its title, explanation, examples and tags against the exact cited transcript passages.
- Use GPT-6 Luna at high effort to propose corrections and independently check them.
- Review the proposed changes against the sources before applying them. Passing a model check alone is not enough.
- Save progress in small, finite jobs so the audit can resume without starting over.
- Validate the published data and website after each completed batch.

We also keep spoken evidence separate from visual demonstrations. A transcript can support an explanation, but it cannot prove that a movement is visible in a clip. Visual demonstrations need separate footage review before looping can be enabled.

## Why we do it

The aim is to make the knowledge base trustworthy and prevent the same mistakes from returning—not just improve the wording. Each claim should have traceable support, and corrections should preserve the conditions and meaning of the original instruction.

When the source is unclear, we record the problem and leave it unresolved rather than guessing or counting the article as passed.

## Progress checkpoint

As of 16 October 2026 at 19:04 EEST:

- 135 of 377 articles have passed the audit.
- 242 articles still need work.
- Normal content processing remains paused.
- Unclear source claims and unreviewed footage remain unresolved.

These numbers are a dated checkpoint. See the [project backlog](prioritized-backlog-2026-07-15.md) and [current session checkpoint](Session%20Logs/2026-10-16-19.md) for the recorded status and evidence.

