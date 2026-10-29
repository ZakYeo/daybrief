# Development setup

Python 3.12 and uv 0.11.21 are the contributor
baseline. The committed lockfile fixes development dependencies.

```sh
uv sync --frozen
uv run --frozen python scripts/install_hooks.py
uv run --frozen python scripts/check.py
```

The aggregate check validates the lockfile, formatting, lint, strict typing,
tests, and wheel/source builds. GitHub Actions runs the same command. It needs
no agent account or paid service; the initial dependency installation needs
network access. Native-client research probes in `spikes/` are separate from
the deterministic gate and are not production code.

Use `uv run ruff format .` to format and `uv run pytest` for focused test runs.
Build artifacts go to ignored `dist/`. Runtime SQLite data, local configuration,
caches, and virtual environments must not be committed. The library is licensed
under MIT; the complete license is included in distributions.

Pre-commit checks staged whitespace and Python formatting/lint using a temporary
copy of the index. It never stashes, formats, or rewrites your working files.
Pre-push runs the entire aggregate gate. Both hooks are version controlled in
`.githooks`; setup refuses to replace an unrelated `core.hooksPath` or bypass
existing executable hooks in Git's default hook directory. If you
already use another hook manager, integrate these commands there explicitly.
The local CLI is available; see [command workflow](cli.md).

After committing hook changes, run `uv run python scripts/verify_push_hook.py`.
It clones committed HEAD, sets up the hooks, and verifies passing/failing pushes
to a temporary local bare repository. Dependencies must already be cached for
its offline fresh-clone install. This separate integration check avoids
recursively running the full gate from inside its own test suite.
