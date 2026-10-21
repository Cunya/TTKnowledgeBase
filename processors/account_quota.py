"""Read account quota without making a model request."""

import json
import math
import os
import queue
import shutil
import subprocess
import threading
import time


def read_account_rate_limits(timeout: float = 15) -> dict:
    executable = shutil.which("codex")
    if not executable:
        raise ValueError("Codex CLI unavailable for account quota check")
    process = subprocess.Popen(
        [executable, "-c", "features.apps=false", "app-server"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, encoding="utf-8",
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    messages = queue.Queue()

    def read_lines():
        for line in process.stdout:
            messages.put(line)
        messages.put(None)

    reader = threading.Thread(target=read_lines, daemon=True)
    reader.start()
    deadline = time.monotonic() + timeout

    def response(request_id):
        while True:
            line = messages.get(timeout=max(0, deadline - time.monotonic()))
            if line is None:
                raise ValueError("Quota reader exited before responding")
            message = json.loads(line)
            if message.get("id") == request_id:
                if "error" in message or not isinstance(message.get("result"), dict):
                    raise ValueError("Account quota request failed")
                return message["result"]

    def send(message):
        process.stdin.write(json.dumps(message) + "\n")
        process.stdin.flush()

    try:
        send({"id": 1, "method": "initialize", "params": {
            "clientInfo": {"name": "momentgraph-quota", "version": "1.0.0"}}})
        response(1)
        send({"method": "initialized"})
        send({"id": 2, "method": "account/rateLimits/read"})
        return response(2)
    except (queue.Empty, OSError, ValueError) as error:
        raise ValueError("Account quota unavailable; new LLM calls deferred") from error
    finally:
        if process.poll() is None:
            if os.name == "nt":
                # The CLI may be an npm shim: clean up its child server too.
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            else:
                process.terminate()
        process.wait(timeout=5)
        reader.join(timeout=1)
        process.stdin.close()
        process.stdout.close()


def quota_block_reason(snapshot: dict, threshold: float, grace_minutes: float,
                       now: float | None = None, weekly_threshold: float | None = None) -> str | None:
    """Only the five-hour window gets a near-reset exception."""
    now = time.time() if now is None else now
    buckets = snapshot.get("rateLimitsByLimitId")
    if not isinstance(buckets, dict) or not buckets:
        buckets = {"codex": snapshot.get("rateLimits")}
    found = False
    for bucket_id, bucket in buckets.items():
        if not isinstance(bucket, dict):
            raise ValueError("Account quota window unavailable")
        for name in ("primary", "secondary"):
            window = bucket.get(name)
            if window is None:
                continue
            if not isinstance(window, dict):
                raise ValueError("Account quota window invalid")
            used = window.get("usedPercent")
            duration = window.get("windowDurationMins")
            reset = window.get("resetsAt")
            if any(isinstance(v, bool) or not isinstance(v, (int, float))
                   or not math.isfinite(v) for v in (used, duration, reset)):
                raise ValueError("Account quota timing/usage unavailable")
            if not 0 <= used <= 100 or duration <= 0 or reset <= now:
                raise ValueError("Account quota snapshot invalid or expired")
            found = True
            cutoff = weekly_threshold if duration == 10080 and weekly_threshold is not None else threshold
            if used >= cutoff and not (duration == 300 and reset - now <= grace_minutes * 60):
                return f"account quota {bucket_id} {duration:g}-minute window {used:g}% used"
    if not found:
        raise ValueError("Account quota windows unavailable")
    return None
