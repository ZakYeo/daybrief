# Daybrief

## Purpose

Daybrief provides temporary instructions for coding agents. A user writes a brief once, gives it an expiry, and has it supplied to agents working in the applicable scope across supported tools.

The primary target tools are Codex, Claude Code, and GitHub Copilot. The intended interface is a `/daybrief` command inside each supported client.

**Product description:** Daybrief — a message of the day for your coding agents, lasting as long as you need.

**Core promise:** Tell your agents once, and have the instruction expire automatically.

MOTD, or “message of the day,” remains a useful explanation of the concept. Daybrief is the product name. Think of it as an `AGENTS.md` for temporary circumstances, with an explicit lifetime and a way to share the same information across tools.

This document captures the product discussed with the user. It is a product specification, not a claim that the functionality already exists. Requirements below describe intended behaviour; implementation choices and unresolved decisions are identified separately.

## Problem

Permanent agent instruction files are useful for enduring project guidance. Temporary circumstances also affect how an agent should work, but repeating them in every conversation is tedious, and leaving them in permanent instructions can mislead agents after the situation changes.

Examples include:

- A messaging service is temporarily unavailable, so agents should use an alternative.
- CI is flaky today, and failures should be checked against a known incident.
- A demo is approaching, so work should prioritise the checkout flow.
- A staging database is being restored, so agents should use local fixtures.
- An API migration requires a temporary endpoint for the next month.

Daybrief should make these instructions easy to create, discover, change, and retire. Its value depends on both cross-tool delivery and reliable expiry, beyond adding a message to the current conversation.

## Core experience

1. The user enters `/daybrief` followed by a message in a supported agent client.
2. Daybrief determines the message, applicable scope, and expiry.
3. It saves the brief and confirms what it understood, including the exact expiry and timezone.
4. Applicable agents receive active briefs through their client integration.
5. The user can list, inspect, edit, extend, or delete briefs.
6. When a brief expires or is deleted, it stops being supplied as an active instruction.

Example:

```text
/daybrief The messaging service is down temporarily today; use xxx as an alternative.
```

An illustrative confirmation:

```text
Saved b3 for this repository.
Expires 30 October 2026 at 00:00, Europe/London.
```

This example assumes creation on 29 October 2026. The wording illustrates the information to show, rather than a required format. The default lifetime is the remainder of the current local day.

## Commands

| Command | Intended behaviour |
| --- | --- |
| `/daybrief <message>` | Create a brief, optionally expressing its expiry in natural language. |
| `/daybrief list` | List active briefs, including short IDs, message previews, scopes, and expiries. |
| `/daybrief list --all` | Include expired briefs in the listing for history. |
| `/daybrief show <id>` | Display the full message and its details. |
| `/daybrief edit <id> <message>` | Update the message. Keep its existing expiry unless a new expiry is specified. |
| `/daybrief extend <id> <duration>` | Add the supplied duration to the existing expiry. |
| `/daybrief delete <id>` | Remove a brief immediately from active use. |
| `/daybrief clear` | Remove all active briefs in the current scope. |
| `/daybrief config` | View or change defaults. |

Brief IDs should be short and stable so similar messages can be managed without copying their text. IDs such as `b3` and `k7` are illustrative, not a prescribed format or length.

Example listing:

```text
/daybrief list

ID   Message                                 Scope       Expires
b3   Messaging service down; use xxx.         This repo   Today, midnight
k7   Use staging API during migration.       Global      29 Nov, 14:30
```

Examples of subsequent management:

```text
/daybrief show b3
/daybrief edit b3 Messaging service is down; use the local adapter.
/daybrief extend b3 2 days
/daybrief delete k7
/daybrief clear
```

Listings may use concise dates, but full details and save confirmations must make the exact expiry and timezone available. “Today, midnight” means the start of the following local calendar day.

## Expiry and natural-language input

Today is the default, not a hard limit. Users must be able to specify other durations or deadlines in ordinary language.

```text
/daybrief Messaging service is down; use xxx instead.
```

With the default settings, this expires at the next local midnight.

```text
/daybrief Use the staging API. Have this last one month.
```

This lasts one calendar month from creation. For example, a brief created on 29 October 2026 at 14:30 expires on 29 November 2026 at 14:30 in the configured timezone.

```text
/daybrief Avoid deployments until Friday at 5pm.
```

This uses the stated deadline. The confirmation must show the resolved date and time, rather than only repeating “Friday.” If the intended deadline is genuinely ambiguous, ask a short clarification before saving.

An explicit form is also required for precision and scripted use:

```text
/daybrief --for 1mo Use the staging API.
/daybrief --until 2026-11-30 Use the staging API.
```

Rules established in the discussion:

- A message without an explicit expiry uses the configured default.
- The initial default is the end of today in the configured timezone.
- “One month” means one calendar month.
- “30 days” means exactly 30 days, rather than one calendar month.
- Explicit timestamps should be used internally and included with the instructions delivered to agents.
- Saving or changing a brief must show the interpreted expiry so mistakes are visible.
- Genuine ambiguity should trigger a concise clarification.
- Expiry must be checked when selecting active briefs; it must not depend solely on an agent interpreting a date or on a cleanup job running.

Exact parsing grammar, date-only deadline semantics, daylight-saving behaviour for day durations, and end-of-month calendar arithmetic remain implementation decisions to resolve and document.

## Configuration and scopes

Configuration should support:

| Setting | Initial default | Other intended options |
| --- | --- | --- |
| Default expiry | End of today | 24 hours, one week, or a custom duration. |
| Timezone | User's local timezone | An explicitly configured timezone. |
| Default scope | Current repository | Global, across the user's projects. |

A repository brief applies to agents working in that repository. A global brief applies across the user's projects. Global scope does not, by itself, mean team sharing or cross-device synchronisation.

In a repository, the normal reading experience should expose both applicable global briefs and briefs for that repository, with scope clearly labelled. Mutating commands, especially `clear`, must have a clearly defined target scope; clearing the current repository must not also clear global briefs implicitly.

The exact configuration file format, scope-selection syntax, configuration precedence, and repository identity rules are not yet chosen.

## Delivery to agents

The intended experience is that creating a brief through one supported tool makes it available to the other supported tools in the same applicable scope. Users should not have to enter the same message separately in Codex, Claude Code, and Copilot.

An implementation therefore needs a shared source of brief data and an adapter for each supported client. No particular database, runtime, package manager, or transport has been selected.

Each delivered brief should carry enough information for an agent to understand its applicability: ID, message, scope, expiry, and timezone. It supplements enduring project instructions. Rules for conflicts with existing instructions or other active briefs still need to be defined; do not silently assume that a temporary brief overrides every other instruction.

The command syntax shown in this document is the desired product interface. Custom-command registration and instruction loading differ by client, so identical native support everywhere must be verified rather than assumed.

The initial implementation can target specific CLI clients before expanding to other surfaces. In particular, “GitHub Copilot support” must identify the supported environment, such as Copilot CLI or an IDE integration, rather than implying that every Copilot surface behaves identically.

## Existing conversations and withdrawn instructions

Expiry in storage does not erase text that an agent has already read. This is a central product constraint.

- New instruction delivery must omit briefs that are expired or deleted.
- Injected instructions must include their explicit expiry so an agent can recognise when they cease to apply.
- Editing, extending, deleting, or expiring a brief may require an update to an already-running conversation.
- Each integration must define when it refreshes briefs and how it communicates changes or withdrawals.
- The product must not promise that every running agent instantly forgets an expired or deleted instruction.

Checking only at session startup would leave long-running sessions with stale instructions. Investigate refresh opportunities supported by each client and describe the resulting guarantees honestly.

## State and history

A brief has a stable ID, message, scope, creation time, and expiry. Implementations should also track updates as needed to deliver changed instructions reliably.

- **Active:** Available for delivery and has not reached its expiry.
- **Expired:** Its expiry has been reached; no longer delivered as active.
- **Deleted:** Explicitly withdrawn; no longer delivered as active.

Expired briefs should remain discoverable through `list --all`. Whether deleted briefs are retained in history, and how history is purged, have not been decided. Do not interpret “delete” as a promise about permanent erasure until those semantics are defined.

## Initial delivery priorities

Keep the first version focused on the agreed workflow:

1. Create a brief with default, natural-language, or explicit expiry.
2. Confirm the message's scope and resolved expiry.
3. List, inspect, edit, extend, delete, and clear briefs.
4. Configure expiry, timezone, and default scope.
5. Supply active briefs across the initial supported agent clients.
6. Exclude expired or withdrawn briefs and document active-session refresh behaviour.

A web dashboard, hosted service, accounts, team administration, cross-device sync, and external incident integrations were not requested. They are not prerequisites for the first version.

## Open decisions for implementation

- Which exact client surfaces and versions are supported first, and how is `/daybrief` registered in each?
- What shared storage and installation approach lets those clients use the same briefs?
- How are repository identities handled across worktrees, clones, and machines?
- How does a user explicitly select repository or global scope for each command?
- What does a date-only `--until` mean, and how are conflicting expiry expressions handled?
- How are calendar months handled when the target month lacks the original day?
- How are day durations interpreted across daylight-saving transitions?
- Can an expired brief be extended to reactivate it, or must the user create a new one?
- How do active sessions learn about new, edited, expired, and withdrawn briefs?
- What happens when two active briefs conflict with one another or with enduring instructions?
- What history is retained after deletion or clearing, and for how long?
- What exact syntax is used to change configuration?

Resolve these deliberately during implementation. They are not settled requirements disguised as technical choices.

## Observable success criteria

- A user can record a temporary service outage once and have the same active brief available across supported tools in the applicable scope.
- A brief without an explicit expiry ends at the next local midnight under the initial defaults.
- A request to last one month resolves to a calendar-month expiry and confirms the exact date, time, and timezone.
- Explicit duration and deadline forms work alongside natural-language creation.
- `list` exposes active briefs with stable IDs, scope, and expiry; `list --all` also exposes expired history.
- Editing preserves expiry unless the user changes it; extending adds time to the existing expiry.
- Deleting and clearing remove the affected briefs from subsequent active delivery.
- Repository and global scopes remain distinguishable, including during bulk removal.
- Client-specific limitations around refresh and existing conversations are explicit.

## Integration research starting points

These official pages were consulted during the discussion. Recheck the capabilities of the chosen client versions before implementing adapters:

- [Codex plugin packaging and hooks](https://developers.openai.com/plugins/build/plugins)
- [Claude Code hooks reference](https://code.claude.com/docs/en/hooks)
- [GitHub Copilot custom-instruction support by environment](https://docs.github.com/en/copilot/reference/custom-instructions-support)
