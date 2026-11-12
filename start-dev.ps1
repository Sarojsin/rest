# start-dev.ps1 — one command to bring up backend + web (+ mobile) for local dev.
# Run from the repo root:  .\start-dev.ps1
# Backend + web only:      .\start-dev.ps1 -SkipMobile

param(
    [switch]$SkipMobile
)

$ErrorActionPreference = "Stop"

$repoRoot   = "E:\rest"
$backendDir = "$repoRoot\backend"
$webDir     = "$repoRoot\apps\web"
$mobileDir  = "$repoRoot\apps\mobile"
$venvPython = "$backendDir\venv\Scripts\python.exe"

# ------------------------------------------------------------------ helpers
function Set-EnvValue {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Key,
        [Parameter(Mandatory = $true)][string]$Value
    )
    $pattern = "^\s*" + [regex]::Escape($Key) + "\s*="
    $found = $false
    $out = @()
    if (Test-Path $Path) {
        foreach ($line in (Get-Content -Path $Path)) {
            if ($line -match $pattern) {
                $out += "$Key=$Value"
                $found = $true
            } else {
                $out += $line
            }
        }
    }
    if (-not $found) { $out += "$Key=$Value" }
    Set-Content -Path $Path -Value $out -Encoding ascii
}

function Ensure-EnvValue {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Key,
        [Parameter(Mandatory = $true)][string]$Value
    )
    if (-not (Test-Path $Path)) { return }
    $pattern = "^\s*" + [regex]::Escape($Key) + "\s*="
    $line = Get-Content -Path $Path | Where-Object { $_ -match $pattern } | Select-Object -First 1
    if ($null -eq $line -or ($line -split "=", 2)[1].Trim() -eq "") {
        Set-EnvValue -Path $Path -Key $Key -Value $Value
    }
}

# ------------------------------------------------------------------ 1. IP
$wifiIp = Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "Wi-Fi" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -eq $wifiIp) {
    $wifiIp = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notmatch "^(127\.|169\.254\.)" } |
        Select-Object -First 1
}
if ($null -eq $wifiIp -or -not $wifiIp.IPAddress) {
    Write-Host "ERROR: Could not detect a local IP address. Set EXPO_PUBLIC_API_URL manually."
    exit 1
}
$ip = $wifiIp.IPAddress
Write-Host "Detected local IP: $ip"

# ------------------------------------------------------------------ 2. mobile .env
if (-not $SkipMobile) {
    $envContent = "EXPO_PUBLIC_API_URL=http://${ip}:8000"
    Set-Content -Path "$mobileDir\.env" -Value $envContent -Encoding ascii
    Write-Host "Wrote $mobileDir\.env -> $envContent"
}

# ------------------------------------------------------------------ 3. backend .env
# Every line is written as its own line; this script never concatenates keys.
$corsOrigins = "http://localhost:5173,http://127.0.0.1:5173,http://${ip}:5173,http://${ip}:8081"
$backendEnv = "$backendDir\.env"
if (-not (Test-Path $backendEnv)) {
    @"
APP_ENV=development
SECRET_KEY=dev-only-change-me-not-for-production
DATABASE_URL=sqlite:///./data/restaurant.db
ACCESS_TOKEN_MINUTES=480
CORS_ORIGINS=$corsOrigins
PLATFORM_COOKIE_SECURE=false
"@ | Set-Content -Path $backendEnv -Encoding ascii
    Write-Host "Created $backendEnv"
} else {
    Set-EnvValue -Path $backendEnv -Key "APP_ENV" -Value "development"
    Set-EnvValue -Path $backendEnv -Key "CORS_ORIGINS" -Value $corsOrigins
    # The admin console is served by the shared Vite server in dev (PA-ADR-003).
    Set-EnvValue -Path $backendEnv -Key "PLATFORM_ADMIN_ORIGIN" -Value "http://${ip}:5173"
    Set-EnvValue -Path $backendEnv -Key "PLATFORM_DEV_ADMIN_ORIGINS" -Value "http://localhost:5173,http://127.0.0.1:5173,http://${ip}:5173"
    Set-EnvValue -Path $backendEnv -Key "PLATFORM_TENANT_ORIGIN" -Value "http://${ip}:5173"
    Set-EnvValue -Path $backendEnv -Key "PLATFORM_API_ORIGIN" -Value "http://${ip}:8000"
    # Plain HTTP locally; production must set this true (startup enforces it).
    Set-EnvValue -Path $backendEnv -Key "PLATFORM_COOKIE_SECURE" -Value "false"
    # Stable dev-only secrets; never overwritten once set.
    Ensure-EnvValue -Path $backendEnv -Key "PLATFORM_SECRET_KEY" -Value "dev-platform-signing-key-not-for-production"
    Ensure-EnvValue -Path $backendEnv -Key "PLATFORM_MFA_KEY" -Value "dev-platform-mfa-key-not-for-production"
    Write-Host "Patched backend .env in $backendEnv"
}

# ------------------------------------------------------------------ 4. start backend
if (-not (Test-Path $venvPython)) {
    Write-Host "WARNING: backend venv not found at $backendDir\venv. Install deps first."
} else {
    $backendCmd = "cd '$backendDir'; & '$venvPython' -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd
    Write-Host "Started backend -> http://${ip}:8000  (new window)"
}

# ------------------------------------------------------------------ 5. start web (Vite)
if (Test-Path "$webDir\package.json") {
    $webCmd = "cd '$webDir'; npm run dev"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $webCmd
    Write-Host "Started web (Vite) -> http://${ip}:5173  (new window)"
    Write-Host "Admin console      -> http://${ip}:5173/admin"
} else {
    Write-Host "WARNING: web not found at $webDir"
}

# ------------------------------------------------------------------ 6. start Expo
if ($SkipMobile) {
    Write-Host ""
    Write-Host "Skipping Expo (-SkipMobile)."
    exit 0
}

Write-Host ""
Write-Host "Starting Expo (foreground). Press Ctrl+C to stop."
Set-Location $mobileDir
npx expo start --android --lan
