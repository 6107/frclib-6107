# ------------------------------------------------------------------------ #
#  test.ps1 - run the unit test suite (equivalent to `make test`).
#
#  NOTE: `make test` runs pytest through tox-uv. On this Windows environment
#  tox's `PYTHONPATH = ./src :./tests` (colon-separated) setting does not
#  translate correctly, so this script runs pytest directly via `uv run`,
#  which honors [tool.pytest.ini_options] (testpaths/pythonpath) already
#  declared in pyproject.toml. Behavior/coverage is equivalent; only the
#  runner differs.
# ------------------------------------------------------------------------ #
[CmdletBinding()]
param()

. "$PSScriptRoot\common.ps1"
$root = Get-RepoRoot
Push-Location $root
try {
    Write-Host "==> Running unit tests (uv run pytest)" -ForegroundColor Cyan
    uv run pytest
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
