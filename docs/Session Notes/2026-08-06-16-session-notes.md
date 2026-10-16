# Session notes — 2026-08-06 16:00

- Human review needs a visible action path after loading: `1. Understand the claim → 2. Check highlighted evidence → 3. Record the decision`.
- Keep the candidate card's decision controls close to the evidence, and label every field by the decision it supports.
- Use shorter onboarding copy and move decision meanings into a compact reference instead of a long preamble.
- Preserve existing API payloads, decision actions, confirmations, and visual-evidence restrictions.
- Dynamically inserted review cards need global page styles; Astro's scoped styles do not attach to `innerHTML` content.
- Final card order is claim first, transcript second, decision third, with the queue-level action guide below the batch.
