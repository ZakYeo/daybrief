# Contributing to Daybrief

Use Linux, Git, Python 3.12 and uv 0.11.21. From a fresh checkout:

```sh
uv sync --frozen
uv run --frozen python scripts/install_hooks.py
uv run --frozen python scripts/check.py
```

The aggregate gate checks the lockfile, formatting, Ruff lint, strict mypy,
pytest, and wheel/source builds. GitHub Actions runs the same checks. Initial
dependency installation needs network access; the checks need no agent login,
paid model, or external service.

Pre-commit checks the staged snapshot, including partially staged files, without
rewriting or stashing your work. Pre-push runs the full gate. Hook setup refuses
to replace an unrelated hook manager or existing executable default hooks;
integrate the documented commands into that manager if you use one. Do not bypass
checks to get a change through.

For day-to-day work:

```sh
uv run ruff format .
uv run pytest tests/test_time.py
uv run daybrief --help
```

Use a temporary `DAYBRIEF_DATA_DIR` when testing commands. Do not commit personal
client configuration, runtime databases, credentials, virtual environments, or
build output. Keep the runtime dependency-free unless a dependency materially
simplifies the design.

Prefer small cohesive modules and explicit boundaries. Keep expiry and lifecycle
policy in the shared core, not in individual adapters. Test observable behavior:
exact time boundaries, scope separation, failed writes, command output and
configuration preservation matter more than tests that repeat implementation.
Document consequential decisions and keep support claims tied to evidence.

Native-client acceptance probes are optional, separate checks against the exact
versions in the [support matrix](docs/support-matrix.md). They use disposable
profiles and a synthetic model. After hook changes, run
`uv run python scripts/verify_push_hook.py` against committed HEAD to verify both
passing and failing push paths in a temporary clone; its dependencies must already
be cached. More details: [development notes](docs/development.md).

Keep commits focused. Describe the problem, resulting behavior and relevant
validation in pull requests. Include a regression check when fixing a behavioral
bug, and update docs when commands or guarantees change.
