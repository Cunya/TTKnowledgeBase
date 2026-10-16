# Opponent feature parity — 2026-09-19

## Result

The project has partial opponent parity.

- Opponent-facing coaching content exists in the reviewed corpus. The published atlas has an **Opponent adaptation** branch with four concepts: adapt rally rhythm to the opponent, match-play framework, opponent targeting, and defensive rhythm variation.
- The relationship atlas already renders a generic `→` arrow for every reviewed concept relation. Two published opponent-named concepts currently have outgoing relations: `adapt-rally-rhythm-to-opponent → used_with → ball-feel` and `opponent-targeting → used_with → direction-reading`.
- These are knowledge-navigation arrows, not arrows showing where the opponent moves, which shot they choose, or where the player should place the next ball.
- No opponent entity, opponent profile, opponent-session record, style/archetype model, point-by-point plan, directional tactical overlay, or opponent-specific review control exists in the current data model or UI.

If “mate arrows” means the existing map/relationship arrows, the answer is **yes, generically**. If it means opponent movement or tactical arrows, the answer is **no**.

## Feature parity matrix

| Capability | Current state | Opponent parity | Evidence |
| --- | --- | --- | --- |
| Browse and search | Shared concept index and client-side search | **Yes, content-level** | `ConceptSearch.astro` searches labels, aliases, definitions, and types. |
| Topic navigation | Shared atlas with cross-listing | **Partial** | `Opponent adaptation` is a published branch; coverage is a curated set of concepts, not an opponent feature model. |
| Concept article | Definition, summary, topic paths, evidence, related topics, and source notes | **Yes** | The normal concept route applies to opponent concepts. |
| Spoken evidence | Timestamped transcript-backed playback and YouTube links | **Yes** | `EvidenceRow.astro` keeps spoken playback separate from visual playback. |
| Visual demonstrations | Separate visual windows; only manually reviewed windows may loop | **Shared limitation** | The current public snapshot has 35 inferred visual windows and zero verified demonstrations. |
| Relationship arrows | Generic arrows between reviewed concepts | **Partial** | Arrows show concept relations, not opponent movement or shot direction. |
| Opponent cues and tendencies | Expressed in article text and evidence reasons | **Partial** | No structured cue, tendency, style, or preferred-zone fields are exposed. |
| Tactical sequence or target map | Not modeled | **Missing** | No reviewed event/sequence relation or directional overlay exists. |
| Opponent notes and match history | Not modeled | **Missing** | Review controls are generic local content-review marks, not opponent records. |

## Minimum useful parity target

Do not add arrows first. The arrow would need a source-grounded meaning before it could be trusted. The smallest coherent future feature is:

1. Define a reviewed opponent-facing relation vocabulary, such as `targets`, `elicits`, `counters`, and `followed_by`, without reusing generic `used_with` for directional claims.
2. Add structured, optional opponent facets only where the reviewed source supports them: observable cue, opponent pattern, response, target zone, and confidence/status.
3. Render those reviewed relations as an opponent tactics panel or compact sequence map. Keep the existing generic atlas arrows for concept navigation.
4. Reuse the existing evidence player and transcript/visual separation. Do not imply that an opponent tactic is visually demonstrated unless a complete clip has been manually reviewed.

## Scope boundary

This is a parity baseline, not an implementation approval. It does not authorize opponent tracking, personalization, match-history storage, or new visual claims. Those would be separate features with their own privacy, data-model, review, and acceptance decisions.

## Evidence

- [Published corpus](../app/public/data/kbs/table-tennis/corpus.json)
- [Opponent navigation branch](../config/kbs/table-tennis/navigation.yaml)
- [Relationship atlas](../app/src/components/ConceptConnections.astro)
- [Concept data model](../app/src/types.ts)
- [Evidence playback](../app/src/components/EvidenceRow.astro)
- [Visual playback and looping rules](../app/src/components/VideoEvidence.astro)
- [Current specification gaps](specification-gaps-and-issues-2026-09-19.md)
