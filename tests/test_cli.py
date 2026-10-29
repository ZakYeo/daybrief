import json
import os
import subprocess
import sys
from pathlib import Path


def invoke(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "daybrief", "--json", *args],
        cwd=root,
        env=dict(os.environ, DAYBRIEF_DATA_DIR=str(root / "data"), TZ="Europe/London"),
        capture_output=True,
        text=True,
    )


def test_real_cli_lifecycle(tmp_path: Path) -> None:
    def call(*args: str):
        result = invoke(tmp_path, *args)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    call("config", "set", "scope", "global")
    first = call("--for", "1mo", "Use staging")
    assert first["timezone"] == "Europe/London"
    assert first["scope"] == "global"
    edited = call("edit", first["id"], "Use fixtures")
    assert edited["expires_at"] == first["expires_at"]
    extended = call("extend", first["id"], "2", "days")
    assert extended["expires_at"] > first["expires_at"]
    assert call("show", first["id"])["message"] == "Use fixtures"
    assert len(call("list")) == 1
    call("delete", first["id"])
    assert call("list") == []
    assert call("list", "--all")[0]["status"] == "deleted"
    call("Use fixtures today")
    assert call("clear")["cleared"] == 1


def test_invalid_and_ambiguous_cli_input(tmp_path: Path) -> None:
    for args in [
        ("--scope", "global", "--for", "0d", "Bad"),
        ("--scope", "global", "Avoid deployments until Friday"),
        ("--scope", "repo", "list"),
    ]:
        result = invoke(tmp_path, *args)
        assert result.returncode == 2
        assert "daybrief:" in result.stderr
        assert "Traceback" not in result.stderr


def test_cli_scopes_and_timezone_overrides(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)

    def call(*args: str):
        result = invoke(tmp_path, *args)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    global_brief = call("--scope", "global", "Global guidance")
    repo = call("--timezone", "America/New_York", "Local guidance")
    assert repo["timezone"] == "America/New_York"
    assert {item["id"] for item in call("list")} == {repo["id"], global_brief["id"]}
    edited = call("edit", repo["id"], "Updated", "--until", "2099-01-01")
    assert edited["expires_at"] == "2099-01-01T05:00:00+00:00"
    changed_zone = call("edit", repo["id"], "Updated", "--timezone", "UTC", "--until", "2099-01-01")
    assert changed_zone["expires_at"] == "2099-01-01T00:00:00+00:00"
    assert changed_zone["timezone"] == "UTC"
    assert call("clear")["cleared"] == 1
    assert [item["id"] for item in call("list")] == [global_brief["id"]]
