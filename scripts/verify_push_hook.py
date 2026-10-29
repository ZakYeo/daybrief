"""Exercise fresh-clone hook setup and push gates using only a temporary remote."""

import os
import subprocess
import tempfile
from pathlib import Path


def clean_environment() -> dict[str, str]:
    return {
        key: value for key, value in os.environ.items() if not key.startswith(("GIT_", "PYTHON"))
    }


def run(args: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(args, cwd=cwd, env=clean_environment(), capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="daybrief-push-check-") as directory:
        root = Path(directory)
        clone, remote = root / "checkout", root / "remote.git"
        source = Path(__file__).resolve().parents[1]
        run(["git", "clone", "--no-hardlinks", str(source), str(clone)])
        run(["git", "init", "--bare", str(remote)])
        run(["uv", "sync", "--frozen", "--offline"], clone)
        run(["uv", "run", "--frozen", "python", "scripts/install_hooks.py"], clone)
        run(["git", "remote", "set-url", "origin", str(remote)], clone)
        run(["git", "push", "origin", "HEAD:refs/heads/main"], clone)
        (clone / "src/daybrief/broken.py").write_text("value=1\n")
        result = subprocess.run(
            ["git", "push", "origin", "HEAD:refs/heads/failure-check"],
            cwd=clone,
            env=clean_environment(),
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, "Broken checkout unexpectedly passed pre-push"
        assert "reformat" in result.stdout + result.stderr
        refs = run(["git", "--git-dir", str(remote), "for-each-ref", "--format=%(refname)"])
        assert "refs/heads/main" in refs
        assert "failure-check" not in refs
        print("PASS: fresh-clone setup, successful push, and rejected failing push.")


if __name__ == "__main__":
    main()
