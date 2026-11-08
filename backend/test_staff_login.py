import requests

session = requests.Session()

# Try logging in as sagardhami84@gmail.com (restaurant owner)
payload = {
    "email": "sagardhami84@gmail.com",
    "password": "TestPass123!"
}

r = session.post('http://127.0.0.1:8000/api/v1/auth/login',
                 json=payload,
                 headers={'Origin': 'http://192.168.1.5:5173'},
                 timeout=10)
print(f'Login status: {r.status_code}')
print(f'Response: {r.text[:500]}')

if r.status_code == 200:
    data = r.json()
    print(f'\nLogin successful!')
    print(f'Admin/Staff email: {data.get("admin", {}).get("email") or data.get("user", {}).get("email")}')
    print(f'Role: {data.get("admin", {}).get("role") or data.get("user", {}).get("role")}')