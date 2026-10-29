# Initial release candidate verification

Verified on Linux on 2026-10-29, using Python 3.12.3 and uv 0.11.21.
This record covers local release validation; GitHub publication/CI is a separate
final milestone recorded in [progress](progress.md).

## Reproducible checks

```sh
uv run --frozen python scripts/check.py
uv run --frozen python scripts/verify_release.py
uv run --frozen python scripts/verify_push_hook.py
```

The aggregate gate passes formatting, Ruff lint, strict mypy, **58 tests**, and
wheel/source builds. The release validator inspects both archives, installs the
wheel without dependencies into a clean Python environment, then exercises the
console entry point, next-midnight default, editing, extension, deletion/history,
configuration, scoped clear and all three packaged adapter install/delivery/removal
paths. Installed hooks read the same CLI-created IDs and omit withdrawn briefs.

Fresh-checkout validation installs the hooks, performs a passing push to a local
bare repository, deliberately introduces a formatting error, and verifies that a
second push is rejected. Aggregate tests cover staged-snapshot pre-commit behavior,
including partially staged files and preservation of existing hooks.

README onboarding was also followed using `uv tool install --python 3.12 .` in
an isolated HOME and tool directory, through all adapter setup/removal commands
and package uninstall. No personal client settings or real brief database were
used for these checks.

## Native-client acceptance

With the prerequisites in the [support matrix](support-matrix.md):

```sh
uv run --frozen python scripts/verify_release.py --native
```

The release **wheel's interpreter and installed package**, not the editable
source environment, passed all six native probes:

| Client | Version | Installed skill + post-tool withdrawal | Same-process prompt + compaction refresh |
| --- | --- | --- | --- |
| Codex CLI | 0.165.0 | Passed (`$daybrief`) | Passed |
| Claude Code CLI | 2.1.312 | Passed (`/daybrief`) | Passed |
| GitHub Copilot CLI | 1.0.105 | Passed (`/daybrief`) | Passed |

These run real client binaries against a **synthetic loopback model**. They
observe actual tool deletion, next-turn context and native manual compaction
completion; post-compaction snapshots must be newer than the deletion timestamp.
No hosted model was used. Model interpretation/obedience and automatic compaction
without a later supported event are not claimed. Brief expiry itself is enforced
in shared storage selection and covered with a controlled clock.

## Distribution and licensing audit

The wheel contains only Daybrief modules/resources and distribution metadata.
It has no `Requires-Dist` runtime dependencies and includes the complete MIT
license. The source archive includes the README and banner. Archive checks reject
runtime SQLite files, bytecode, virtual environments, Git metadata and personal
client configuration. Tracked files contain no runtime database or credentials;
no token/key patterns were found in the source/docs/probes audit.

Development/build dependencies from the installed lockfile metadata:

| Dependency | License metadata |
| --- | --- |
| hatchling, iniconfig, librt, mypy, mypy_extensions, pluggy, pytest, ruff, tomlkit | MIT |
| packaging | Apache-2.0 OR BSD-2-Clause |
| pathspec | MPL-2.0 |
| Pygments | BSD-2-Clause |
| trove-classifiers | Apache Software License |
| typing_extensions | PSF-2.0 |

These tools are used for building/checking and are not bundled as third-party
runtime code in the wheel. Their versions are pinned in `uv.lock`. Python's
standard library comes from the user's interpreter, not the package archive.

The original generated banner has no supplied third-party source image, stock
asset or distributed font file. Its prompt, preparation and visual inspection are
recorded in [asset provenance](assets/README.md). The complete MIT license uses
2026 and ZakYeo attribution.
