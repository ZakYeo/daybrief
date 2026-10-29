"""Exercise real Git hooks against isolated indexes, including partial staging."""

import shutil
import subprocess
from pathlib import Path


def test_precommit_uses_index_and_preserves_worktree(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[1]
    shutil.copytree(source / ".githooks", tmp_path / ".githooks")
    shutil.copytree(source / "scripts", tmp_path / "scripts")
    shutil.copy(source / "pyproject.toml", tmp_path)
    (tmp_path / ".venv").symlink_to(source / ".venv", target_is_directory=True)

    def git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=tmp_path, capture_output=True, text=True)

    assert git("init", "-q").returncode == 0
    assert git("config", "commit.gpgsign", "false").returncode == 0
    assert git("config", "user.name", "Hook Test").returncode == 0
    assert git("config", "user.email", "hook-test@example.invalid").returncode == 0
    subprocess.run(["python3", "scripts/install_hooks.py"], cwd=tmp_path, check=True)
    path = tmp_path / "example with spaces.py"
    path.write_text("value = 1\n")
    assert git("add", "pyproject.toml", path.name).returncode == 0
    path.write_text("value=2\n")
    result = git("commit", "-m", "valid staged content")
    assert result.returncode == 0, result.stdout + result.stderr
    assert path.read_text() == "value=2\n"
    assert git("show", f"HEAD:{path.name}").stdout == "value = 1\n"

    assert git("add", path.name).returncode == 0
    path.write_text("value = 3\n")
    before = git("write-tree").stdout
    result = git("commit", "-m", "invalid staged content")
    assert result.returncode != 0
    assert "reformat" in result.stdout + result.stderr
    assert git("write-tree").stdout == before
    assert path.read_text() == "value = 3\n"


def test_hook_install_preserves_existing_config(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "install_hooks.py"
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "config", "core.hooksPath", "custom-hooks"], cwd=tmp_path, check=True)
    result = subprocess.run(["python3", str(script)], cwd=tmp_path, capture_output=True)
    assert result.returncode != 0
    value = subprocess.check_output(["git", "config", "core.hooksPath"], cwd=tmp_path, text=True)
    assert value.strip() == "custom-hooks"


def test_hook_install_preserves_default_hooks(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "install_hooks.py"
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    hook = tmp_path / ".git/hooks/post-checkout"
    hook.write_text("#!/bin/sh\nexit 0\n")
    hook.chmod(0o755)
    result = subprocess.run(["python3", str(script)], cwd=tmp_path, capture_output=True)
    assert result.returncode != 0
    assert b"Existing default Git hooks" in result.stderr
    assert hook.read_text() == "#!/bin/sh\nexit 0\n"
    config = subprocess.run(["git", "config", "--local", "--get", "core.hooksPath"], cwd=tmp_path)
    assert config.returncode == 1
