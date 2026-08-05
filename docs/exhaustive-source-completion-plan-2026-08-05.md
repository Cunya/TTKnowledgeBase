# Exhaustive source-completion plan — 2026-08-05

## Objective

Completely process every eligible video in the current three-source inventory:

- TT SpinMaster channel: 325 discovered entries.
- GlobalTTStudio channel: 418 discovered entries.
- PingSunday / coach XiaoHan playlist: 95 discovered entries.
- Current total: 838 discovered entries.

An eligible video is public, not members-only, and has a usable source-caption track under the KB language policy. The plan does not expand the PingSunday scope beyond the configured 95-video playlist.

## Corrected current-state model

The 148 video entries in `config/kbs/table-tennis/sources.yaml` are not a user-selected current workset. They accumulated during early project-generated controlled batches. `scripts/run-cp.py` first drains cached work and configured entries that still need acquisition, then automatically continues through unseen discovery-catalog entries ordered by view count where available. Continuation videos are processed without being appended to `sources.yaml`.

Therefore:

- `sources.yaml` video entries are configured batch history and provenance.
- Discovery manifests are the source inventory.
- `cp.latest.json` records the actual work selected for a run.
- Normalized, derived, review-queue, canonical, and published artifacts record stage completion.
- No existing artifact provides one durable per-video eligibility and completion ledger across all 838 entries.

The current snapshot has 729 videos on the site. All 589 published videos outside `sources.yaml` are normalized and extracted; 93 have every candidate decided, while 496 still have deferred candidates. The remaining 109 known videos consist of 8 members-only entries and 101 entries that are not on the site, but those 101 do not yet have a complete durable eligibility classification.

## Revised implementation approach

### 1. Build a durable full-inventory ledger

Add a private generated ledger keyed by video ID and source ID. Derive it from discovery manifests, source policy, retry state, normalized transcripts, candidate artifacts, the review queue, canonical concepts, and the sanitized corpus.

Record at least:

- inventory provenance and discovery timestamp;
- availability: `public`, `members_only`, `unavailable`, `unknown`, or retryable failure;
- caption eligibility, available source tracks, and selected language;
- normalized and extraction status;
- candidate counts by decision;
- canonical incorporation and public-moment counts;
- retry deadline and failure classification;
- completion state and reason;
- whether explicit human review is required.

Do not duplicate raw transcripts, credentials, cookies, or Codex audit output in this ledger.

### 2. Generate run worksets from incomplete eligible states

Refactor `run-cp.py` to use the ledger rather than treating `sources.yaml` membership as the primary workset boundary. Preserve the existing cache-first order, lock, cooldowns, pacing, LLM budget, and route-wide block circuit breaker.

The run priority should be:

1. normalized videos missing current candidate artifacts;
2. extracted videos with retryable automated review work;
3. discovered videos with confirmed or unknown eligibility that still need acquisition;
4. bounded retry probes whose deadlines have arrived;
5. no work when every eligible video is complete or assigned to human review.

View count may order otherwise-equal acquisition candidates, but it must not decide whether an eligible video is eventually processed. Write the exact selected IDs and reasons to the private run manifest before each mutating stage.

### 3. Define strict video completion

An eligible video is complete only when:

- a normalized timed transcript exists using an allowed source-caption language;
- a current schema-validated candidate artifact exists;
- every candidate is accepted, rejected, or explicitly assigned to human review;
- every accepted candidate is incorporated into tracked canonical YAML with valid segment IDs and timestamps;
- deterministic validation and sanitized publication succeed;
- proposed visual windows remain honestly separate from spoken evidence.

Ordinary `pending` and generic `deferred` decisions are incomplete states. Introduce an explicit human-review classification so genuine ambiguity is not confused with retryable automated backlog.

### 4. Drain the existing deferred backlog automatically

Extend the existing `process-pending --retry-deferred` route into an auditable adjudication pass:

- accept only source-grounded, validated matches or defensible new concepts;
- reject unsupported, duplicate, invalid, or non-durable proposals;
- send taxonomy ambiguity, conflicting evidence, uncertain merges, and boundary/context uncertainty to human review;
- never invent source metadata or mark inferred visuals as verified;
- record the adjudication method and reason;
- stop retrying an unchanged ambiguous item automatically after the configured adjudication attempt limit.

Start with the 496 published continuation videos that still contain deferred candidates, then drain deferred work from configured batch-history entries.

### 5. Audit the 101 known videos not currently on the site

Process these through bounded, paced eligibility checks. For each video, record one durable outcome:

- eligible and queued;
- members-only;
- public but no usable source subtitles;
- unavailable or removed;
- temporarily blocked with a retry deadline;
- human decision required for an exceptional policy case.

Do not treat a failed network request as proof that subtitles are absent, and do not repeatedly retry known members-only videos during ordinary processing cycles.

### 6. Correct progress and monitor reporting

Keep the public-content summary simple: known videos, on-site videos, and not-on-site videos. In operator detail, show:

- full inventory eligibility classification;
- complete eligible videos;
- automated work remaining by stage;
- human-review videos and candidate counts;
- retry/cooldown and permanent-exclusion counts;
- the actual current or latest run workset from `cp.latest.json`;
- configured batch history only as provenance, never as the live workset.

### 7. Preserve safety boundaries

- Keep transcript acquisition sequential, bounded, and cache-first.
- Stop acquisition on a route-wide block and retain exact retry deadlines.
- Keep the configured model and budget profile unless an explicit policy change is recorded.
- Publish only validated canonical YAML and sanitized artifacts.
- Keep visual verification human-reviewed unless the complete selected interval has actually been watched.
- Never place private transcripts, media, retry state, or LLM audit data in public output.

## Definition of done

The exhaustive pass is complete when:

- all 838 inventory entries have a durable eligibility result;
- every eligible video satisfies the strict completion definition or is explicitly assigned to human review;
- no eligible video remains in ordinary pending, generic deferred, or unclassified state;
- all permanent exclusions have a specific reason;
- the progress page and monitor derive counts from the full-inventory ledger and latest run manifest;
- validation, publication validation, tests, Ruff, Astro diagnostics, and the static build pass while the monitor is idle for the release gate.

## Implementation order

1. Ledger schema, deterministic builder, and tests.
2. Full-inventory eligibility reporting without changing acquisition behavior.
3. Ledger-driven run-workset selection and manifest reasons.
4. Explicit human-review state and bounded deferred adjudication.
5. Eligibility audit of the 101 non-public entries.
6. Progress/monitor integration and full release verification.

## Implemented state â€” 2026-08-05

The architecture in steps 1â€“6 is implemented. The private ledger resolves exactly 838 valid video IDs, rejects malformed channel placeholders, persists eligibility and completion reasons, and drives exact per-run worksets. Candidate adjudication is bounded to 50 selected videos per cycle, records method/reason/attempt metadata, rejects candidates with invalid source spans, and sends unchanged ambiguity to explicit human review after two attempts. Progress and monitor views now use ledger summaries and the latest recorded workset.

The initial full-ledger audit corrected the earlier configuration-derived exclusion model. The 109 videos without public moments are currently 23 normalized/processed videos with no approved moments, 85 members-only videos, and one public video repeatedly reported as having subtitles disabled. The automated review backlog remains intentionally in progress and will drain through monitor cycles; implementation completion does not mean the corpus-wide adjudication run has already finished.
