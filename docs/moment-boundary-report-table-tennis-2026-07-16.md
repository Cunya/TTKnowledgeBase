# Table Tennis moment-boundary report

Generated: `2026-07-16T14:00:53.201022+00:00`  
Method: `caption_only_sentence_like_units_v1`

## Coverage

| Metric | Value |
|---|---:|
| Evidence records | 1826 |
| Evaluated with local captions | 1826 |
| Missing local transcript | 0 |
| Starts mid-sentence | 16.4% |
| Ends mid-sentence | 17.5% |
| Too short (<4s) | 3.5% |
| Needs context/review | 31.9% |

## Duration distribution

| Statistic | Milliseconds |
|---|---:|
| Minimum | 1400 |
| Median | 15783.5 |
| 90th percentile | 27920 |
| Maximum | 30000 |

## Interpretation

- This is a script-only baseline; it proposes snapped unit bounds but does not alter reviewed evidence.
- Flagged moments should be reviewed for merge, context expansion, split, or defer actions.
- Any future audio or semantic pass must preserve cited segment IDs and the 30-second maximum.
