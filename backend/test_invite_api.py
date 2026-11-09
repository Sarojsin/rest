import json, urllib.request, urllib.error, http.cookiejar

BASE = "http://127.0.0.1:8000"
ORIGIN = "http://192.168.1.5:5173"

# Create a cookiejar to handle cookies automatically
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# Login as platform admin
login_data = json.dumps({"email": "platform@harbor.example", "password": "PlatformOwner!1"}).encode()
req = urllib.request.Request(
    f"{BASE}/api/platform/auth/login",
    data=login_data,
    headers={"Content-Type": "application/json", "Origin": ORIGIN},
    method="POST"
)
try:
    with opener.open(req) as resp:
        login_resp = json.loads(resp.read())
        print("Login OK")
        for c in cj:
            print("  Cookie: %s = %s..." % (c.name, c.value[:20]))
except urllib.error.HTTPError as e:
    print("Login failed:", e.code, e.read().decode()[:200])

# Find CSRF token
csrf_token = None
for c in cj:
    if "csrf" in c.name.lower():
        csrf_token = c.value
        break

print("CSRF token: %s..." % (csrf_token[:30] if csrf_token else "none"))

# Now invite a new platform user
invite_data = json.dumps({
    "email": "test.admin@harbor.example",
    "display_name": "Test Admin",
    "role": "support",
    "reason": "Testing invite flow"
}).encode()

headers = {
    "Content-Type": "application/json",
    "Origin": ORIGIN,
}
if csrf_token:
    headers["X-CSRF-Token"] = csrf_token

req2 = urllib.request.Request(
    f"{BASE}/api/platform/platform-users",
    data=invite_data,
    headers=headers,
    method="POST"
)
try:
    with opener.open(req2) as resp:
        resp_data = json.loads(resp.read())
        print("Invite created!")
        print("  Admin:", resp_data.get("admin", {}).get("email"))
        print("  Role:", resp_data.get("admin", {}).get("role"))
        print("  Token:", resp_data.get("invitation", {}).get("token", "none")[:30])
        print("  Accept URL:", resp_data.get("invitation", {}).get("accept_url", "none"))
except urllib.error.HTTPError as e:
    print("Invite failed:", e.code, e.read().decode()[:300])
