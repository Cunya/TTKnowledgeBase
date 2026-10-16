# Project against specifications — gaps and fixes

Reviewed 2026-09-17; completed verification recorded below on 2026-09-19.

## Scope and interpretation

Compared the current working tree with `AGENTS.md`, `README.md`, `docs/pipeline.md`, `docs/operations.md`, and the original `docs/youtube-knowledge-base-plan.md`, especially its version-1 definition of done. Inspected processor entry points, ingestion/extraction safeguards, review and inventory state, canonical and public validation, publication, generic KB paths, evidence playback, local planning views, and CI/build separation. This is a targeted specification review across the project, not a claim that every line or editorial assertion was independently audited.

The original plan is explicitly proposed and includes future features. Current operations document Codex adjudication followed by deterministic checks and tracked canonical YAML as the normal review path. Extraction proposals alone must never imply acceptance. Full public transcript search and offline archives are not requirements to implement in this pass: the current privacy rules prohibit public transcripts and keep offline work separately authorized.

## Confirmed defects fixed

| Priority / backlog | Location | Defect and impact | Resolution |
| --- | --- | --- | --- |
| P0 / P0-12 | `processors/pipeline.py:build_review_queue` | New queue entries could become accepted from fuzzy label similarity plus a shared segment, bypassing an explicit review decision. | New or changed proposals remain pending; unchanged tracked review decisions are preserved. Added an exact-match regression to show that even matching names/citations cannot supply approval. |
| P0 / P0-12 | `processors/pipeline.py:publish`, `validate_corpus`, `validate_graph` | Publication retained unapproved relations; relation sources bypassed transcript and timestamp checks. | Publish only approved relations; validate their sources using the same shared citation checks as evidence; ignore unreviewed graph edges. Three overlong relations were preserved as unreviewed history. |
| P0 / P0-12 | `processors/pipeline.py:validate_published_corpus` | Artifact validation did not explicitly reject embedded private transcripts or unapproved records. | Reject transcript-bearing videos and unapproved concepts, evidence, or relations before a public artifact passes validation. |
| P1 / P1-42 | `processors/pipeline.py:publish` | Only spoken-evidence video IDs were retained, so a separate visual or relation-only source could disappear from the corpus. | Retain the union of spoken, visual, and relation video references, sanitized of transcript data. |
| P1 / P1-42 | `processors/inventory.py:build_inventory_ledger` | Inventory ignored stored adjudicated segment IDs that queue validation already recognized, misreporting incorporated decisions as unfinished. | Share candidate/adjudicated citation accounting between queue validation and inventory. |
| P1 / P1-42 | `processors/cli.py:validate` | `--include-demo` referenced an uninitialized exclusion set; normal validation retained relations to excluded demo sources. | Initialize exclusions in both modes and apply demo-source filtering to relation citations. Corrected demo test isolation. |
| P1 / P2-01 | `.gitignore` | Successful adjudication/summary audits, budget backups, cp runtime manifests, and temporary writes could appear in Git's untracked inventory. | Added private-state ignore patterns. Existing tracked files and history still require operator remediation; no files were staged or removed from the index. |

The shared citation validator also uses the maximum cited end time, so overlapping captions cannot hide an earlier cue that ends after the final cue by start time.

## Remaining gaps and issues to fix

| Priority / backlog | Evidence / gap | Required next action and acceptance criteria |
| --- | --- | --- |
| P0 / P0-02, P0-04, P0-05 | Acquisition basis, removal procedures, and permissions remain planning items. This review did not establish creator authorization. | Record source-specific decisions and demonstrate withdrawal propagation before expanding source acquisition. No legal conclusion is inferred from a passing build. |
| P1 / P1-01, P1-13 | Published corpus has zero manually verified demonstrations; 35 visual windows are nearby inferences. The original version-1 requirement for verified core-concept demonstrations is not met. | Watch complete selected clips and record honest manual review for a defined core set; retain disabled looping for unverified/transcript-only moments. |
| P1 / P1-43 | Visual inference has no enforced 15-second ceiling or structured reviewed-exception record. Canonical `ConceptRelation.relation_type` is unrestricted while extraction uses a finite vocabulary; existing `related_to` edges require an explicit vocabulary decision. | Add a reviewed exception mechanism and shared vocabulary validation only after deciding how to preserve existing reviewed semantics. Cover canonical and public validation with tests; do not silently rename relations. |
| P1 / P1-43 | Three existing relation sources span 37.367s, 38.840s, and 35.600s. | Review and reselect supported spans for `brush-around-the-ball → forehand-loop-swing-path`, `contact-zone-on-ball → contact-point`, and `weight-transfer-through-stroke → loaded-legs`. They remain unreviewed and excluded until each passes the citation contract. |
| P1 / P1-32, P1-33, P1-34 | The recovered corpus remains uneven in article depth, graph coverage, repeated excerpts, and source diversity. A deterministic passing validator is not proof of semantic accuracy. | Continue bounded adjudication and article/relationship curation; establish a versioned support/boundary/placement benchmark with acceptance thresholds. Preserve quarantine history. |
| P1 / P1-35 | Backlog Markdown contains repeated IDs and the local page uses curated IDs with `items.find`, which can hide later duplicate entries. | Assign unique follow-up IDs, preserve reference migration, and verify every source heading renders exactly once. This pass explicitly maps its new items. |
| P1 / P1-36 | Earlier backlog and operations prose described the August 73-concept snapshot as current after recovery had advanced. | Current count interpretation is corrected below and in planning/operations documentation; use generated snapshots for subsequent counts rather than treating dated reports as live state. |
| P2 / P2-01 | Private budget/summary audit files are already tracked; ignore rules cannot remove prior commits. CI scans the site output but does not fully allowlist every file in `app/public/data/`. | Review tracked private-state paths and repository history, remove private state from version control while preserving local files, and add a complete public-artifact allowlist. Index/history mutation was not performed in this pass. |
| P2 / existing future-plan sections | Rich claim/contradiction artifacts, translations, generated courses, preserved media, and archive cleanup are incomplete or future scope. | Implement only as separately scoped features after trust and core evidence gaps; retain multi-KB isolation and private-media boundaries. |

## Current measured snapshot

The regenerated public corpus contains **342 concepts, 202 videos, and 1,828 evidence moments**. There are **35 inferred visual windows and zero verified visual demonstrations**. These counts describe public content, not the full canonical or discovery inventory.

The read-only inventory calculation found **838 catalog videos**, **752 eligible**, **60 complete**, **692 with automated work remaining**, and **86 excluded**. The queue contains **6,930 proposals**: 1,249 accepted, 101 rejected, 65 pending, and 5,515 deferred. It still reports **90 accepted proposals not represented in the public corpus** after recognizing adjudicated IDs; this is not automatically a claim of missing canonical data because quarantined/nonpublic evidence is deliberately absent. Track remediation under P1-34 rather than changing review decisions to improve a metric.

## Verification and limits

Release gate and local/public route checks are in progress; final results will be recorded before handoff. No new network acquisition, Codex extraction, footage verification, external deployment, staging, or commit was performed. Pre-existing worktree changes were preserved.

Planning source: [consolidated backlog](prioritized-backlog-2026-07-15.md). Session evidence: [September 17](Session%20Logs/2026-09-17-19.md), [September 19](Session%20Logs/2026-09-19-10.md).
