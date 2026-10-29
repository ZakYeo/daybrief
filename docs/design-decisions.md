# Product decisions proposed for step 1 review

These decisions guide the remaining feasibility work. Adapter design is not
approved until the spike and independent review are complete.

## Shared core

Use Python 3.12+, a wheel with a `daybrief` console entry point, and SQLite.
Python supplies timezone and calendar primitives; SQLite supplies transactions
and locking across concurrent client processes without a background service.
Keep clock, domain operations, date arithmetic, repository discovery, SQLite
access, CLI formatting, and client adapters in separate cohesive modules.
Use uv for locked contributor dependencies. Runtime data lives outside the repo.

Resolve storage under `$XDG_DATA_HOME/daybrief`, defaulting to
`~/.local/share/daybrief`; permit `DAYBRIEF_DATA_DIR` for isolation and testing.
Store settings and briefs in the same database for transactional updates.
Reject unknown schema versions and corrupt records without resetting data.
Use explicit transactions and a bounded busy timeout; report lock failures.

## Time

- Store UTC instants with a saved IANA timezone per brief; show both resolved
  local time and offset in detailed output.
- The initial expiry is the next local calendar midnight, not 24 hours later.
- Seconds, minutes, hours, days, and weeks are fixed elapsed durations; a day
  is exactly 86,400 seconds even over a daylight-saving transition.
- Months are calendar arithmetic in the brief's timezone, clamping to the last
  valid day of the target month. Reject ambiguous or nonexistent resulting
  local times and request an explicit offset timestamp.
- Date-only `--until YYYY-MM-DD` means the start of that date in the configured
  timezone. A brief is inactive at the exact expiry instant.
- Reject conflicting expiry options and deadlines at or before creation time.
- Extension adds to existing expiry. Expired briefs can reactivate if the new
  expiry is in the future; deleted briefs cannot be extended or edited.

## Scope, identity, history

Default scope is the current repository. Resolve its canonical Git common
directory so worktrees share briefs; distinct clones remain independent.
Outside a repository, repository operations fail with guidance to select global.
Do not silently turn repository mutations into global mutations.
Use explicit `--scope repo|global`; normal reads combine applicable global and
repository briefs. Clear affects only the selected/default mutation scope.

Retain expired and soft-deleted briefs indefinitely for `list --all`, with
status, stable randomly generated short IDs, timestamps, and revision counters.
Deletion is withdrawal, not secure erasure. Document how to remove the whole
local database when uninstalling. Updates keep the ID and creation timestamp.

`config` displays settings; `config set timezone|expiry|scope VALUE` changes
defaults. Precedence is explicit invocation, saved defaults, initial defaults.
Capture the OS IANA timezone at initialization; if unavailable, require the user
to set one rather than guessing from an ambiguous timezone abbreviation.

## Input and delivery

Client skills interpret ordinary-language requests and translate them to
deterministic CLI options. They must clarify genuinely ambiguous deadlines
before saving and display the actual saved result. The standalone CLI accepts
explicit durations/deadlines; its documented natural-language subset will be
bounded and tested rather than claiming general language understanding.

Every delivery is a complete applicable active snapshot including generation
time, ID, message, scope, expiry, and timezone. An empty snapshot explicitly
withdraws previous Daybrief instructions. Fresh selections always filter by
expiry and deletion, regardless of cleanup. A snapshot supplements enduring
instructions; conflicting briefs require clarification, not silent precedence.
Do not execute brief text. JSON encoding and fixed executable arguments carry
data across process boundaries.

Hook refresh can update context only at supported events. It cannot erase
transcript history or revoke an action already underway. Exact refresh guarantees
remain to be established per client through the spike.
