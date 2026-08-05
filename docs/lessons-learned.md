# Lessons learned

## 2026-08-05

- Do not assume `sources.yaml` video membership is the live workset. In this project it accumulated configured batch history, while `run-cp.py` continued through discovery entries without appending them.
- Show the discovered partition and the public-corpus equation separately, with their overlap stated numerically.
- Lead a mixed public/operator dashboard with the user-facing content state, then preserve configuration and pipeline mechanics in a visibly subordinate operator section with an explicit definition.
- Configuration-only exclusion counts can materially understate full-catalog eligibility: derive members-only, subtitle, retry, and completion states from the complete inventory plus durable retry evidence before explaining the not-on-site group.
- A bounded adjudication pass needs both an attempt limit and an explicit selected-video filter; a candidate-count limit alone does not make the run manifest an exact description of the work performed.

## 2026-08-04

- A successful base language such as `en` should remain the first choice; caption adapters need a source-track fallback for regional variants such as `en-US` without treating YouTube translation-language listings as original captions.
- When the processor monitor is active, source-only processor changes can be prepared and tested without starting another run, but validation/publish must wait for the active generated-data cycle to become idle.
- Cumulative per-process CPU seconds are useful for the detail list but not for current load; the monitor should expose a separate system CPU/memory snapshot and short history for operational decisions.
- When a progress table mixes videos, candidate proposals, evidence moments, concepts, and visual intervals, percentages alone are not enough; a relationship graph must explicitly mark unit changes and show exclusions or parallel review states as branches rather than sequential steps.
- Updating a scheduler's cooldown value is incomplete if an already-armed timer keeps its old deadline; an idle loop must clear and rebuild the timer, while an active run should defer rescheduling until completion.

## 2026-07-20

- A subprocess exit code without captured stdout/stderr is not an operational diagnosis. Unattended stages should preserve bounded output and a machine-readable outcome/reason.
- Retry reporting should distinguish a failed cycle from a scheduled retry and reset its consecutive-failure counter only after a successful complete cycle.

## 2026-07-21

- On Windows, terminating the monitor's parent cp process does not reliably terminate nested Python discovery workers. Stop handling must terminate the verified process tree and discovery stages need bounded timeouts after sleep/network resumes.
- Atlas placement needs to be checked against the full editorial context: label, definition, facets, evidence summary, and evidence reasons. A concept can pass label-based checks while its summary clearly belongs to a receive, push, fundamentals, or practice branch.
- Deterministic evidence-summary cleanup must cover reporting constructions embedded mid-sentence, not only prefixes; run the repository-wide generated-summary assertion after changing sanitizer rules.
- Alternate transcript routes must use a separate normalized-data namespace; overwriting a caption cache can invalidate reviewed segment references even when video IDs match.
- Published-only queue validation must compare accepted queue citations with reviewed canonical concepts, not sanitized published concepts that intentionally remove demo/private evidence.
