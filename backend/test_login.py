import requests

session = requests.Session()

# Try logging in as sagardhami84@gmail.com
payload = {
    "email": "sagardhami84@gmail.com",
    "password": "TestPass123!"
}

r = session.post('http://127.0.0.1:8000/api/platform/auth/login',
                 json=payload,
                 headers={'Origin': 'http://127.0.0.1:5173'},
                 timeout=10)
print(f'Login status: {r.status_code}')
print(f'Response: {r.text[:500]}')

if r.status_code == 200:
    data = r.json()
    print(f'\nLogin successful!')
    print(f'Admin email: {data.get("admin", {}).get("email")}')
    print(f'Admin display name: {data.get("admin", {}).get("display_name")}')
    print(f'Auth token obtained')