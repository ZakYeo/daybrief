"""Install repository hooks without replacing an unrelated hooks directory."""

import subprocess


def main() -> None:
    current = subprocess.run(
        ["git", "config", "--get", "core.hooksPath"], capture_output=True, text=True
    )
    if current.returncode not in (0, 1):
        raise SystemExit(current.stderr)
    if current.stdout.strip() not in ("", ".githooks"):
        raise SystemExit("An existing core.hooksPath is configured; integrate .githooks manually.")
    subprocess.run(["git", "config", "--local", "core.hooksPath", ".githooks"], check=True)
    print("Installed pre-commit and pre-push hooks from .githooks.")


if __name__ == "__main__":
    main()
