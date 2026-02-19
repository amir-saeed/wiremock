# --- CONFIGURATION ---
$projectName = "sira-integration"
$sourceDir = Join-Path $root "sira-integration" # Folder containing config, core, etc.
$stagingDir = Join-Path $root "temp_package"
$zipName = "lambda_deploy.zip"

Write-Host "🚀 Starting Production Build for AWS Lambda (Python 3.12)..." -ForegroundColor Cyan

# 1. Clean up previous builds
if (Test-Path $stagingDir) { Remove-Item -Recurse -Force $stagingDir }
if (Test-Path $zipName) { Remove-Item $zipName }
New-Item -ItemType Directory -Path $stagingDir | Out-Null

# 2. Export Poetry dependencies to requirements.txt
Write-Host "📦 Exporting Poetry lock file..." -ForegroundColor Yellow
poetry export -f requirements.txt --output requirements.txt --without-hashes

# 3. Install Linux-compatible dependencies via Poetry's Pip
Write-Host "🐧 Fetching Linux-compatible wheels (manylinux)..." -ForegroundColor Yellow
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
    Write-Error "Pip failed to fetch Linux binaries. Check if a dependency lacks a Wheel."
    exit $LASTEXITCODE
}

# 4. Copy your project code into the staging area
Write-Host "📂 Merging project source code..." -ForegroundColor Yellow
# This copies everything inside sira-integration/sira-integration (config, core, etc.)
# directly into the root of the package.
Copy-Item -Path "$sourceDir\*" -Destination $stagingDir -Recurse -Force

# 5. Cleanup junk files to keep the ZIP small
Write-Host "🧹 Cleaning up cache files..." -ForegroundColor Gray
Get-ChildItem -Path $stagingDir -Include "__pycache__", "*.dist-info", "*.pyc" -Recurse | Remove-Item -Recurse -Force

# 6. Create the final ZIP
Write-Host "🤐 Creating $zipName..." -ForegroundColor Green
$currentDir = Get-Location
Set-Location $stagingDir
Compress-Archive -Path * -DestinationPath "..\\$zipName" -Force
Set-Location $currentDir

Write-Host "`n✅ SUCCESS!" -ForegroundColor Green
Write-Host "Upload: $zipName"
Write-Host "AWS Handler Setting: sira-integration.config.function.lambda_handler" -ForegroundColor Magenta