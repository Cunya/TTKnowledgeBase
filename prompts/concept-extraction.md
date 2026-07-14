# Concept extraction prompt contract

The executable prompt is assembled in `processors/codex_engine.py` so it can include the exact taxonomy, known concepts, and bounded transcript segments. Keep prompt revisions aligned with `PROMPT_VERSION`.

The model must:

- return only schema-valid structured data;
- cite supplied segment IDs for every concept, relation, and evidence item;
- preserve source terminology as aliases;
- prefer concrete teachable concepts;
- mark uncertain merges as ambiguous;
- never create timestamps or claim a visually verified demonstration.

