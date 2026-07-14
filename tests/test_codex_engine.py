from processors.codex_engine import parse_codex_usage


def test_parse_codex_usage_uses_final_jsonl_event() -> None:
    stdout = "\n".join(
        [
            '{"type":"item.completed"}',
            '{"type":"turn.completed","usage":{"input_tokens":120,"output_tokens":30}}',
        ]
    )
    assert parse_codex_usage(stdout) == {"input_tokens": 120, "output_tokens": 30}


def test_parse_codex_usage_tolerates_non_json_output() -> None:
    assert parse_codex_usage("diagnostic text") is None
