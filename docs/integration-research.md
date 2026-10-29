# Integration research

Status: step 1 investigation, not a support declaration. Checked 2026-10-29.

## Local inventory

Commands returned Codex CLI `0.165.0`, Claude Code `2.1.312`, Python `3.12.3`,
and uv `0.11.21`. Copilot is absent from PATH. The first two versions are
candidate spike targets, not yet tested adapter versions.

## Codex

[Hook reference](https://learn.chatgpt.com/docs/hooks) documents user and project
`hooks.json` beside config layers. Project trust and per-hook trust apply.
`UserPromptSubmit` accepts plain stdout or JSON containing
`hookSpecificOutput.additionalContext` with the matching `hookEventName`.
This becomes developer context. Session and tool events offer refresh points.
The installer must preserve existing hooks and leave trust decisions visible.

[Plugin packaging](https://developers.openai.com/plugins/build/plugins) focuses
local plugin installation on desktop. Prefer direct CLI hook configuration for
the spike; do not infer CLI plugin installation from marketplace registration.
Exact `/daybrief` registration still needs verification.

## Claude Code

[Hook reference](https://code.claude.com/docs/en/hooks) provides session, prompt,
and tool lifecycle events. Next: inspect their precise context-output contracts,
then test settings discovery and command registration in an isolated directory.

## GitHub Copilot CLI

Scope the integration to CLI, not cloud agents or IDEs.
[Hooks reference](https://docs.github.com/en/copilot/reference/hooks-reference)
documents user hooks under `~/.copilot/hooks/` and project hooks under
`.github/hooks/`. `sessionStart` consumes top-level `additionalContext`;
`postToolUse` can also inject context. Do not copy the Codex envelope here.
Prompt transformation and submission have distinct contracts requiring further
inspection before selecting the refresh event.

[Skills guide](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills)
documents personal and project skills, explicit slash-name invocation, and
`/skills reload`. A Daybrief skill is a candidate command entry point.

## Spike acceptance criteria

- Native client discovers the intended command and hook configuration.
- A harmless marker from a hook reaches model context, with evidence distinct
  from merely running the hook executable by hand.
- Replacing the marker between turns produces refreshed context; empty active
  state explicitly withdraws previously supplied Daybrief instructions.
- No modification of personal client settings or permanent instruction files.
- Record exact versions, commands, events, and outcomes; distinguish fixture
  validation from live client results and report authentication constraints.

Architecture and product decisions remain pending the spike. No step 2 work
should begin before the complete step 1 review gate.

## Initial executable evidence

`python3 spikes/check_hook_probe.py` passes four subprocess envelope checks.
The probe reads context from a disposable directory and logs event names only.
It does not implement persistence or claim model delivery.

A native Claude Code 2.1.312 print-mode attempt used an explicit temporary
settings file, empty setting sources, strict MCP configuration, and no tools.
SessionStart and UserPromptSubmit were configured to invoke this probe.
The subprocess timed out after 40 seconds and was terminated; no event log
was produced. Temporary directory: `/tmp/daybrief-spike-o_dzu4_t`.
This establishes neither successful discovery nor a hook incompatibility.
Next investigate startup/authentication and obtain actual native delivery
evidence before closing the spike. Codex and Copilot native checks are pending.

### Native discovery follow-up

Codex 0.165.0 with a fresh temporary configuration executed `SessionStart`
and the probe logged that event. Its subsequent API websocket connection
failed with `Operation not permitted`; the client was terminated at 30 seconds.
The isolated probe trusted only its fixed hook for that invocation. No user
settings or credentials were copied. Evidence directory:
`/tmp/daybrief-codex-qvi85509`. Reproduce with
`python3 spikes/native_codex_probe.py` (which also closes input explicitly).
This proves native discovery/execution, not receipt by a model or prompt refresh.

Claude with `CLAUDE_CONFIG_DIR` pointing to a fresh temporary directory exited 1
with `authentication_failed` and no hook events. This distinguishes the
authentication failure from the earlier unexplained startup timeout. Live
Claude delivery and all Copilot native checks remain pending.

### Codex request capture — passed

`python3 spikes/codex_request_probe.py` starts an ephemeral loopback HTTP
endpoint and runs the real Codex 0.165.0 executable against it with a fresh
configuration and no authentication. Both `SessionStart` and `UserPromptSubmit`
executed. The captured model request contained `amber-dawn-731`, which was
present only in hook context, not the user prompt. The endpoint deliberately
returns HTTP 400 after capture; no live model is involved. The check fails if
no request arrives or the marker is absent.

Local socket binding required sandbox escalation in this environment. The
successful run completed in under a second. This is stronger than an envelope
fixture: the native client actually assembled and transmitted the context.
It does not prove model compliance, same-conversation refresh, or independent
delivery from each event (both currently provide the same marker).

Provider configuration follows the official
[advanced configuration reference](https://learn.chatgpt.com/docs/config-file/config-advanced).

### Claude request capture — passed

`python3 spikes/claude_request_probe.py` runs Claude Code 2.1.312 with a fresh
configuration, fixed dummy API key, loopback endpoint, no enabled tools, and
nonessential traffic disabled. Both configured events executed; at least one
of the three captured requests contained the marker supplied only by the hook.
The endpoint returns HTTP 400 intentionally. As with Codex, this validates native
request construction, not a live model or refresh in an existing conversation.
The earlier missing authentication is therefore not a blocker for this local
transport check. Configuration variables are documented in the official
[environment reference](https://code.claude.com/docs/en/env-vars).

### Copilot spike environment

Installed official npm package `@github/copilot@1.0.105` under
`/tmp/daybrief-copilot-spike` using `--ignore-scripts --no-audit --no-fund`.
The binary reports GitHub Copilot CLI 1.0.105. Set
`XDG_CACHE_HOME=/tmp/daybrief-copilot-spike/cache` and
`COPILOT_HOME=/tmp/daybrief-copilot-spike/config` when running it: the native
loader otherwise tries to extract into the user's cache, which is read-only
in this sandbox. No global package installation was performed.
Native Copilot delivery is still untested.

### Copilot request capture — passed

Native Copilot CLI 1.0.105 now passes the isolated loopback request check:
`python3 spikes/copilot_request_probe.py` tests `sessionStart`, and
`python3 spikes/copilot_request_probe.py userPromptTransformed` tests prompt
refresh separately. Each ran its configured hook and transmitted the hook-only
marker in one captured request. The endpoint intentionally rejects the request;
no real model or account is involved. Provider environment variables follow the
installed CLI's `copilot help providers`. The probe uses the temporary install
and cache paths above; it is a spike, not a portable installed test suite.

The [hook reference](https://docs.github.com/en/copilot/reference/hooks-reference)
states that command-hook output from `userPromptSubmitted` is dropped. Therefore
use `userPromptTransformed` to preserve the existing transformed prompt and
append a current Daybrief snapshot. The spike verifies this path independently
of session context. Running-session multi-turn replacement remains to be tested.

### Command registration checks

`python3 spikes/claude_request_probe.py --skill` passes for Claude 2.1.312:
an isolated user skill named `daybrief` expands `/daybrief list`, transmitting
the unique skill-body marker to the captured request. The user setting source
must be enabled (it points at the temporary configuration directory).

`python3 spikes/copilot_request_probe.py --skill` currently fails its stronger
skill-body assertion. Tested both temporary personal and trusted project skill
paths; the current probe uses `.github/skills/daybrief/SKILL.md`. The marker is
absent from the first captured request. This does not establish unsupported
skills: Copilot may defer reading the body to a tool call, which the rejecting
endpoint cannot exercise. Investigate native skill discovery and a successful
mock response/tool cycle before claiming command registration. The optional
failing spike is deliberately retained to make the unresolved requirement
reproducible; ordinary hook mode remains separate.

### Deferred skill loading resolved

The Copilot `--skill` probe now passes. The first request advertises a `skill`
tool; a fixed mock response calls it with `{"skill":"daybrief"}`. The real
client loads the temporary repository skill and the second captured request
contains its unique body marker. This proves discovery and native loading,
not that a real model always chooses the skill. The original one-request
assertion was insufficient for a client that defers skill loading. The probe
now initializes a real temporary Git repository and exercises the tool cycle.
`--inspect` can save the last synthetic request under `/tmp` for diagnosis.

`python3 spikes/codex_request_probe.py --skill` also passes using the documented
`$daybrief list` skill mention. This verifies the skill entry point; the desired
bare `/daybrief` CLI alias is still unverified and must not be advertised yet.

### Two-turn withdrawal transport — Codex and Copilot passed

`python3 spikes/codex_refresh_probe.py` runs Codex against a local synthetic
successful endpoint, captures an initial brief, changes hook data to an explicit
withdrawal snapshot, and resumes the same thread ID. The second request includes
the withdrawal. Both native invocations exit successfully.

`python3 spikes/copilot_refresh_probe.py` does the same with Copilot 1.0.105,
resuming the session ID emitted by the first turn. It uses only the
`userPromptTransformed` hook, so the result demonstrates refresh independently
of session-start injection. Both invocations succeed and the second request
contains the withdrawal snapshot.

These tests verify resumed-session transport. They do not establish that a
continuously running interactive session refreshes correctly, or that a live
model obeys the withdrawal. They deliberately retain old transcript text: the
new snapshot must communicate that prior Daybrief instructions no longer apply.
