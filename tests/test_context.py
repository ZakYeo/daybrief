import subprocess
from pathlib import Path

import pytest

from daybrief.config import Config
from daybrief.context import data_directory, local_timezone, repository_scope


def test_worktrees_share_scope_but_clones_do_not(tmp_path: Path) -> None:
    repo, worktree, clone = (tmp_path / name for name in ("repo", "worktree", "clone"))
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "--allow-empty",
            "-m",
            "initial",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "worktree", "add", "-b", "other", str(worktree)], cwd=repo, check=True)
    subprocess.run(["git", "clone", "--no-hardlinks", str(repo), str(clone)], check=True)
    assert repository_scope(repo) == repository_scope(worktree)
    assert repository_scope(repo) != repository_scope(clone)
    nested = repo / "nested"
    nested.mkdir()
    assert repository_scope(nested) == repository_scope(repo)
    with pytest.raises(ValueError, match="global"):
        repository_scope(tmp_path)


def test_storage_precedence_and_invalid_xdg_path(tmp_path: Path) -> None:
    assert data_directory({}, tmp_path) == tmp_path / ".local/share/daybrief"
    assert data_directory({"XDG_DATA_HOME": str(tmp_path)}) == tmp_path / "daybrief"
    assert data_directory({"DAYBRIEF_DATA_DIR": str(tmp_path)}) == tmp_path
    with pytest.raises(ValueError, match="absolute"):
        data_directory({"XDG_DATA_HOME": "relative"})


def test_timezone_discovery_requires_named_zone(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    assert local_timezone({"TZ": "Europe/London"}, missing, missing) == "Europe/London"
    with pytest.raises(ValueError, match="IANA"):
        local_timezone({"TZ": "BST"}, missing, missing)
    timezone_file = tmp_path / "timezone"
    timezone_file.write_text("Europe/Paris\n")
    assert local_timezone({}, missing, timezone_file) == "Europe/Paris"


def test_invalid_configuration_is_rejected() -> None:
    with pytest.raises(ValueError, match="scope"):
        Config("UTC", scope="everything")
    with pytest.raises(KeyError):
        Config("Not/AZone")
