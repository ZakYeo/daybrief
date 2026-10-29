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
