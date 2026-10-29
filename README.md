![Daybrief — an ivory wordmark and terminal prompt above a warm dawn horizon](docs/assets/daybrief-banner.png)

# Daybrief

**A message of the day for your coding agents, lasting as long as you need.**

Record a temporary instruction once. Daybrief shares it with Codex, Claude Code,
and GitHub Copilot CLI on your machine, then stops supplying it when it expires.

“Staging is being restored; use local fixtures today” belongs in a temporary
brief, not a permanent project instruction file. Give it a lifetime, keep working,
and let the next agent refresh pick up the current state.

- Default to the next local midnight, or choose a duration or deadline.
- Share global guidance across projects and repository guidance across worktrees.
- Inspect, edit, extend, delete, and retain history through one local CLI.
- Store data in SQLite; no Daybrief account, daemon, or hosted service.

## Install

Prerequisites: **Linux, Python 3.12+, Git, and uv**. The contributor baseline is
Python 3.12 and uv 0.11.21. Other operating systems have not been qualified.

Clone the repository and install from the checkout:

```sh
git clone https://github.com/ZakYeo/daybrief.git
cd daybrief
uv tool install --python 3.12 .
daybrief --help
```

If `daybrief` is not on your PATH, run `uv tool update-shell` and open a new
terminal. This installs into a persistent isolated environment; do not move or
delete that environment while hooks use it. There is no PyPI release yet.

## Quick start

Run these commands inside a Git repository:

```sh
daybrief "Staging is being restored; use local fixtures today"
daybrief list
```

Daybrief confirms the ID, repository scope, exact expiry and timezone. Without an
expiry phrase or flag, the initial default is the next midnight in your local
IANA timezone. If timezone discovery fails, set one explicitly:

```sh
daybrief config set timezone Europe/London
```

Install the integrations you use:

```sh
daybrief install codex
daybrief install claude
daybrief install copilot
```

Restart those clients. In Codex, review and trust the Daybrief hooks when its
native trust prompt appears. Then use `$daybrief list` in Codex, or
`/daybrief list` in Claude and Copilot. Skills run the same CLI and share the
same local data; normal client tool permissions still apply.

| Client | Qualified version | Create inside the client |
| --- | --- | --- |
| Codex CLI | 0.165.0 | `$daybrief Use local fixtures today` |
| Claude Code CLI | 2.1.312 | `/daybrief Use local fixtures today` |
| GitHub Copilot CLI | 1.0.105 | `/daybrief Use local fixtures today` |

This is **CLI support**, not Copilot IDE/cloud support. See the
[setup and support matrix](docs/support-matrix.md) for alternate profiles,
configuration preservation, native verification and refresh details.

## A brief that lasts a month

```sh
daybrief --scope global --timezone Europe/London --for 1mo \
  "Use the staging API during the migration."
```

Actual output captured on 29 October 2026 (your ID and time will differ):

```text
973f72a1 [global] active: Use the staging API during the migration.
Expires 2026-11-29T17:32:22.594701+00:00 (Europe/London)
```

One month means a calendar month, preserving local time and clamping to the last
valid day when necessary. Thirty days means exactly 30 × 24 hours.

## Manage briefs

Replace `ID` with a saved ID. Mutations use the configured scope, initially `repo`;
add `--scope global` when changing a global brief.

| Command | Behavior |
| --- | --- |
| `daybrief "MESSAGE"` | Create a brief with the configured default expiry |
| `daybrief --for 24h "MESSAGE"` | Create with a fixed duration |
| `daybrief --until 2099-11-30T17:00:00+00:00 "MESSAGE"` | Create with an exact deadline |
| `daybrief list` | Read applicable global and repository briefs |
| `daybrief list --all` | Include expired and deleted history |
| `daybrief show ID` | Inspect the full message and metadata |
| `daybrief edit ID "MESSAGE"` | Edit while preserving expiry |
| `daybrief extend ID 2 days` | Add time to the existing expiry |
| `daybrief delete ID` | Withdraw a brief immediately from active storage |
| `daybrief clear` | Withdraw active briefs in the selected scope only |
| `daybrief config` | Show defaults |

Use `--json` for machine-readable output. Use explicit `create` when a message
starts with a command name. Full syntax and examples: [command guide](docs/cli.md).

### Expiry and natural language

The CLI recognizes trailing `today`, `for 2 days`, `Have this last one month.`,
and `until Friday at 5pm.`. Client skills can translate broader language into
explicit flags and ask about genuinely ambiguous deadlines.

- `--for` accepts positive durations such as `30m`, `24h`, `7d`, `1w`, and `1mo`.
- A date-only `--until YYYY-MM-DD` means **the start of that date**, not its end.
- A weekday deadline selects its next occurrence strictly after now.
- Ambiguous/nonexistent local times at daylight-saving transitions are rejected;
  use an explicit timestamp with an offset.
- Edits preserve expiry unless changed. An expired brief can be extended to a
  future expiry; a deleted brief cannot be reactivated.
- Conflicting expiry expressions fail. `--literal` preserves time words in the
  message and can be combined with an explicit expiry flag.

### Scope and defaults

Repository identity is the canonical Git common directory: linked worktrees
share briefs; separate clones do not. Normal reads combine repository and global
briefs. `clear` never implicitly clears both. Outside Git, select global scope
or configure it as your default.

```sh
daybrief config set timezone Europe/London
daybrief config set expiry 24h
daybrief config set scope global
```

Set expiry back to `today` for next-midnight behavior. Explicit invocation options
override saved defaults. `--timezone` affects creation/editing; use configuration
to change the default for later briefs. Existing briefs keep their saved timezone.

## What expiry guarantees

At supported startup, prompt and post-tool events, each adapter reads a fresh
snapshot and excludes expired or deleted briefs. Each snapshot includes exact
expiry and supersedes earlier Daybrief snapshots; an empty snapshot explicitly
withdraws earlier guidance. Read failures invalidate old snapshots and report
that the current state could not be read.

Expiry **does not erase conversation history or cancel an action already
underway**. There is no background timer. Native checks cover same-process
prompt/tool refresh and manual compaction followed by another prompt. Automatic
compaction without a later prompt/tool event is not separately qualified.
Keep briefs concise because client context limits apply. Conflicting temporary
and enduring instructions require clarification.

The deterministic tests run without accounts or paid APIs. Native-client checks
use real binaries with a synthetic local model endpoint; they verify delivery,
not hosted-model interpretation or obedience. Reproduction details are in the
[support matrix](docs/support-matrix.md).

## Data, privacy and uninstalling

SQLite data is stored at `$XDG_DATA_HOME/daybrief/state.sqlite`, defaulting to
`~/.local/share/daybrief/state.sqlite`. `DAYBRIEF_DATA_DIR` overrides the directory
for all clients that inherit it. Keep that setting consistent across terminals.
Brief text is local at rest, but active briefs are sent to the coding-agent model
through your client. Use the same care as for any other agent prompt.

Expired and deleted records are retained indefinitely for history. Deletion is
withdrawal, not secure erasure. There is no cross-device or team synchronization.

Remove adapters **before** removing the package:

```sh
daybrief uninstall codex
daybrief uninstall claude
daybrief uninstall copilot
uv tool uninstall daybrief
```

Use the same `--root` if you installed into an alternate profile, then restart
clients. Unrelated client settings and instruction files are preserved. History
remains; to erase all Daybrief settings and history, stop clients using it and
remove the resolved Daybrief data directory. Back it up first if needed.

## Contribute and understand the code

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, installed Git hooks and the single
quality gate. [Design decisions](docs/design-decisions.md) explain the time,
scope and installation contracts.

The dependency-free runtime separates immutable brief/time rules, a lifecycle
service, transactional SQLite storage, CLI presentation, snapshot delivery and
client installation. Client skills translate requests; the shared core owns
scope, expiry and lifecycle behavior. The adapters never evaluate brief text as
shell code.

## License

[MIT](LICENSE), © 2026 ZakYeo. The original banner was generated for this project;
[artwork provenance and regeneration notes](docs/assets/README.md) record its
prompt and preparation.
