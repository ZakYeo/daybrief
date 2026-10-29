"""Run the deterministic contributor and CI gate."""

import subprocess


def main() -> None:
    commands = [
        ["uv", "lock", "--check"],
        ["uv", "run", "--frozen", "ruff", "format", "--check", "."],
        ["uv", "run", "--frozen", "ruff", "check", "."],
        ["uv", "run", "--frozen", "mypy"],
        ["uv", "run", "--frozen", "pytest"],
        ["uv", "build", "--no-build-isolation"],
    ]
    for command in commands:
        print("+ " + " ".join(command), flush=True)
        subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
