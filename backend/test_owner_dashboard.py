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

if r.status_code == 200:
    data = r.json()
    token = data.get("access_token", "")
    print(f'Login successful! Token obtained.')
    
    # Test dashboard endpoint
    headers = {'Authorization': f'Bearer {token}', 'Origin': 'http://127.0.0.1:5173'}
    
    # Try various dashboard endpoints
    endpoints = [
        '/api/v1/restaurant',
        '/api/v1/dashboard/revenue',
        '/api/v1/dashboard/orders',
        '/api/v1/dashboard/sales/daily',
        '/api/v1/dashboard/best-dishes',
        '/api/v1/restaurant_memberships',
    ]
    
    for endpoint in endpoints:
        r2 = session.get(f'http://127.0.0.1:8000{endpoint}',
                        headers=headers,
                        timeout=10)
        print(f'{r2.status_code} {endpoint}')
        if r2.status_code == 200:
            resp = r2.json()
            print(f'   Response: {str(resp)[:200]}')
        else:
            print(f'   Error: {r2.text[:200]}')
else:
    print(f'Login failed: {r.status_code}')