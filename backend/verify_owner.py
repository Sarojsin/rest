import json, urllib.request

BASE = "http://127.0.0.1:8000"
OWNER_PASS = "Saroj@#12345"

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

lr = post_json("/api/v1/auth/login", {"email": "bahadhami14@gmail.com", "password": OWNER_PASS})
st = lr["access_token"]
me = get_json("/api/v1/me", st)
perms = sorted(me["membership"].get("permissions", []))
print(f"Owner ({me['email']}) - {len(perms)} permissions:")
for p in perms:
    print(f"  {p}")

# Key owner-only perms that manager should NOT have
owner_only = ["audit.read", "settings.manage", "staff.manage", "subscriptions.read", "subscriptions.create", "subscriptions.manage"]
print("\nOwner-only perms that manager lacks:")
for p in owner_only:
    has = p in perms
    print(f"  {p}: {'YES (owner has it)' if has else 'MISSING'}")

print("\nDone.")
