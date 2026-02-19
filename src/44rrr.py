# 1. Define Paths
$root = Get-Location
$stagingDir = Join-Path $root "temp_package"
$sourceDir = Join-Path $root "sira-integration" # This is your code folder
$zipName = "lambda_deploy.zip"

Write-Host "--- Starting Lambda Package Build ---" -ForegroundColor Cyan

# 2. Check if temp_package exists (dependencies should already be there from your pip command)
if (-not (Test-Path $stagingDir)) {
    Write-Error "temp_package not found! Run the poetry/pip install command first."
    exit
}

# 3. Copy your project code INTO the temp_package folder
Write-Host "Merging source code into dependency folder..." -ForegroundColor Yellow
# We copy the *contents* of sira-integration/sira-integration so the package
# starts with 'config', 'core', etc. at the root.
Copy-Item -Path "$sourceDir\*" -Destination $stagingDir -Recurse -Force

# 4. Clean up unnecessary junk to save space
Write-Host "Cleaning up __pycache__ and dist info..." -ForegroundColor Gray
Get-ChildItem -Path $stagingDir -Include "__pycache__", "*.dist-info", "*.egg-info" -Recurse | Remove-Item -Recurse -Force

# 5. Create the ZIP file
Write-Host "Zipping contents..." -ForegroundColor Green
if (Test-Path $zipName) { Remove-Item $zipName }

# IMPORTANT: We zip the contents of the folder, not the folder itself
Set-Location $stagingDir
Compress-Archive -Path * -DestinationPath "..\\$zipName" -Force
Set-Location $root

Write-Host "--- Success! $zipName created ---" -ForegroundColor Cyan
Write-Host "Your Lambda Handler setting should be: sira-integration/config/function.lambda_handler" -ForegroundColor Magenta