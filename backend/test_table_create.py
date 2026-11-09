import json, urllib.request, urllib.error

BASE = "http://127.0.0.1:8000"
ORIGIN = "http://192.168.1.5:5173"

def post_json(path, body, origin=None, token=None):
    headers = {"Content-Type": "application/json"}
    if origin:
        headers["Origin"] = origin
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
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]

# Login as owner
lr = post_json("/api/v1/auth/login", {"email": "bahadhami14@gmail.com", "password": "Saroj@#12345"}, origin=ORIGIN)
print("Owner login:", lr[0])
if lr[0] == 200:
    token = lr[1]["access_token"]
    
    # Try creating a table
    result = post_json("/api/v1/tables", {
        "table_code": "T1",
        "display_name": "Table 1",
        "seating_capacity": 5,
        "sort_order": 1
    }, origin=ORIGIN, token=token)
    print("Create table:", result[0])
    if result[0] == 201:
        print("  Success:", result[1].get("table_code"), result[1].get("display_name"))
    else:
        print("  Error:", result[1])

# Login as waiter (should NOT have tables.configure)
lr2 = post_json("/api/v1/auth/login", {"email": "bahadhami14+main.waiter@gmail.com", "password": "Staff@#12345"}, origin=ORIGIN)
print("\nWaiter login:", lr2[0])
if lr2[0] == 200:
    token2 = lr2[1]["access_token"]
    result2 = post_json("/api/v1/tables", {
        "table_code": "T2",
        "display_name": "Table 2",
        "seating_capacity": 4,
        "sort_order": 2
    }, origin=ORIGIN, token=token2)
    print("Waiter create table:", result2[0])
    if result2[0] == 403:
        print("  Correctly forbidden - waiter doesn't have tables.configure")
    else:
        print("  Result:", result2[1])

print("\nDone!")
