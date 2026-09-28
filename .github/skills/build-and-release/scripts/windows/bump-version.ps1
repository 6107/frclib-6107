# ------------------------------------------------------------------------ #
#  bump-version.ps1 - bump the project version using Commitizen, with this
#  project's calendar-based YYYY.MAJOR.MINOR.PATCH scheme (e.g. 2026.0.0.6).
#
#  This project's installed Commitizen version (4.x) no longer supports the
#  older `--manual-version <version>` flag; the manual version is now passed
#  as a positional argument instead (`cz bump <version>`). This script uses
#  the positional form under the hood so the behavior described in this
#  skill's docs ("run cz bump with a manual version") still works.
#
#  Guardrails:
#   - Refuses to bump from a branch other than 'main' unless -AllowBranch is
#     passed (only pass this when the user explicitly asked for it).
#   - Refuses to bump if the git working tree has modified or untracked
#     files unless -AllowDirty is passed (Commitizen creates a commit + tag
#     for the bump, so the tree must be clean first).
#   - Verifies the requested -Version matches this project's
#     YYYY.MAJOR.MINOR.PATCH scheme (e.g. 2026.0.0.6).
#   - Refuses to "bump" to the exact version already recorded in
#     pyproject.toml (nothing to do / likely a mistake).
#
#  Exit codes: 0 = success, 1 = bump failed, 2 = blocked - needs a user decision.
# ------------------------------------------------------------------------ #
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Version,
    [switch]$AllowBranch,
    [switch]$AllowDirty
)

. "$PSScriptRoot\common.ps1"
$root = Get-RepoRoot
Push-Location $root
try {
    $branch = Get-CurrentBranch
    if ($branch -ne 'main' -and -not $AllowBranch) {
        Write-Host "ACTION REQUIRED: current branch is '$branch', not 'main'." -ForegroundColor Yellow
        Write-Host "Refusing to bump the version from a non-main branch without explicit confirmation."
        exit 2
    }

    if (-not (Test-GitClean) -and -not $AllowDirty) {
        Write-Host "ACTION REQUIRED: the working tree has modified or untracked files." -ForegroundColor Yellow
        Write-Host "Commitizen commits the version bump; commit or stash your changes first."
        git status --porcelain
        exit 2
    }

    if (-not (Test-VersionFormat -Version $Version)) {
        Write-Host "ACTION REQUIRED: requested version '$Version' is not in the expected" -ForegroundColor Yellow
        Write-Host "YYYY.MAJOR.MINOR.PATCH format (e.g. 2026.0.0.6)."
        exit 2
    }

    $pyprojectPath = Join-Path $root "pyproject.toml"
    $currentVersion = Get-ProjectVersion -PyprojectPath $pyprojectPath
    if ($Version -eq $currentVersion) {
        Write-Host "ACTION REQUIRED: requested version '$Version' is already the current version." -ForegroundColor Yellow
        Write-Host "Choose a new version to bump to."
        exit 2
    }

    Write-Host "==> Bumping version $currentVersion -> $Version (via Commitizen)" -ForegroundColor Cyan
    uv run cz bump $Version --yes --check-consistency
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
