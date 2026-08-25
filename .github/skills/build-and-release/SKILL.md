---
name: build-and-release
description: >-
  Automates checking, building, and publishing PyPI releases of the lib_6107 package for this
  repository (frclib-6107). Use this skill whenever the user asks to run a release check, run a
  publish dry run, publish a release, build a release, or otherwise verify/build/publish this
  project to PyPI. Also covers running the individual test, bandit (security), and lint (ruff)
  steps on their own. Currently only the Windows (PowerShell) automation is implemented; Linux
  automation is a placeholder for a future environment.
license: N/A - internal project automation skill.
---

# Build and Release Skill

## Purpose & Scope

Automates the release workflow for the `lib_6107` package (this repository, `frclib-6107`):
running pre-release checks, building the sdist/wheel, and publishing to PyPI - while enforcing the safety rules below.
This mirrors (and in a couple of spots slightly improves on, see
`scripts/windows/test.ps1`) the targets already defined in this project's `Makefile`.

- **Platform status**: Windows automation (`scripts/windows/*.ps1`) is implemented and verified. Linux automation
  (`scripts/linux/`) is a placeholder to be filled in later, after this skill is imported into a Linux environment.
- This skill uses **ruff** for the lint step (not pylint), per this project's convention.

## Hard Safety Rules (never bypass these silently)

1. **Branch guard**: Never build a release (`release-build`) or publish/dry-run publish (`publish`, `publish-dry-run`)
   from any branch other than `main`, unless the user has *explicitly* asked to do so from the current (non-main) branch
   in this request. If the branch check blocks a script (exit code `2`), stop and use `ask_user` to confirm before
   retrying with
   `-AllowBranch`.
2. **Clean working tree guard**: Never run `publish` or `publish-dry-run` if `git status
   --porcelain` reports any modified, staged, or untracked files. If the script blocks (exit code
   `2`), show the user the reported files and use `ask_user` whether to commit/stash first, or - only if they explicitly
   say so - re-run with `-AllowDirty`.
3. **Version format guard**: Before `release-build` or `publish`, the version in
   `pyproject.toml`'s `[project].version` must match this project's `YYYY.MAJOR.MINOR.PATCH`
   scheme (e.g. `2026.0.0.4` = target year, major, minor, patch). The scripts already validate this and block (exit code
   `2`) with a clear message if invalid - relay this to the user via
   `ask_user` and do not attempt to auto-fix the version yourself.
4. **No duplicate publish**: Before `publish`, the scripts check the exact `[project].version`
   against PyPI's public JSON API for this package. If that version is already published, the script blocks (exit code
   `2`) and reports the latest published version - relay this to the user via `ask_user` and let them choose the new
   version; do not guess or bump it yourself.
5. **Never store secrets**: Never hardcode, print in full, or write `UV_PUBLISH_TOKEN` (or any other credential) to any
   file, including this skill's own files, logs, or chat output. The scripts resolve the token via `Get-PublishToken` in
   `common.ps1`: use `$env:UV_PUBLISH_TOKEN`
   if already set, else read the local (gitignored) `.make\pypi-token.mk` if present, else prompt interactively via a
   secure, non-echoed prompt. The token only ever lives in the current process's environment - never persist it anywhere
   else.

## Script Exit Code Convention

Every script in `scripts/windows/` follows this convention so you (the agent) can react correctly:

| Exit code | Meaning                                                                           | What to do                                                            |
|-----------|-----------------------------------------------------------------------------------|-----------------------------------------------------------------------|
| `0`       | Success                                                                           | Continue to the next step.                                            |
| `1`       | The step genuinely failed (test failures, lint errors, build/publish error)       | Stop the pipeline, show the relevant output to the user.              |
| `2`       | Blocked - needs a user decision (dirty tree, wrong branch, bad/duplicate version) | Stop immediately, relay the "ACTION REQUIRED" message via `ask_user`. |

Always run scripts with PowerShell, e.g.:

```powershell
pwsh -File ".github/skills/build-and-release/scripts/windows/release-check.ps1"
```

(or `powershell -File ...` if `pwsh` is unavailable). Check `$LASTEXITCODE` after each call.

## Command → Action Mapping

Match the user's request to the narrowest applicable row. When in doubt, ask via `ask_user`
rather than guessing.

| User asks for...                                                                   | Steps to run, in order                                                                                                          |
|------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------|
| "run a release check", "is this ready for a release?", "check if ready to release" | `release-check.ps1`                                                                                                             |
| "run a dry run", "publish dry run", "test the publish"                             | `publish-dry-run.ps1` (branch + clean guards apply)                                                                             |
| "publish a release" (standalone request, not part of a full/create flow)           | `publish.ps1` (branch + clean + version + duplicate guards apply)                                                               |
| "create a release", "cut a release", "release be created/published", full release  | `release-check.ps1` → `release-build.ps1` → `publish-dry-run.ps1` → `publish.ps1` (stop the chain if any step returns non-zero) |
| "build a release now", "build a release but skip the checks"                       | `release-build.ps1` → `publish.ps1` (skips `release-check`/`publish-dry-run`)                                                   |
| "run the tests"                                                                    | `test.ps1`                                                                                                                      |
| "run bandit", "run a security scan"                                                | `bandit.ps1`                                                                                                                    |
| "run lint", "run ruff"                                                             | `lint.ps1`                                                                                                                      |
| "clean the build artifacts" / "full clean"                                         | `clean.ps1` (add `-Full` for a `distclean`-equivalent wipe of `.venv`/`dist`)                                                   |

## Scripts (`scripts/windows/`)

| Script                | Equivalent Makefile target(s)   | Notes                                                                                                                                                                           |
|-----------------------|---------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `common.ps1`          | n/a (shared helpers)            | `Get-RepoRoot`, `Get-ProjectVersion`, `Test-VersionFormat`, `Get-CurrentBranch`, `Test-GitClean`, `Get-PublishToken`, `Get-PyPiPackageInfo`. Dot-sourced by every other script. |
| `clean.ps1`           | `clean` / `distclean` (`-Full`) | Removes lint/test artifacts; `-Full` also removes `.venv`, `.venv-dev`, `dist`.                                                                                                 |
| `test.ps1`            | `test`                          | Runs `uv run pytest` directly (see note below on why this differs from the Makefile's tox runner).                                                                              |
| `bandit.ps1`          | `bandit`                        | `uv run bandit -n 3 -r src\lib_6107 -o bandit.log`.                                                                                                                             |
| `lint.ps1`            | `ruff` / `lint`                 | `uv run ruff check src\lib_6107`; writes `ruff.out`. Uses ruff, not pylint.                                                                                                     |
| `release-check.ps1`   | `release-check`                 | Runs `clean` → `test` → `bandit` → `lint`, prints a pass/fail summary.                                                                                                          |
| `release-build.ps1`   | `release-build`                 | Branch + version-format guards, then `uv build --no-sources`.                                                                                                                   |
| `publish-dry-run.ps1` | `publish-dry-run`               | Branch + clean-tree guards, then dry-run publish to TestPyPI and PyPI.                                                                                                          |
| `publish.ps1`         | `publish`                       | Branch + clean-tree + version-format + duplicate-version guards, then real publish + import check.                                                                              |

### Why `test.ps1` doesn't use tox

`make test` runs pytest through `uvx --with tox-uv tox`. On Windows, `tox.ini`'s
`PYTHONPATH = ./src :./tests` setting (colon-separated) does not translate correctly and the tox run fails even though
the tests themselves pass. `test.ps1` instead runs `uv run pytest` directly, which honors `[tool.pytest.ini_options]`
(`testpaths`, `pythonpath`) already declared in
`pyproject.toml`. Coverage/behavior is equivalent; only the runner differs. Revisit this if/when
`tox.ini` is fixed for cross-platform paths.

### Makefile issues fixed upstream

The Makefile previously had a `release-check` dependency on a nonexistent `bandit` target (only
`bandit-test` existed) and a typo in `publish-dry-run`'s TestPyPI URL (`test/pypi.org` instead of
`test.pypi.org`). Both have since been fixed directly in the Makefile (the security-scan target is now named `bandit`,
and the TestPyPI URL is correct) - `bandit.ps1` and `publish-dry-run.ps1`
already matched the corrected behavior.

## Version Scheme

Versions in `pyproject.toml`'s `[project].version` follow `YYYY.MAJOR.MINOR.PATCH`, e.g.
`2026.0.0.4`:

- `YYYY` - target competition season year (e.g. `2026`)
- `MAJOR` - major version
- `MINOR` - minor version
- `PATCH` - patch version

`Test-VersionFormat` in `common.ps1` enforces this shape (`^\d{4}\.\d+\.\d+\.\d+$`).

## Please Do

- Always check `$LASTEXITCODE` after every script invocation and react per the exit-code convention above before moving
  to the next step.
- Stop a multi-step pipeline (e.g. the full create/publish flow) as soon as any step returns non-zero; report what
  happened and, for exit code `2`, ask the user how to proceed.
- Show the user the relevant script output (not just "it failed") so they can act on it.
- Re-verify guardrails freshly for each run; do not cache/assume a previous "clean tree" or
  "correct branch" result still holds.

## Avoid (Do Not Do)

- Do not pass `-AllowBranch` or `-AllowDirty` unless the user explicitly authorized bypassing that specific guard in
  their current request.
- Do not hardcode, log, or persist `UV_PUBLISH_TOKEN` or any other credential anywhere, including in this skill's files.
- Do not bump/edit the `[project].version` in `pyproject.toml` yourself to work around a blocked `release-build`/
  `publish` - always ask the user via `ask_user`.
- Do not run `publish`/`publish-dry-run` against a dirty working tree even if only untracked (not modified) files are
  present - both cases block per the user's rule.
- Do not implement Linux automation as part of unrelated tasks; that work is intentionally deferred (see
  `scripts/linux/README.md`).
