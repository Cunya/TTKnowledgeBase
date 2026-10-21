# Refactorings

## 2026-10-17

- Completed 2026-10-17 (P1-51), actual total-cap regression added: after complete-context packing, inspect the remaining fixed eight-row selected-proof reserve. A proof with73–80owned rows and little context may fit the configured80row total but still defer. Remove the redundant reserve only with a full-budget regression test;keep complete context and ownership checks. Do this after the current release,with source-completion planning,not by truncating proofs.

## 2026-09-15

- Reused the existing streamed stage runner for operator-readable purpose, heartbeat, and duration messages instead of adding a second logging pipeline; the existing machine-readable stage markers remain unchanged.
- Reused the existing navigation scoring path and expanded its input context instead of adding a second placement pass after summary generation.
- Reused the monitor's existing bounded child-output buffer for allowlisted failure summaries instead of storing or streaming raw tracebacks.

## 2026-09-08

- Reused one adjudication persistence helper for final writes and ten-candidate checkpoints, avoiding separate queue/concept serialization paths.

## 2026-07-20

- Replaced whole-stage subprocess capture in `scripts/run-cp.py` with one bounded streaming reader. This keeps the monitor live during long ingest and extraction stages while retaining the existing final stage report contract.

## 2026-07-21

- Extracted shared local-ASR transcription from the temporary audio fallback so the retained-media ASR route and normal fallback use the same segment construction and explicit `local_asr` provenance.

- 2026-09-15: Reused the run manifest stage list as the source for `Stage x/y` numbering so the runner and monitor do not maintain separate counters.

## 2026-09-16

- Reused the existing review-queue item and validator instead of adding a second reconciliation pass; accepted adjudications now carry their exact selected segment IDs through the current rebuild path.
- Reused the existing navigation scorer and added one configured editorial holding node for ambiguous generated concepts, avoiding a second publish-only reconciliation pass.

- 2026-10-17: Repair edit permissions are declared in validation and per-unit JSON schema. Keep the demonstration-to-explanation permission synchronized in both; extract a common permission helper only if additional classification edits are introduced. Current paired restrictions are regression-tested.

- 2026-10-17: Reused existing article source chunks and proposal reducer for oversized field-proof authoring instead of creating another selector/model contract. Final verification still owns complete contributing citations/context; cached interrupted stages resume without repeating extraction.

2026-10-17 18 EEST — published_repair.run_repair_campaign authoring passes _unchanged_draft(failures),which discards selected field proof for authoring and expands to full article. A one-alias removal on rhythm re-runs two chunk authors and reducer. Consider reusing a complete existing owned proof for explicitly narrow primary edits,falling back to whole-article alternative selection only when necessary; final independent verification and fresh exact primary approval must remain mandatory. Track P1-51; evidence media/audit-rhythm-alias-repair-2026-10-17-18.log.

2026-10-17 19 EEST — Failed schema-validation calls can report0recorded_tokens: _model_call writes response provenance then rethrows plain ValueError;run_repair_campaign reads error.provenance,which is absent. Preserve real returned usage in failure accounting without publishing private response content. Source:initial rip aliases failure,media/audit-rip-backswing-primary-repair-2026-10-17-18.log and shared code. Do not treat0reported as free. Track P1-51.

2026-10-17 20:59 EEST — Temporary finite source-review scripts duplicated orchestration and some replaced drafts instead of using shared campaign merge. Reuse existing production merge behavior when consolidating source-review tooling;avoid more one-off replacement scripts. P1-51 retention scan16signals requires source/primarydisposition,not bulkrestore.

2026-10-17: RepairEdit field Literal and EDITABLE_FIELDS intentionally serve typed schema versus per-target authorization but must stay synchronized. A missing concept_type capability caused repeated unactionable draft findings. Keep a generated-schema + guarded-application regression; consider a shared definition only if another drift occurs.

- 2026-10-18: Private source-completion prototypes repeat typed draft, verification, checkpoint and guarded-write orchestration. If reused, consolidate editorial import/additive context into the existing repair path, preserving exact source/byte/fingerprint/primary guards and private provenance. Deferred under P1-51/P1-34 (P2 tooling follow-up); no parallel production workflow added.

- 2026-10-19: Operational mitigation for repeated repair-stage cost: all84 remaining articles already have private plans. Reuse them for complete-source editorial correction and finite whole-article Luna/high verification, skipping unchanged audit/draft stages. Preserve source/fingerprint/hash/primary/application/release guards; no production refactor needed for this continuation. Existing private-orchestration consolidation remains deferred under P1-34/P1-51.

- 2026-10-19: The existing guarded repair application correctly rejected a new alias that duplicated another canonical label. Reuse its normalized complete-corpus term check before paid editorial verification to avoid an otherwise supported plan reaching this late rejection. Deferred P2 under P1-34/P1-51 tooling follow-up; do not weaken the application guard or introduce a separate publishing path.

- 2026-10-19: The private recovery verifier now retains prior jobs for an unchanged source identity and stage versions, reusing results only when the complete payload, policy and model-profile digest matches. A changed article definition still invalidates every affected payload. Keep private-wrapper consolidation under the existing P1-34/P1-51 tooling follow-up; do not weaken source or approval guards.

- 2026-10-20: P2-12 records consolidating source-completion wrappers into the existing production per-unit/context/profile/policy verification cache. One changed excerpt currently reruns unrelated units in the private wrapper. A focused literal-unit check retained23exact unchanged positive units with source/value hashes and prior-plan provenance; preserve negative findings, do not select results by voting. See consolidated backlog and17h session.

- 2026-10-20: P1-54 reuses the existing evidence renderer with hidden ranked overflow rather than rendering a second full component/player/list. Source grouping keeps visible and overflow citations separate, preserving the initial cap without duplicate citation IDs. No new dependency or parallel rendering system.

- 2026-10-20: P1-55 renders reviewed canonical prose directly in EvidenceRow/full VideoToc, avoiding repeated regex-based title cleanup on claim bodies. This removes an unnecessary transformation path while preserving source attribution/limitations. No new formatter/cache abstraction; exact built-corpus prose checks cover the completed change.
