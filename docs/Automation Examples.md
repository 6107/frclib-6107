# Build-and-Release Automation Examples

This document gives copy/paste command-line examples for the 9 request types handled by the
[`build-and-release`](../.github/skills/build-and-release/SKILL.md) skill, so you can run them directly at a shell
prompt without going through the Copilot agent (and therefore without incurring any agent/token usage).

- **Windows** examples use `powershell`/`pwsh` and call the skill's scripts directly
  (`.github/skills/build-and-release/scripts/windows/*.ps1`).
- **Linux** examples use the project's `Makefile` targets (`make ...`) plus the underlying `uv`/`cz`/`git` commands for
  the version-bump steps, since the Linux side of the skill (`scripts/linux/`) is still a placeholder and has no
  scripts of its own yet — see `.github/skills/build-and-release/scripts/linux/README.md`.

All commands below assume your shell's current directory is the repository root (`D:\Source\repos\github\frclib-6107` on
Windows, or wherever you cloned the repo on Linux).

> **None of the commands in this document were executed as part of writing it.** They are provided as reference only.
> In particular, the "publish a release", "create a release", and "build a release now" examples are real,
> repository-mutating and PyPI-publishing operations — read the notes under each one carefully before running them.

---

## 1. "run a release check" / "is this ready for a release?"

Runs clean → test → bandit → lint (ruff) and prints a pass/fail summary. Does not touch git or build/publish anything.

**Windows (PowerShell):**

```powershell
powershell -File ".github\skills\build-and-release\scripts\windows\release-check.ps1"
```

Options:

- `-Full` — also wipes `.venv`/`.venv-dev`/`dist` first (equivalent to `make distclean` before checking).

```powershell
powershell -File ".github\skills\build-and-release\scripts\windows\release-check.ps1" -Full
```

**Linux (bash):**

```bash
make release-check
```

`make release-check` already depends on `distclean` first, so there's no separate "full" flag needed on Linux.

---

## 2. "run a dry run" / "publish dry run" / "test the publish"

Dry-run publishes to TestPyPI and PyPI (no real upload) via `uv publish --dry-run`.

**Windows (PowerShell):**

```powershell
powershell -File ".github\skills\build-and-release\scripts\windows\publish-dry-run.ps1"
```

Options:

- `-AllowBranch` — allow running from a branch other than `main` (only use this if you specifically intend to dry-run
  from a feature branch).
- `-AllowDirty` — allow running with a dirty working tree (modified/staged/untracked files present). Normally the
  script blocks (exit code 2) and asks you to commit or stash first.

```powershell
powershell -File ".github\skills\build-and-release\scripts\windows\publish-dry-run.ps1" -AllowBranch -AllowDirty
```

**Linux (bash):**

```bash
make publish-dry-run
```

This project's `Makefile` doesn't implement the branch/clean-tree guardrails the Windows script has — if you want that
same safety, check manually first:

```bash
[ "$(git branch --show-current)" = "main" ] || echo "WARNING: not on main"
git status --porcelain   # should print nothing before a dry run
make publish-dry-run
```

---

## 3. "publish a release" (standalone — package already built, no full check pipeline)

Full sequence: ask for the version → bump it via Commitizen → review/edit `CHANGELOG.md` → push the bump → publish.

> **This is a real, mutating operation.** `bump-version.ps1`/`cz bump` creates a real commit + git tag locally;
> pushing sends that to `origin`; `publish.ps1`/`uv publish` uploads a real package version to PyPI, which cannot be
> deleted or re-uploaded once used. Only run past step 2 when you're sure.

**Windows (PowerShell):**

```powershell
# 1. Bump the version (replace 2026.0.0.6 with your target version).
#    Prints the CHANGELOG.md section it generated; review/edit CHANGELOG.md yourself before continuing.
powershell -File ".github\skills\build-and-release\scripts\windows\bump-version.ps1" -Version "2026.0.0.6"

# 2. (Optional) If you edited CHANGELOG.md after the bump, fold the edit into the bump commit and move the tag:
git add CHANGELOG.md
git commit --amend --no-edit
git tag -f v2026.0.0.6

# 3. Push the bump commit + tag to origin.
powershell -File ".github\skills\build-and-release\scripts\windows\push-version-bump.ps1" -Version "2026.0.0.6"

# 4. Publish to PyPI.
powershell -File ".github\skills\build-and-release\scripts\windows\publish.ps1"
```

`bump-version.ps1` options:

- `-AllowBranch` — allow bumping from a branch other than `main`.
- `-AllowDirty` — allow bumping with a dirty working tree (normally blocked, since Commitizen needs to commit the bump).

`publish.ps1` options:

- `-AllowBranch` — allow publishing from a branch other than `main`.
- `-AllowDirty` — allow publishing with a dirty working tree.

**Linux (bash):**

```bash
# 1. Bump the version (replace 2026.0.0.6 with your target version).
uv run cz bump 2026.0.0.6 --yes --check-consistency

# Review/edit CHANGELOG.md now if desired, then:
git add CHANGELOG.md
git commit --amend --no-edit
git tag -f v2026.0.0.6

# 2. Push the bump commit + tag.
git push
git push origin v2026.0.0.6

# 3. Publish to PyPI.
make publish
```

---

## 4. "create a release" / "cut a release" / full release request

Same version-bump/review/push preamble as above, then the full check → build → dry-run → publish pipeline.

> **This is a real, mutating operation** — same caveats as #3 above, plus it builds and publishes a real distribution.

**Windows (PowerShell):**

```powershell
# 1. Bump the version.
powershell -File ".github\skills\build-and-release\scripts\windows\bump-version.ps1" -Version "2026.0.0.6"

# 2. (Optional) fold in any CHANGELOG.md edits, as in example 3 above.
git add CHANGELOG.md
git commit --amend --no-edit
git tag -f v2026.0.0.6

# 3. Push the bump.
powershell -File ".github\skills\build-and-release\scripts\windows\push-version-bump.ps1" -Version "2026.0.0.6"

# 4. Full release pipeline.
powershell -File ".github\skills\build-and-release\scripts\windows\release-check.ps1"
powershell -File ".github\skills\build-and-release\scripts\windows\release-build.ps1"
powershell -File ".github\skills\build-and-release\scripts\windows\publish-dry-run.ps1"
powershell -File ".github\skills\build-and-release\scripts\windows\publish.ps1"
```

Stop and address the problem if any step above exits non-zero before running the next one.

`release-build.ps1` options:

- `-AllowBranch` — allow building from a branch other than `main`.

**Linux (bash):**

```bash
# 1. Bump the version.
uv run cz bump 2026.0.0.6 --yes --check-consistency

# 2. Review/fold in CHANGELOG.md edits, as above.
git add CHANGELOG.md
git commit --amend --no-edit
git tag -f v2026.0.0.6

# 3. Push the bump.
git push
git push origin v2026.0.0.6

# 4. Full release pipeline.
make release-check
make release-build
make publish-dry-run
make publish
```

(Stop between each `make` target and check its exit status — `echo $?` — before proceeding to the next.)

---

## 5. "build a release now" / "build a release but skip the checks"

Skips `release-check`/`publish-dry-run`/the version-bump prompt entirely — just builds and publishes what's currently
checked in.

> **This is a real, mutating operation.** It publishes whatever is currently in `pyproject.toml`'s `[project].version`
> to PyPI without running tests, bandit, or lint first, and without bumping the version for you.

**Windows (PowerShell):**

```powershell
powershell -File ".github\skills\build-and-release\scripts\windows\release-build.ps1"
powershell -File ".github\skills\build-and-release\scripts\windows\publish.ps1"
```

**Linux (bash):**

```bash
make release-build
make publish
```

---

## 6. "run the tests"

**Windows (PowerShell):**

```powershell
powershell -File ".github\skills\build-and-release\scripts\windows\test.ps1"
```

(Runs `uv run pytest` directly — see the comment in `test.ps1` for why this differs from the Makefile's `tox`
runner on Windows.)

**Linux (bash):**

```bash
make test
```

---

## 7. "run bandit" / "run a security scan"

**Windows (PowerShell):**

```powershell
powershell -File ".github\skills\build-and-release\scripts\windows\bandit.ps1"
```

**Linux (bash):**

```bash
make bandit
```

---

## 8. "run lint" / "run ruff"

Uses **ruff**, not pylint, per this project's convention.

**Windows (PowerShell):**

```powershell
powershell -File ".github\skills\build-and-release\scripts\windows\lint.ps1"
```

**Linux (bash):**

```bash
make lint
```

`make lint` is just an alias for `make ruff` in this project's Makefile; either works:

```bash
make ruff
```

---

## 9. "clean the build artifacts" / "full clean"

**Windows (PowerShell):**

```powershell
powershell -File ".github\skills\build-and-release\scripts\windows\clean.ps1"
```

Options:

- `-Full` — also removes `.venv`, `.venv-dev`, and `dist` (equivalent to `make distclean`).

```powershell
powershell -File ".github\skills\build-and-release\scripts\windows\clean.ps1" -Full
```

**Linux (bash):**

```bash
make clean
```

For a full wipe including virtual environments and `dist/`:

```bash
make distclean
```

---

## Notes

- If `pwsh` isn't available on your Windows machine, substitute `powershell` for `pwsh` in the examples above.
- All Windows scripts set `$LASTEXITCODE`: `0` = success, `1` = the step genuinely failed, `2` = blocked pending a
  decision from you (wrong branch, dirty tree, bad/duplicate version, etc.) — check it after each run, e.g.
  `if ($LASTEXITCODE -ne 0) { ... }`.
- On Linux, check `$?` after each `make` target the same way.
- The PyPI publish token (`UV_PUBLISH_TOKEN`) is never stored by these scripts/targets — set it as an environment
  variable in your own shell session, or you'll be prompted for it interactively. Never commit it anywhere.
