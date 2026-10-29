"""Install repository hooks without replacing an unrelated hooks directory."""

import os
import subprocess
from pathlib import Path


def main() -> None:
    current = subprocess.run(
        ["git", "config", "--get", "core.hooksPath"], capture_output=True, text=True
    )
    if current.returncode not in (0, 1):
        raise SystemExit(current.stderr)
    if current.stdout.strip() not in ("", ".githooks"):
        raise SystemExit("An existing core.hooksPath is configured; integrate .githooks manually.")
    if not current.stdout.strip():
        hooks = Path(
            subprocess.check_output(["git", "rev-parse", "--git-path", "hooks"], text=True).strip()
        )
        if hooks.is_dir() and any(
            path.is_file() and not path.name.endswith(".sample") and os.access(path, os.X_OK)
            for path in hooks.iterdir()
        ):
            raise SystemExit("Existing default Git hooks found; integrate .githooks manually.")
    subprocess.run(["git", "config", "--local", "core.hooksPath", ".githooks"], check=True)
    print("Installed pre-commit and pre-push hooks from .githooks.")


if __name__ == "__main__":
    main()
