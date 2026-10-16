# Session notes — 2026-08-05 00:00

- The public corpus and current configuration are overlapping classifications of the same discovered catalogs, not consecutive stages of one funnel.
- Required visible partition: 838 discovered = 148 currently configured + 690 outside current configuration; 148 = 140 public + 8 members-only; 690 = 589 previously published + 101 not public; therefore 729 public = 140 + 589.
- Implemented that partition directly in the Source summary graph and removed the misleading “Not selected” label.
- Simplified the primary view further: 838 known = 729 on the site + 109 not on the site. Configuration is now visibly subordinate operator detail, while all processing and review metrics remain available.
- Corrected the model after reviewing project history: the 148 `sources.yaml` entries are accumulated configured-batch provenance, not the current workset. `run-cp.py` generates each live workset and continued automatically through discovery entries without adding them to configuration.
- The revised exhaustive plan centers on a durable 838-video eligibility/completion ledger, ledger-driven run worksets, bounded deferred adjudication, explicit human review, and classification of the 101 non-public entries.
- Implementation uses a strict 11-character YouTube ID filter and the largest matching retained catalog per enabled source; this prevents channel placeholders from entering acquisition.
- The complete retry-backed inventory shows 85 members-only videos, while the earlier count of eight covered only configured batch history. The full 109 not-on-site split is 23 processed/no approved moments + 85 members-only + one subtitle-disabled.
- Automated adjudication is bounded by an exact 50-video workset per cycle. A deferred item becomes explicit human review after two unchanged deterministic attempts.
- The root `start.bat` previously started only Astro; the intended local launcher should also start the processor monitor while avoiding duplicate monitor instances.
- Do not place a caret-escaped PowerShell pipeline inside a quoted batch `-Command`; direct batch invocation can pass the caret literally, and a separate readiness check can mask that failure when the target service already exists.
- Monitor resource telemetry should be scoped by the repository process tree; machine-wide CPU/memory and unrelated Python/Node services obscure the load attributable to this project.
- Frequently changing monitor cards need reserved line boxes and tabular time text; otherwise normal status-label wrapping produces distracting vertical layout shifts.
- Human-review resolution must remain source-grounded: show exact cited segments and nearby context, require explicit source and concept confirmations, preserve an audit note, and permit canonical writes only while automated processing is paused.
- The monitor's wide-screen main area should stay balanced: active output owns one half, while the other half uses a two-by-two operational grid and collapses to one column below the desktop breakpoint.
- Full processing requires two honest measures: source-balanced automation triage and final editorial completion. Moving a candidate to `human_review` ends automatic retries but does not make its video fully processed.
