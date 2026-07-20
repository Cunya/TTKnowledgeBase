# Lessons learned

## 2026-07-20

- A subprocess exit code without captured stdout/stderr is not an operational diagnosis. Unattended stages should preserve bounded output and a machine-readable outcome/reason.
- Retry reporting should distinguish a failed cycle from a scheduled retry and reset its consecutive-failure counter only after a successful complete cycle.
