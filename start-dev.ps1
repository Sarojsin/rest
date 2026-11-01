# start-dev.ps1 — one command to bring up backend + web + mobile for local dev.
# Run from the repo root:  .\start-dev.ps1
# Mirrors the her_care workflow but adapted to the E:\rest layout.

$ErrorActionPreference = "Stop"

$repoRoot   = "E:\rest"
$backendDir = "$repoRoot\backend"
$webDir     = "$repoRoot\apps\web"
$mobileDir  = "$repoRoot\apps\mobile"
$venvPython = "$backendDir\venv\Scripts\python.exe"

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
$envContent = "EXPO_PUBLIC_API_URL=http://${ip}:8000"
Set-Content -Path "$mobileDir\.env" -Value $envContent -Encoding ascii
Write-Host "Wrote $mobileDir\.env -> $envContent"

# ------------------------------------------------------------------ 3. backend .env (CORS for LAN origin, idempotent)
$corsOrigins = "http://localhost:5173,http://127.0.0.1:5173,http://${ip}:5173,http://${ip}:8081"
$backendEnv = "$backendDir\.env"
if (-not (Test-Path $backendEnv)) {
    @"
APP_ENV=development
SECRET_KEY=dev-only-change-me-not-for-production
DATABASE_URL=sqlite:///./data/restaurant.db
ACCESS_TOKEN_MINUTES=480
CORS_ORIGINS=$corsOrigins
"@ | Set-Content -Path $backendEnv -Encoding ascii
    Write-Host "Created $backendEnv"
} else {
    # Patch CORS_ORIGINS line in place
    $lines = Get-Content $backendEnv
    $patched = $false
    $out = foreach ($l in $lines) {
        if ($l -match "^CORS_ORIGINS=") { "CORS_ORIGINS=$corsOrigins"; $patched = $true }
        else { $l }
    }
    if (-not $patched) { $out += "CORS_ORIGINS=$corsOrigins" }
    $out | Set-Content -Path $backendEnv -Encoding ascii
    Write-Host "Patched CORS_ORIGINS in $backendEnv"
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
} else {
    Write-Host "WARNING: web not found at $webDir"
}

# ------------------------------------------------------------------ 6. start Expo (foreground)
Write-Host ""
Write-Host "Starting Expo (foreground). Press Ctrl+C to stop."
Set-Location $mobileDir
npx expo start --android --lan
