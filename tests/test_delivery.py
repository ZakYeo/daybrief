import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta

from daybrief.config import Config
from daybrief.delivery import snapshot
from daybrief.hooks import EVENTS, envelope
from daybrief.service import Daybrief
from daybrief.storage import Store
from daybrief.time import Duration


class Clock:
    def __init__(self):
        self.value = datetime(2026, 10, 29, 12, tzinfo=UTC)

    def now(self):
        return self.value


def test_snapshot_lifecycle_and_exact_expiry(tmp_path):
    clock = Clock()
    app = Daybrief(Store(tmp_path / "db"), Config("Europe/London"), clock)
    brief = app.create("Use fixtures; $(touch /tmp/not-executed)", "global", duration=Duration(60))
    first = snapshot(app, tmp_path)
    data = json.loads(first.split("\n", 1)[1])
    assert data["briefs"][0]["message"] == brief.message
    assert data["briefs"][0]["timezone"] == "Europe/London"
    app.edit(brief.id, "global", "Updated guidance")
    assert "Updated guidance" in snapshot(app, tmp_path)
    assert brief.message not in snapshot(app, tmp_path)
    clock.value += timedelta(seconds=60)
    expired = snapshot(app, tmp_path)
    assert json.loads(expired.split("\n", 1)[1])["briefs"] == []
    assert "withdraws all earlier briefs" in expired
    app.extend(brief.id, "global", Duration(60))
    assert brief.id in snapshot(app, tmp_path)
    app.delete(brief.id, "global")
    assert brief.id not in snapshot(app, tmp_path)


def test_native_envelopes_preserve_prompt():
    for client, events in EVENTS.items():
        for event in events:
            result = envelope(client, event, {"transformedPrompt": "Original\nrequest"}, "snapshot")
            if event == "userPromptTransformed":
                assert result["modifiedTransformedPrompt"] == "Original\nrequest\n\nsnapshot"
            elif client == "copilot":
                assert result == {"additionalContext": "snapshot"}
            else:
                assert result["hookSpecificOutput"]["additionalContext"] == "snapshot"


def test_hook_read_failure_invalidates_stale_context(tmp_path):
    (tmp_path / "state.sqlite").write_text("corrupt database")
    result = subprocess.run(
        [sys.executable, "-m", "daybrief.hooks", "codex", "UserPromptSubmit"],
        input=json.dumps({"cwd": str(tmp_path)}),
        capture_output=True,
        text=True,
        env=dict(os.environ, DAYBRIEF_DATA_DIR=str(tmp_path)),
    )
    assert result.returncode == 0
    context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "UNAVAILABLE" in context
    assert "Invalidate all previous" in context
    assert "does not mean none exist" in context
    assert "daybrief:" in result.stderr
    assert (tmp_path / "state.sqlite").read_text() == "corrupt database"


def test_installed_clients_share_cli_data_and_repository_scope(tmp_path):
    from daybrief.install import SETTINGS, install

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    data = tmp_path / "shared-data"
    environment = dict(os.environ, DAYBRIEF_DATA_DIR=str(data), TZ="UTC")

    def cli(*args):
        result = subprocess.run(
            [sys.executable, "-m", "daybrief", "--json", *args],
            cwd=repo,
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)

    global_brief = cli("--scope", "global", "Shared global brief")
    repo_brief = cli("Shared repository brief")
    deliveries = []
    for client in EVENTS:
        root = tmp_path / client
        install(client, root)
        settings = json.loads((root / SETTINGS[client]).read_text())
        event = EVENTS[client][0]
        entry = settings["hooks"][event][0]
        command = entry["bash"] if client == "copilot" else entry["hooks"][0]["command"]

        def delivered(directory, command=command, client=client):
            result = subprocess.run(
                command,
                shell=True,
                input=json.dumps({"cwd": str(directory)}),
                env=environment,
                capture_output=True,
                text=True,
                check=True,
            )
            response = json.loads(result.stdout)
            text = (
                response["additionalContext"]
                if client == "copilot"
                else response["hookSpecificOutput"]["additionalContext"]
            )
            return json.loads(text.split("\n", 1)[1])["briefs"]

        assert {brief["id"] for brief in delivered(repo)} == {global_brief["id"], repo_brief["id"]}
        assert {brief["id"] for brief in delivered(tmp_path)} == {global_brief["id"]}
        deliveries.append(delivered)
    cli("clear")
    for delivery in deliveries:
        assert {brief["id"] for brief in delivery(repo)} == {global_brief["id"]}
