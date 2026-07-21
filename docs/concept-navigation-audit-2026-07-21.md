# Concept navigation audit — 2026-07-21

## Scope and method

Reviewed all 371 approved table-tennis concepts against their navigation paths. The audit compared each placement with the concept label, short definition, evidence summary, concept type, facets, and whether a placement was an intentional cross-list. The audit focused on semantic parent fit rather than keyword presence alone.

## Corrected placements

The following clear mismatches were corrected in `config/kbs/table-tennis/navigation.yaml`:

| Concept | Previous placement | Corrected placement | Reason |
| --- | --- | --- | --- |
| `concept-close-step` | Push → Forehand push | Fundamentals → Footwork and spacing | Describes a wide-angle adjustment step, not a push stroke. |
| `concept-backhand-system-body-led-ripping` | Push → Backhand push | Loop → Backhand loop | Describes a body-led backhand rip/power system, not backhand push mechanics. |
| `concept-flat-hit-swing-size-control` | Push | Drive | Describes a compact flat-hitting stroke and contrasts it with a forehand drive. |
| `concept-open-shoulder-and-pivot-for-forehand-transition` | Counter → Forehand counter | Fundamentals → Footwork and spacing | Describes pivoting and creating forehand space before the stroke; it is not counter-specific. |
| `concept-post-shot-recovery-to-ready-position` | Loop → Backhand loop | Fundamentals → Footwork and spacing | Evidence covers recovery after pushing, serving, looping, and general rally preparation. |
| `concept-rhythm-spacing-and-recovery-for-backhand-rip` | Flick → Backhand flick | Fundamentals → Footwork and spacing | Describes general rhythm, spacing, knee bend, and recovery rather than a flick. |
| `concept-forearm-position-relative-to-the-elbow` | Loop → Forehand loop | Movement and contact fundamentals | Its definition explicitly covers blocking, forehand drive, and forehand loop. |
| `concept-push-flick-close-distance-control` | Flick → Backhand flick | Serve receive → Timing and spacing | Describes generic push-flick receive distance and control, without a backhand-flick restriction. |

## Reviewed but retained

Generic-looking concepts were retained where their evidence or cross-listing supports the current path. In particular, serve/receive timing concepts describe incoming-ball decisions, hook-serve contact concepts are cross-listed with shared grip/contact fundamentals, and backhand spacing concepts explicitly support both backhand loop and flick learning paths.

## Verification

- Navigation coverage remained complete for all 371 concepts.
- The corrected paths were checked against the reviewed YAML and navigation parser.
- The full release gate passed after the audit: reviewed validation, publish, published-artifact validation, 48 tests, Ruff, and Astro diagnostics/static build.
