"""Validate built archives and observable workflows in a clean wheel environment."""

import argparse
import json
import os
import shlex
import subprocess
import tarfile
import tempfile
import zipfile
from datetime import datetime, timedelta
from email.parser import BytesParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def archives() -> Path:
    wheel = ROOT / "dist/daybrief-0.1.0-py3-none-any.whl"
    source = ROOT / "dist/daybrief-0.1.0.tar.gz"
    with zipfile.ZipFile(wheel) as package:
        names = package.namelist()
        metadata = BytesParser().parsebytes(package.read("daybrief-0.1.0.dist-info/METADATA"))
        assert not metadata.get_all("Requires-Dist"), "Unexpected runtime dependency"
        assert metadata["License-Expression"] == "MIT"
        assert (
            package.read("daybrief-0.1.0.dist-info/licenses/LICENSE")
            == (ROOT / "LICENSE").read_bytes()
        )
        assert "daybrief/resources/SKILL.md" in names
        assert all(name.startswith(("daybrief/", "daybrief-0.1.0.dist-info/")) for name in names)
    with tarfile.open(source) as package:
        names += package.getnames()
        assert "daybrief-0.1.0/README.md" in names
        assert "daybrief-0.1.0/docs/assets/daybrief-banner.png" in names
    for name in names:
        parts = Path(name).parts
        assert not any(part in {".git", ".venv", ".codex", ".claude", ".copilot"} for part in parts)
        assert not name.endswith((".sqlite", ".sqlite-wal", ".sqlite-shm", ".pyc"))
    print("PASS: wheel/sdist contents, complete MIT license, no runtime dependencies or state.")
    return wheel


def verify(wheel: Path, native: bool) -> None:
    with tempfile.TemporaryDirectory(prefix="daybrief-release-") as directory:
        root = Path(directory)
        home, repo = root / "home", root / "repo"
        home.mkdir()
        repo.mkdir()
        environment = dict(
            os.environ, HOME=str(home), DAYBRIEF_DATA_DIR=str(root / "data"), TZ="UTC"
        )

        def run(args: list[str], cwd: Path = repo) -> str:
            result = subprocess.run(args, cwd=cwd, env=environment, capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(result.stdout + result.stderr)
            return result.stdout

        run(["uv", "venv", str(root / "env"), "--python", "3.12"])
        python = root / "env/bin/python"
        run(["uv", "pip", "install", "--python", str(python), "--no-deps", str(wheel)])
        executable = str(root / "env/bin/daybrief")
        run(["git", "init", "-q"])
        assert "Commands:" in run([executable, "--help"])

        def cli(*args: str) -> Any:
            return json.loads(run([executable, "--json", *args]))

        brief = cli("Staging is being restored; use local fixtures today")
        created = datetime.fromisoformat(brief["created_at"])
        expires = datetime.fromisoformat(brief["expires_at"])
        assert expires == (created + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        original_expiry = brief["expires_at"]
        identifier = brief["id"]
        assert cli("edit", identifier, "Use local fixtures")["expires_at"] == original_expiry
        assert cli("extend", identifier, "2", "days")["expires_at"] > original_expiry
        assert cli("show", identifier)["message"] == "Use local fixtures"
        cli("delete", identifier)
        assert cli("list") == []
        assert cli("list", "--all")[0]["status"] == "deleted"
        global_brief = cli("--scope", "global", "--for", "1mo", "Use staging")
        local = cli("Repo-specific guidance")
        for client, relative, event in [
            ("codex", "hooks.json", "SessionStart"),
            ("claude", "settings.json", "SessionStart"),
            ("copilot", "hooks/daybrief.json", "sessionStart"),
        ]:
            profile = home / f".{client}"
            run([executable, "install", client])
            config = json.loads((profile / relative).read_text())
            entry = config["hooks"][event][0]
            command = entry["bash"] if client == "copilot" else entry["hooks"][0]["command"]
            result = subprocess.run(
                shlex.split(command),
                input=json.dumps({"cwd": str(repo)}),
                cwd=repo,
                env=environment,
                capture_output=True,
                text=True,
                check=True,
            )
            assert global_brief["id"] in result.stdout and local["id"] in result.stdout
            assert identifier not in result.stdout
            run([executable, "uninstall", client])
            assert not (profile / "skills/daybrief/SKILL.md").exists()
        assert cli("clear")["cleared"] == 1
        assert [item["id"] for item in cli("list")] == [global_brief["id"]]
        cli("config", "set", "expiry", "24h")
        assert cli("config")["expiry"]["seconds"] == 86400
        print("PASS: clean wheel CLI lifecycle, defaults, scope, packaged adapters and removal.")
        if native:
            for client in ("codex", "claude", "copilot"):
                for mode in ("--skill", "--interactive"):
                    print(
                        run(
                            [
                                str(python),
                                str(ROOT / "spikes/installed_adapter_probe.py"),
                                client,
                                mode,
                            ]
                        ),
                        end="",
                    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--native", action="store_true", help="Also run installed native-client probes"
    )
    args = parser.parse_args()
    verify(archives(), args.native)


if __name__ == "__main__":
    main()
