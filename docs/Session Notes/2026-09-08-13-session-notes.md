# Session notes — 2026-09-08 13:00

- Implement a fixed ten-candidate checkpoint in the existing adjudication persistence path.
- Test that the first ten decisions remain on disk when candidate eleven raises an unexpected error.
- Keep the current 45-minute stage timeout and retry semantics unchanged.
- Replace the rejected `gpt-5.4-mini` processor default with the lowest-cost model supported by the installed CLI, verified by a read-only smoke test.
- Keep the explicit retry model on `gpt-5.6-luna` at low reasoning; do not use Terra.
