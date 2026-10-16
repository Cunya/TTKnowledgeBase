import io
import json

import pytest

from processors.account_quota import quota_block_reason, read_account_rate_limits
from processors.llm_budget import LLMBudgetExceeded, LLMTokenBudget


def snapshot(used=80, remaining=601, duration=300):
    return {"rateLimits": {"primary": {
        "usedPercent": used, "windowDurationMins": duration, "resetsAt": 1000 + remaining}}}


@pytest.mark.parametrize(("used", "remaining", "blocked"), [
    (79, 601, False), (80, 601, True), (80, 600, False),
    (99, 599, False), (100, 1, False),
])
def test_five_hour_threshold_and_strict_ten_minute_boundary(used, remaining, blocked):
    assert bool(quota_block_reason(snapshot(used, remaining), 80, 10, now=1000)) == blocked


def test_weekly_window_not_exempt_near_reset_and_primary_order_not_assumed():
    value = snapshot(80, 599, duration=10080)
    value["rateLimits"]["secondary"] = snapshot(90, 1)["rateLimits"]["primary"]
    assert quota_block_reason(value, 80, 10, now=1000)


def test_configurable_cutoff_and_multi_bucket_precedence():
    value = snapshot(100, 900)
    value["rateLimitsByLimitId"] = {"codex": snapshot(69, 900)["rateLimits"]}
    assert quota_block_reason(value, 70, 10, now=1000) is None
    value["rateLimitsByLimitId"]["other"] = snapshot(70, 900)["rateLimits"]
    assert "other" in quota_block_reason(value, 70, 10, now=1000)


@pytest.mark.parametrize("value", [{}, {"rateLimits": {}}, snapshot(80, 0),
                                    snapshot(None), snapshot(float("nan")),
                                    {"rateLimits": {"primary": []}}])
def test_missing_invalid_or_expired_quota_is_not_zero(value):
    with pytest.raises(ValueError):
        quota_block_reason(value, 80, 10, now=1000)


def test_guard_defers_before_reservation_even_when_local_budget_disabled(tmp_path, monkeypatch):
    config = tmp_path / "config.yaml"
    config.write_text("llm_budget:\n  enabled: false\n  account_quota:\n    enabled: true\n")
    ledger = tmp_path / "budget.json"
    monkeypatch.setattr("processors.llm_budget.read_account_rate_limits", lambda: snapshot(85, 900))
    monkeypatch.setattr("processors.account_quota.time.time", lambda: 1000)
    with pytest.raises(LLMBudgetExceeded, match="account quota"):
        LLMTokenBudget(config, ledger).reserve("extraction", "test")
    assert not ledger.exists()


def test_unavailable_quota_defers_without_reserving(tmp_path, monkeypatch):
    config = tmp_path / "config.yaml"
    config.write_text("llm_budget:\n  account_quota:\n    enabled: true\n")
    def unavailable():
        raise ValueError("unavailable")
    monkeypatch.setattr("processors.llm_budget.read_account_rate_limits", unavailable)
    with pytest.raises(LLMBudgetExceeded, match="unavailable"):
        LLMTokenBudget(config, tmp_path / "budget.json").reserve("extraction", "test")


def test_reader_initializes_reads_without_model_call_and_cleans_up(monkeypatch):
    class Process:
        stdin = io.StringIO()
        stdout = io.StringIO('\n'.join(json.dumps(x) for x in [
            {"id": 1, "result": {}}, {"method": "notification"},
            {"id": 2, "result": snapshot()},
        ]))
        pid = 123
        def poll(self):
            return 0
        def wait(self, timeout):
            self.requests = [json.loads(line) for line in self.stdin.getvalue().splitlines()]
    process = Process()
    monkeypatch.setattr("processors.account_quota.shutil.which", lambda _: "codex")
    monkeypatch.setattr("processors.account_quota.subprocess.Popen", lambda *a, **kw: process)
    assert read_account_rate_limits() == snapshot()
    assert [r["method"] for r in process.requests] == ["initialize", "initialized", "account/rateLimits/read"]
    assert process.stdin.closed and process.stdout.closed
