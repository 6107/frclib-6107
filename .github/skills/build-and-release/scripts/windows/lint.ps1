# ------------------------------------------------------------------------ #
#  lint.ps1 - run ruff lint checks (equivalent to `make ruff` / the "lint"
#             step of this project's release process). This project uses
#             ruff for linting, not pylint.
# ------------------------------------------------------------------------ #
[CmdletBinding()]
param()

. "$PSScriptRoot\common.ps1"
$root = Get-RepoRoot
Push-Location $root
try {
    Write-Host "==> Running ruff lint checks" -ForegroundColor Cyan
    uv run ruff check "src\lib_6107" | Tee-Object -FilePath "ruff.out"
    $code = $LASTEXITCODE
    Write-Host "See `"$(Join-Path $root 'ruff.out')`" for the full report"
    exit $code
} finally {
    Pop-Location
}
