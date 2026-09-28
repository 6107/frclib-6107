# ------------------------------------------------------------------------ #
#  push-version-bump.ps1 - push the local commit + tag created by
#  `bump-version.ps1` (Commitizen) to origin.
#
#  This is a separate step (not folded into bump-version.ps1) because the
#  agent must pause between the bump and the push to let the programmer
#  review/edit CHANGELOG.md first. See "Version Bumping with Commitizen" in
#  SKILL.md for the full flow.
#
#  Guardrails:
#   - Verifies the expected tag (v<version>, per this project's
#     tag_format) exists locally before attempting to push anything.
#
#  Exit codes: 0 = success, 1 = push failed, 2 = blocked - tag not found.
# ------------------------------------------------------------------------ #
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Version
)

. "$PSScriptRoot\common.ps1"
$root = Get-RepoRoot
Push-Location $root
try {
    $tag = "v$Version"
    git rev-parse $tag *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ACTION REQUIRED: tag '$tag' was not found locally." -ForegroundColor Yellow
        Write-Host "Run bump-version.ps1 -Version $Version first."
        exit 2
    }

    Write-Host "==> Pushing current branch to origin" -ForegroundColor Cyan
    git push
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "==> Pushing tag $tag to origin" -ForegroundColor Cyan
    git push origin $tag
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
