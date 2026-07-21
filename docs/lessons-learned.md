# Lessons learned

## 2026-07-20

- A subprocess exit code without captured stdout/stderr is not an operational diagnosis. Unattended stages should preserve bounded output and a machine-readable outcome/reason.
- Retry reporting should distinguish a failed cycle from a scheduled retry and reset its consecutive-failure counter only after a successful complete cycle.

## 2026-07-21

- On Windows, terminating the monitor's parent cp process does not reliably terminate nested Python discovery workers. Stop handling must terminate the verified process tree and discovery stages need bounded timeouts after sleep/network resumes.
