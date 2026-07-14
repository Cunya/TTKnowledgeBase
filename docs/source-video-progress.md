# Source video progress

Last updated: 2026-07-14 23:54 EEST

This document tracks how far videos from each configured source have progressed through discovery, transcript ingestion, Codex extraction, editorial review, and publication. Counts are derived from the current local processing data and sanitized published corpus.

## Progress-state definitions

| State | Meaning |
|---|---|
| Discovered | Video metadata appeared in a channel discovery manifest. Discovery does not mean the video is relevant or has usable captions. |
| Configured | The video is explicitly listed in `config/kbs/table-tennis/sources.yaml`. |
| Eligible | The configured video is selected and publicly accessible enough for processing. |
| Ingested | A private normalized transcript and video metadata file exist locally. |
| Extracted | A private schema-validated Codex candidate artifact exists locally. |
| Reviewed | Every extracted candidate for the video has an explicit accepted or rejected decision; none remain pending. |
| Published | At least one approved evidence moment from the video appears in the sanitized public corpus. |
| Visual verified | A reviewer watched a selected visual interval and marked it as a verified demonstration. This is separate from transcript review. |

## Source summary

| Source | Trustworthy discovered total | Configured | Eligible | Ingested | Extracted | Fully reviewed | Published | Accepted candidates | Rejected | Evidence moments | Concepts supported | Proposed visuals | Verified visuals |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| TT SpinMaster / `@FreeCoachBradHan` | 304 | 33 | 33 | 33 | 33 | 33 | 33 | 340 | 0 | 879 | 70 | 19 | 0 |
| GlobalTTStudio / `@GlobalTTStudio` | Unknown | 11 | 9 | 9 | 9 | 9 | 9 | 102 | 1 | 231 | 33 | 16 | 0 |
| **Total configured** | — | **44** | **42** | **42** | **42** | **42** | **42** | **442** | **1** | **1,110** | **73 unique overall** | **35** | **0** |

Concept counts overlap across sources: a concept supported by both channels is counted once in each source row, so the source rows must not be added to obtain the 73 unique concepts.

## Funnel interpretation

### TT SpinMaster / Free Coach Brad Han

- Channel catalog captured: 304 videos.
- Configured pilot corpus: 33 videos, or about 10.9% of the captured catalog.
- Configured pipeline completion: 33 of 33 eligible videos are ingested, extracted, fully reviewed, and published.
- Remaining discovered catalog: 271 videos have not been selected for this KB yet.
- Editorial state: all 340 candidates from configured videos are accepted; none are pending or rejected.
- Visual state: 19 proposed nearby visual windows exist, but none has been manually verified. They are non-looping on the public site.

The 271-video remainder is a discovery backlog, not an automatic processing queue. Videos should be selected for missing concepts, second-source support, or visual demonstrations instead of processed only to increase volume.

### GlobalTTStudio

- Trustworthy channel total: unknown. The latest channel discovery attempt returned invalid channel-tab placeholder IDs, so it is not used as a denominator.
- Configured corpus: 11 videos.
- Eligible corpus: 9 videos.
- Pipeline completion: all 9 eligible videos are ingested, extracted, fully reviewed, and published.
- Inaccessible items: 2 configured videos are members-only and remain unprocessed.
- Editorial state: 102 candidates are accepted, 1 is explicitly rejected, and none is pending.
- Visual state: 16 proposed nearby visual windows exist, but none has been manually verified. They are non-looping on the public site.

## Configured video state by source

### TT SpinMaster / Free Coach Brad Han — 33 published

All configured videos below are in the same completed transcript pipeline state: **ingested → extracted → reviewed → published**.

| Video ID | Primary topic indicated by title |
|---|---|
| `BToLYdKLIMM` | Loose grip and backhand spin |
| `3kC8KEl3iow` | Creating space and stance stability |
| `csJgHR7Daog` | Contact zone and serve spin |
| `I99BjizeWeE` | Beginner forehand loop |
| `i68OG8UzMyQ` | Forehand loop fundamentals, episode 1 |
| `dWZw3A0X-4A` | Forehand loop fundamentals, episode 2 |
| `m93pWt9MIZE` | Spin loop versus power loop |
| `JmOI0L7SiG8` | Looping underspin contact point |
| `V__nqiNHeKE` | Forehand-loop mistakes |
| `p3hweUir1Mg` | Push technique |
| `etKOmktKw1k` | Active and dangerous blocking |
| `xWrDKGnqmBs` | Backhand topspin, rip, and drive |
| `JcH1Nudznvk` | Backhand-loop contact, weight, and elbow |
| `QET6W3rjOxo` | Consistency, footwork, body height, and rhythm |
| `I-_3TIjU4qI` | Push-to-spin-to-power progression |
| `uag7n7hq3bM` | Post-serve recovery |
| `rTQcgBBWKWg` | Match tactics |
| `3yx5OMDyM8c` | Serve-receive principles |
| `tWJXY0cUPRQ` | Serve-receive distance and spin reduction |
| `f7uZPRPIwpU` | Table-height preparation and loop consistency |
| `Ge6u_cFpfDU` | Backswing rhythm and serve-attack patterns |
| `hDXIuFwtrHE` | Backhand serve and deception |
| `hZmEfLkbNI8` | Push variations against different opponents |
| `1v7qPrGhvTU` | Two-phase loop power |
| `q9c2_hCwlhs` | Backhand loop keys |
| `0eMDTeOBR5A` | Rhythm matching |
| `wF-YklKS7pI` | Short, half-long, and long receive decisions |
| `q7kEYGprLYo` | Hook and sidespin-backspin serve mechanics |
| `zd8tcVUWwK4` | Forehand and backhand correction system |
| `nUotsfFiQqY` | Push-to-loop strategy |
| `t3HX8AEujWw` | Drive versus loop |
| `p19HWlk7LGo` | Down-the-line forehand loop and placement |
| `bUCFpvTlaMU` | Receiving and borrowing spin |

### GlobalTTStudio — 9 published, 2 inaccessible

| Video ID | State | Primary topic indicated by title |
|---|---|---|
| `YUEaL2HiPIE` | Published | Whole-body stroke coordination |
| `leQBUn8-4tw` | Published | Serve selection and follow-up attack |
| `G7eiadOxN8E` | Published | Ball feel, timing, rhythm, and space |
| `OcPo7MgSNVM` | Published | Looping different spins |
| `qLT0MvwitZc` | Published | Powerful forehand loops |
| `0E67TotjJFE` | Published | Looping heavy backspin |
| `Cq6MbP6TEdc` | Published | Forehand-loop trajectory correction |
| `XfWXrGTlW5M` | Published | Second-loop timing |
| `V2YGbh829eU` | Published | Forehand-loop contact point |
| `2GWq4FdtSRU` | Members-only; not ingested | Friction mechanics and equipment |
| `c894uv9vOFk` | Members-only; not ingested | Advanced forehand-loop swing path |

## Outstanding work by state

| Work item | Count | Recommended action |
|---|---:|---|
| Pending extracted candidates | 0 | No editorial queue backlog remains. |
| Proposed visual intervals requiring viewing | 35 | Watch the complete intervals and mark only genuine demonstrations as `manual_review` / `verified_visual_demo`. |
| Single-source concepts | 19 | Select videos that add an independent supporting source rather than more moments from the same lesson. |
| Eligible configured videos not published | 0 | The configured transcript pipeline is complete. |
| Members-only configured videos | 2 | Leave unprocessed unless access and processing rights are explicitly available. |
| Unselected TT SpinMaster discoveries | 271 | Curate by coverage gap; do not bulk-ingest automatically. |
| GlobalTTStudio discovery catalog | Unknown | Fix per-source discovery manifests and channel-tab handling before measuring coverage percentage. |

## Refresh procedure

Update this report after a material discovery, ingestion, extraction, review, or publication batch. The authoritative inputs are:

- `config/kbs/table-tennis/sources.yaml` for configured selection and availability;
- `data/manifests/table-tennis/discovered-videos.json` for the currently captured discovery catalog;
- `data/normalized/table-tennis/` for private transcript ingestion state;
- `data/derived/table-tennis/` for private Codex extraction state;
- `content/kbs/table-tennis/annotations/review-queue.yaml` for editorial state;
- `data/publish/kbs/table-tennis/corpus.json` for supporting videos and evidence;
- `docs/quality-report-table-tennis.json` for corpus-level quality metrics.

Discovery manifests should become source-specific before this report is automated. The current single `discovered-videos.json` describes the most recent trustworthy TT SpinMaster discovery and cannot represent both channels simultaneously.
