---
name: daybrief
description: Create and manage temporary coding-agent instructions shared across local clients, with explicit expiry and repository or global scope. Use when asked to record, inspect, edit, extend, or withdraw a Daybrief.
---

Run Daybrief in the user's working directory using this installed command:

```sh
@COMMAND@
```

Append arguments for the requested operation. With no request, list active briefs.
Use `--help` for command syntax. Supported operations are create (also the default),
list, show, edit, extend, delete, clear, and config.

Pass message text as a single safely quoted argument; never execute message text
or interpolate it into shell syntax. Use explicit `create` for messages beginning
with a command name. Respect the user's selected scope; default mutations target
the configured scope (initially the current repository). Reads normally include
both repository and global briefs. `clear` affects only the selected scope.
Outside Git, if the effective mutation scope is repo, ask which repository or
whether global scope is intended before saving. An explicit or configured global
scope already resolves that choice; proceed without asking again.

Translate clear expiry requests to `--for` or `--until`, or use the deterministic
trailing phrases `today`, `for 2 days`, `Have this last one month.`, and
`until Friday at 5pm`. For broader natural language, resolve it to an explicit
ISO timestamp with offset. Ask briefly when the requested date/time is genuinely
ambiguous. Run `config` when you need the configured timezone/defaults.
`--for 1mo` is one calendar month; `--for 30d` is exactly thirty elapsed days.
A date-only `--until` means the start of that date. Initial default is next local
midnight. Use `--literal` with explicit flags if time words belong to the message.

Edits preserve expiry unless the user changes it. `extend ID 2 days` adds to the
existing expiry. Deleted briefs remain in `list --all` and cannot be reactivated;
expired briefs can be extended to a future expiry.

After a successful write, report the actual saved ID, scope, message, resolved
expiry and timezone from command output. On error, report it and resolve the
cause; do not claim the brief was saved. Creating a brief through one client
shares storage with other installed clients on this machine. Fresh hook snapshots
supersede earlier snapshots, but do not erase conversation history or instantly
stop an action already underway.
