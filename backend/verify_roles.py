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

roles = [
    ("Manager", "bahadhami14+main.manager@gmail.com"),
    ("Kitchen", "bahadhami14+main.kitchen@gmail.com"),
    ("Cashier", "bahadhami14+main.cashier@gmail.com"),
    ("Waiter", "bahadhami14+main.waiter@gmail.com"),
]

for label, email in roles:
    lr = post_json("/api/v1/auth/login", {"email": email, "password": STAFF_PASS})
    st = lr["access_token"]
    me = get_json("/api/v1/me", st)
    perms = sorted(me["membership"].get("permissions", []))
    print(f"\n=== {label} ({email}) ===")
    print(f"Permissions ({len(perms)}): {perms}")

print("\nDone.")
