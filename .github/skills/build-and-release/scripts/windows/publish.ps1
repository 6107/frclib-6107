# ------------------------------------------------------------------------ #
#  publish.ps1 - publish the built package to PyPI (equivalent to
#  `make publish`).
#
#  Guardrails:
#   - Refuses to run from a branch other than 'main' unless -AllowBranch is
#     passed (only pass this when the user explicitly asked for it).
#   - Refuses to run if the git working tree has modified or untracked files
#     unless -AllowDirty is passed (only pass this when the user explicitly
#     confirmed they want to proceed anyway).
#   - Verifies the pyproject.toml [project] version matches the project's
#     YYYY.MAJOR.MINOR.PATCH scheme (e.g. 2026.0.0.4).
#   - Verifies that exact version is not already published on PyPI; reports
#     the latest published version if it is.
#   - Never stores the PyPI token; see Get-PublishToken in common.ps1.
#
#  Exit codes: 0 = success, 1 = publish failed, 2 = blocked - needs a user decision.
# ------------------------------------------------------------------------ #
[CmdletBinding()]
param(
    [switch]$AllowBranch,
    [switch]$AllowDirty
)

. "$PSScriptRoot\common.ps1"
$root = Get-RepoRoot
$packageName = "lib_6107"
Push-Location $root
try {
    $branch = Get-CurrentBranch
    if ($branch -ne 'main' -and -not $AllowBranch) {
        Write-Host "ACTION REQUIRED: current branch is '$branch', not 'main'." -ForegroundColor Yellow
        exit 2
    }

    if (-not (Test-GitClean) -and -not $AllowDirty) {
        Write-Host "ACTION REQUIRED: the working tree has modified or untracked files." -ForegroundColor Yellow
        Write-Host "Commit or stash your changes before publishing."
        git status --porcelain
        exit 2
    }

    $pyprojectPath = Join-Path $root "pyproject.toml"
    $version = Get-ProjectVersion -PyprojectPath $pyprojectPath
    if (-not (Test-VersionFormat -Version $version)) {
        Write-Host "ACTION REQUIRED: version '$version' in pyproject.toml is not in the expected" -ForegroundColor Yellow
        Write-Host "YYYY.MAJOR.MINOR.PATCH format (e.g. 2026.0.0.4). Update it before publishing."
        exit 2
    }

    $info = Get-PyPiPackageInfo -PackageName $packageName
    if ($info) {
        $publishedVersions = $info.releases.PSObject.Properties.Name
        if ($publishedVersions -contains $version) {
            Write-Host "ACTION REQUIRED: version $version is already published on PyPI." -ForegroundColor Yellow
            Write-Host "Latest published version: $($info.info.version)"
            Write-Host "Update the [project] version in pyproject.toml before publishing."
            exit 2
        }
    }

    $token = Get-PublishToken

    Write-Host "==> Dry-run sanity check before publishing" -ForegroundColor Cyan
    uv publish --dry-run --token $token
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "==> Publishing $packageName $version to PyPI" -ForegroundColor Cyan
    uv publish --token $token
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "==> Verifying the published package can be imported" -ForegroundColor Cyan
    uv run --with $packageName --no-project -- python -c "import $packageName"
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
