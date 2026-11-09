import json, urllib.request, urllib.error

BASE = "http://127.0.0.1:8000"
OWNER_EMAIL = "bahadhami14@gmail.com"
OWNER_PASS = "Saroj@#12345"

def post_json(path, body, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode(),
        headers=headers,
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read()), resp.status
    except urllib.error.HTTPError as e:
        print("HTTP ERROR", e.code)
        print(e.read().decode()[:1000])
        raise

def get_json(path, token):
    headers = {"Authorization": f"Bearer {token}"}
    req = urllib.request.Request(f"{BASE}{path}", headers=headers, method="GET")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

login_resp, _ = post_json("/api/v1/auth/login", {"email": OWNER_EMAIL, "password": OWNER_PASS})
owner_token = login_resp["access_token"]
print("owner ok")

inv, status = post_json("/api/v1/restaurant_memberships/invite", {
    "email": "bahadhami14+main.kitchen@gmail.com",
    "role": "kitchen",
    "name": "Kitchen Main Branch",
    "branch_id": "bc62498a-279b-487b-9d20-076306a661c3",
}, owner_token)
print("invite status:", status)
print("token:", inv.get("invitation_token"))
