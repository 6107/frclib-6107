# CI / Code Quality GitHub Actions Setup

This document summarizes the work done to add Continuous Integration (CI) and code-quality automation
via GitHub Actions, and lists the steps needed to get these changes committed and active on GitHub.

## What was added

### 1. `.github/workflows/ci.yml` — Test workflow

- Triggers: push to `main`, all pull requests, manual `workflow_dispatch`.
- Matrix: `ubuntu-latest` and `windows-latest`.
- Steps: `actions/checkout` → `astral-sh/setup-uv` (Python 3.14, dependency cache enabled) → `uv sync --locked`
  → `uv run python -m pytest`.
- Uses `uv run python -m pytest` instead of `uv run pytest` to avoid a known `uv` trampoline/shim bug
  observed on Windows (`uv trampoline failed to canonicalize script path`).
- A `concurrency` group cancels superseded runs on the same branch/PR.

### 2. `.pre-commit-config.yaml` — Code quality hook definitions (new file)

- `astral-sh/ruff-pre-commit` (`v0.17.3`): `ruff-check --fix` + `ruff-format`, reusing the existing
  `[tool.ruff]` configuration in `pyproject.toml`.
- `pre-commit/pre-commit-hooks` (`v6.0.0`): `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`,
  `check-added-large-files`, `check-merge-conflict`, `mixed-line-ending`.
- Top-level `exclude` regex skips virtualenvs, build/cache output, and `uv.lock`.

### 3. `.github/workflows/code-quality.yml` — Code quality workflow

- Same triggers as `ci.yml`.
- Steps: `actions/checkout` → `actions/setup-python` → `pre-commit/action`, which runs every hook defined
  in `.pre-commit-config.yaml` against all files.
- Pre-commit is the single source of truth for `ruff` here — there is intentionally no separate/duplicate
  `ruff-action` step.

### 4. Supporting changes

- `pyproject.toml` / `uv.lock`: added `pre-commit >= 4.0.1` to the `dev` dependency group so contributors
  can run the same hooks locally via `uv run pre-commit ...`.
- `README.md`: added CI and Code Quality status badges under the title.
- `AGENTS.md`: added a "Continuous Integration" section describing the two workflows and how to install
  the git hook locally (`uv run pre-commit install`).

## Findings / design decisions

- **`Makefile` gotcha**: `Makefile` does `include .make/pypi-token.mk` (not `-include`), and that file is
  gitignored (`.make/pypi-*.mk`). It will not exist on a fresh CI checkout, so any `make <target>` call
  would fail in CI. To avoid depending on this local-only file, both workflows invoke `uv`, `pytest`, and
  `pre-commit` directly rather than through `make test` / `make lint`.
- **Validation caveat**: Running `pre-commit run --all-files` for the first time against the existing
  codebase reformats a large number of pre-existing files (via `ruff-format` and the hygiene hooks), since
  the codebase hasn't been formatted to these rules before. During development of this change, that
  full-repo reformat was triggered locally for validation purposes and was **fully reverted** — only the
  files listed above were committed. If you want the codebase brought into compliance with
  `.pre-commit-config.yaml`, that should be a deliberate, reviewed follow-up commit, not a side effect of
  CI setup.
- Explicitly **out of scope** for this change (planned for a future request): dependency/package
  management automation (e.g., Dependabot/Renovate), PyPI publishing automation, and security scanning
  (bandit/pip-audit) in CI.

## Files changed in this request

| Path                                 | Change                                          |
|--------------------------------------|-------------------------------------------------|
| `.github/workflows/ci.yml`           | **New** — test workflow                         |
| `.github/workflows/code-quality.yml` | **New** — pre-commit workflow                   |
| `.pre-commit-config.yaml`            | **New** — pre-commit hook definitions           |
| `pyproject.toml`                     | Modified — added `pre-commit` dev dependency    |
| `uv.lock`                            | Modified — relocked for the new dependency      |
| `README.md`                          | Modified — added CI/Code Quality badges         |
| `AGENTS.md`                          | Modified — added Continuous Integration section |
| `docs/CI-SETUP.md`                   | **New** — this document                         |

## Steps to install / activate on GitHub

These changes only take effect once they are committed and pushed to the repository that GitHub Actions
watches (`6107/frclib-6107`).

1. **Stage the new and modified files** (the two new workflow files and `.pre-commit-config.yaml` are
   currently untracked and must be explicitly added):

   ```bash
   git add .github/workflows/ci.yml \
           .github/workflows/code-quality.yml \
           .pre-commit-config.yaml \
           pyproject.toml \
           uv.lock \
           README.md \
           AGENTS.md \
           docs/CI-SETUP.md
   ```

   Or simply `git add -A` if there are no other unrelated pending changes in your working tree at the
   time — check `git status` first.

2. **Commit**:

   ```bash
   git commit -m "Add CI and code-quality GitHub Actions workflows"
   ```

3. **Push to GitHub** (on `main`, or via a feature branch + pull request if you prefer review before the
   workflows go live):

   ```bash
   git push origin main
   ```

   If using a feature branch instead, open a pull request — the `code-quality.yml` and `ci.yml` workflows
   will run automatically on the PR once pushed, since both are configured to trigger on `pull_request`.

4. **No GitHub repository settings changes are required** to enable these workflows — Actions are enabled
   by default for repositories once a workflow file exists under `.github/workflows/` on the default
   branch (or within a PR for `pull_request`-triggered runs). Just confirm under **Settings → Actions → General** that
   "Actions permissions" isn't restricted to disallow workflows.

5. **Optional, recommended local setup** for contributors (not required for CI to function, but keeps
   local commits consistent with what CI checks):

   ```bash
   uv sync                      # picks up the new `pre-commit` dev dependency
   uv run pre-commit install    # installs the git pre-commit hook
   ```

6. **First-time repo-wide formatting (optional, separate follow-up)**: if/when you want the existing
   codebase to pass `pre-commit run --all-files` cleanly, run it locally, review the diff carefully, and
   commit it as its own dedicated change — do not bundle it with this CI setup commit.

After pushing, verify the workflows ran successfully under the repository's **Actions** tab, and confirm
the new README badges render (they may show "no status" until the first run completes on `main`).
