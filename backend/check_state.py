import json, urllib.request

BASE = "http://127.0.0.1:8000"

def post_json(path, body, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE}{path}", data=json.dumps(body).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read())

def get_json(path, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE}{path}", headers=headers, method="GET")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

# Login as owner
lr = post_json("/api/v1/auth/login", {"email": "bahadhami14@gmail.com", "password": "Saroj@#12345"})
status_code, body = lr
token = body["access_token"]
print("Owner logged in")

# Get branches
branches = get_json("/api/v1/branches", token)
print(f"Branches: {len(branches)}")
for b in branches:
    print("  %s (%s) - id=%s" % (b["name"], b["code"], b["id"]))

# Get tables
tables = get_json("/api/v1/tables", token)
print("\nTables: %d" % len(tables))
for t in tables:
    print("  %s | %s | status=%s" % (t["table_code"], t["display_name"], t["status"]))

# Check categories
try:
    cats = get_json("/api/v1/categories", token)
    print("\nCategories: %d" % len(cats))
    for c in cats:
        print("  %s" % c["name"])
except Exception as e:
    print("\nCategories error: %s" % e)

# Check items
try:
    items = get_json("/api/v1/items", token)
    print("Menu items: %d" % len(items))
    for i in items[:10]:
        print("  %s [%s]" % (i["name"], i.get("status", "N/A")))
except Exception as e:
    print("\nItems error: %s" % e)
