import requests

# Check if admin user can access different API endpoints
session = requests.Session()

# Try to login as platform admin
print("Attempting platform admin login...")
payload = {'email': 'owner@harbor.example', 'password': 'PlatformOwner!1'}
r = session.post('http://127.0.0.1:8000/api/platform/auth/login', 
                 json=payload,
                 headers={'Origin': 'http://127.0.0.1:5173'},
                 timeout=10)
print(f'Login status: {r.status_code}')
print(f'Login response: {r.text[:200]}')

if r.status_code == 200:
    print("\n=== Checking API endpoints WITH auth ===")
    endpoints = [
        "/api/platform/public/plans",
        "/api/platform/self-service/registrations",
        "/api/platform/onboarding/restaurants",
        "/api/platform/settings",
    ]
    
    for ep in endpoints:
        r = session.get(f"http://127.0.0.1:8000{ep}", 
                        headers={"Origin": "http://127.0.0.1:5173"},
                        timeout=10)
        try:
            body = r.json()
            print(f"  {ep}: status={r.status_code}, code={body.get('code','N/A')}")
        except:
            print(f"  {ep}: status={r.status_code}, response={r.text[:100]}")
else:
    print("\nLogin failed, checking endpoints without auth...")
    endpoints = [
        "/api/platform/public/plans",
        "/api/platform/self-service/registrations",
    ]
    
    for ep in endpoints:
        r = session.get(f"http://127.0.0.1:8000{ep}", 
                        headers={"Origin": "http://127.0.0.1:5173"},
                        timeout=10)
        print(f"  {ep}: status={r.status_code}, response={r.text[:100]}")
PYEOF