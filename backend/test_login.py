import requests

session = requests.Session()
session.headers.update({'Origin': 'http://127.0.0.1:5173'})

# Try login
payload = {
    'email': 'sarojsinghdhami91@gmail.com',
    'password': 'TestPass123!'
}

r = session.post('http://127.0.0.1:8000/api/platform/auth/login', json=payload, timeout=10)
print(f'Login status: {r.status_code}')
if r.status_code == 200:
    data = r.json()
    print(f'Login successful: {data.get("user", {}).get("email")}')
    print(f'Token: {data.get("access_token", "")[:50]}...')
    print(f'Permissions: {data.get("user", {}).get("permissions", [])}')
else:
    print(f'Login failed: {r.text[:200]}')