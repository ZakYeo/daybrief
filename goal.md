# Goal: build and publish Daybrief

## Overall goal

Build **Daybrief**, as defined in `product.md`, into a working, well-tested, maintainable open-source tool and publish it as a polished public repository under my personal GitHub account, **ZakYeo**.

Daybrief is a message of the day for coding agents: write a temporary instruction once, make it available across supported tools, and stop supplying it when it expires. Deliver the complete initial workflow, shared storage, repository and global scopes, reliable expiry, and integrations for Codex, Claude Code, and GitHub Copilot. Include a welcoming README, an original custom banner, pre-commit and pre-push hooks, CI, and an MIT license.

The working directory is `motd`, but the product name is **Daybrief**. Use **`ZakYeo/daybrief`** as the intended GitHub repository unless an existing remote establishes a different personal repository for this project. `product.md` is the product source of truth; this document defines the delivery sequence and working approach. Preserve existing user work.

## How to execute this goal

Work through the numbered steps below **in order**. They are high-level milestones: the implementor should break each step into small, coherent implementation slices when reaching it, rather than treating this document as a task-by-task implementation plan.

For every step:

1. Define its slices and the evidence needed to demonstrate the step's outcome.
2. Implement each slice, run appropriate checks, and **commit as you go** with clear commit messages. Keep commits focused and preserve unrelated user changes. Do not defer all commits until the end of a step or bypass hooks.
3. Once all slices for the step are complete, **launch a fresh subagent to independently review the whole step**. This review happens after each high-level step, not after every slice. Give the reviewer this goal, the relevant product requirements, the step's commit range, and the validation results. Have it inspect the actual changes and their interaction with the existing code, not just the implementor's summary.
4. Ask the reviewer to identify correctness problems, missing requirements, maintainability issues, inadequate verification, and misleading documentation or support claims. For non-code steps, review the relevant design, assets, documentation, or publication evidence.
5. Implement the review findings, rerun affected checks, and commit the fixes. If a finding is demonstrably inapplicable, record the evidence rather than silently ignoring it. Have the reviewer confirm that the findings are resolved; repeat fixes and review as needed.
6. Record a concise step completion note with the outcome, checks, commits, and review disposition. **Do not start the next step until this review-and-fix gate is complete.** Apply the same gate to the final step before declaring the overall goal complete.

Use the available subagent mechanism for these reviews. Use Term Dad only if I explicitly request it for this task. If subagents are unavailable, report that blocker instead of substituting a self-check and claiming the review gate passed.

Make reasonable implementation decisions autonomously, document consequential choices, and give concise progress updates. Ask only when missing information materially blocks progress. Do not claim completion of an unmet requirement merely by listing it as a limitation.

## Ordered implementation steps

### 1. Validate the product approach and integration feasibility

Read `product.md` and applicable repository instructions. Inspect the repository, existing remote, and personal Git identity before making commits; use the configured personal identity without guessing an email address or changing global Git settings.

Verify the current integration capabilities against official client documentation. Identify the exact supported client surfaces and versions, especially the Copilot environment, and investigate command registration, instruction delivery, refresh, and withdrawal. Use a small integration spike to validate the approach before building around it. Do not invent APIs or promise that an existing conversation instantly forgets withdrawn instructions.

Choose a proportionate runtime, storage, packaging, and adapter design. Resolve and document the open product decisions, including time arithmetic, repository identity and worktrees, scope selection, configuration, conflicting instructions, and history. Make clear which natural-language interpretation belongs to the client agent and which belongs to Daybrief; preserve deterministic explicit command forms.

**Outcome:** an evidence-backed implementation approach, explicit product decisions, and a realistic support matrix. Any capability gap that prevents the required workflow is surfaced before dependent implementation begins.

### 2. Establish the repository foundation and quality gates

Set up the project structure, dependency management, build/package workflow, and development commands. Provide one aggregate check command, backed by formatting, linting, type checking where applicable, tests, and build validation. Add GitHub Actions using the same underlying checks for pull requests and default-branch pushes.

Install version-controlled hooks: fast staged-file checks on **pre-commit**, with safe handling of partially staged files, and the full deterministic local quality gate on **pre-push**. Document fresh-clone setup and verify both passing and deliberately failing hook paths in isolation. Checks must not require paid services or interactive client authentication. Extend the checks as functionality arrives in later steps.

Add the complete **MIT license**, using the implementation year and **ZakYeo** attribution unless an established preferred attribution exists. Align package metadata, ignore runtime data and personal configuration, and commit the appropriate lockfile.

**Outcome:** a reproducible contributor setup with working hooks, CI configuration, licensing, and checks that all subsequent implementation uses.

### 3. Implement the shared brief model, persistence, and expiry

Build the shared core for briefs, configuration, repository/global applicability, history, and lifecycle operations. Implement the agreed time semantics, including next-local-midnight defaults, calendar months versus fixed durations, exact expiry boundaries, and timezone handling. Filter expired and deleted briefs whenever active data is selected.

Keep domain behaviour, time handling, persistence, and external I/O clearly separated. Use an injectable clock and meaningful tests for boundary cases, scope isolation, malformed state, and concurrent writes. Handle errors without silently losing data. Prefer cohesive modules, descriptive names, explicit contracts, and straightforward control flow over speculative abstractions or giant files.

**Outcome:** a tested shared core that reliably stores, selects, updates, and withdraws briefs according to `product.md`.

### 4. Deliver the complete command-line workflow

Expose creation, listing, inspection, editing, extension, deletion, clearing, and configuration through a usable local CLI. Support explicit expiry forms and the agreed natural-language path. Show exact resolved expiry and timezone, preserve expiry on edits unless changed, and keep bulk mutations scoped correctly.

Provide clear validation and actionable errors. Test observable command behaviour against isolated temporary data, including invalid and ambiguous input. Keep the CLI thin so integrations reuse the same rules and data.

**Outcome:** the full product workflow works through real commands, with repeatable end-to-end evidence and clear user-facing output.

### 5. Integrate the supported coding-agent clients

Implement and package the verified adapters for Codex, Claude Code, and the chosen GitHub Copilot surface. Connect them to the shared data and command behaviour so a brief created through one supported client is available to the others in the applicable scope.

Deliver each brief with its ID, message, scope, expiry, and timezone. Implement the supported refresh and withdrawal mechanisms, preserve existing client configuration and instruction files, and make installation, updates, and removal repeatable. Treat brief text as data rather than executable shell content.

Test each adapter's delivery and lifecycle behaviour. Run live client smoke checks where available, and distinguish them from fixtures or mocked tests. Document exact limitations; a stub, unsupported command, or README claim is not a working integration.

**Outcome:** working cross-client delivery with verified installation paths and explicit evidence for the advertised support and refresh guarantees.

### 6. Create the public-facing documentation and visual identity

Write a polished README led by the custom banner, the Daybrief name, and a concise value statement, such as “A message of the day for your coding agents, lasting as long as you need.” Explain the problem with a concrete example and give verified prerequisites, installation instructions, and a copyable quick start.

Cover client setup and support, commands, expiry and scope rules, configuration, data storage and retention, uninstallation, architecture, and licensing. Include a compact demonstration using real output or a reproducible example. Add a concise `CONTRIBUTING.md` covering setup, hooks, checks, and clean code expectations. Use only genuine badges and working links; do not link to unpublished packages as though they exist.

Use the available image-generation capability and its skill to create an **original custom README banner**. Aim for a distinctive, restrained developer-tool identity with a subtle dawn, daily briefing, or terminal motif. Use a wide composition around 3:1, legible text if included, and good contrast. Save an optimised asset such as `docs/assets/daybrief-banner.png`, use a relative link and useful alt text, and include brief provenance/regeneration notes. Inspect the image for spelling, cropping, and readability on light and dark backgrounds. Do not count a placeholder as finished artwork.

**Outcome:** a new visitor can understand, install, use, and contribute to Daybrief, and the repository has a finished custom visual identity.

### 7. Verify the complete release candidate

Run the full quality gate and exercise the product's observable success criteria. Build the distributable artifact, install it into a clean temporary environment, and follow the README quick start. Verify hook setup from a fresh checkout and test the real cross-client workflow where the required clients are available.

Check that documentation matches actual behaviour, that runtime data is excluded from the repository, and that dependency licenses and asset attribution are consistent with distribution. Fix discovered problems, add regression coverage where useful, and distinguish live verification from simulated evidence. Keep the initial release focused: hosted services, dashboards, accounts, team administration, and cross-device sync are outside this goal.

**Outcome:** a release candidate with reproducible checks, verified packaging and onboarding, and no unresolved findings from this step's subagent review.

### 8. Publish to personal GitHub and verify the result

Confirm the authenticated account and intended remote. Create **`ZakYeo/daybrief`** as a public repository if needed, or use the existing intended personal repository. Resolve any conflict with an unrelated repository before modifying it. Preserve existing history and push the reviewed commits to the intended default branch.

Set a concise repository description and relevant topics. Verify public visibility, the README and banner rendering, repository links, license, and the actual GitHub Actions result. Fix publication issues and have the final step's subagent review the published result as well as any changes. Keep publication within this goal to GitHub; package-registry publication is a separate release task.

**Outcome:** a public, usable repository owned by my personal account, with passing CI and the final review gate complete. If authentication, permissions, or unavailable services prevent completion, report the exact blocker and completed local work without claiming publication succeeded.

## Final handoff

Provide the repository URL, a short explanation of what shipped, verification results, and a summary of the completed step reviews and fixes. State any remaining limitations accurately and distinguish local completion, live client verification, and successful GitHub publication. Declare the goal complete only when the required deliverables and every step's review gate are satisfied.
