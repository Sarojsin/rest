import requests

# Try to find a working login
session = requests.Session()

# Try different auth approaches
# 1. Platform auth login with various credentials
for email, pwd in [
    ('owner@harbor.example', 'PlatformOwner!1'),
    ('manager@harbor.example', 'PlatformOwner!1'),
    ('waiter@harbor.example', 'PlatformOwner!1'),
]:
    session = requests.Session()
    payload = {'email': email, 'password': pwd}
    r = session.post('http://127.0.0.1:8000/api/platform/auth/login', 
                     json=payload,
                     headers={'Origin': 'http://127.0.0.1:5173'},
                     timeout=10)
    print(f'{email}: status={r.status_code}, body={r.text[:100]}')
    if r.status_code == 200:
        print('  SUCCESS! Getting me...')
        r2 = session.get('http://127.0.0.1:8000/api/platform/auth/me', 
                         headers={'Origin': 'http://127.0.0.1:5173'},
                         timeout=10)
        print(f'  Me: {r2.text[:100]}')
        break