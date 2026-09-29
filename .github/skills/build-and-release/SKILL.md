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
5. **Version bump requires the user's version, every time**: When the user asks to "publish a release" or "create a
   release" (see Command → Action Mapping below), always `ask_user` for the release version *before* doing anything
   else - even if they didn't include one in their request. The prompt must remind them of the current version (read
   fresh via `Get-ProjectVersion`) so they have a reference point, e.g. "What version should this release be? (current:
   2026.0.0.5)". Once you have the version, run `bump-version.ps1 -Version <version>` (which drives Commitizen) before
   any check/build/publish steps. Never invent, guess, or auto-increment the version yourself.
6. **Pause for changelog review after every bump**: `bump-version.ps1` regenerates `CHANGELOG.md` and creates a local
   commit + tag, but never pushes. After it succeeds, always show the programmer the new `CHANGELOG.md` entry (e.g. via
   `open_file`) and give them the chance to request edits before anything is pushed or published. Only after that
   review is acknowledged should you `ask_user` whether to push the bump (commit + tag) and continue with the rest of
   the release. See "Version Bumping with Commitizen" below for the exact sequence.
7. **Never store secrets**: Never hardcode, print in full, or write `UV_PUBLISH_TOKEN` (or any other credential) to any
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

| User asks for...                                                                   | Steps to run, in order                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
|------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| "run a release check", "is this ready for a release?", "check if ready to release" | `release-check.ps1`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| "run a dry run", "publish dry run", "test the publish"                             | `publish-dry-run.ps1` (branch + clean guards apply)                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| "publish a release" (standalone request, not part of a full/create flow)           | **1.** `ask_user` for the version (remind them of the current version) → **2.** `bump-version.ps1 -Version <version>` → **3.** show/`open_file` the new `CHANGELOG.md` entry, let the programmer request edits → **4.** `ask_user` whether to push the bump and continue → **5.** if yes: `push-version-bump.ps1 -Version <version>` → **6.** `publish.ps1` (branch + clean + version + duplicate guards apply)                                                                                    |
| "create a release", "cut a release", "release be created/published", full release  | **1.** `ask_user` for the version (remind them of the current version) → **2.** `bump-version.ps1 -Version <version>` → **3.** show/`open_file` the new `CHANGELOG.md` entry, let the programmer request edits → **4.** `ask_user` whether to push the bump and continue → **5.** if yes: `push-version-bump.ps1 -Version <version>` → **6.** `release-check.ps1` → **7.** `release-build.ps1` → **8.** `publish-dry-run.ps1` → **9.** `publish.ps1` (stop the chain if any step returns non-zero) |
| "build a release now", "build a release but skip the checks"                       | `release-build.ps1` → `publish.ps1` (skips `release-check`/`publish-dry-run`; **no version prompt/bump** - only "publish a release" and "create a release" trigger the bump step)                                                                                                                                                                                                                                                                                                                  |
| "run the tests"                                                                    | `test.ps1` (coverage on by default; add `-NoCoverage` if the user asks to skip coverage)                                                                                                                                                                                                                                                                                                                                                                                                           |
| "run bandit", "run a security scan"                                                | `bandit.ps1`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| "run lint", "run ruff"                                                             | `lint.ps1`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| "clean the build artifacts" / "full clean"                                         | `clean.ps1` (add `-Full` for a `distclean`-equivalent wipe of `.venv`/`dist`)                                                                                                                                                                                                                                                                                                                                                                                                                      |

## Scripts (`scripts/windows/`)

| Script                  | Equivalent Makefile target(s)                      | Notes                                                                                                                                                                                                                      |
|-------------------------|----------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `common.ps1`            | n/a (shared helpers)                               | `Get-RepoRoot`, `Get-ProjectVersion`, `Test-VersionFormat`, `Get-CurrentBranch`, `Test-GitClean`, `Get-PublishToken`, `Get-PyPiPackageInfo`. Dot-sourced by every other script.                                            |
| `clean.ps1`             | `clean` / `distclean` (`-Full`)                    | Removes lint/test artifacts; `-Full` also removes `.venv`, `.venv-dev`, `dist`.                                                                                                                                            |
| `test.ps1`              | `test`                                             | Runs `uv run pytest --cov` directly (see note below on why this differs from the Makefile's tox runner). Code coverage is on by default - pass `-NoCoverage` to skip it. See "Code Coverage" below.                        |
| `bandit.ps1`            | `bandit`                                           | `uv run bandit -n 3 -r src\lib_6107 -o bandit.log`.                                                                                                                                                                        |
| `lint.ps1`              | `ruff` / `lint`                                    | `uv run ruff check src\lib_6107`; writes `ruff.out`. Uses ruff, not pylint.                                                                                                                                                |
| `bump-version.ps1`      | n/a (Commitizen-driven, no direct Makefile target) | Branch + clean-tree + version-format + already-current-version guards, then `uv run cz bump <version> --yes --check-consistency`. Creates a local commit + tag; never pushes. See "Version Bumping with Commitizen" below. |
| `push-version-bump.ps1` | n/a (Commitizen-driven, no direct Makefile target) | Pushes the branch and the `v<version>` tag created by `bump-version.ps1` to origin. Only run this after the programmer has reviewed `CHANGELOG.md` and agreed to continue - see below.                                     |
| `release-check.ps1`     | `release-check`                                    | Runs `clean` → `test` → `bandit` → `lint`, prints a pass/fail summary.                                                                                                                                                     |
| `release-build.ps1`     | `release-build`                                    | Branch + version-format guards, then `uv build --no-sources`.                                                                                                                                                              |
| `publish-dry-run.ps1`   | `publish-dry-run`                                  | Branch + clean-tree guards, then dry-run publish to TestPyPI and PyPI.                                                                                                                                                     |
| `publish.ps1`           | `publish`                                          | Branch + clean-tree + version-format + duplicate-version guards, then real publish + import check.                                                                                                                         |

### Version Bumping with Commitizen

This project uses [Commitizen](https://commitizen-tools.github.io/commitizen/) (`[tool.commitizen]` in
`pyproject.toml`) to bump the version and update `CHANGELOG.md`. Because the version scheme here is calendar-based
(`YYYY.MAJOR.MINOR.PATCH`, not semver), bumps are always done with an explicit, user-supplied version rather than
letting Commitizen infer the next version from commit messages.

- **Always ask first**: for "publish a release" and "create a release" requests, `ask_user` for the target version
  before running anything, reminding them of the current version (`Get-ProjectVersion`). Never guess or auto-increment.
- **Command used under the hood**: `uv run cz bump <version> --yes --check-consistency`. Note that the installed
  Commitizen version (4.x, per `pyproject.toml`'s `dev` dependency group) no longer accepts the older
  `--manual-version <version>` flag - the target version is now a **positional** argument (`cz bump <version>`).
  `bump-version.ps1` already uses the correct positional form; if you ever invoke `cz bump` directly instead of via
  the script, use the positional form, not `--manual-version`.
- **What it does**: updates the version in both `version_files` entries (`pyproject.toml` and
  `src/lib_6107/__init__.py`'s `__version__`), regenerates `CHANGELOG.md`, and creates a commit + a `v<version>` tag -
  this is why `bump-version.ps1` requires a clean working tree (same guard style as `publish`/`publish-dry-run`).
- **Guardrails** (see `bump-version.ps1`): branch must be `main` (unless `-AllowBranch`), working tree must be clean
  (unless `-AllowDirty`), requested version must match `YYYY.MAJOR.MINOR.PATCH`, and the requested version must differ
  from the current one.
- **After the bump: pause for changelog review, then ask before pushing.** `bump-version.ps1` never pushes anything -
  the commit and tag only exist locally when it returns `0`. Once it succeeds:
    1. Show the programmer the new section of `CHANGELOG.md` (e.g. `open_file` on `CHANGELOG.md`, or quote the new
       entry in chat) and explicitly invite them to request edits before anything goes further.
    2. If they request changes, make them with `edit`, then fold them into the bump commit and move the tag to match
       (the tag must point at the amended commit):
       ```powershell
       git add CHANGELOG.md
       git commit --amend --no-edit
       git tag -f v<version>
       ```
    3. `ask_user` whether to push the bump (commit + tag) now and continue with the rest of the release, e.g. "Ready to
       push this version bump and continue with the release?" with choices like "Yes, push and continue" / "No, stop
       here for now".
    4. If yes: run `push-version-bump.ps1 -Version <version>`, then resume the pipeline for the original request
       (`publish.ps1` alone for "publish a release", or `release-check.ps1` → ... → `publish.ps1` for "create a
       release").
    5. If no: stop. Leave the commit/tag local and unpushed, and tell the programmer they can resume later by asking to
       push and continue, or by running `push-version-bump.ps1` themselves.

### Why `test.ps1` doesn't use tox

`make test` runs pytest through `uvx --with tox-uv tox`. On Windows, `tox.ini`'s
`PYTHONPATH = ./src :./tests` setting (colon-separated) does not translate correctly and the tox run fails even though
the tests themselves pass. `test.ps1` instead runs `uv run pytest` directly, which honors `[tool.pytest.ini_options]`
(`testpaths`, `pythonpath`) already declared in
`pyproject.toml`. Test behavior/results are equivalent; only the runner (and, as of this version, coverage
reporting - see below) differs. Revisit this if/when `tox.ini` is fixed for cross-platform paths.

### Code Coverage

`test.ps1` runs with coverage **on by default** using `pytest-cov` (already a dev dependency in `pyproject.toml`):

```powershell
uv run pytest --cov=lib_6107 --cov-report=term-missing --cov-report=html:htmlcov
```

- A terminal summary (including missing line numbers) is always printed after the test run.
- A browsable HTML report is written to `htmlcov/index.html` (open it directly in a browser to see line-by-line
  coverage). `htmlcov/`, `.coverage`, and the project's actual coverage data file (`frclib.coverage*`, see below) are
  all gitignored and removed by `clean.ps1`.
- Coverage behavior (branch coverage, the data file name, and `omit` patterns) is configured in this project's
  existing **`.coveragerc`** file at the repo root - not in `pyproject.toml`. Coverage.py gives `.coveragerc` priority
  over any `[tool.coverage.*]` table in `pyproject.toml`, so don't add coverage settings to `pyproject.toml`; edit
  `.coveragerc` instead if you need to change them. Its `data_file = frclib.coverage` setting is why the raw coverage
  data file on disk is named `frclib.coverage` (with `.<hostname>.<pid>.<random>` suffixes, since `parallel = True`),
  not the more common `.coverage`.
- Pass `-NoCoverage` to `test.ps1` to run plain `uv run pytest` with no coverage instrumentation, e.g. for the fastest
  possible local iteration loop:

```powershell
pwsh -File ".github\skills\build-and-release\scripts\windows\test.ps1" -NoCoverage
```

- `release-check.ps1` calls `test.ps1` with no arguments, so coverage is always collected (and reported) as part of a
  release check.

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
- For "publish a release" and "create a release" requests, always `ask_user` for the version first (reminding them of
  the current version) and run `bump-version.ps1` before any other step in that flow.
- After every `bump-version.ps1` run, pause and let the programmer review/edit `CHANGELOG.md` before pushing anything;
  only push and continue after they explicitly say so via `ask_user`.

## Avoid (Do Not Do)

- Do not pass `-AllowBranch` or `-AllowDirty` unless the user explicitly authorized bypassing that specific guard in
  their current request.
- Do not hardcode, log, or persist `UV_PUBLISH_TOKEN` or any other credential anywhere, including in this skill's files.
- Do not bump/edit the `[project].version` in `pyproject.toml` yourself to work around a blocked `release-build`/
  `publish` - always ask the user via `ask_user`.
- Do not edit `pyproject.toml`'s version or `src/lib_6107/__init__.py`'s `__version__` by hand to perform a "bump" -
  always go through `bump-version.ps1` (Commitizen) so `CHANGELOG.md` and the git tag stay in sync.
- Do not run `publish`/`publish-dry-run` against a dirty working tree even if only untracked (not modified) files are
  present - both cases block per the user's rule.
- Do not run `push-version-bump.ps1` (or otherwise push the bump commit/tag) before the programmer has had a chance to
  review `CHANGELOG.md` and you've received explicit confirmation via `ask_user` to proceed.
- Do not implement Linux automation as part of unrelated tasks; that work is intentionally deferred (see
  `scripts/linux/README.md`).
