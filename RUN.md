How to Run the Mobile App
Here are the exact steps to get the React Native staff app running on the Android emulator (AVD Medium_Phone is already set up).

1. Start the Backend API
The mobile app connects to the FastAPI backend at http://10.0.2.2:8000 (emulator host loopback). Start it first:

cd E:\rest\backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
Verify it's healthy:

curl http://127.0.0.1:8000/health
# Should return: {"status":"ok"}
2. Verify the Emulator is Running
adb devices
# Should show: emulator-5554 device
If the emulator isn't running, start it:

& "$env:LOCALAPPDATA\Android\Sdk\emulator\emulator.exe" -avd Medium_Phone -no-snapshot-load -gpu swiftshader_indirect
Wait a moment then check:

adb devices
3. Fix JSON BOM (one-time setup)
The write tool sometimes emits a UTF-8 BOM. If you get Unexpected token '﻿' errors, strip it:

$files = @(
  "E:\rest\apps\mobile\package.json",
  "E:\rest\apps\mobile\app.json",
  "E:\rest\apps\mobile\tsconfig.json",
  "E:\rest\packages\api-client\index.ts"
)
foreach ($f in $files) {
  $bytes = [System.IO.File]::ReadAllBytes($f)
  $hasBom = $bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF
  if ($hasBom) {
    $text = [System.Text.Encoding]::UTF8.GetString($bytes, 3, $bytes.Length - 3)
    [System.IO.File]::WriteAllText($f, $text, (New-Object System.Text.UTF8Encoding $false))
    Write-Host "BOM stripped from $f"
  }
}
4. Start the Expo Development Server
From the mobile app directory:

cd E:\rest\apps\mobile
npx expo start --android
The first time may take a minute to build the Metro bundle. It will output something like:

› Opening exp://192.168.1.4:8081?__expo_disable_fab=1... on Infinix_X669C
5. Launch on the Device/Emulator
On a physical device: Scan the QR code with the Expo Go app
On the Android emulator: The adb device should auto-connect. The app will launch directly.
6. Login with Demo Accounts
After the app opens, use one of these demo accounts (password always Harbor{Role}!1):

Role	Email	Permissions
Waiter	waiter@harbor.example	orders.create, orders.confirm_qr, orders.read, tables.manage
Kitchen	kitchen@harbor.example	kitchen.read, kitchen.update, orders.read
Cashier	cashier@harbor.example	bills.issue, kitchen.read, orders.read, payments.record, reports.read
Manager	manager@harbor.example	(full staff permissions)
Owner	owner@harbor.example	(all permissions)
Password pattern: Harbor<Role>!1 (e.g., HarborWaiter!1, HarborCashier!1).

7. What You'll See Per Role
Waiter → Tables grid (occupancy badges, pending QR count) → Tap a table → Take order (menu with stepper) → Send to kitchen → See order on kitchen board → Accept/reject pending QR requests
Kitchen → 3-column ticket board (NEW/Cooking/READY) → Per-item transitions (START → READY → SERVED) → "All ready — call waiter" → Service calls acknowledged
Cashier → Table list (open sessions) → Issue bill → View bill lines/subtotal/tax/balance → Record payment (CASH only, QR images not yet uploaded) → Verification pending local UI → Settled/part-paid states
Troubleshooting
Issue	Fix
Unexpected token '﻿'	Strip BOM from JSON files (step 3)
Cannot resolve asset "./assets/images/icon.png"	Ensure assets are in E:\rest\apps\mobile\assets\ (they are from the template copy)
Backend 401 on /me	Ensure backend is running and API_BASE_URL defaults to http://10.0.2.2:8000 for emulator
White screen / Metro error	Run npx expo install to ensure all deps are aligned (already done: 546 packages)
Permission denied on navigation	Check that has(permission) matches: waiter needs orders.create, kitchen needs kitchen.update, cashier needs bills.issue
Quick Re-run
If you've already started everything once, you can just:

# From mobile app directory
npx expo start --android
The emulator should reconnect and the app will reload from the Metro cache.