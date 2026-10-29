"""Native hook protocol entry point; receives client JSON on standard input."""

import argparse
import json
import sys
from pathlib import Path

from daybrief.config import Config
from daybrief.context import data_directory
from daybrief.delivery import snapshot, unavailable
from daybrief.service import Daybrief
from daybrief.storage import StorageError, Store

EVENTS = {
    "codex": ("SessionStart", "UserPromptSubmit", "PostToolUse"),
    "claude": ("SessionStart", "UserPromptSubmit", "PostToolUse"),
    "copilot": ("sessionStart", "userPromptTransformed", "postToolUse"),
}


def envelope(
    client: str, event: str, payload: dict[str, object], context: str
) -> dict[str, object]:
    if event not in EVENTS[client]:
        raise ValueError(f"Unsupported {client} hook event: {event}")
    if client == "copilot":
        if event == "userPromptTransformed":
            original = payload.get("transformedPrompt")
            if not isinstance(original, str):
                raise ValueError("Copilot hook requires transformedPrompt text.")
            return {"modifiedTransformedPrompt": original + "\n\n" + context}
        return {"additionalContext": context}
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": context}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("client", choices=EVENTS)
    parser.add_argument("event")
    args = parser.parse_args()
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError("Hook input must be a JSON object.")
        directory = payload.get("cwd", str(Path.cwd()))
        if not isinstance(directory, str) or not Path(directory).is_absolute():
            raise ValueError("Hook cwd must be an absolute path.")
        try:
            app = Daybrief(Store(data_directory() / "state.sqlite"), Config("UTC"))
            context = snapshot(app, Path(directory))
        except (StorageError, OSError, ValueError) as error:
            print(f"daybrief: {error}", file=sys.stderr)
            context = unavailable(error)
        print(json.dumps(envelope(args.client, args.event, payload, context), ensure_ascii=False))
    except (ValueError, OSError) as error:
        print(f"daybrief hook: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
