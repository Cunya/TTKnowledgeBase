from pathlib import Path

from processors.utils import read_json, write_json


def test_write_json_retries_transient_windows_replace_lock(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "ledger.json"
    original_replace = Path.replace
    attempts: list[tuple[Path, Path]] = []

    def flaky_replace(source: Path, destination: Path) -> Path:
        attempts.append((source, destination))
        if len(attempts) < 3:
            raise PermissionError(13, "Access is denied", str(destination))
        return original_replace(source, destination)

    monkeypatch.setattr(Path, "replace", flaky_replace)
    monkeypatch.setattr("processors.utils.time.sleep", lambda _: None)

    write_json(target, {"status": "ok"})

    assert len(attempts) == 3
    assert read_json(target) == {"status": "ok"}
    assert not list(tmp_path.glob(".*.tmp"))
