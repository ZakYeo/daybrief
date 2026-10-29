import json
from pathlib import Path

import pytest

from daybrief.install import MANIFEST, SETTINGS, SKILL, install
from daybrief.install_files import apply_changes


@pytest.mark.parametrize("client", ["codex", "claude", "copilot"])
def test_install_update_remove_preserves_user_configuration(tmp_path, client):
    root = tmp_path / client
    root.mkdir()
    settings_path = root / SETTINGS[client]
    original = {"custom": {"unchanged": True}, "hooks": {"OtherEvent": [{"custom": "hook"}]}}
    if client != "copilot":
        settings_path.write_text(json.dumps(original))
    instructions = root / "AGENTS.md"
    instructions.write_text("User instructions")
    install(client, root)
    skill = (root / SKILL).read_bytes()
    assert b"@COMMAND@" not in skill
    installed = settings_path.read_bytes()
    install(client, root)
    assert settings_path.read_bytes() == installed
    # User edits to unrelated settings after installation also survive removal.
    current = json.loads(settings_path.read_text())
    current["after_install"] = 42
    settings_path.write_text(json.dumps(current))
    install(client, root, remove=True)
    remaining = json.loads(settings_path.read_text())
    if client != "copilot":
        assert remaining == dict(original, after_install=42)
    else:
        assert remaining == {"version": 1, "after_install": 42}
    assert instructions.read_text() == "User instructions"
    assert not (root / SKILL).exists()
    assert not (root / MANIFEST).exists()
    install(client, root, remove=True)


@pytest.mark.parametrize("client", ["codex", "claude", "copilot"])
def test_clean_uninstall_removes_generated_files(tmp_path, client):
    install(client, tmp_path)
    install(client, tmp_path, remove=True)
    assert not (tmp_path / SETTINGS[client]).exists()
    assert not (tmp_path / SKILL).exists()


def test_modified_owned_content_and_collisions_are_preserved(tmp_path):
    skill = tmp_path / SKILL
    skill.parent.mkdir(parents=True)
    skill.write_text("User skill")
    with pytest.raises(ValueError, match="unowned"):
        install("codex", tmp_path)
    assert skill.read_text() == "User skill"
    skill.unlink()
    install("codex", tmp_path)
    original = skill.read_bytes()
    skill.write_text("User modification")
    for remove in (False, True):
        with pytest.raises(ValueError, match="changed"):
            install("codex", tmp_path, remove=remove)
    skill.write_bytes(original)
    config = tmp_path / SETTINGS["codex"]
    value = json.loads(config.read_text())
    value["hooks"]["SessionStart"][0]["hooks"][0]["command"] = "custom hook"
    config.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="changed"):
        install("codex", tmp_path, remove=True)
    assert "custom hook" in config.read_text()
    assert skill.exists()


def test_malformed_config_and_symlink_fail_without_overwrite(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text("{malformed")
    with pytest.raises(ValueError):
        install("claude", tmp_path)
    assert settings.read_text() == "{malformed"
    settings.unlink()
    target = tmp_path / "target"
    target.write_text("{}")
    settings.symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        install("claude", tmp_path)
    assert target.read_text() == "{}"


def test_failed_install_write_rolls_back(tmp_path, monkeypatch):
    from daybrief import install_files

    first, second = tmp_path / "first", tmp_path / "second"
    first.write_bytes(b"original")
    original_write = install_files.atomic_write

    def fail_second(path: Path, content):
        if path == second:
            raise OSError("injected write failure")
        original_write(path, content)

    monkeypatch.setattr(install_files, "atomic_write", fail_second)
    with pytest.raises(OSError, match="injected"):
        apply_changes({first: b"changed", second: b"new"})
    assert first.read_bytes() == b"original"
    assert not second.exists()


def test_generated_commands_ignore_cwd_and_pythonpath_shadowing(tmp_path):
    import os
    import subprocess

    root = tmp_path / "profile"
    work = tmp_path / "work"
    injected = tmp_path / "injected"
    work.mkdir()
    injected.mkdir()
    shadow = 'raise RuntimeError("LOCAL_MODULE_EXECUTED")\n'
    (work / "daybrief.py").write_text(shadow)
    (injected / "daybrief.py").write_text(shadow)
    install("codex", root)
    environment = dict(
        os.environ, PYTHONPATH=str(injected), DAYBRIEF_DATA_DIR=str(tmp_path / "data"), TZ="UTC"
    )
    settings = json.loads((root / SETTINGS["codex"]).read_text())
    command = settings["hooks"]["SessionStart"][0]["hooks"][0]["command"]
    result = subprocess.run(
        command,
        shell=True,
        input=json.dumps({"cwd": str(work)}),
        cwd=work,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    assert (
        "daybrief_snapshot_at"
        in json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    )
    skill = (root / SKILL).read_text()
    command = skill.split("```sh\n", 1)[1].split("\n```", 1)[0]
    result = subprocess.run(
        command + " --scope global --json 'Isolated skill command'",
        shell=True,
        cwd=work,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout)["message"] == "Isolated skill command"
