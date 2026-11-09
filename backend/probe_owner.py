import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"

def post(path, body):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def get(path, token):
    req = urllib.request.Request(
        BASE + path,
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

login = post("/api/v1/auth/login", {"email": "bahadhami14@gmail.com", "password": "Saroj@#12345"})
print("login keys:", sorted(login.keys()))
token = login["access_token"]
me = get("/api/v1/me", token)
print("me:", json.dumps(me, indent=2, default=str)[:800])
members = get("/api/v1/restaurant_memberships", token)
print("memberships:", json.dumps(members, indent=2, default=str)[:1200])
branches = get("/api/v1/branches", token)
print("branches:", json.dumps(branches, indent=2, default=str)[:800])
