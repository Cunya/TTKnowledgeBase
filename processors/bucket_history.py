"""Private inventory observations recorded independently of the monitor UI."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from .utils import read_json, write_json

RETENTION = timedelta(days=7)
HISTORY_LIMIT = 1000
STAGES = {
    "acquisition": "needs_acquisition",
    "extraction": "needs_extraction",
    "adjudication": "needs_adjudication",
    "complete": "complete",
    "excluded": "excluded",
    "retry_wait": "retry_wait",
}
DECISIONS = ("pending", "deferred", "accepted", "rejected", "human_review")


def observation(at: str, summary: dict) -> dict:
    states = summary.get("states", {})
    candidates = summary.get("candidates", {})
    return {
        "at": at,
        "stages": {name: states.get(state, 0) for name, state in STAGES.items()},
        "decisions": {name: candidates.get(name, 0) for name in DECISIONS},
    }


def record_bucket_history(manifests: Path, ledger: dict, *, now: datetime) -> None:
    """Save observations while the caller owns the KB's inventory write lock.

    Unchanged counts still record an observation, so idle periods have measured
    endpoints. Retain one older observation for the seven-day boundary.
    """
    history_path = manifests / "bucket-history.json"
    saved = read_json(history_path) if history_path.exists() else {}
    entries = saved if isinstance(saved, list) else saved.get("entries", [])
    latest_path = manifests / "cp.latest.json"
    latest = read_json(latest_path) if latest_path.exists() else {}
    entries = list(entries)
    for timestamp, counts in (("started_at", "inventory_before"), ("finished_at", "inventory_after")):
        if latest.get(timestamp) and isinstance(latest.get(counts), dict):
            entries.append(observation(latest[timestamp], latest[counts]))
    entries.append(observation(ledger["generated_at"], ledger["summary"]))
    by_time = {}
    for entry in entries:
        try:
            at = datetime.fromisoformat(entry["at"].replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError):
            continue
        if at.tzinfo is None or at > now or not isinstance(entry.get("stages"), dict) or not isinstance(entry.get("decisions"), dict):
            continue
        by_time[at] = {"at": at.astimezone(UTC).isoformat(), "stages": entry["stages"], "decisions": entry["decisions"]}
    ordered = sorted(by_time)
    cutoff = now - RETENTION
    older = [at for at in ordered if at < cutoff]
    retained = ([older[-1]] if older else []) + [at for at in ordered if at >= cutoff]
    if len(retained) > HISTORY_LIMIT:
        retained = [retained[round(index * (len(retained) - 1) / (HISTORY_LIMIT - 1))] for index in range(HISTORY_LIMIT)]
    write_json(history_path, {"version": 1, "entries": [by_time[at] for at in retained]})
