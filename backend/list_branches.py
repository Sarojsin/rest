import json, urllib.request, urllib.error

BASE = "http://127.0.0.1:8000"

login_req = urllib.request.Request(
    f"{BASE}/api/v1/auth/login",
    method="POST",
    data=json.dumps({"email": "bahadhami14@gmail.com", "password": "Saroj@#12345"}).encode(),
    headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(login_req) as resp:
    token = json.loads(resp.read())['access_token']

branches_req = urllib.request.Request(
    f"{BASE}/api/v1/branches",
    headers={"Authorization": f"Bearer {token}"}
)
with urllib.request.urlopen(branches_req) as resp:
    branches = json.loads(resp.read())
    print("branches:", json.dumps(branches, indent=2))