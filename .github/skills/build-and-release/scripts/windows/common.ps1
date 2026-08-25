# ------------------------------------------------------------------------ #
#  Shared helper functions for the build-and-release skill (Windows).
#  Dot-source this file from other scripts: . "$PSScriptRoot\common.ps1"
# ------------------------------------------------------------------------ #

function Get-RepoRoot {
    <#
    .SYNOPSIS
        Returns the absolute path to the repository root (Windows-style path).
    #>
    $root = git rev-parse --show-toplevel 2>$null
    if (-not $root) {
        throw "Not inside a git repository."
    }
    return ($root -replace '/', '\')
}

function Get-ProjectVersion {
    <#
    .SYNOPSIS
        Reads the [project] version field out of pyproject.toml.
    #>
    param([Parameter(Mandatory)][string]$PyprojectPath)

    if (-not (Test-Path $PyprojectPath)) {
        throw "pyproject.toml not found at $PyprojectPath"
    }
    $content = Get-Content -Path $PyprojectPath -Raw
    if ($content -match '(?m)^\s*version\s*=\s*"([^"]+)"') {
        return $Matches[1]
    }
    throw "Could not find a [project] version field in $PyprojectPath"
}

function Test-VersionFormat {
    <#
    .SYNOPSIS
        Validates the "YYYY.MAJOR.MINOR.PATCH" version scheme used by this project
        (e.g. 2026.0.0.4): a 4-digit season/target year followed by three numeric parts.
    #>
    param([Parameter(Mandatory)][string]$Version)
    return [bool]($Version -match '^\d{4}\.\d+\.\d+\.\d+$')
}

function Get-CurrentBranch {
    <#
    .SYNOPSIS
        Returns the current git branch name.
    #>
    return (git rev-parse --abbrev-ref HEAD).Trim()
}

function Test-GitClean {
    <#
    .SYNOPSIS
        Returns $true only when there are no modified, staged, or untracked files
        tracked/visible to git (i.e. `git status --porcelain` is empty).
    #>
    $status = git status --porcelain
    return [string]::IsNullOrWhiteSpace($status)
}

function Get-PublishToken {
    <#
    .SYNOPSIS
        Resolves the PyPI publish token without ever writing it to disk.
        Resolution order:
          1. $env:UV_PUBLISH_TOKEN, if already set.
          2. A local (gitignored) .make\pypi-token.mk, if present - read only, never copied.
          3. Interactive secure prompt (not echoed, not persisted beyond this process).
    #>
    if ($env:UV_PUBLISH_TOKEN) {
        return $env:UV_PUBLISH_TOKEN
    }

    $tokenFile = Join-Path (Get-RepoRoot) ".make\pypi-token.mk"
    if (Test-Path $tokenFile) {
        $content = Get-Content $tokenFile -Raw
        if ($content -match 'UV_PUBLISH_TOKEN\s*:?=\s*(\S+)') {
            $env:UV_PUBLISH_TOKEN = $Matches[1]
            return $Matches[1]
        }
    }

    $secure = Read-Host -Prompt "Enter your PyPI publish token (UV_PUBLISH_TOKEN)" -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        $plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
    if ([string]::IsNullOrWhiteSpace($plain)) {
        throw "No PyPI publish token supplied."
    }
    $env:UV_PUBLISH_TOKEN = $plain
    return $plain
}

function Get-PyPiPackageInfo {
    <#
    .SYNOPSIS
        Fetches the public PyPI JSON metadata for a package. Returns $null if the
        package has never been published (HTTP 404).
    #>
    param([Parameter(Mandatory)][string]$PackageName)

    $normalized = $PackageName -replace '_', '-'
    $uri = "https://pypi.org/pypi/$normalized/json"
    try {
        return Invoke-RestMethod -Uri $uri -TimeoutSec 20
    } catch {
        $response = $_.Exception.Response
        if ($response -and [int]$response.StatusCode -eq 404) {
            return $null
        }
        throw
    }
}
