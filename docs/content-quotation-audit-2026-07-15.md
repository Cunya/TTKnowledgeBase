# Published-content quotation audit — 2026-07-15

This audit reviews the published table-tennis evidence excerpts for overly direct transcript quotation. It compares each public `excerpt` with the private normalized transcript segments cited by that evidence item. It does not determine legal infringement; it identifies editorial material that should be rephrased or explicitly marked as a quotation before broader public promotion.

Related policy review: [legal-review-youtube-2026-07-15.md](legal-review-youtube-2026-07-15.md).

## Method

For each of the 1,118 published evidence items, the audit:

1. Loaded the cited transcript segments from `data/normalized/table-tennis/`.
2. Normalized case, punctuation, and whitespace.
3. Checked whether the complete excerpt appears in the cited segment text.
4. Found the longest contiguous transcript word sequence appearing in the excerpt.
5. Separately checked the editorial `reason` field.

This is a conservative screening heuristic. A match can be a short generic coaching phrase, and a non-match can still be too close in meaning or structure. Human review remains necessary.

## Results

| Measure | Count | Share |
| --- | ---: | ---: |
| Published evidence items | 1,118 | 100% |
| Complete normalized excerpt matches | 32 | 2.9% |
| Excerpts with at least 8 contiguous matching words | 64 | 5.7% |
| Excerpts with at least 75% of their wording matching contiguously and at least 8 words | 38 | 3.4% |
| Excerpts with at least 5 contiguous matching words | 130 | 11.6% |
| Editorial reasons that exactly match their cited transcript | 0 | 0% |

The important distinction is that the `reason` fields are generally original editorial analysis. The principal risk is the public `excerpt` field, which currently presents source wording without a visible quotation marker.

## Highest-priority rephrasing set

These are exact or near-exact matches with distinctive wording and at least 12 words. They should be rephrased first or deliberately converted into short, visibly attributed quotations.

| Concept file | Video | Current excerpt |
| --- | --- | --- |
| `loose-grip-backhand-friction.yaml` | `BToLYdKLIMM` | “The tighter I hold, the less friction I can generate. The looser I hold, the more friction I create.” |
| `backhand-swing-arc-spacing.yaml` | `3kC8KEl3iow` | “There's no space between hand and ball, so all the player can do is push forward from the chest.” |
| `backhand-flick-on-rise.yaml` | `BToLYdKLIMM` | “When you're close to the table, your only real choice is to flick on the rise.” |
| `short-serve-third-ball-attack.yaml` | `G7eiadOxN8E` | “After your serve, look for a weak return to set up a powerful third-ball attack.” |
| `loose-grip-backhand-friction.yaml` | `BToLYdKLIMM` | “The space between thumb and index finger is practically open. Then I whip through.” |
| `forehand-loop.yaml` | `G7eiadOxN8E` | “For a loop, the backswing is much larger, creating a bigger swing radius.” |
| `body-hand-synchronization.yaml` | `3kC8KEl3iow` | “Body and hand must stop together. When the body stops, the hand stops.” |
| `backspin-serve-under-ball-contact.yaml` | `csJgHR7Daog` | “To create spin, you must be under the ball. That's how it grips.” |
| `loaded-legs.yaml` | `YUEaL2HiPIE` | “The issue is your legs are not engaged; they're like wet noodles.” |
| `loaded-legs.yaml` | `3kC8KEl3iow` | “When your legs are loaded, your upper body can actually generate power.” |
| `forehand-loop-spacing.yaml` | `I99BjizeWeE` | “Leave at least one upper-arm's distance when playing a forehand topspin loop.” |
| `forehand-loop-practice-progression.yaml` | `I99BjizeWeE` | “Do not use full power; use about 40 to 50 percent strength.” |
| `brush-around-the-ball.yaml` | `V__nqiNHeKE` | “Press and brush into the ball; only then can you generate spin.” |
| `ball-feel.yaml` | `G7eiadOxN8E` | “The key is understanding rhythm. You must learn to control the tempo.” |
| `short-serve-third-ball-attack.yaml` | `leQBUn8-4tw` | “The best serve is one that sets up your strongest attack.” |
| `serve-action-decomposition.yaml` / `body-hand-synchronization.yaml` | `csJgHR7Daog` | “Fingers move first, driving the wrist, then forearm, then upper arm.” |
| `body-hand-synchronization.yaml` | `csJgHR7Daog` | “Amateurs swing through as one block. Without decomposition, there's no spin.” |
| `body-hand-synchronization.yaml` | `3kC8KEl3iow` | “If the body stops but the hand still swings, that's disconnected.” |
| `backhand-flick-on-rise.yaml` | `BToLYdKLIMM` | “At the peak, after two or three shots, I'm jammed completely.” |
| `forehand-loop-against-backspin.yaml` / `forehand-loop.yaml` | `0E67TotjJFE` | “Drop your shoulder, lower your legs, and drop your wrist.” |

## Secondary rephrasing set

These are shorter but still substantially copied or near-copied. They should be reviewed in the same pass:

- `loose-grip-backhand-friction.yaml`: “The faster the racket head rotates, the spinnier the ball.”
- `loose-back-tight-release.yaml`: “Relax on the way back, tighten on the way out.”
- `loaded-legs.yaml`: “The stomp creates a body-ground connection. It's a force multiplier.”
- `forehand-loop-spacing.yaml`: “The distance between your hand and the ball is crucial.”
- `ready-position.yaml`: “In the ready position, your left shoulder is forward.”
- `serve-action-decomposition.yaml`: “Spin comes from decomposition—separating your power sources.”
- `short-serve-third-ball-attack.yaml`: “What they really fear is your follow-up attack.”
- `forehand-loop-swing-path.yaml` and `forehand-loop.yaml`: “When looping, focus more on the feeling of brushing the ball.”
- `forehand-loop-swing-path.yaml` and `forehand-loop.yaml`: “Brushing over the ball with a closed racket generates spin.”
- `forehand-loop-practice-progression.yaml`: “Hold the racket and do shadow practice without hitting the ball to develop coordination.”
- `contact-point.yaml`: “Practice different contact points—on the rise, at the peak, and on the fall.”
- `backspin-serve-under-ball-contact.yaml`: “Players contact the back of the ball, then wonder why it doesn't spin.”
- `ball-feel.yaml`: “Ball feel includes touch, spatial awareness, and rhythm.”

## Duplicate-expression issues

Some source sentences are published under multiple concepts. The most visible examples are:

- “Fingers move first, driving the wrist, then forearm, then upper arm.” appears under both `serve-action-decomposition` and `body-hand-synchronization`.
- “Drop your shoulder, lower your legs, and drop your wrist.” appears under both `forehand-loop` and `forehand-loop-against-backspin`.
- “When looping, focus more on the feeling of brushing the ball.” appears under both `forehand-loop` and `forehand-loop-swing-path`.
- “Brushing over the ball with a closed racket generates spin.” appears under both of those concepts as well.

Even when a short quotation is acceptable, repeating it across concept pages increases the appearance that the site is reproducing a transcript rather than adding independent analysis. Keep one primary source quotation if it is genuinely useful and paraphrase the other concept entries around their distinct meaning.

## Rephrasing policy

For normal evidence, the public excerpt should be an original, concise description of what the source establishes. Keep the exact segment IDs and timestamp, but change the wording and sentence structure.

Examples:

| Current wording | Safer editorial direction |
| --- | --- |
| “The tighter I hold, the less friction I can generate…” | Explain that excessive grip tension reduces the racket’s ability to brush the ball, while a relaxed grip preserves friction and acceleration. |
| “There's no space between hand and ball…” | Describe the mechanical consequence: insufficient working room forces a chest-driven push instead of a free stroke. |
| “Drop your shoulder, lower your legs, and drop your wrist.” | Summarize the three preparation adjustments in a new sentence and explain that they create a lower, better-connected opening position. |
| “Fingers move first, driving the wrist…” | Describe the sequence as a proximal-to-distal acceleration chain, then explain why the decomposition matters for spin. |

If the speaker’s exact wording is important, retain only a short excerpt, wrap it in quotation marks, label it as a source quotation, identify the speaker/channel, and keep the surrounding explanation clearly original. Do not use quotation marks as a way to publish long contiguous passages.

## Recommended implementation order

1. Rephrase the 20 highest-priority entries in the table above.
2. Resolve the duplicate expressions so each concept has a distinct editorial purpose.
3. Review the secondary set for short but distinctive copied phrases.
4. Add an `excerpt_kind: editorial_summary|source_quote` field to the content schema.
5. Render source quotes visibly and require attribution; default new evidence to `editorial_summary`.
6. Add a validator that flags complete matches, long contiguous n-grams, and repeated excerpts across concepts.
7. Re-run this audit after every extraction batch and before public deployment.

## What this audit does not show

- It does not prove that any item is legally infringing.
- It does not assess thumbnails, titles, or visual demonstrations for separate rights issues.
- It does not replace a human review of meaning, quotation purpose, or jurisdiction.
- It does show that the current data contains a measurable set of entries where rephrasing would reduce avoidable risk and make the knowledge base more clearly transformative.

