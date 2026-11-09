import json, urllib.request, urllib.error

BASE = "http://127.0.0.1:8000"
STAFF_PASS = "Staff@#12345"

def login(email):
    req = urllib.request.Request(
        f"{BASE}/api/v1/auth/login",
        data=json.dumps({"email": email, "password": STAFF_PASS}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["access_token"]

def api(token, method, path, body=None):
    headers = {"Authorization": "Bearer " + token}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]

# Waiter should NOT access reports
w_token = login("bahadhami14+main.waiter@gmail.com")
code, body = api(w_token, "GET", "/api/v1/reports/sales")
print("Waiter GET /reports/sales -> %d (expect 403): %s" % (code, body))

# Kitchen should NOT issue bills
k_token = login("bahadhami14+main.kitchen@gmail.com")
code, body = api(k_token, "GET", "/api/v1/sessions/x/bill")
print("Kitchen GET /sessions/x/bill -> %d (expect 403/404): %s" % (code, body))

# Manager SHOULD access reports
m_token = login("bahadhami14+main.manager@gmail.com")
code, body = api(m_token, "GET", "/api/v1/reports/sales")
print("Manager GET /reports/sales -> %d (expect 200): %s" % (code, str(body)[:100]))

# Waiter should NOT access branches.create
code, body = api(w_token, "POST", "/api/v1/restaurant_memberships/invite", {
    "email": "x@y.com", "role": "waiter", "branch_id": "bc62498a-279b-487b-9d20-076306a661c3"
})
print("Waiter POST /invite -> %d (expect 403): %s" % (code, body))

print("\nDone.")
