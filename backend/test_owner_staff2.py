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
    
    # Test branches endpoint
    print("=== Branch Management ===")
    r = session.get('http://127.0.0.1:8000/api/v1/branches',
                    headers=headers, timeout=10)
    print(f'Branches status: {r.status_code}')
    if r.status_code == 200:
        data = r.json()
        branches = data if isinstance(data, list) else data.get('items', [])
        print(f'Total branches: {len(branches)}')
        for item in branches[:5]:
            print(f"  - {item.get('name', 'N/A')} | {item.get('slug', 'N/A')} | {item.get('status', 'N/A')}")
    
    # Test tables endpoint
    print("\n=== Tables ===")
    r = session.get('http://127.0.0.1:8000/api/v1/tables',
                    headers=headers, timeout=10)
    print(f'Tables status: {r.status_code}')
    if r.status_code == 200:
        data = r.json()
        tables = data if isinstance(data, list) else data.get('items', [])
        print(f'Total tables: {len(tables)}')
        for item in tables[:5]:
            print(f"  - Table {item.get('table_number', 'N/A')} | {item.get('status', 'N/A')} | QR: {bool(item.get('qr_token'))}")
    
    # Test menu items
    print("\n=== Menu Items ===")
    r = session.get('http://127.0.0.1:8000/api/v1/menu/items',
                    headers=headers, timeout=10)
    print(f'Menu items status: {r.status_code}')
    if r.status_code == 200:
        data = r.json()
        items = data.get('items', []) if isinstance(data, dict) else data
        print(f'Total menu items: {len(items)}')
        for item in items[:5]:
            print(f"  - {item.get('name', 'N/A')} | ${item.get('price_minor', 0)/100:.2f} | {item.get('status', 'N/A')}")
else:
    print(f'Login failed: {r.status_code}')