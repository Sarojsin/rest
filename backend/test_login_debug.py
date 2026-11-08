import requests

# Test login with detailed cookie inspection
session = requests.Session()
r = session.post('http://127.0.0.1:8000/api/platform/auth/login',
                 json={'email': 'platform@harbor.example', 'password': 'PlatformOwner!1'},
                 headers={'Origin': 'http://127.0.0.1:5173'},
                 timeout=10)
print(f"Login status: {r.status_code}")
print(f"Cookies: {session.cookies.get_dict()}")
print(f"Response headers: {dict(r.headers)}")

# Try accessing an endpoint with the session
r2 = session.get('http://127.0.0.1:8000/api/platform/tenants',
                 headers={'Origin': 'http://127.0.0.1:5173'},
                 timeout=10)
print(f"\nTenants status: {r2.status_code}")
print(f"Tenants response: {r2.text[:200]}")

# Try auth/me endpoint
r3 = session.get('http://127.0.0.1:8000/api/platform/auth/me',
                 headers={'Origin': 'http://127.0.0.1:5173'},
                 timeout=10)
print(f"\nMe status: {r3.status_code}")
print(f"Me response: {r3.text[:200]}")