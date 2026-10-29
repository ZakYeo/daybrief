"""Disposable native-hook probe; no brief persistence or product API."""
import json
import sys
from pathlib import Path

payload = json.load(sys.stdin)
root = Path(sys.argv[1])
event = payload.get("hook_event_name", "sessionStart")
with (root / "events.jsonl").open("a") as log:
    log.write(json.dumps({"event": event}) + "\n")
context = (root / "context.txt").read_text()
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": event, "additionalContext": context
}}))
