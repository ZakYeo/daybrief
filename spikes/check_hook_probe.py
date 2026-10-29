"""Run protocol checks without client authentication or personal configuration."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

probe = Path(__file__).with_name("hook_probe.py")
with tempfile.TemporaryDirectory(prefix="daybrief-protocol-") as directory:
    root = Path(directory)
    contexts = [
        "Active b1: amber-dawn-731; expires 2026-10-30T00:00:00Z.",
        "Daybrief snapshot replaces previous snapshot. No active briefs; "
        "previous briefs withdrawn.",
    ]
    for context in contexts:
        (root / "context.txt").write_text(context)
        for event in ["SessionStart", "UserPromptSubmit"]:
            result = subprocess.run(
                [sys.executable, str(probe), directory],
                input=json.dumps({"hook_event_name": event}),
                capture_output=True, text=True, check=True,
            )
            assert json.loads(result.stdout) == {"hookSpecificOutput": {
                "hookEventName": event, "additionalContext": context,
            }}
    assert len((root / "events.jsonl").read_text().splitlines()) == 4
print("PASS: four protocol checks; native client delivery is not proven.")
