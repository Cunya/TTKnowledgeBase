# Session notes — 2026-08-06 13:00

- “Bounded source-balanced deferred adjudication” is internal workflow language, not a useful operator label.
- Preferred wording for this pass:
  - “bounded” → “small” or “limited,” when the fixed cap matters;
  - “source-balanced” → “fair across sources” or “rotates across sources”;
  - “deferred adjudication” → “retrying unclear candidates”;
  - “workset” → “selected batch” or “videos selected for this run”;
  - “automation triage” → “automatic first pass”;
  - “eligible” → “allowed to process,” where the audience is operational rather than technical.
- Keep stable state values such as `deferred`, `human_review`, and `adjudication` in code, manifests, schemas, and tests unless a migration is explicitly requested.
- The processor monitor was active during this pass. Generated manifests, queues, and publish snapshots must not be hand-edited.
