# Development setup

Daybrief is under construction. Python 3.12 and uv 0.11.21 are the contributor
baseline. The committed lockfile fixes development dependencies.

```sh
uv sync --frozen
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

Version-controlled Git hooks and their setup instructions are the next
foundation slice. There is no usable product CLI yet.
