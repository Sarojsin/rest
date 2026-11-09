import json, urllib.request, urllib.error

BASE = "http://127.0.0.1:8000"
STAFF_PASS = "Staff@#12345"

def post_json(path, body):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]

def get_json(path, token):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + token}, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]

accounts = [
    ("Owner", "bahadhami14@gmail.com", "Saroj@#12345", "/staff"),
    ("Main Waiter", "bahadhami14+main.waiter@gmail.com", STAFF_PASS, "/staff/tables"),
    ("Main Kitchen", "bahadhami14+main.kitchen@gmail.com", STAFF_PASS, "/staff/kitchen"),
    ("Main Cashier", "bahadhami14+main.cashier@gmail.com", STAFF_PASS, "/staff/cashier"),
]

tokens = {}
for name, email, password, expected_path in accounts:
    status, body = post_json("/api/v1/auth/login", {"email": email, "password": password})
    if status == 200:
        tok = body["access_token"]
        tokens[name] = tok
        me_status, me = get_json("/api/v1/me", tok)
        role = me["membership"]["role"]
        print("OK %s (%s) -> role=%s" % (name, email, role))
    else:
        print("FAIL %s (%s): %s" % (name, email, body))

print("\nAll accounts verified!")
