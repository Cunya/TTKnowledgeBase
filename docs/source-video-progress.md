# Source video progress

Last updated: 2026-07-16 16:22 EEST

This document explains the source-progress metrics and preserves an editorial snapshot for reference. The live counts are
not maintained here: run `python -m processors.cli publish --kb table-tennis` and read
`app/src/data/generated/table-tennis-progress.json` (or the local `/progress/` page). The processor regenerates that
snapshot from local artifacts; neither the LLM nor a page edit should update totals by hand.

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
| TT SpinMaster / `@FreeCoachBradHan` | 304 | 101 | 101 | 101 | 101 | 57 | 100 | 865 accepted / 109 deferred | 0 | 1,467 | 72 | 19 | 0 |
| GlobalTTStudio / `@GlobalTTStudio` | 418 | 31 | 23 | 23 | 23 | 13 | 23 | 207 accepted / 36 deferred | 1 | 359 | 58 | 16 | 0 |
| **Total configured** | — | **132** | **124** | **124** | **124** | **70** | **123** | **1,072 accepted / 145 deferred** | **1** | **1,826** | **73 unique overall** | **35** | **0** |

Concept counts overlap across sources: a concept supported by both channels is counted once in each source row, so the source rows must not be added to obtain the 73 unique concepts.

## Funnel interpretation

### TT SpinMaster / Free Coach Brad Han

- Channel catalog captured: 304 videos.
- Configured corpus: 101 videos, or about 33.2% of the captured catalog.
- Ingestion completion: 101 of 101 eligible videos are ingested.
- Downstream completion: 100 of 101 selected videos are published; 57 are fully reviewed, while 44 videos retain explicitly deferred candidates for later taxonomy/weak-match review. One extracted video currently has only deferred candidates and is not yet published.
- Remaining discovered catalog: 203 videos have not been selected for this KB yet.
- Editorial state: 865 candidates are accepted, 109 are explicitly deferred, and none are rejected for this source.
- Visual state: 19 proposed nearby visual windows exist, but none has been manually verified. They are non-looping on the public site.

The 205-video remainder is a discovery backlog, not an automatic processing queue. Videos should be selected for missing concepts, second-source support, or visual demonstrations instead of processed only to increase volume.

### GlobalTTStudio

- Trustworthy channel total: 418 public videos from a metadata-only discovery of the explicit `/videos` tab on 2026-07-15.
- Configured corpus: 31 videos.
- Eligible corpus: 23 videos.
- Pipeline completion: all 23 eligible videos are ingested, extracted, and published; 13 are fully reviewed and 10 retain explicitly deferred candidates.
- Inaccessible items: 8 configured videos are members-only and remain unprocessed.
- Remaining discovered catalog: 387 videos are not configured for processing.
- Editorial state: 207 candidates are accepted, 36 are explicitly deferred, 1 is explicitly rejected, and no candidates remain pending.
- Visual state: 16 proposed nearby visual windows exist, but none has been manually verified. They are non-looping on the public site.

## Configured video state by source

### GlobalTTStudio / Coach Han - controlled batch

The latest controlled batch added six public videos: `sosNHzR8A9U`, `2Wk2xe0I1s8`, `kv80YX__eJE`, `wd_E9NZBVtU`, `6vwxmC36InY`, and `h5jUJL_P82w`. Two catalogued videos, `saJV_mSKHaw` and `MS5-0DaZ_h8`, were confirmed members-only and marked inaccessible without retrying. The six public videos contributed 46 accepted candidates/evidence moments and 11 explicitly deferred candidates.

### TT SpinMaster / Free Coach Brad Han — 101 extracted, 100 published, 44 with deferred candidates

All 101 videos below are ingested and extracted. One hundred have published evidence; 57 have no deferred candidates and are fully reviewed, 44 retain explicitly deferred candidates, and one has no accepted evidence yet.

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
| `bKtA240EvTQ` | **Published / review pending:** backhand serve-receive training |
| `9OxcCPWI-k8` | **Published / review pending:** backhand serve spin and deception |
| `mTnHV7k_Wes` | **Published / review pending:** receiving short backspin serves |
| `A4-lKRVwSFc` | **Published / review pending:** backhand-loop spin mechanics |
| `ti_YUZdHu3o` | **Published / review pending:** heavy forehand-topspin braking action |
| `5JzSUTg_ojc` | **Published / review pending:** backhand receive framework |
| `lO0H9Cs6JEo` | **Published / review pending:** looping and receiving heavy backspin |
| `StQ86EhPFpo` | **Published / review pending:** forehand push flick against short serves |
| `15KzTMIx65s` | **Published / review pending:** power conditions and swing selection |
| `8pUgdfqXPj4` | **Published / review pending:** stroke-feel and body-position correction |
| `8yuRXgTWOxc` | **Published / review pending:** backspin-loop positioning and power transfer |
| `-1uBDv1Aq7A` | **Published / review pending:** receiving side spin |
| `SF0Sv2ZzrRI` | **Published / review pending:** vertical push against backspin |
| `_biE-Dzy0aM` | **Published / review pending:** adding power without misses |
| `XlGnK1z_7C0` | **Published / review pending:** serve-loop-smash point pattern |
| `ONXmZHozLTA` | **Published / review pending:** acceleration for heavy-spin loops |
| `KpjJFdkUD54` | **Published / review pending:** hook serve corrections |
| `L-m_mjGB5X0` | **Published / review pending:** universal push receive method |
| `TMrN47uIHiI` | **Published / review pending:** high-ball smash decisions |
| `ylfChS7Da-k` | **Published / review pending:** slow-soft-middle receive placement |
| `OMgoeirhpyc` | **Published / review pending:** aggressive mindset and backhand technique |
| `wyna7UXctZQ` | Published | Loop errors that send the ball into the net |
| `xmQrJ5l5A9c` | **Published / review pending:** point push and lift push |
| `yekYhw94rVI` | **Published / review pending:** backhand power hesitation |
| `deTFdwcfnrE` | **Published / review pending:** forehand basic correction |
| `Dj-oOxwQn1s` | **Published / review pending:** hook serve secrets |
| `J_ra9qsXCxo` | **Published / review pending:** forehand friction |
| `ODwFaYDY1co` | **Published / review pending:** third-ball attack |
| `xwKSNLxVaBg` | **Published / review pending:** fast left sidespin serve |
| `byk-MQTWbBs` | **Published / review pending:** backhand serve guide |
| `DXL3ZnLNXqE` | **Published / review pending:** forehand-loop corrections |
| `vXZPX5wybTY` | **Published / review pending:** smash after the loop |
| `PDFXww03DHM` | **Published / review pending:** match-winning fundamentals |
| `MV98YAD9lzs` | **Published / review pending:** all-purpose push against spin |
| `13z0kO_hd0M` | **Published / review pending:** looping underspin adjustments |
| `RjgITcuxl5I` | **Published / review pending:** curving left sidespin |
| `HHVds_mLi3I` | **Published / review pending:** rally consistency corrections |
| `zMP_ptkdNHk` | **Published / review pending:** brushing and compact response |
| `E6sGbY4sQH0` | **Published / review pending:** hook-serve mechanics |
| `3SvgpoJSW3o` | **Published / review pending:** reading and neutralizing spin |
| `m44MwRy-sT8` | **Extracted / deferred:** forehand flick wrist control |
| `vo26XE2LIjI` | **Published / review pending:** backhand flick correction |
| `6NvlGVPIC6E` | **Published / review pending:** backspin hook serve |
| `N3GieiMNE7Y` | **Published:** racket-angle correction |
| `R9InWNDCJQM` | **Published / review pending:** curving half-long timing and footwork |
| `Ad8Ox7xSvSU` | **Published:** forehand elbow stability |
| `wpIxIvnuOac` | **Published:** efficient spin generation |
| `HCkIFKn0-Ds` | **Published / review pending:** hook-serve wrist direction |
| `D1cBF0nsjKo` | **Published / review pending:** heavy backspin push |
| `Kg4hLYnEbAs` | **Published / review pending:** backhand-loop training and error correction |

### GlobalTTStudio — 23 published, 8 inaccessible

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
| `2Wk2xe0I1s8` | Published | Forehand-loop braking against backspin |
| `6vwxmC36InY` | Published | Banana-flick footwork and timing |
| `6Xx11I8CB9M` | Published | Racket angle for blocking power loops |
| `eIKLgVChAdA` | Published | Compact serve-receive rip |
| `h5jUJL_P82w` | Published | Forehand push variation |
| `kv80YX__eJE` | Published | Backhand punch mechanics |
| `nENxAvinCe8` | Published | Forehand-loop error correction |
| `nNLLuV_wY24` | Published | Forehand flick against heavy backspin |
| `sosNHzR8A9U` | Published | Delayed forehand-loop backswing |
| `TWv2MUl_64Q` | Published | Counter-topspin |
| `wd_E9NZBVtU` | Published | Triangle block against fast drives |
| `zAGc3h7gpxs` | Published | Forehand block correction |
| `7jWqEsHtN3Y` | Published | Push-rally and looping strategy |
| `hwT7cH6PbZQ` | Published | Push against different spin types |
| `2GWq4FdtSRU` | Members-only; not ingested | Friction mechanics and equipment |
| `c894uv9vOFk` | Members-only; not ingested | Advanced forehand-loop swing path |
| `saJV_mSKHaw` | Members-only; not ingested | Advanced looping mechanics |
| `MS5-0DaZ_h8` | Members-only; not ingested | Backhand kinetic chain |
| `6_GowxnyC94` | Members-only; not ingested | Fixed-drill alternatives |
| `gqVe2JURIY0` | Members-only; not ingested | Contact-point practice transfer |
| `V9rDt4zBHKw` | Members-only; not ingested | Training drills for consistency |
| `C03mgoF66a4` | Members-only; not ingested | Forehand flick principles |

## Outstanding work by state

| Work item | Count | Recommended action |
|---|---:|---|
| Deferred extracted candidates | 139 | Review taxonomy proposals and weak matches before another expansion pass. |
| Proposed visual intervals requiring viewing | 35 | Watch the complete intervals and mark only genuine demonstrations as `manual_review` / `verified_visual_demo`. |
| Single-source concepts | 2 | Select videos that add an independent supporting source rather than more moments from the same lesson. |
| Published videos with remaining review backlog | 50 | Resolve deferred candidates; publication currently includes only incorporated evidence. |
| Members-only configured videos | 8 | Leave unprocessed unless access and processing rights are explicitly available. |
| Unselected TT SpinMaster discoveries | 205 | Curate by coverage gap; do not bulk-ingest automatically. |
| Unselected GlobalTTStudio discoveries | 387 | Curate by missing topic, independent support, or useful visual demonstration. |

Latest ingestion attempt: on 2026-07-16, a conservatively paced six-video GlobalTTStudio batch found two public videos and four members-only entries. The two public videos entered the ingested state; the four inaccessible entries were marked members-only and were not retried.

Latest extraction batch: two newly ingested transcripts completed sequentially with `gpt-5.4-mini` at low reasoning, producing schema-validated candidates. The subsequent pending pass accepted 23 candidates, added 30 focused evidence moments, and deferred 5 weak or new-taxonomy proposals. No fast/flex tier or automatic stronger-model escalation was used.

## Refresh procedure

Update this report after a material discovery, ingestion, extraction, review, or publication batch. The authoritative inputs are:

- `config/kbs/table-tennis/sources.yaml` for configured selection and availability;
- `data/manifests/table-tennis/discovered-videos.json` for the currently captured discovery catalog;
- `data/normalized/table-tennis/` for private transcript ingestion state;
- `data/derived/table-tennis/` for private Codex extraction state;
- `content/kbs/table-tennis/annotations/review-queue.yaml` for editorial state;
- `data/publish/kbs/table-tennis/corpus.json` for supporting videos and evidence;
- `docs/quality-report-table-tennis.json` for corpus-level quality metrics.

Discovery manifests should become source-specific before this report is fully automated. The current single processor manifest still describes TT SpinMaster; the site keeps the verified GlobalTTStudio metadata catalog separately until the processor supports per-source manifests.
