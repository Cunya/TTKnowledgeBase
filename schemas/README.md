# Schemas

Pydantic models in `processors/models.py` are the single schema source of truth. The Codex runner generates `ExtractionResponse.model_json_schema()` inside each isolated job directory, passes it to `codex exec --output-schema`, and validates the response again before writing candidates.

