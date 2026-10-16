# Affected-content spot check — 2026-10-14

## Scope and method

Reviewed five published concepts and 17 selected evidence records: five half-long-ball records from `eIsYt1sCPRI`, nine ready-position records from `J7Lm5IL-ggs` and `JLGqLr-9-2w`, and one record each for forearm forward drive, defensive block against long fast serves, and variation in placement. Compared canonical definitions/excerpts/reasons with exact cited normalized transcript rows and adjacent context; confirmed these records occur in the public corpus.

This is a targeted transcript-content sample, not a whole-corpus certification or visual-footage review. It uses the source captions as evidence, without independently verifying their translation or the coach's underlying advice. Processing remained active; no canonical content or runtime manifests were modified. Findings are tracked under **P1-49**, with dependencies on P1-03, P1-33, P1-34, and the completed P1-48 identity repair.

## Findings

### F1 — Forearm drive definition loses a grip restriction (P1)

- File: `content/kbs/table-tennis/concepts/forearm-forward-drive.yaml`, definition at line 5.
- Evidence: `phKJvL-8VbQ-concept-forearm-forward-drive-codex-reviewed`, 719700–745700 ms, segments `phKJvL-8VbQ:00167`–`:00171`.
- The definition presents forearm drive as a general long-serve instruction. Segment `:00168` specifically addresses penhold players. The immediately following context `:00172` supplies a different cue for shakehand players: drive the wrist forward.
- The cited excerpt retains the penhold qualification, but the article definition drops it. This is a real scope mismatch, rather than an invented movement or timestamp.
- Correction target: retain the penhold/long-serve context in the definition and taxonomy, or cite and review additional evidence that justifies a broader topic. Do not silently generalize this source to both grips.

### F2 — Half-long-ball definition is too broad (P1)

- File: `content/kbs/table-tennis/concepts/half-long-ball.yaml`, definition at line 7.
- The definition describes a ball landing on the table and then bouncing off, without the defining near-end-line depth. That also describes ordinary long balls.
- All five sampled citations include `eIsYt1sCPRI:00003`, 15166–19833 ms, which specifies that the ball just clears the end line after its first bounce on the receiver's side.
- Correction target: restore the near-end-line qualifier from the cited definition. The cited evidence is useful; the canonical paraphrase lost a necessary distinction.

### F3 — One ready-position excerpt exceeds its cited support (P1)

- File: `content/kbs/table-tennis/concepts/ready-position.yaml`, evidence beginning at line 1990.
- Evidence ID: `JLGqLr-9-2w-concept-ready-position-codex-reviewed-2610aa4f`.
- Its excerpt includes the claim that players simply finish the stroke, while its selected IDs are `JLGqLr-9-2w:00050`–`:00054`, ending at 185833 ms. The relevant statement occurs in `:00055`, 186266–188233 ms, outside both the selected IDs and playback window.
- The claim exists in nearby source material, but the published citation does not include it. Valid segment IDs and a valid time envelope therefore did not establish support for the entire excerpt.
- Correction target: trim that clause or explicitly review inclusion of `:00055` and extend the envelope to 188233 ms. Several sibling records already cite that complete passage; consider consolidation rather than another overlapping record.

### F4 — Duplicate and overlapping published evidence remains (P1)

There are three exact duplicate-citation pairs among the 17 sampled records (same video and same ordered segment IDs):

| Concept/source | Duplicate IDs |
| --- | --- |
| Half-long ball / `eIsYt1sCPRI` | `eIsYt1sCPRI-concept-half-long-ball-codex-reviewed` and suffix `-a16e6fd2` |
| Ready position / `J7Lm5IL-ggs` | `J7Lm5IL-ggs-concept-ready-position-codex-reviewed` and suffix `-80c44c1e` |
| Ready position / `JLGqLr-9-2w` | `JLGqLr-9-2w-concept-ready-position-codex-reviewed` and suffix `-6a96e621` |

Beyond those exact pairs, all five half-long-ball citations reuse segment `eIsYt1sCPRI:00003`; the four sampled `J7Lm5IL-ggs` ready-position records reuse `:00050`; and the five sampled `JLGqLr-9-2w` ready-position records reuse `:00052`. These are overlapping variants of three source moments, not 14 independent demonstrations or cross-source confirmations.

The identity fix prevents unchanged proposals from being reset again. It does not remove the existing duplicate citations. Correction target: review same-topic/same-source overlap groups, retain the most useful supported windows, preserve editorial provenance, and prevent exact citation duplication in future incorporation. Do not merge distinct claims solely because their timestamps overlap.

### F5 — Generated summaries contain review rationale (P1)

- Forearm forward drive, defensive block against long fast serves, half-long ball, and variation in placement use deterministic summaries assembled from evidence reasons.
- Those reasons include concept-matching judgments, supplied-concept comparisons, segment IDs, and time-window compliance. This produces public article prose about the adjudication process rather than a concise explanation of the subject. The half-long summary also repeats near-identical descriptions of the same cited moment.
- Correction target: write source-grounded reader-facing summaries, with retained technical scope and no review scaffolding. Existing P1-33 summary-quality work is relevant; fixing P1-48 alone does not repair this prose.

## Supported sampled claims and limits

- **Defensive block against long fast serves:** `phKJvL-8VbQ:00052`–`:00056`, 218366–240400 ms, supports a controlled block that absorbs incoming power rather than adding force. The article's technique definition and excerpt fit that passage. Its `distance: far` and `level: beginner` facets are not established by these cited lines and need separate justification or removal.
- **Variation in placement:** `PVNp35T9kL4:00159`–`:00164`, 757400–785300 ms, supports avoiding predictable placement and varying wide forehand, wide backhand, and middle. The sampled excerpt matches the source.
- **Ready-position passages:** the serve passage supports returning to ready position after the action. The loop passage describes the speaker's straight-back recovery in contrast to elite players' circular recovery; surrounding `J7Lm5IL-ggs:00053` allows a comfortable choice. It should not be recast as proof that straight-back recovery is universally superior. The sampled excerpts currently retain that contrast.
- All 17 sampled public records have no `visual_source`. Some are classified `transcript_inferred`; this audit does not verify visible movement, and those records must remain spoken citations with looping disabled.

## Conclusion and follow-up

The sample found genuine editorial defects: two overly broad definitions, one excerpt whose selected citation omits a supporting clause, duplicate/overlapping evidence, and review-oriented summaries. The source passages are real; the demonstrated problems concern scope, citation completeness, and presentation. The queue bug plausibly contributed to redundant evidence, but these findings do not establish that it caused every wording defect.

P1-49 records the content correction and regression targets. The consolidated backlog and local `/backlog/` view remain the planning source of truth. See `docs/Session Logs/2026-10-14-00.md` for the inspection and verification record.

## Authorized corrections and wider investigation

After the initial read-only sample, the user authorized corrections. Enumerating all 12 colliding video/candidate-ID groups identified seven groups with associated public evidence and five without it in that snapshot. Additional source-level inspection covered half-high-ball attack opportunity, backhand rip, and serve-receive reading/rhythm. Inspection then extended to all 13 exact same-concept/video/segment duplicate groups in the public corpus.

### Additional confirmed defects

- **F6 — Wrong topic role:** two `8EoTrLShMWQ` records under half-high-ball attack opportunity cite `:00349`–`:00358`, about the player's outgoing half-high shots and error tolerance. This does not establish attacking an incoming opponent return. Both records were preserved as unreviewed and removed from publication. The corresponding proposal was replayed once through the unchanged configured `gpt-5.6-luna` profile with prompt 1.1.0 and the editorial advice. The normal validators ran in an isolated copy; the model rejected the proposal for that same distinction. The real queue retains that rejection and its provenance.
- **F7 — Fragment-only backhand-serve citations:** selected rows `hDXIuFwtrHE:00154`, `:00162`, and `:00259` were fragments, while their excerpts claimed detailed spin paths or toss positions. Reviewed replacements cite complete passages: `:00154`–`:00159` for mirrored chest/hip paths, `:00160`–`:00165` for spin path/contact zone, `:00247`–`:00252` for left-side backhand contact/arm freedom, and `:00255`–`:00259` for serve-specific toss positions. Each window is at most 30 seconds. Distinct useful claims were retained as distinct windows rather than collapsed into one incomplete citation.
- The down-the-line loop pair included details outside the exact selected passage. Its retained excerpt now states only the three cited keys: minimal backswing, slightly faster rhythm, and an open racket face. Other reviewed duplicate pairs preserve the complete supported body-coordination, outward-arc, and slow/fast-rhythm points.

### Corrections applied

| Finding | Correction |
| --- | --- |
| F1 | Penhold/long-serve restriction restored in forearm-drive definition, summary, and reason. |
| F2 | Half-long definition now requires just clearing the end line after the first receiver-side bounce. |
| F3 | Equivalent ready-position variants consolidated into a retained citation including the supporting final row; circular/straight recovery distinction retains the comfortable-choice context. |
| F4 | Exact duplicates and reviewed equivalent overlapping variants consolidated; separate visual windows and distinct supported claims remain separate. Approved canonical corpus has zero exact same-concept/video/segment duplicates after correction. |
| F5 | Five affected summaries rewritten as reviewed instructional prose, with generated fingerprints removed so automatic refresh preserves them. Deterministic generation filters detected review rationale and falls back to the reviewed definition when no useful reason remains; the fallback fingerprint includes the definition. |
| F6 | Two topic-mismatched records quarantined, incoming-ball scope clarified, and proposal rejected by an audited configured-model replay. |
| F7 | Four complete, source-backed backhand-serve windows replace fragment citations; unsupported clauses were dropped. |

Editorial history, old source windows, superseded evidence, and changed article fields are retained in `content/kbs/table-tennis/annotations/content-audit-2026-10-14.yaml`. Private working backups and model replay data remain under ignored `media/`; no full raw transcripts or model audit responses are published.

### Recurrence prevention and limits

- Incorporation recognizes an already approved same-topic/video/segment citation independently of candidate ID. Distinct cited spans remain distinct; a topic-specific ID suffix avoids cross-topic evidence-ID collisions.
- Validation rejects duplicate spoken citations with the same visual window while allowing separate visual demonstrations.
- Adjudication prompt 1.1.0 explicitly preserves qualifiers and incoming/outgoing roles, requires every excerpt clause to be supported by selected rows, and requests reader-facing accepted reasons. Editorial correction notes reach adjudication as advice, not source evidence. Model, schema, confidence, and boundary thresholds remain unchanged.
- These semantic instructions and one successful replay are improvements, not proof that the model will never make another support or topic error. The broader benchmark remains under P1-34.

### Wider boundary screen

At 00:39 EEST, the existing caption-only tooling evaluated 1,871 approved non-demo citations after the targeted repairs. It flagged 193 starts and 205 ends as mid-sentence, 61 windows under four seconds, and 381 citations needing context (20.36%). Those flags are overlapping review signals, not 381 established factual errors; noisy/overlapping captions can trigger them. P1-14 carries this remaining source-boundary review work. No unreviewed bulk timestamp expansion or whole-corpus approval reset was performed.

Final release and live-route verification are recorded in the October 14 session logs. P1-49 tracks the scoped corrections; P1-14, P1-33, and P1-34 retain broader quality work.

### Final-gate definition follow-up

The summary-style test exposed two additional reporting-style definitions when the safe fallback reused them. Their approved caption passages were reviewed before correction. The clock-position article now describes the cited contact/brushing model and its backspin example, without claiming coverage of every drive/loop method. The finger-action article now describes concentrated acceleration at contact to handle incoming spin, rather than treating that passage as proof of outgoing-spin generation or a universal primary-force rule. Display labels were narrowed; stable IDs/slugs and prior wording are preserved in the editorial archive. The style test was retained rather than weakened.

The final neutral-definition wording instruction is recorded as adjudication prompt **1.1.1**; the earlier isolated mismatch replay retains its actual **1.1.0** provenance.

### Final verification

The final release gate passed reviewed validation, publication, published-artifact validation, 142 Python tests, Ruff, nine Node monitor tests, and an Astro build with zero diagnostics. Public-artifact inspection confirms zero identical same-topic/video/segment/visual-window duplicates and exclusion of both outgoing-shot records. Fifteen concept files received direct editorial corrections; forty evidence actions and changed article fields are archived. The verified snapshot contains 365 concepts, 218 videos, and 1,877 evidence moments. This completes P1-49's scoped repairs, not the remaining corpus-wide semantic and caption-context work.
