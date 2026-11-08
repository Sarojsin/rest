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
    headers = {'Authorization': f'Bearer {token}', 'Origin': 'http://127.0.0.1:5173'}
    
    # Test employees endpoint (owner can manage staff)
    print("=== Staff Management ===")
    r = session.get('http://127.0.0.1:8000/api/v1/restaurant_memberships',
                    headers=headers, timeout=10)
    print(f'Staff list status: {r.status_code}')
    if r.status_code == 200:
        data = r.json()
        items = data.get('items', [])
        print(f'Total staff: {len(items)}')
        for item in items[:5]:
            print(f"  - {item.get('email', 'N/A')} | {item.get('role', 'N/A')} | {item.get('status', 'N/A')}")
    
    # Test branches endpoint
    print("\n=== Branch Management ===")
    r = session.get('http://127.0.0.1:8000/api/v1/branches',
                    headers=headers, timeout=10)
    print(f'Branches status: {r.status_code}')
    if r.status_code == 200:
        data = r.json()
        items = data.get('items', [])
        print(f'Total branches: {len(items)}')
        for item in items[:5]:
            print(f"  - {item.get('name', 'N/A')} | {item.get('slug', 'N/A')} | {item.get('status', 'N/A')}")
    
    # Test tables endpoint
    print("\n=== Tables ===")
    r = session.get('http://127.0.0.1:8000/api/v1/tables',
                    headers=headers, timeout=10)
    print(f'Tables status: {r.status_code}')
    if r.status_code == 200:
        data = r.json()
        items = data.get('items', [])
        print(f'Total tables: {len(items)}')
        for item in items[:5]:
            print(f"  - Table {item.get('table_number', 'N/A')} | {item.get('status', 'N/A')} | QR: {bool(item.get('qr_token'))}")
else:
    print(f'Login failed: {r.status_code}')