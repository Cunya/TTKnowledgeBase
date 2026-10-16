"""Cross-entry-point per-knowledge-base process locking."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO


class RunAlreadyActive(RuntimeError):
    """Raised when another process already owns a knowledge-base run lock."""


class KnowledgeBaseRunLock:
    """Hold an OS-level lock for the lifetime of one knowledge-base run."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.handle: TextIO | None = None

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+", encoding="utf-8")
        try:
            handle.seek(0, 2)
            if handle.tell() == 0:
                handle.write("{}")
                handle.flush()
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError as error:
                    raise RunAlreadyActive(self._existing_owner(handle)) from error
            else:
                import fcntl

                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError as error:
                    raise RunAlreadyActive(self._existing_owner(handle)) from error
            handle.seek(0)
            handle.truncate()
            json.dump(
                {
                    "pid": os.getpid(),
                    "started_at": datetime.now(UTC).isoformat(),
                },
                handle,
            )
            handle.flush()
            self.handle = handle
        except Exception:
            handle.close()
            raise

    @staticmethod
    def _existing_owner(handle: TextIO) -> str:
        try:
            handle.seek(0)
            payload = json.load(handle)
            return f"knowledge-base run already active (pid {payload.get('pid', 'unknown')})"
        except (OSError, ValueError, TypeError):
            return "knowledge-base run already active"

    def release(self) -> None:
        handle = self.handle
        self.handle = None
        if handle is None:
            return
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()

    def __enter__(self) -> KnowledgeBaseRunLock:
        self.acquire()
        return self

    def __exit__(self, _exc_type: object, _exc_value: object, _traceback: object) -> None:
        self.release()
