"""Small filesystem boundary for conservative adapter installation."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def checked_path(root: Path, relative: str) -> Path:
    path = root / relative
    if Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError("Invalid installation manifest path.")
    for part in (path, *path.parents):
        if part == root:
            break
        if part.is_symlink():
            raise ValueError(f"Refusing symlink in installation path: {part}")
    return path


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def encoded(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


def atomic_write(path: Path, content: bytes | None) -> None:
    if content is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".daybrief-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            os.chmod(temporary, path.stat().st_mode & 0o777)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def apply_changes(changes: dict[Path, bytes | None]) -> None:
    originals = {path: path.read_bytes() if path.exists() else None for path in changes}
    completed: list[Path] = []
    try:
        for path, content in changes.items():
            atomic_write(path, content)
            completed.append(path)
    except OSError:
        for path in reversed(completed):
            atomic_write(path, originals[path])
        raise
