"""Filesystem and Git discovery boundaries."""

import os
import subprocess
from collections.abc import Mapping
from pathlib import Path
from zoneinfo import ZoneInfo


def data_directory(environment: Mapping[str, str] | None = None, home: Path | None = None) -> Path:
    environment = os.environ if environment is None else environment
    home = Path.home() if home is None else home
    override = environment.get("DAYBRIEF_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    base = environment.get("XDG_DATA_HOME")
    if base and not Path(base).is_absolute():
        raise ValueError("XDG_DATA_HOME must be an absolute path.")
    return (Path(base) if base else home / ".local/share") / "daybrief"


def repository_scope(directory: Path) -> str:
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    result = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        cwd=directory,
        env=environment,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise ValueError("No Git repository here; select --scope global or enter a repository.")
    return "repo:" + str(Path(result.stdout.strip()).resolve())


def local_timezone(
    environment: Mapping[str, str] | None = None,
    localtime: Path = Path("/etc/localtime"),
    timezone_file: Path = Path("/etc/timezone"),
) -> str:
    """Discover an IANA name without guessing from an abbreviation or UTC offset."""
    environment = os.environ if environment is None else environment
    candidates = []
    if environment.get("TZ"):
        candidates.append(environment["TZ"].removeprefix(":"))
    try:
        target = str(localtime.resolve(strict=True))
        if "/zoneinfo/" in target:
            candidates.append(target.split("/zoneinfo/", 1)[1])
    except OSError:
        pass
    try:
        candidates.append(timezone_file.read_text().strip())
    except OSError:
        pass
    for candidate in candidates:
        if "/" not in candidate and candidate not in ("UTC", "Etc/UTC"):
            continue
        try:
            ZoneInfo(candidate)
        except (KeyError, ValueError):
            continue
        return candidate
    raise ValueError("Cannot determine the local IANA timezone; set config timezone explicitly.")
