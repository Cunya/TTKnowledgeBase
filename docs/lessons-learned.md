# Lessons learned

## 2026-07-20

- A subprocess exit code without captured stdout/stderr is not an operational diagnosis. Unattended stages should preserve bounded output and a machine-readable outcome/reason.
- Retry reporting should distinguish a failed cycle from a scheduled retry and reset its consecutive-failure counter only after a successful complete cycle.

## 2026-07-21

- On Windows, terminating the monitor's parent cp process does not reliably terminate nested Python discovery workers. Stop handling must terminate the verified process tree and discovery stages need bounded timeouts after sleep/network resumes.
- Atlas placement needs to be checked against the full editorial context: label, definition, facets, evidence summary, and evidence reasons. A concept can pass label-based checks while its summary clearly belongs to a receive, push, fundamentals, or practice branch.
- Deterministic evidence-summary cleanup must cover reporting constructions embedded mid-sentence, not only prefixes; run the repository-wide generated-summary assertion after changing sanitizer rules.
- Alternate transcript routes must use a separate normalized-data namespace; overwriting a caption cache can invalidate reviewed segment references even when video IDs match.
- Published-only CI cannot infer synthetic fixture metadata from private normalized files; fixture IDs used by queue validation must be declared in tracked code and covered by a published-only regression test.
