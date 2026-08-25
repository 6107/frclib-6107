# ------------------------------------------------------------------------ #
#  bandit.ps1 - run the bandit security scan (equivalent to `make bandit`).
# ------------------------------------------------------------------------ #
[CmdletBinding()]
param()

. "$PSScriptRoot\common.ps1"
$root = Get-RepoRoot
Push-Location $root
try {
    Write-Host "==> Running bandit security scan" -ForegroundColor Cyan
    uv run bandit -n 3 -r "src\lib_6107" -o bandit.log
    $code = $LASTEXITCODE
    Write-Host "See `"$(Join-Path $root 'bandit.log')`" for the full report"
    exit $code
} finally {
    Pop-Location
}
