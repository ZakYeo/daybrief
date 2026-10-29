# Local command workflow

Install from this checkout with `uv tool install .`, or for development run
`uv sync --frozen` and prefix commands with `uv run`. The initial defaults are
the local IANA timezone, current repository scope, and next local midnight.
Outside a Git repository, use `--scope global` for mutations.

```sh
daybrief --scope global --for 1mo Use the staging API.
daybrief list
daybrief show ID
daybrief edit ID Updated guidance.
daybrief extend ID 2 days
daybrief delete ID
daybrief clear
daybrief list --all
daybrief config
daybrief config set timezone Europe/London
daybrief config set expiry 24h
daybrief config set scope global
```

Replace `ID` with the ID returned when saving. Specify `--scope global` when
changing a global brief if the configured mutation scope is repo. Normal
lists and details include both applicable global and repository briefs.
`clear` targets only the selected/default scope; `list --all` includes expired
and deleted history. `--json` returns machine-readable records.

Explicit expiry forms: `--for 1mo`, `--for "30 days"`, and
`--until 2099-11-30T17:00:00+00:00`. A date-only deadline means the start of
that date. Month durations use calendar months; days are exactly 24 hours.
Every saved record shows its resolved expiry, offset, and IANA timezone.
Editing keeps expiry unless supplied again. Extension adds to existing expiry.
Expired briefs can reactivate; deleted briefs cannot.

Recognized trailing phrases include `today`, `for 2 days`,
`Have this last one month.`, and `until Friday at 5pm.`. Ambiguous weekday
deadlines require a time. Broader language belongs to the client skill.
Use `--literal` to preserve message text without expiry parsing. Combine it
with an explicit flag when the message itself contains a time phrase.
Use `create` to save a message beginning with a reserved command name.
`--timezone` overrides the timezone for creation or editing; edit otherwise
uses the brief's saved timezone. Use `config set timezone` to change defaults.

Data lives in `DAYBRIEF_DATA_DIR/state.sqlite` when set, otherwise under
`$XDG_DATA_HOME/daybrief` or `~/.local/share/daybrief`. History is retained
indefinitely. Deletion withdraws instructions and is not secure erasure.
The CLI is implemented; client installation is the next milestone.
