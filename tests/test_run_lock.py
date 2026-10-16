import subprocess
import sys
from pathlib import Path

from processors.run_lock import KnowledgeBaseRunLock


def test_run_lock_blocks_a_second_process(tmp_path: Path) -> None:
    lock_path = tmp_path / "processor.lock"
    lock = KnowledgeBaseRunLock(lock_path)
    lock.acquire()
    try:
        script = """
import sys
from pathlib import Path
from processors.run_lock import KnowledgeBaseRunLock, RunAlreadyActive

lock = KnowledgeBaseRunLock(Path(sys.argv[1]))
try:
    lock.acquire()
except RunAlreadyActive as error:
    print(error)
    raise SystemExit(0)
raise SystemExit(1)
"""
        result = subprocess.run(
            [sys.executable, "-c", script, str(lock_path)],
            cwd=Path(__file__).parents[1],
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        lock.release()

    assert result.returncode == 0
    assert "already active" in result.stdout
