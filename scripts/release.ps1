# PowerShell script for easy release management
param(
    [Parameter(Mandatory=$true)]
    [string]$Version,
    
    [switch]$PreRelease,
    
    [switch]$Help
)

if ($Help) {
    Write-Host "Usage: .\scripts\release.ps1 -Version <version> [-PreRelease]"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\scripts\release.ps1 -Version 0.1.1"
    Write-Host "  .\scripts\release.ps1 -Version 0.2.0-beta.1 -PreRelease"
    Write-Host ""
    Write-Host "This script will:"
    Write-Host "  1. Update VERSION file"
    Write-Host "  2. Update manifest.json"
    Write-Host "  3. Update CHANGELOG.md"
    Write-Host "  4. Commit and push changes"
    Write-Host "  5. Create and push git tag"
    Write-Host "  6. Show GitHub CLI command for creating release"
    exit 0
}

Write-Host "🚀 Starting release process for version: $Version" -ForegroundColor Green

if ($PreRelease) {
    Write-Host "🔶 This will be marked as a PRE-RELEASE" -ForegroundColor Yellow
}

# Check if we're in the right directory
if (-not (Test-Path "VERSION")) {
    Write-Host "❌ Error: VERSION file not found. Make sure you're in the project root." -ForegroundColor Red
    exit 1
}

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Error: Python not found. Please install Python to use this script." -ForegroundColor Red
    exit 1
}

# Run the Python release script
$pythonArgs = @("scripts/release.py", $Version)
if ($PreRelease) {
    $pythonArgs += "--pre-release"
}

try {
    & python $pythonArgs
    Write-Host ""
    Write-Host "🎉 Release process completed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Check the GitHub repository for the new tag"
    Write-Host "2. Create a GitHub release using the command shown above"
    Write-Host "3. Test the release in HACS"
} catch {
    Write-Host "❌ Error during release process: $_" -ForegroundColor Red
    exit 1
}
