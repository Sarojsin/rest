import json, urllib.request

BASE = "http://127.0.0.1:8000"

def get_json(path):
    req = urllib.request.Request(BASE + path, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]

# Test QR token from the table listing
full_token = "8cf528eebafe4e62a9ee16225e7fbd1a"

print("Testing QR token:", full_token)
status, menu = get_json(f"/api/v1/public/qr/{full_token}/menu")
if status == 200:
    print("Menu loaded: OK")
    print("Restaurant:", menu["restaurant_name"])
    print("Table:", menu["table_display_name"])
    print("QR ordering enabled:", menu["qr_ordering_enabled"])
    print("Categories:", len(menu["categories"]))
    for cat in menu["categories"]:
        items = [i["name"] for i in cat["items"]]
        print(f"  {cat['name']}: {', '.join(items)}")
else:
    print("Menu load failed:", menu)

# Also test with a preview (16 char) token - should fail
short_token = full_token[:16]
print("\nTesting short token (preview only):", short_token)
status2, menu2 = get_json(f"/api/v1/public/qr/{short_token}/menu")
if status2 == 200:
    print("Short token worked: OK")
else:
    print("Short token correctly rejected:", status2, menu2[:100] if isinstance(menu2, str) else menu2)
