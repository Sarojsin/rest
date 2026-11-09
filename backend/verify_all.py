import json, urllib.request

BASE = "http://127.0.0.1:8000"
STAFF_PASS = "Staff@#12345"

accounts = [
    ("main.manager", "bahadhami14+main.manager@gmail.com", "manager", "Main Branch"),
    ("main.waiter", "bahadhami14+main.waiter@gmail.com", "waiter", "Main Branch"),
    ("main.kitchen", "bahadhami14+main.kitchen@gmail.com", "kitchen", "Main Branch"),
    ("main.cashier", "bahadhami14+main.cashier@gmail.com", "cashier", "Main Branch"),
    ("lake.manager", "bahadhami14+lake.manager@gmail.com", "manager", "Lakeside Branch"),
    ("lake.waiter", "bahadhami14+lake.waiter@gmail.com", "waiter", "Lakeside Branch"),
    ("lake.kitchen", "bahadhami14+lake.kitchen@gmail.com", "kitchen", "Lakeside Branch"),
    ("lake.cashier", "bahadhami14+lake.cashier@gmail.com", "cashier", "Lakeside Branch"),
]

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

all_ok = True
for key, email, role, branch in accounts:
    try:
        lr = post_json("/api/v1/auth/login", {"email": email, "password": STAFF_PASS})
        st = lr["access_token"]
        me = get_json("/api/v1/me", st)
        m = me["membership"]
        print("OK %-16s -> role=%-8s status=%s branch_ids=%s perms=%d" % (
            email, m["role"], m.get("status"), m.get("branch_ids"), len(m.get("permissions", []))))
    except Exception as e:
        print("FAIL %s: %s" % (email, e))
        all_ok = False

print("\nAll OK:", all_ok)
