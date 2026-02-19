#Requires -Version 5.1
<#
.SYNOPSIS
    Builds AWS Lambda deployment package for sira-integration.
.DESCRIPTION
    Exports Poetry dependencies, installs manylinux-compatible wheels,
    and copies the sira-integration source tree into ./lambda_deploy.
.NOTES
    Run from the project root (where pyproject.toml lives).
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ─── Configuration ────────────────────────────────────────────────────────────
$SourceDir      = Join-Path $PSScriptRoot 'sira-integration'
$DeployDir      = Join-Path $PSScriptRoot 'lambda_deploy'
$RequirementsFile = Join-Path $PSScriptRoot 'requirements.txt'
$PythonVersion  = '3.12'
$AbiTag         = 'cp312'
$Platform       = 'manylinux2014_x86_64'

# ─── Helpers ──────────────────────────────────────────────────────────────────
function Write-Step {
    param([string]$Message)
    Write-Host "`n[ $(Get-Date -Format 'HH:mm:ss') ] $Message" -ForegroundColor Cyan
}

function Invoke-Command-Safe {
    param([string]$Description, [scriptblock]$Command)
    Write-Step $Description
    & $Command
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: '$Description' failed with exit code $LASTEXITCODE." -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

# ─── Preflight checks ─────────────────────────────────────────────────────────
Write-Step 'Checking prerequisites...'

foreach ($tool in @('poetry', 'pip')) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        Write-Host "ERROR: '$tool' is not on PATH." -ForegroundColor Red
        exit 1
    }
}

if (-not (Test-Path $SourceDir)) {
    Write-Host "ERROR: Source directory not found: $SourceDir" -ForegroundColor Red
    exit 1
}

# ─── Step 1 – Clean previous build ───────────────────────────────────────────
Write-Step 'Cleaning previous lambda_deploy...'
if (Test-Path $DeployDir) {
    Remove-Item -Recurse -Force $DeployDir
}
New-Item -ItemType Directory -Path $DeployDir | Out-Null

# ─── Step 2 – Export requirements.txt ────────────────────────────────────────
Invoke-Command-Safe 'Exporting dependencies via Poetry' {
    poetry export -f requirements.txt --output $RequirementsFile --without-hashes
}

# ─── Step 3 – Install manylinux-compatible wheels ────────────────────────────
Invoke-Command-Safe 'Installing manylinux wheels into lambda_deploy' {
    pip install `
        --platform        $Platform `
        --implementation  cp `
        --python-version  $PythonVersion `
        --abi             $AbiTag `
        --only-binary     :all: `
        --target          $DeployDir `
        --upgrade `
        -r $RequirementsFile
}

# ─── Step 4 – Copy sira-integration source tree ───────────────────────────────
Write-Step "Copying source tree: $SourceDir → $DeployDir"

# Recursively copy every .py file and every sub-directory that contains .py files.
# This preserves the exact package layout Lambda needs.
Get-ChildItem -Path $SourceDir -Recurse | ForEach-Object {
    $relativePath = $_.FullName.Substring($SourceDir.Length).TrimStart('\', '/')
    $destination  = Join-Path $DeployDir $relativePath   # flatten into deploy root

    if ($_.PSIsContainer) {
        # Recreate directory structure
        if (-not (Test-Path $destination)) {
            New-Item -ItemType Directory -Path $destination | Out-Null
        }
    } else {
        # Copy all files (py, json, yaml, txt, etc.) – Lambda may need non-.py assets
        $destDir = Split-Path $destination -Parent
        if (-not (Test-Path $destDir)) {
            New-Item -ItemType Directory -Path $destDir | Out-Null
        }
        Copy-Item -Path $_.FullName -Destination $destination -Force
    }
}

# ─── Step 5 – Verify entry point exists ──────────────────────────────────────
Write-Step 'Verifying entry point...'
$entryPoint = Join-Path $DeployDir 'function.py'
if (-not (Test-Path $entryPoint)) {
    Write-Host "WARNING: function.py not found in lambda_deploy root." -ForegroundColor Yellow
    Write-Host "         Ensure your handler path in Lambda config is correct." -ForegroundColor Yellow
} else {
    Write-Host "  Entry point OK: $entryPoint" -ForegroundColor Green
}

# ─── Step 6 – Summary ─────────────────────────────────────────────────────────
Write-Step 'Build complete.'
$itemCount = (Get-ChildItem -Recurse -File $DeployDir).Count
$sizeMB    = [math]::Round((
    Get-ChildItem -Recurse -File $DeployDir |
    Measure-Object -Property Length -Sum
).Sum / 1MB, 2)

Write-Host "  Output  : $DeployDir"                    -ForegroundColor Green
Write-Host "  Files   : $itemCount"                    -ForegroundColor Green
Write-Host "  Size    : $sizeMB MB"                    -ForegroundColor Green

if ($sizeMB -gt 250) {
    Write-Host "  WARNING : Package exceeds 250 MB Lambda unzipped limit!" -ForegroundColor Yellow
}

# Optional – zip for direct upload (uncomment if needed)
# Write-Step 'Creating lambda_deploy.zip...'
# $zipPath = Join-Path $PSScriptRoot 'lambda_deploy.zip'
# if (Test-Path $zipPath) { Remove-Item $zipPath }
# Compress-Archive -Path "$DeployDir\*" -DestinationPath $zipPath
# Write-Host "  Zip     : $zipPath" -ForegroundColor Green