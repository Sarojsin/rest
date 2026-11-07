import requests

# Check the me endpoint
session = requests.Session()

print("=== Checking /api/platform/auth/me ===")
r = requests.get('http://127.0.0.1:8000/api/platform/auth/me', 
                 headers={'Origin': 'http://127.0.0.1:5173'},
                 timeout=10)
print(f"Me endpoint: status={r.status_code}")
if r.status_code == 200:
    data = r.json()
    admin = data.get('admin', {})
    print(f"  Admin email: {admin.get('email')}")
    print(f"  Role: {admin.get('role')}")
    print(f"  Permissions: {admin.get('permissions', [])}")
    print(f"  Display name: {admin.get('display_name')}")
else:
    print(f"  Response: {r.text[:200]}")

# Check onboarding API
print("\n=== Checking /api/platform/onboarding ===")
r = requests.get('http://127.0.0.1:8000/api/platform/onboarding?page=1&page_size=25', 
                 headers={'Origin': 'http://127.0.0.1:5173'},
                 timeout=10)
print(f"Onboarding API: status={r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"  Items: {data.get('items', [])}")
    print(f"  Total: {data.get('total', 0)}")
    for item in data.get('items', [])[:3]:
        print(f"  Item: id={item.get('id')}, name={item.get('name')}, stage={item.get('onboarding_stage')}, tenant_id={item.get('tenant_id')}")
elif r.status_code == 401:
    print(f"  Response: {r.text[:200]}")
PYEOF