import json, urllib.request

BASE = "http://127.0.0.1:8000"

def post_json(path, body, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]

def get_json(path, token=None):
    headers = {}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(BASE + path, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]

# Login as waiter
lr = post_json("/api/v1/auth/login", {"email": "bahadhami14+main.waiter@gmail.com", "password": "Staff@#12345"})
waiter_token = lr[1]["access_token"]

status, orders = get_json("/api/v1/orders?status=PENDING_CONFIRMATION", waiter_token)
print("Pending orders for waiter: %d" % len(orders))
for o in orders:
    print("  Order %s | status=%s" % (str(o["id"])[:8], o["status"]))

# Login as cashier
lr = post_json("/api/v1/auth/login", {"email": "bahadhami14+main.cashier@gmail.com", "password": "Staff@#12345"})
cashier_token = lr[1]["access_token"]

status, sessions = get_json("/api/v1/sessions", cashier_token)
print("Cashier sessions: %d" % len(sessions))
for s in sessions[:3]:
    print("  Session %s | status=%s | total=%s" % (str(s["id"])[:8], s.get("status", "?"), s.get("total_minor", "N/A")))

print("\nWorkflow test complete!")
