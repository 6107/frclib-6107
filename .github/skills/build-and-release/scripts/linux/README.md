# Linux automation (not yet implemented)

This folder is a placeholder for the Linux/macOS side of the `build-and-release` skill.

The Windows automation lives in `../windows/*.ps1` and mirrors (and, in a couple of spots, slightly improves on) the
release-related targets in this project's `Makefile`
(`test`, `bandit-test`, `ruff`/`lint`, `release-check`, `release-build`, `publish-dry-run`,
`publish`).

On Linux, `make` and `bash` are natively available, so the equivalent scripts here should either:

- shell out directly to the existing `Makefile` targets (simplest, keeps a single source of truth), adding the same
  guardrails documented in `../../SKILL.md` (branch check, git-clean check, version-format check, PyPI duplicate-version
  check, no stored secrets), or
- reimplement the same logic as small POSIX-shell scripts (`common.sh`, `test.sh`, `bandit.sh`,
  `lint.sh`, `release-check.sh`, `release-build.sh`, `publish-dry-run.sh`, `publish.sh`) for parity with the Windows
  scripts if shelling out to `make` proves awkward for guardrail enforcement (e.g. exit-code conventions for "blocked,
  needs user input" vs. "failed").

This will be fleshed out once the skill is imported into a Linux environment.
