"""Check staged Python content without stashing or modifying the worktree."""

import os
import subprocess
import tempfile
from pathlib import Path


def main() -> None:
    root = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
    names = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"], cwd=root
    )
    files = [os.fsdecode(name) for name in names.split(b"\0") if name.endswith(b".py")]
    subprocess.run(["git", "diff", "--cached", "--check"], cwd=root, check=True)
    if not files:
        return
    ruff = root / ".venv" / "bin" / "ruff"
    if not ruff.is_file():
        raise SystemExit("Run uv sync --frozen before committing Python changes.")
    with tempfile.TemporaryDirectory(prefix="daybrief-index-") as directory:
        subprocess.run(
            ["git", "checkout-index", "--all", f"--prefix={directory}/"], cwd=root, check=True
        )
        for arguments in (["format", "--check"], ["check"]):
            subprocess.run(
                [str(ruff), *arguments, "--force-exclude", "--", *files],
                cwd=directory,
                check=True,
            )


if __name__ == "__main__":
    main()
