"""Install owned personal skills and merge only owned native hook entries."""

import argparse
import fcntl
import hashlib
import os
import shlex
import sys
from importlib.resources import files
from pathlib import Path
from typing import Any

from daybrief.hooks import EVENTS
from daybrief.install_files import apply_changes, checked_path, encoded, read_json

SETTINGS = {"codex": "hooks.json", "claude": "settings.json", "copilot": "hooks/daybrief.json"}
ENVIRONMENT = {"codex": "CODEX_HOME", "claude": "CLAUDE_CONFIG_DIR", "copilot": "COPILOT_HOME"}
SKILL = "skills/daybrief/SKILL.md"
MANIFEST = ".daybrief-install.json"


def default_root(client: str) -> Path:
    override = os.environ.get(ENVIRONMENT[client])
    return Path(override).expanduser() if override else Path.home() / f".{client}"


def hook_entries(client: str) -> dict[str, list[dict[str, Any]]]:
    result = {}
    for event in EVENTS[client]:
        command = shlex.join([sys.executable, "-m", "daybrief.hooks", client, event])
        if client == "copilot":
            entry: dict[str, Any] = {"type": "command", "bash": command}
        else:
            entry = {"hooks": [{"type": "command", "command": command}]}
        result[event] = [entry]
    return result


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def validate_manifest(manifest: dict[str, Any], client: str) -> None:
    if manifest and (
        manifest.get("version") != 1
        or manifest.get("client") != client
        or not isinstance(manifest.get("skill_sha256"), str)
        or not isinstance(manifest.get("entries"), dict)
        or not isinstance(manifest.get("settings_existed"), bool)
        or not isinstance(manifest.get("hooks_existed"), bool)
    ):
        raise ValueError("Unknown or malformed Daybrief installation manifest.")


def merge_hooks(settings: dict[str, Any], old: dict[str, Any], new: dict[str, Any]) -> None:
    hooks = settings.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("Client hooks must be a JSON object.")
    for event in set(old) | set(new):
        entries = hooks.get(event, [])
        if not isinstance(entries, list) or not isinstance(old.get(event, []), list):
            raise ValueError(f"Malformed hooks for {event}.")
        for entry in old.get(event, []):
            if entries.count(entry) != 1:
                raise ValueError(
                    f"Owned {event} hook was changed; restore it before updating/removing."
                )
            entries.remove(entry)
        for entry in new.get(event, []):
            if entry in entries:
                raise ValueError(f"Unowned Daybrief hook collision for {event}.")
            entries.append(entry)
        if entries:
            hooks[event] = entries
        else:
            hooks.pop(event, None)


def install(client: str, root: Path, *, remove: bool = False) -> None:
    root = root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    lock = checked_path(root, ".daybrief-install.lock")
    with lock.open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        _install(client, root, remove=remove)


def _install(client: str, root: Path, *, remove: bool) -> None:
    manifest_path = checked_path(root, MANIFEST)
    skill_path = checked_path(root, SKILL)
    settings_path = checked_path(root, SETTINGS[client])
    manifest = read_json(manifest_path)
    validate_manifest(manifest, client)
    if not manifest and remove:
        return
    if manifest:
        if not skill_path.exists() or digest(skill_path.read_bytes()) != manifest["skill_sha256"]:
            raise ValueError(
                "Installed Daybrief skill was changed; restore it before updating/removing."
            )
    elif skill_path.exists():
        raise ValueError(f"Refusing to overwrite an unowned skill: {skill_path}")
    if client == "copilot" and not manifest and settings_path.exists():
        raise ValueError(f"Refusing to overwrite unowned hook file: {settings_path}")
    settings = read_json(settings_path)
    settings_existed = manifest.get("settings_existed", settings_path.exists())
    hooks_existed = manifest.get("hooks_existed", "hooks" in settings)
    if client == "copilot":
        if settings.get("version", 1) != 1:
            raise ValueError("Unsupported Copilot hook schema version.")
        settings["version"] = 1
    entries = {} if remove else hook_entries(client)
    merge_hooks(settings, manifest.get("entries", {}), entries)
    if remove and not settings["hooks"] and not hooks_existed:
        del settings["hooks"]
    if remove:
        if client == "copilot" and settings == {"version": 1}:
            settings = {}
        settings_content = encoded(settings) if settings or settings_existed else None
        apply_changes({settings_path: settings_content, skill_path: None, manifest_path: None})
        return
    command = shlex.join([sys.executable, "-m", "daybrief"])
    skill = (
        files("daybrief").joinpath("resources/SKILL.md").read_text().replace("@COMMAND@", command)
    )
    content = skill.encode()
    new_manifest = {
        "version": 1,
        "client": client,
        "skill_sha256": digest(content),
        "entries": entries,
        "settings_existed": settings_existed,
        "hooks_existed": hooks_existed,
    }
    apply_changes(
        {
            settings_path: encoded(settings),
            skill_path: content,
            manifest_path: encoded(new_manifest),
        }
    )


def main(arguments: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="daybrief " + arguments[0])
    parser.add_argument("client", choices=EVENTS)
    parser.add_argument(
        "--root", type=Path, help="Alternate personal client configuration directory"
    )
    args = parser.parse_args(arguments[1:])
    install(args.client, args.root or default_root(args.client), remove=arguments[0] == "uninstall")
    print(f"Daybrief {arguments[0]} complete for {args.client}.")
    if arguments[0] == "install":
        print("Restart the client to load the skill and hooks.")
        if args.client == "codex":
            print("Review and trust the Daybrief hooks in Codex's native hook trust prompt.")
