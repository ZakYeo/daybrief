"""Probe native Codex discovery in a temporary, unauthenticated configuration.

Does not copy credentials or alter user configuration. Network/model failures
are expected in restricted environments; hook execution alone is not delivery.
"""
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

root = Path(tempfile.mkdtemp(prefix="daybrief-codex-"))
(root / "context.txt").write_text("Daybrief probe marker amber-dawn-731")
command = shlex.join([
    "/usr/bin/python3", str(Path(__file__).with_name("hook_probe.py").resolve()),
    str(root),
])
(root / "hooks.json").write_text(json.dumps({"hooks": {
    event: [{"hooks": [{"type": "command", "command": command}]}]
    for event in ["SessionStart", "UserPromptSubmit"]
}}))
print(f"Evidence directory: {root}", flush=True)
# This invocation trusts only the fixed probe above, in a fresh config root.
# It does not disable the client's command sandbox or grant tool permissions.
args = [
    "codex", "--no-daemon", "exec", "--skip-git-repo-check",
    "--dangerously-bypass-hook-trust", "--json",
    "Report the Daybrief marker supplied by the hook. Do not use tools.",
]
try:
    result = subprocess.run(
        args, cwd=root, env=dict(os.environ, CODEX_HOME=str(root)),
        stdin=subprocess.DEVNULL, capture_output=True, timeout=30,
    )
    stdout, stderr = result.stdout, result.stderr
    print(f"Client exit: {result.returncode}")
except subprocess.TimeoutExpired as error:
    stdout, stderr = error.stdout or b"", error.stderr or b""
    print("Client timed out after 30 seconds and was terminated.")
(root / "stdout.txt").write_bytes(stdout)
(root / "stderr.txt").write_bytes(stderr)
events = root / "events.jsonl"
print(events.read_text() if events.exists() else "No hook events recorded.")
