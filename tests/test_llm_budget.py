from pathlib import Path

import pytest

from processors.llm_budget import (
    LLMBudgetExceeded,
    LLMTokenBudget,
    usage_token_total,
)


def write_budget_config(path: Path, *, enabled: bool = True, limit: int = 100) -> Path:
    path.write_text(
        "\n".join(
            [
                "llm_budget:",
                f"  enabled: {'true' if enabled else 'false'}",
                "  timezone: UTC",
                f"  daily_token_limit: {limit}",
                "  task_token_limits:",
                f"    extraction: {limit}",
                "  estimated_output_tokens:",
                "    extraction: 10",
            ]
        ),
        encoding="utf-8",
    )
    return path


def test_budget_reserves_and_finalizes_reported_usage(tmp_path: Path) -> None:
    config = write_budget_config(tmp_path / "processors.yaml", limit=100)
    ledger = tmp_path / "llm-budget.json"
    budget = LLMTokenBudget(config, ledger)

    reservation = budget.reserve("extraction", "x" * 40, input_hash="sha256:test")
    result = reservation.finish({"input_tokens": 20, "output_tokens": 5})

    assert result["actual_tokens"] == 25
    status = budget.status()
    assert status["used_tokens"] == 25
    assert status["remaining_tokens"] == 75
    assert status["tasks"]["extraction"]["calls"] == 1


def test_budget_defers_before_call_when_daily_limit_is_exceeded(tmp_path: Path) -> None:
    config = write_budget_config(tmp_path / "processors.yaml", limit=50)
    budget = LLMTokenBudget(config, tmp_path / "llm-budget.json")
    budget.reserve("extraction", "x" * 40).finish({"input_tokens": 40, "output_tokens": 0})

    with pytest.raises(LLMBudgetExceeded) as raised:
        budget.reserve("extraction", "x" * 80)

    assert "daily limit" in raised.value.reason
    assert budget.status()["tasks"]["extraction"]["deferred"] == 1


def test_disabled_budget_does_not_create_a_ledger(tmp_path: Path) -> None:
    config = write_budget_config(tmp_path / "processors.yaml", enabled=False)
    ledger = tmp_path / "llm-budget.json"
    budget = LLMTokenBudget(config, ledger)
    reservation = budget.reserve("extraction", "prompt")

    assert reservation.finish(None)["enabled"] is False
    assert not ledger.exists()


def test_usage_total_is_conservative_and_tolerates_missing_usage() -> None:
    assert usage_token_total({"input_tokens": 10, "output_tokens": 5}) == 15
    assert usage_token_total({"total_tokens": 12, "input_tokens": 10, "output_tokens": 5}) == 12
    assert usage_token_total(None) == 0
