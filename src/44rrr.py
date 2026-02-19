# --- PATH CONFIGURATION ---
$root = Get-Location
$stagingDir = Join-Path $root "temp_package"
# Points to where your 'config', 'core', 'models', and 'function.py' live
$sourceDir = Join-Path $root "sira-integration" 
$zipName = "lambda_deploy.zip"

Write-Host "🚀 Starting Production Build for AWS Lambda (Python 3.12)..." -ForegroundColor Cyan

# 1. Clean previous build data
if (Test-Path $stagingDir) { Remove-Item -Recurse -Force $stagingDir }
if (Test-Path $zipName) { Remove-Item $zipName }
New-Item -ItemType Directory -Path $stagingDir | Out-Null

# 2. Export Poetry dependencies
Write-Host "📦 Exporting Poetry lock file..." -ForegroundColor Yellow
poetry export -f requirements.txt --output requirements.txt --without-hashes

# 3. Download Linux-compatible binaries
Write-Host "🐧 Downloading Linux-compatible wheels (manylinux)..." -ForegroundColor Yellow
poetry run pip install `
    --platform manylinux2014_x86_64 `
    --implementation cp `
    --python-version 3.12 `
    --abi cp312 `
    --only-binary=:all: `
    --target $stagingDir `
    --upgrade `
    -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Error "Pip failed. Check your network or if a dependency lacks a Wheel."
    exit $LASTEXITCODE
}

# 4. Copy your project code into the staging folder
Write-Host "📂 Merging project source code..." -ForegroundColor Yellow
if (Test-Path $sourceDir) {
    Copy-Item -Path "$sourceDir\*" -Destination $stagingDir -Recurse -Force
} else {
    Write-Error "Source directory not found at $sourceDir!"
    exit 1
}

# 5. FIX: Ensure all subdirectories have __init__.py for imports
Write-Host "🛠️ Ensuring __init__.py files exist..." -ForegroundColor Yellow
Get-ChildItem -Path $stagingDir -Directory -Recurse | ForEach-Object {
    $initFile = Join-Path $_.FullName "__init__.py"
    if (-not (Test-Path $initFile)) {
        New-Item -Path $initFile -ItemType "file" | Out-Null
        Write-Host "   Created: $($_.Name)/__init__.py" -ForegroundColor Gray
    }
}

# 6. Cleanup cache files and requirements
Write-Host "🧹 Cleaning up junk files..." -ForegroundColor Gray
Get-ChildItem -Path $stagingDir -Include "__pycache__", "*.pyc", "*.dist-info" -Recurse | Remove-Item -Recurse -Force
if (Test-Path "requirements.txt") { Remove-Item "requirements.txt" }

# 7. Create the final ZIP
Write-Host "🤐 Zipping contents..." -ForegroundColor Green
Set-Location $stagingDir
Compress-Archive -Path * -DestinationPath "..\\$zipName" -Force
Set-Location $root

Write-Host "`n✅ SUCCESS! $zipName is ready." -ForegroundColor Green
Write-Host "------------------------------------------------"
Write-Host "AWS HANDLER SETTING: function.lambda_handler" -ForegroundColor Magenta
Write-Host "------------------------------------------------"