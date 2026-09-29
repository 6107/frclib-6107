# ------------------------------------------------------------------------ #
#  test.ps1 - run the unit test suite (equivalent to `make test`).
#
#  NOTE: `make test` runs pytest through tox-uv. On this Windows environment
#  tox's `PYTHONPATH = ./src :./tests` (colon-separated) setting does not
#  translate correctly, so this script runs pytest directly via `uv run`,
#  which honors [tool.pytest.ini_options] (testpaths/pythonpath) already
#  declared in pyproject.toml. Behavior/coverage is equivalent; only the
#  runner differs.
#
#  Code coverage (via pytest-cov, already a dev dependency) is ON by
#  default: a terminal summary (with missing line numbers) is always
#  printed, and an HTML report is written to htmlcov/index.html. Pass
#  -NoCoverage to skip coverage instrumentation entirely (e.g. for the
#  fastest possible local test loop).
# ------------------------------------------------------------------------ #
[CmdletBinding()]
param(
    [switch]$NoCoverage   # skip coverage instrumentation/reports
)

. "$PSScriptRoot\common.ps1"
$root = Get-RepoRoot
Push-Location $root
try {
    if ($NoCoverage) {
        Write-Host "==> Running unit tests (uv run pytest, coverage disabled)" -ForegroundColor Cyan
        uv run pytest
        exit $LASTEXITCODE
    }

    Write-Host "==> Running unit tests with coverage (uv run pytest --cov)" -ForegroundColor Cyan
    uv run pytest `
        --cov=lib_6107 `
        --cov-report=term-missing `
        --cov-report=html:htmlcov
    $code = $LASTEXITCODE
    Write-Host "See `"$(Join-Path $root 'htmlcov\index.html')`" for the full HTML coverage report"
    exit $code
} finally {
    Pop-Location
}
