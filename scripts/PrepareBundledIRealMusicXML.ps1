# Stages the bundled ireal-musicxml converter (and optionally a portable
# Node.js runtime) into tools\bundled\ for the desktop build.
#
# The payloads are not committed to the repo; this script fetches a pinned
# version so the staging is reproducible. The npm registry tarball already
# contains the prebuilt self-contained build\ireal-musicxml.mjs, so no
# npm install / npm run build is needed.
#
# Usage:
#   .\scripts\PrepareBundledIRealMusicXML.ps1                  # ireal-musicxml only
#   .\scripts\PrepareBundledIRealMusicXML.ps1 -IncludeNode     # + portable node.exe
#   .\scripts\PrepareBundledIRealMusicXML.ps1 -FromLocalCheckout ..\External\ireal-musicxml-main

param(
    [string]$IRealMusicXMLVersion = "2.1.1",
    [string]$NodeVersion = "22.14.0",
    [switch]$IncludeNode,
    [string]$FromLocalCheckout = ""
)

$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\.."

$irealDir = "tools\bundled\ireal-musicxml"
$nodeDir = "tools\bundled\node"

# ── ireal-musicxml ────────────────────────────────────────────────────────────

New-Item -ItemType Directory -Force (Join-Path $irealDir "build") | Out-Null

if ($FromLocalCheckout) {
    Write-Host "Staging ireal-musicxml from local checkout: $FromLocalCheckout"
    if (-not (Test-Path (Join-Path $FromLocalCheckout "build\ireal-musicxml.mjs"))) {
        Write-Error "build\ireal-musicxml.mjs not found in $FromLocalCheckout (run 'npm run build' there first)"
        exit 1
    }
    Copy-Item (Join-Path $FromLocalCheckout "build\ireal-musicxml.mjs") (Join-Path $irealDir "build\") -Force
    Copy-Item (Join-Path $FromLocalCheckout "LICENSE.txt") $irealDir -Force
    Copy-Item (Join-Path $FromLocalCheckout "package.json") $irealDir -Force
} else {
    $tarballUrl = "https://registry.npmjs.org/@music-i18n/ireal-musicxml/-/ireal-musicxml-$IRealMusicXMLVersion.tgz"
    $workDir = Join-Path $env:TEMP "eub-ireal-musicxml-$IRealMusicXMLVersion"
    $tarball = Join-Path $env:TEMP "ireal-musicxml-$IRealMusicXMLVersion.tgz"

    Write-Host "Downloading $tarballUrl"
    Invoke-WebRequest -Uri $tarballUrl -OutFile $tarball -UseBasicParsing

    if (Test-Path $workDir) { Remove-Item -Recurse -Force $workDir }
    New-Item -ItemType Directory -Force $workDir | Out-Null
    tar -xzf $tarball -C $workDir
    if ($LASTEXITCODE -ne 0) { Write-Error "tar extraction failed"; exit 1 }

    $pkg = Join-Path $workDir "package"
    Copy-Item (Join-Path $pkg "build\ireal-musicxml.mjs") (Join-Path $irealDir "build\") -Force
    Copy-Item (Join-Path $pkg "LICENSE.txt") $irealDir -Force
    Copy-Item (Join-Path $pkg "package.json") $irealDir -Force

    Remove-Item -Recurse -Force $workDir
    Remove-Item -Force $tarball
}

if (-not (Test-Path (Join-Path $irealDir "build\ireal-musicxml.mjs"))) {
    Write-Error "Staging failed: $irealDir\build\ireal-musicxml.mjs is missing"
    exit 1
}
Write-Host "OK: ireal-musicxml $IRealMusicXMLVersion staged in $irealDir"

# ── Node.js portable runtime (optional) ───────────────────────────────────────

if ($IncludeNode) {
    $nodeZipName = "node-v$NodeVersion-win-x64"
    $nodeUrl = "https://nodejs.org/dist/v$NodeVersion/$nodeZipName.zip"
    $nodeZip = Join-Path $env:TEMP "$nodeZipName.zip"
    $nodeWork = Join-Path $env:TEMP "eub-node-$NodeVersion"

    New-Item -ItemType Directory -Force $nodeDir | Out-Null

    Write-Host "Downloading $nodeUrl"
    Invoke-WebRequest -Uri $nodeUrl -OutFile $nodeZip -UseBasicParsing

    if (Test-Path $nodeWork) { Remove-Item -Recurse -Force $nodeWork }
    Expand-Archive -Path $nodeZip -DestinationPath $nodeWork -Force

    Copy-Item (Join-Path $nodeWork "$nodeZipName\node.exe") $nodeDir -Force
    Copy-Item (Join-Path $nodeWork "$nodeZipName\LICENSE") $nodeDir -Force

    Remove-Item -Recurse -Force $nodeWork
    Remove-Item -Force $nodeZip

    if (-not (Test-Path (Join-Path $nodeDir "node.exe"))) {
        Write-Error "Staging failed: $nodeDir\node.exe is missing"
        exit 1
    }
    Write-Host "OK: Node.js $NodeVersion (node.exe) staged in $nodeDir"
} else {
    Write-Host "Skipped Node.js staging (use -IncludeNode for the desktop build)"
}
