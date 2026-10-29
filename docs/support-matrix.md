# Client support and verification

Daybrief targets these native **CLI** versions on Linux with Python 3.12+.
Earlier versions, Windows, macOS, Copilot IDE extensions and cloud agents have
not been qualified. Clients must run as the same user with the same data location.

| Client | Tested version | Native command | Refresh events |
| --- | --- | --- | --- |
| Codex CLI | 0.165.0 | `$daybrief` | SessionStart, UserPromptSubmit, PostToolUse |
| Claude Code CLI | 2.1.312 | `/daybrief` | SessionStart, UserPromptSubmit, PostToolUse |
| GitHub Copilot CLI | 1.0.105 | `/daybrief` | sessionStart, userPromptTransformed, postToolUse |

The user approved Codex's native `$daybrief` invocation after its TUI rejected
`/daybrief`. Copilot's `userPromptSubmitted` output is ignored by the client;
Daybrief uses `userPromptTransformed` and preserves the original prompt.

## Setup and removal

Install Daybrief into a persistent virtual environment (for example with
`uv tool install`) first, then run:

```sh
daybrief install codex
daybrief install claude
daybrief install copilot
```

Restart the client. Review and trust the installed hooks when Codex presents its
native hook trust prompt. Client policies that disable skills or hooks can prevent
delivery; Daybrief does not change those policies. Normal tool permissions still
apply when a skill runs a Daybrief command.

Personal roots default to `~/.codex`, `~/.claude`, and `~/.copilot`, respectively.
`CODEX_HOME`, `CLAUDE_CONFIG_DIR`, and `COPILOT_HOME` select alternate roots.
`daybrief install CLIENT --root /absolute/path` is useful for an alternate profile;
configure the client to use that same root. Each gets `skills/daybrief/SKILL.md`.
Codex merges `hooks.json`; Claude merges `settings.json`; Copilot gets
`hooks/daybrief.json`. No project instruction file is modified.

Rerun installation after moving/reinstalling Daybrief: hooks and skills reference
the installing Python environment by absolute path. Python isolated mode prevents
repository files and `PYTHONPATH` from shadowing Daybrief. User-site-only
(`pip install --user`) installations are unsupported; installation checks this
before writing client configuration. The manifest
`.daybrief-install.json` records owned entries and the skill hash. Installation
refuses unowned collisions, malformed settings, symlinks in managed paths, and
modified owned content. Preserve or restore your edits before trying again;
do not delete the manifest to force an overwrite. Unrelated JSON keys and hooks
survive updates and removal. Writes are atomic per file and roll back on ordinary
write errors; a machine crash during the multi-file operation can require repair.

```sh
daybrief uninstall codex
daybrief uninstall claude
daybrief uninstall copilot
```

Removal uses the same optional `--root`. It retains briefs and history, unrelated
settings, empty directories and the installer lock file. Restart clients afterward.

## Refresh guarantees

Every supported hook event reads shared storage and filters expired/deleted
briefs. It supplies a complete applicable snapshot with generation time, IDs,
messages, scopes, UTC/local expiry, timezone and revision. Empty snapshots
explicitly withdraw prior snapshots. Read errors deliver an unavailable notice
that invalidates prior snapshots and asks for diagnosis.

Native checks demonstrate startup delivery, withdrawal after a successful tool
call, refresh on the next user turn in the same process, and refresh after manual
`/compact` followed by a user prompt. These are event-driven guarantees: there is
no timer, no instantaneous revocation of an operation already underway, and no
promise that old text disappears from conversation history. Automatic compaction
without a subsequent prompt/tool event was not separately qualified. Client
context/output limits still apply; keep briefs concise. Conflicting instructions
require clarification; temporary guidance does not override higher-priority rules.

## Reproduce the evidence

The deterministic aggregate gate includes subprocess checks of all installed hook
commands against shared CLI-created global/repository data, plus lifecycle,
expiry, corruption, installation/update/removal and configuration preservation.
It requires no client account, network, or paid service.

Native probes require the exact binaries above and permission to bind a loopback
port. Install Copilot into `/tmp/daybrief-copilot-spike` as recorded in
[integration research](integration-research.md). Run with the development Python:

```sh
.venv/bin/python spikes/installed_adapter_probe.py codex --skill
.venv/bin/python spikes/installed_adapter_probe.py claude --skill
.venv/bin/python spikes/installed_adapter_probe.py copilot --skill
.venv/bin/python spikes/installed_adapter_probe.py codex --interactive
.venv/bin/python spikes/installed_adapter_probe.py claude --interactive
.venv/bin/python spikes/installed_adapter_probe.py copilot --interactive
```

Interactive probes additionally require system `pexpect` (tested 4.9.0). They use
disposable homes, profiles, repositories and databases. Synthetic tool responses
run only a fixed CLI deletion of a temporary brief. They verify that the actual
client transmits fresh snapshots to a local model endpoint, including after native
compaction completes. Codex title-generation requests are excluded from turn checks.

These are **real native-client checks with a synthetic model**, not hosted-model
behavior tests. No paid model was used, and model interpretation/obedience is not
proven. Earlier feasibility probes in `spikes/*_request_probe.py` and
`spikes/*_refresh_probe.py` test transport and resumed sessions with fixture hooks;
they are historical evidence, not substitutes for installed-adapter checks.

Official contracts: [Codex hooks](https://developers.openai.com/codex/hooks),
[Claude hooks](https://code.claude.com/docs/en/hooks), and
[Copilot skills](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills).
