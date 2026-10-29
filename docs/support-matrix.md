# Feasibility matrix

This records step 1 evidence, not a released product support promise. Versions
are exact spike targets; earlier versions have not been qualified. All runs
used Linux and isolated configuration. No live hosted model was used.

| Surface | Version | Command evidence | Delivery evidence | Resume/withdrawal evidence |
| --- | --- | --- | --- | --- |
| Codex CLI | 0.165.0 | `$daybrief list` loads the skill into its request; bare `/daybrief` still unverified | SessionStart and UserPromptSubmit hooks run and inject context | Same thread resumed with a new snapshot; withdrawal reaches the next request |
| Claude Code CLI | 2.1.312 | `/daybrief list` expands the installed user skill | SessionStart and UserPromptSubmit hooks run and inject context | Same session resumed with a new snapshot; withdrawal reaches the next request |
| GitHub Copilot CLI | 1.0.105 | `/daybrief list` reaches the request; fixed mock skill tool call loads its body | SessionStart and userPromptTransformed independently inject context | Prompt transformation supplies withdrawal when the same session resumes |

Codex and Claude hooks use `hookSpecificOutput` with an event name and
`additionalContext`. Copilot session hooks use top-level `additionalContext`;
prompt refresh uses `modifiedTransformedPrompt` preserving the original content.
Copilot command-hook output from `userPromptSubmitted` is ignored, so it is not
a suitable delivery event.

## Evidence commands

Install Copilot for the spike into `/tmp/daybrief-copilot-spike` as documented in
`integration-research.md`. Python 3.12 and the indicated native binaries are
prerequisites. Loopback network permission is required by request probes.

```sh
python3 spikes/check_hook_probe.py
python3 spikes/codex_request_probe.py
python3 spikes/codex_request_probe.py --skill
python3 spikes/claude_request_probe.py
python3 spikes/claude_request_probe.py --skill
python3 spikes/copilot_request_probe.py
python3 spikes/copilot_request_probe.py userPromptTransformed
python3 spikes/copilot_request_probe.py --skill
python3 spikes/codex_refresh_probe.py
python3 spikes/claude_refresh_probe.py
python3 spikes/copilot_refresh_probe.py
```

Request probes exercise real client binaries against a synthetic local server.
Most end by deliberately returning HTTP 400 after capturing the request.
Refresh probes return fixed success responses and resume the recorded session.
These establish transport, not live model interpretation or obedience.

## Open feasibility checks

- Codex's native TUI rejects `/daybrief`; the user explicitly approved the
  verified `$daybrief` spelling instead. `spikes/codex_slash_probe.py` captures
  the rejection using pexpect 4.9.0 and a disposable configuration.
- Test refreshing within a continuously running client process, separately
  from the successful resume checks.
- Finalize refresh coverage during autonomous tool execution and compaction.
- Parser grammar and installation/removal contracts are in design-decisions.md.
- Complete independent step 1 review and fixes before starting the foundation.

Existing transcript text remains after withdrawal. The proposed complete
snapshot protocol explicitly supersedes previous Daybrief snapshots, but
cannot erase memory or revoke an already-started operation. No support is
claimed for Copilot IDE/cloud surfaces or for cross-device synchronization.
