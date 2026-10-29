"""Command-line parsing and presentation over the shared lifecycle service."""

import argparse
import json
import sys
from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from daybrief.config import Config
from daybrief.context import data_directory, local_timezone, repository_scope
from daybrief.install import main as installation_main
from daybrief.model import Brief
from daybrief.parsing import deadline, duration, message_expiry
from daybrief.service import Daybrief
from daybrief.storage import StorageError, Store

COMMANDS = {
    "create",
    "list",
    "show",
    "edit",
    "extend",
    "delete",
    "clear",
    "config",
    "install",
    "uninstall",
}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="daybrief",
        description="Temporary instructions for coding agents.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Commands:
  create MESSAGE            Create a brief (create may be omitted)
  list [--all]              List applicable briefs; --all includes history
  show ID                   Inspect a brief
  edit ID MESSAGE           Edit, preserving expiry unless overridden
  extend ID DURATION        Add time to the existing expiry
  delete ID                 Withdraw a brief
  clear                     Withdraw active briefs in the selected scope
  config                    Show defaults
  config set timezone ZONE  Set an IANA timezone
  config set scope SCOPE    Set repo or global as the default
  config set expiry VALUE   Set today (next midnight) or a duration
  install CLIENT [--root DIR]    Install codex, claude, or copilot integration
  uninstall CLIENT [--root DIR]  Remove owned integration files and hooks

Examples:
  daybrief "Focus on checkout today"
  daybrief --scope global --for 1mo "Use staging"
  daybrief edit ID "Use fixtures" --until 2027-03-04T17:00
  daybrief extend ID 2 days""",
    )
    result.add_argument("--scope", choices=("repo", "global"))
    result.add_argument("--timezone", help="IANA timezone override")
    result.add_argument("--for", dest="lifetime", help="Duration, such as 24h or 1mo")
    result.add_argument("--until", help="ISO date or timestamp")
    result.add_argument(
        "--literal", action="store_true", help="Do not interpret message expiry phrases"
    )
    result.add_argument("--all", action="store_true", help="Include expired and deleted history")
    result.add_argument("--json", action="store_true", help="Machine-readable output")
    result.add_argument("words", nargs="*", help="Command and arguments, or a new brief message")
    return result


def record(brief: Brief, now: datetime) -> dict[str, object]:
    data: dict[str, object] = asdict(brief)
    for key in ("created_at", "updated_at", "expires_at", "deleted_at"):
        value = data[key]
        data[key] = value.isoformat() if isinstance(value, datetime) else value
    data["status"] = brief.status(now)
    data["expires_local"] = brief.expires_at.astimezone(ZoneInfo(brief.timezone)).isoformat()
    return data


def emit(value: object, as_json: bool, details: bool = False) -> None:
    if as_json:
        print(json.dumps(value, ensure_ascii=False))
    elif isinstance(value, list):
        if not value:
            print("No briefs.")
        for item in value:
            emit(item, False)
    elif isinstance(value, dict):
        if "message" in value:
            print(f"{value['id']} [{value['scope']}] {value['status']}: {value['message']}")
            print(f"Expires {value['expires_local']} ({value['timezone']})")
            if details:
                for key in ("created_at", "updated_at", "deleted_at", "revision"):
                    print(f"{key}: {value[key]}")
        else:
            for key, item in value.items():
                print(f"{key}: {item}")
    else:
        print(value)


def application(args: argparse.Namespace) -> Daybrief:
    store = Store(data_directory() / "state.sqlite")
    with store.transaction() as tx:
        saved = tx.config()
    setting_timezone = (
        args.words[3]
        if len(args.words) == 4 and args.words[:3] == ["config", "set", "timezone"]
        else None
    )
    defaults = saved or Config(args.timezone or setting_timezone or local_timezone())
    if args.timezone:
        defaults = replace(defaults, timezone=args.timezone)
    return Daybrief(store, defaults)


def arguments(words: list[str], count: int, usage: str) -> None:
    if len(words) != count:
        raise ValueError(f"Usage: daybrief {usage}")


def configure(app: Daybrief, words: list[str]) -> Config:
    current = app.configuration()
    if not words:
        return current
    arguments(words, 3, "config set timezone|scope|expiry VALUE")
    action, key, value = words
    if action != "set":
        raise ValueError("Use config set timezone|scope|expiry VALUE.")
    if key == "timezone":
        current = replace(current, timezone=value)
    elif key == "scope":
        current = replace(current, scope=value)
    elif key == "expiry":
        current = replace(current, expiry=None if value == "today" else duration(value))
    else:
        raise ValueError("Setting must be timezone, scope, or expiry.")
    app.configure(current)
    return current


def dispatch(args: argparse.Namespace) -> object:
    words = list(args.words)
    command = words.pop(0) if words and words[0] in COMMANDS else "create"
    if command in ("install", "uninstall"):
        raise ValueError(f"Use daybrief {command} CLIENT [--root DIR], without brief options.")
    if command not in ("create", "edit") and (args.lifetime or args.until or args.literal):
        raise ValueError("Expiry flags and --literal apply only to create and edit.")
    if args.all and command != "list":
        raise ValueError("--all applies only to list.")
    app = application(args)
    config = app.configuration()
    if args.timezone:
        config = replace(config, timezone=args.timezone)
    if command == "config":
        return asdict(configure(app, words))
    selected = args.scope or config.scope
    try:
        repo = repository_scope(Path.cwd())
    except ValueError:
        repo = None
    scope = "global" if selected == "global" else repo
    if args.scope == "repo" and repo is None:
        raise ValueError("No repository here; use --scope global.")
    read_scopes = (scope,) if args.scope and scope else ("global", repo) if repo else ("global",)
    now = app.clock.now()
    if command == "list":
        arguments(words, 0, "list [--all]")
        return [record(item, now) for item in app.list(read_scopes, include_all=args.all)]
    if command == "show":
        arguments(words, 1, "show ID")
        return record(app.show(words[0], read_scopes), now)
    if scope is None:
        raise ValueError("No repository here; use --scope global.")
    if command == "clear":
        arguments(words, 0, "clear")
        return {"cleared": app.clear(scope), "scope": scope}
    if command == "delete":
        arguments(words, 1, "delete ID")
        return record(app.delete(words[0], scope), now)
    if command == "extend":
        if len(words) < 2:
            raise ValueError("Usage: daybrief extend ID DURATION")
        return record(app.extend(words[0], scope, duration(" ".join(words[1:]))), now)
    identifier = words.pop(0) if command == "edit" and words else None
    if not words:
        raise ValueError("Provide a message; use daybrief --help for commands.")
    if identifier is not None and not args.timezone:
        config = replace(config, timezone=app.show(identifier, (scope,)).timezone)
    parsed = message_expiry(
        " ".join(words),
        now,
        config.zone,
        literal=args.literal,
        explicit=bool(args.lifetime or args.until),
    )
    lifetime = duration(args.lifetime) if args.lifetime else parsed.duration
    until = deadline(args.until, config.zone) if args.until else parsed.until
    if command == "edit":
        assert identifier is not None
        return record(
            app.edit(
                identifier,
                scope,
                parsed.message,
                duration=lifetime,
                until=until,
                timezone=args.timezone,
            ),
            now,
        )
    return record(
        app.create(parsed.message, scope, duration=lifetime, until=until, timezone=args.timezone),
        now,
    )


def main() -> None:
    try:
        if len(sys.argv) > 1 and sys.argv[1] in ("install", "uninstall"):
            installation_main(sys.argv[1:])
            return
        args = parser().parse_intermixed_args()
        emit(dispatch(args), args.json, details=bool(args.words and args.words[0] == "show"))
    except (ValueError, KeyError, StorageError, OSError, OverflowError) as error:
        print(f"daybrief: {error}", file=sys.stderr)
        raise SystemExit(2) from None
