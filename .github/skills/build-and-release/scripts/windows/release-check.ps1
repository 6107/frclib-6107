# ------------------------------------------------------------------------ #
#  release-check.ps1 - full pre-release verification, equivalent to
#  `make release-check`: clean -> test -> bandit -> lint (ruff).
#  Does NOT touch the git branch, build a distribution, or publish anything.
#
#  Exit codes: 0 = all steps passed, 1 = one or more steps failed.
# ------------------------------------------------------------------------ #
[CmdletBinding()]
param(
    [switch]$Full   # also wipe .venv/.venv-dev/dist first (equivalent to `make distclean`)
)

. "$PSScriptRoot\common.ps1"

$results = [ordered]@{}

& "$PSScriptRoot\clean.ps1" -Full:$Full
$results['clean'] = $LASTEXITCODE

& "$PSScriptRoot\test.ps1"
$results['test'] = $LASTEXITCODE

& "$PSScriptRoot\bandit.ps1"
$results['bandit'] = $LASTEXITCODE

& "$PSScriptRoot\lint.ps1"
$results['lint (ruff)'] = $LASTEXITCODE

Write-Host ""
Write-Host "==================== release-check summary ====================" -ForegroundColor Cyan
$failed = $false
foreach ($k in $results.Keys) {
    if ($results[$k] -eq 0) {
        Write-Host ("  {0,-12} PASS" -f $k) -ForegroundColor Green
    } else {
        $failed = $true
        Write-Host ("  {0,-12} FAIL (exit {1})" -f $k, $results[$k]) -ForegroundColor Red
    }
}
Write-Host "=================================================================" -ForegroundColor Cyan

if ($failed) { exit 1 } else { exit 0 }
