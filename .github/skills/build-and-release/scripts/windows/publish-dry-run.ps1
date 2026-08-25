# ------------------------------------------------------------------------ #
#  publish-dry-run.ps1 - dry-run publish to PyPI (equivalent to
#  `make publish-dry-run`). Performs no real upload.
#
#  Guardrails:
#   - Refuses to run from a branch other than 'main' unless -AllowBranch is
#     passed (only pass this when the user explicitly asked for it).
#   - Refuses to run if the git working tree has modified or untracked files
#     unless -AllowDirty is passed (only pass this when the user explicitly
#     confirmed they want to proceed anyway).
#   - Never stores the PyPI token; see Get-PublishToken in common.ps1.
#
#  Exit codes: 0 = success, 1 = dry-run failed, 2 = blocked - needs a user decision.
# ------------------------------------------------------------------------ #
[CmdletBinding()]
param(
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
        exit 2
    }

    if (-not (Test-GitClean) -and -not $AllowDirty) {
        Write-Host "ACTION REQUIRED: the working tree has modified or untracked files." -ForegroundColor Yellow
        Write-Host "Commit or stash your changes before publishing (even for a dry run)."
        git status --porcelain
        exit 2
    }

    $token = Get-PublishToken

    Write-Host "==> Dry-run publishing to the PyPI test index" -ForegroundColor Cyan
    uv publish --dry-run --token $token --publish-url https://test.pypi.org/legacy/
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "==> Dry-run publishing to PyPI" -ForegroundColor Cyan
    uv publish --dry-run --token $token
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
