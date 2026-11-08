import requests

session = requests.Session()
payload = {
    "email": "sagardhami84@gmail.com",
    "password": "TestPass123!"
}

r = session.post('http://127.0.0.1:8000/api/v1/auth/login',
                 json=payload,
                 headers={'Origin': 'http://127.0.0.1:5173'},
                 timeout=10)
print(f'Login status: {r.status_code}')
print(f'Response: {r.text[:500]}')

if r.status_code == 200:
    data = r.json()
    print(f'\nLogin successful!')
    user = data.get("user", {})
    print(f'User email: {user.get("email")}')
    print(f'Display name: {user.get("display_name")}')
    print(f'Role: {user.get("role")}')
    token = data.get("access_token", "")
    print(f'Access token: {token[:50]}...')
else:
    print(f'\nLogin failed')