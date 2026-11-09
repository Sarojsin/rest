import json, urllib.request

BASE = "http://127.0.0.1:8000"
STAFF_PASS = "Staff@#12345"

def post_json(path, body):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def get_json(path, token):
    req = urllib.request.Request(f"{BASE}{path}",
                                 headers={"Authorization": "Bearer " + token},
                                 method="GET")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

# Login as waiter
lr = post_json("/api/v1/auth/login", {"email": "bahadhami14+main.waiter@gmail.com", "password": STAFF_PASS})
st = lr["access_token"]
me = get_json("/api/v1/me", st)
perms = me["membership"].get("permissions", [])
print(f"Waiter permissions ({len(perms)}):")
for p in sorted(perms):
    print(f"  {p}")

# Test: waiter should NOT access inventory or employees
try:
    get_json("/api/v1/inventory", st)
    print("\nERROR: waiter can access inventory (should be forbidden)")
except Exception as e:
    print(f"\nOK: waiter cannot access inventory")

try:
    get_json("/api/v1/employees", st)
    print("ERROR: waiter can access employees (should be forbidden)")
except Exception as e:
    print("OK: waiter cannot access employees")

print("\nDone.")
