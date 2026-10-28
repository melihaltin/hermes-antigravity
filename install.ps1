# Hermes Antigravity Windows Installer
$ErrorActionPreference = "Stop"

Write-Host "=== Installing Hermes Antigravity Plugin ===" -ForegroundColor Cyan

$pluginDir = "$env:USERPROFILE\.hermes\plugins\model-providers\antigravity"
New-Item -ItemType Directory -Force -Path $pluginDir | Out-Null

$baseUrl = "https://raw.githubusercontent.com/melihaltin/hermes-antigravity/main"
$files = @("plugin.yaml", "__init__.py", "adapter.py", "login.py")

foreach ($file in $files) {
    Write-Host "Downloading $file..."
    Invoke-WebRequest -Uri "$baseUrl/$file" -OutFile "$pluginDir\$file"
}

Write-Host "Plugin files downloaded to $pluginDir" -ForegroundColor Green

# Find Python in system or Hermes
$pythonExe = $null

# 1. Try PATH
$cmd = Get-Command python, py -ErrorAction SilentlyContinue | Select-Object -First 1
if ($cmd) {
    $pythonExe = $cmd.Source
}

# 2. Try Hermes bundled python
if (-not $pythonExe) {
    $found = Get-ChildItem -Path "$env:LOCALAPPDATA\hermes", "$env:USERPROFILE\.hermes" -Filter "python.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) {
        $pythonExe = $found.FullName
    }
}

if ($pythonExe) {
    Write-Host "Starting Google login with Python: $pythonExe" -ForegroundColor Cyan
    & $pythonExe "$pluginDir\login.py"
} else {
    Write-Host "`n[!] Python not automatically found in PATH." -ForegroundColor Yellow
    Write-Host "Please run the login script manually with your Python interpreter:" -ForegroundColor Yellow
    Write-Host "  python `"$pluginDir\login.py`"`n"
}

Write-Host "Enabling plugin in Hermes..." -ForegroundColor Cyan
try {
    hermes plugins enable antigravity
} catch {
    # Ignore if hermes command is not in current PATH yet
}

Write-Host "`nInstallation complete! You can now select the model in Hermes:" -ForegroundColor Green
Write-Host "  hermes model antigravity/gemini-3.8-flash" -ForegroundColor White
Write-Host "  hermes model antigravity/claude-sonnet-4-6`n" -ForegroundColor White
