[CmdletBinding()]
param(
    [ValidateSet("x64", "arm64")]
    [string]$Architecture = "x64",
    [string]$Version = "0.1.0",
    [string]$OutputRoot = "release-out/windows"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$ManifestPath = Join-Path $RepositoryRoot "next/Cargo.toml"
$TargetDirectory = Join-Path $RepositoryRoot "next/target/release"
$BinaryPath = Join-Path $TargetDirectory "onboard-next.exe"
$OutputDirectory = Join-Path $RepositoryRoot "$OutputRoot/$Architecture/onboard-next-preview-$Version"

Push-Location $RepositoryRoot
try {
    cargo test --manifest-path $ManifestPath --workspace --locked
    cargo build --manifest-path $ManifestPath --bin onboard-next --release --locked

    if (-not (Test-Path $BinaryPath)) {
        throw "Expected Windows binary was not created: $BinaryPath"
    }

    Remove-Item -Recurse -Force $OutputDirectory -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
    Copy-Item -Force $BinaryPath (Join-Path $OutputDirectory "onboard-next.exe")

    $Diagnostics = & (Join-Path $OutputDirectory "onboard-next.exe") diagnose ar_SA
    if ($LASTEXITCODE -ne 0 -or $Diagnostics -notmatch '"direction":"rtl"') {
        throw "Arabic RTL diagnostic failed for the Windows preview binary."
    }

    $Commit = (git rev-parse HEAD).Trim()
    $Provenance = [ordered]@{
        product = "onboard-next"
        channel = "preview"
        platform = "windows"
        architecture = $Architecture
        version = $Version
        commit = $Commit
        signed = $false
        input_source = "read-only-tsf-pending"
        notes = "Preview bridge build. Do not treat as a signed stable installer."
    } | ConvertTo-Json -Depth 3
    Set-Content -NoNewline -Encoding utf8 (Join-Path $OutputDirectory "provenance.json") $Provenance

    Get-ChildItem -File $OutputDirectory |
        Get-FileHash -Algorithm SHA256 |
        ForEach-Object { "{0}  {1}" -f $_.Hash.ToLowerInvariant(), $_.Path.Substring($OutputDirectory.Length + 1) } |
        Set-Content -NoNewline -Encoding ascii (Join-Path $OutputDirectory "SHA256SUMS")

    Write-Host "Windows preview directory created: $OutputDirectory"
}
finally {
    Pop-Location
}
