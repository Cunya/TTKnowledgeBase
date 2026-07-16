from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from math import ceil
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .utils import read_json, read_yaml, write_json

DEFAULT_DAILY_TOKEN_LIMIT = 500_000
DEFAULT_OUTPUT_TOKENS = {
    "extraction": 8_000,
    "rephrase": 1_000,
    "benchmark": 8_000,
}


def usage_token_total(usage: dict | None) -> int:
    """Return a conservative token total from Codex usage metadata."""
    if not usage:
        return 0
    total = usage.get("total_tokens")
    if isinstance(total, (int, float)):
        return max(0, int(total))
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    return sum(
        max(0, int(value))
        for value in (input_tokens, output_tokens)
        if isinstance(value, (int, float))
    )


def estimate_prompt_tokens(prompt: str) -> int:
    """Estimate prompt tokens without adding a tokenizer dependency."""
    return max(1, ceil(len(prompt) / 4))


class LLMBudgetExceeded(RuntimeError):
    """Raised before a Codex call when the configured daily/task budget is full."""

    def __init__(self, task: str, requested_tokens: int, status: dict[str, Any], reason: str):
        self.task = task
        self.requested_tokens = requested_tokens
        self.status = status
        self.reason = reason
        remaining = status.get("remaining_tokens")
        super().__init__(
            f"LLM budget deferred {task}: requested about {requested_tokens:,} token(s), "
            f"{remaining:,} remaining ({reason})"
        )


@dataclass
class BudgetReservation:
    manager: LLMTokenBudget
    day_key: str
    task: str
    estimated_tokens: int
    event_index: int | None
    input_hash: str | None
    disabled: bool = False
    _finished: bool = False
    _result: dict[str, Any] | None = None

    def finish(self, usage: dict | None, *, charge_unknown: bool = True) -> dict[str, Any]:
        """Finalize the reservation and return the recorded usage summary."""
        if self._finished:
            return self._result or {}
        self._finished = True
        if self.disabled:
            self._result = {"enabled": False, "actual_tokens": 0, "estimated_tokens": 0}
            return self._result
        self._result = self.manager.finish(
            self,
            usage,
            charge_unknown=charge_unknown,
        )
        return self._result


class LLMTokenBudget:
    """A small local, per-KB daily token ledger for Codex-backed tasks."""

    def __init__(self, config_path: Path, ledger_path: Path):
        config = read_yaml(config_path) or {}
        raw = config.get("llm_budget", {}) or {}
        self.enabled = bool(raw.get("enabled", True))
        self.timezone_name = str(raw.get("timezone", "local"))
        self.daily_limit = int(raw.get("daily_token_limit", DEFAULT_DAILY_TOKEN_LIMIT))
        if self.daily_limit < 0:
            raise ValueError("llm_budget.daily_token_limit must be non-negative")
        self.task_limits = {
            str(task): int(limit)
            for task, limit in (raw.get("task_token_limits", {}) or {}).items()
            if limit is not None
        }
        if any(limit < 0 for limit in self.task_limits.values()):
            raise ValueError("llm_budget.task_token_limits values must be non-negative")
        configured_outputs = raw.get("estimated_output_tokens", {}) or {}
        self.output_limits = {**DEFAULT_OUTPUT_TOKENS}
        self.output_limits.update(
            {str(task): int(limit) for task, limit in configured_outputs.items()}
        )
        if any(limit < 0 for limit in self.output_limits.values()):
            raise ValueError("llm_budget.estimated_output_tokens values must be non-negative")
        self.ledger_path = ledger_path

    def _now(self) -> datetime:
        if self.timezone_name in {"", "local", "system"}:
            return datetime.now().astimezone()
        if self.timezone_name.upper() in {"UTC", "ETC/UTC"}:
            return datetime.now(UTC)
        try:
            return datetime.now(ZoneInfo(self.timezone_name))
        except ZoneInfoNotFoundError:
            # Windows installations may not ship the IANA database. Keep the
            # guard usable and fall back to the operator's local date rather
            # than disabling the budget; installing `tzdata` enables exact
            # named-zone behavior.
            return datetime.now().astimezone()

    def _empty_ledger(self) -> dict[str, Any]:
        return {"version": 1, "timezone": self.timezone_name, "days": {}}

    def _load(self) -> dict[str, Any]:
        if not self.ledger_path.exists():
            return self._empty_ledger()
        payload = read_json(self.ledger_path)
        if not isinstance(payload, dict) or payload.get("version") != 1:
            raise ValueError(f"Invalid LLM budget ledger: {self.ledger_path}")
        payload.setdefault("days", {})
        return payload

    def _day(self, ledger: dict[str, Any], day_key: str) -> dict[str, Any]:
        days = ledger.setdefault("days", {})
        day = days.setdefault(
            day_key,
            {
                "reserved_tokens": 0,
                "actual_tokens": 0,
                "tasks": {},
                "events": [],
            },
        )
        day.setdefault("reserved_tokens", 0)
        day.setdefault("actual_tokens", 0)
        day.setdefault("tasks", {})
        day.setdefault("events", [])
        return day

    @staticmethod
    def _task(day: dict[str, Any], task: str) -> dict[str, Any]:
        tasks = day.setdefault("tasks", {})
        return tasks.setdefault(
            task,
            {"reserved_tokens": 0, "actual_tokens": 0, "calls": 0, "deferred": 0},
        )

    def _status_for_day(self, ledger: dict[str, Any], day_key: str) -> dict[str, Any]:
        day = self._day(ledger, day_key)
        committed = int(day["reserved_tokens"]) + int(day["actual_tokens"])
        remaining = max(0, self.daily_limit - committed)
        tasks: dict[str, dict[str, Any]] = {}
        task_names = set(self.task_limits) | set(day.get("tasks", {}))
        for task in sorted(task_names):
            record = self._task(day, task)
            limit = self.task_limits.get(task)
            used = int(record["reserved_tokens"]) + int(record["actual_tokens"])
            tasks[task] = {
                "used_tokens": used,
                "remaining_tokens": max(0, limit - used) if limit is not None else None,
                "limit_tokens": limit,
                "calls": int(record.get("calls", 0)),
                "deferred": int(record.get("deferred", 0)),
            }
        return {
            "enabled": self.enabled,
            "date": day_key,
            "timezone": self.timezone_name,
            "daily_limit_tokens": self.daily_limit,
            "used_tokens": committed,
            "actual_tokens": int(day["actual_tokens"]),
            "reserved_tokens": int(day["reserved_tokens"]),
            "remaining_tokens": remaining,
            "tasks": tasks,
        }

    def status(self, now: datetime | None = None) -> dict[str, Any]:
        """Return current status without creating a ledger file."""
        day_key = (now or self._now()).date().isoformat()
        ledger = self._load()
        return self._status_for_day(ledger, day_key)

    def reserve(
        self,
        task: str,
        prompt: str,
        *,
        input_hash: str | None = None,
        output_tokens: int | None = None,
    ) -> BudgetReservation:
        if not self.enabled:
            return BudgetReservation(self, "", task, 0, None, input_hash, disabled=True)
        if task not in self.output_limits:
            self.output_limits[task] = DEFAULT_OUTPUT_TOKENS["extraction"]
        estimated = estimate_prompt_tokens(prompt) + int(
            self.output_limits[task] if output_tokens is None else output_tokens
        )
        day_key = self._now().date().isoformat()
        ledger = self._load()
        day = self._day(ledger, day_key)
        task_record = self._task(day, task)
        status = self._status_for_day(ledger, day_key)
        reasons: list[str] = []
        if status["used_tokens"] + estimated > self.daily_limit:
            reasons.append("daily limit")
        task_limit = self.task_limits.get(task)
        task_used = status["tasks"].get(task, {}).get("used_tokens", 0)
        if task_limit is not None and task_used + estimated > task_limit:
            reasons.append(f"{task} task limit")
        if reasons:
            task_record["deferred"] = int(task_record.get("deferred", 0)) + 1
            day["events"].append(
                {
                    "at": self._now().isoformat(),
                    "task": task,
                    "status": "deferred",
                    "estimated_tokens": estimated,
                    "input_hash": input_hash,
                    "reason": ", ".join(reasons),
                }
            )
            write_json(self.ledger_path, ledger)
            raise LLMBudgetExceeded(task, estimated, status, ", ".join(reasons))
        event = {
            "at": self._now().isoformat(),
            "task": task,
            "status": "reserved",
            "estimated_tokens": estimated,
            "input_hash": input_hash,
        }
        day["events"].append(event)
        event_index = len(day["events"]) - 1
        day["reserved_tokens"] = int(day["reserved_tokens"]) + estimated
        task_record["reserved_tokens"] = int(task_record["reserved_tokens"]) + estimated
        write_json(self.ledger_path, ledger)
        return BudgetReservation(self, day_key, task, estimated, event_index, input_hash)

    def finish(
        self,
        reservation: BudgetReservation,
        usage: dict | None,
        *,
        charge_unknown: bool = True,
    ) -> dict[str, Any]:
        ledger = self._load()
        day = self._day(ledger, reservation.day_key)
        task_record = self._task(day, reservation.task)
        actual = usage_token_total(usage)
        if usage is None and charge_unknown:
            actual = reservation.estimated_tokens
        day["reserved_tokens"] = max(
            0, int(day["reserved_tokens"]) - reservation.estimated_tokens
        )
        day["actual_tokens"] = int(day["actual_tokens"]) + actual
        task_record["reserved_tokens"] = max(
            0, int(task_record["reserved_tokens"]) - reservation.estimated_tokens
        )
        task_record["actual_tokens"] = int(task_record["actual_tokens"]) + actual
        task_record["calls"] = int(task_record.get("calls", 0)) + 1
        if reservation.event_index is not None and reservation.event_index < len(day["events"]):
            event = day["events"][reservation.event_index]
            event.update(
                {
                    "status": "completed",
                    "actual_tokens": actual,
                    "usage_available": usage is not None,
                    "finished_at": self._now().isoformat(),
                }
            )
        write_json(self.ledger_path, ledger)
        status = self._status_for_day(ledger, reservation.day_key)
        return {
            "enabled": True,
            "estimated_tokens": reservation.estimated_tokens,
            "actual_tokens": actual,
            "usage_available": usage is not None,
            "remaining_tokens": status["remaining_tokens"],
            "date": reservation.day_key,
            "task": reservation.task,
        }
