# ------------------------------------------------------------------------ #
#  clean.ps1 - remove build/test/lint artifacts (equivalent to `make clean` /
#              `make distclean` when -Full is used).
# ------------------------------------------------------------------------ #
[CmdletBinding()]
param(
    [switch]$Full   # also remove .venv/.venv-dev/dist (equivalent to `make distclean`)
)

. "$PSScriptRoot\common.ps1"
$root = Get-RepoRoot
Push-Location $root
try {
    Write-Host "==> Cleaning build/test/lint artifacts" -ForegroundColor Cyan

    $filesToRemove = @(
        "pylint.out", "ruff.out", "license-check.out", "bandit.log"
    )
    foreach ($f in $filesToRemove) {
        Remove-Item -Path $f -Force -ErrorAction SilentlyContinue
    }

    $dirsToRemove = @(
        ".tox", "tests\.pytest_cache", "src\lib_6107\ctre_sim", "src\lib_6107\logs"
    )
    foreach ($d in $dirsToRemove) {
        Remove-Item -Path $d -Recurse -Force -ErrorAction SilentlyContinue
    }

    Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Path . -Recurse -Directory -Filter "*.egg-info" -ErrorAction SilentlyContinue |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Path . -Recurse -Directory -Filter "htmlcov" -ErrorAction SilentlyContinue |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Path . -Recurse -File -Include "*.pyc", "*.log", "*.wpilog", "junit-report.xml", "coverage.xml" -ErrorAction SilentlyContinue |
        Remove-Item -Force -ErrorAction SilentlyContinue

    if ($Full) {
        Write-Host "==> Removing virtual environments and dist/ (distclean)" -ForegroundColor Cyan
        Remove-Item -Path ".venv", ".venv-dev", "dist" -Recurse -Force -ErrorAction SilentlyContinue
    }

    exit 0
} finally {
    Pop-Location
}
