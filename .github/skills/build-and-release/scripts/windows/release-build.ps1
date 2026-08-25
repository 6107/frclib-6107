# ------------------------------------------------------------------------ #
#  release-build.ps1 - build sdist/wheel into dist/ (equivalent to
#  `make release-build`).
#
#  Guardrails:
#   - Refuses to build from a branch other than 'main' unless -AllowBranch
#     is passed (only pass this when the user explicitly asked for it).
#   - Verifies the pyproject.toml [project] version matches the project's
#     YYYY.MAJOR.MINOR.PATCH scheme (e.g. 2026.0.0.4).
#
#  Exit codes: 0 = success, 1 = build failed, 2 = blocked - needs a user decision.
# ------------------------------------------------------------------------ #
[CmdletBinding()]
param(
    [switch]$AllowBranch   # allow building from a branch other than 'main'
)

. "$PSScriptRoot\common.ps1"
$root = Get-RepoRoot
Push-Location $root
try {
    $branch = Get-CurrentBranch
    if ($branch -ne 'main' -and -not $AllowBranch) {
        Write-Host "ACTION REQUIRED: current branch is '$branch', not 'main'." -ForegroundColor Yellow
        Write-Host "Refusing to build a release from a non-main branch without explicit confirmation."
        exit 2
    }

    $pyprojectPath = Join-Path $root "pyproject.toml"
    $version = Get-ProjectVersion -PyprojectPath $pyprojectPath
    if (-not (Test-VersionFormat -Version $version)) {
        Write-Host "ACTION REQUIRED: version '$version' in pyproject.toml is not in the expected" -ForegroundColor Yellow
        Write-Host "YYYY.MAJOR.MINOR.PATCH format (e.g. 2026.0.0.4). Update it before building a release."
        exit 2
    }

    Write-Host "==> Building release $version from branch '$branch'" -ForegroundColor Cyan
    Remove-Item -Path "dist" -Recurse -Force -ErrorAction SilentlyContinue
    uv build --no-sources
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
