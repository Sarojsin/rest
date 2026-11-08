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
    
    print("=" * 60)
    print("COMPREHENSIVE RESTAURANT OWNER WORKFLOW TEST")
    print("=" * 60)
    
    # Test restaurant info
    print("\n[RO-2] Restaurant Dashboard:")
    r = session.get('http://127.0.0.1:8000/api/v1/restaurant',
                    headers=headers, timeout=10)
    if r.status_code == 200:
        rest = r.json()
        print(f"  Restaurant: {rest.get('name')} ({rest.get('slug')})")
        print(f"  Currency: {rest.get('currency_code')} | Timezone: {rest.get('timezone')}")
        print(f"  QR Ordering: {rest.get('qr_ordering_enabled')}")
    
    # Test subscriptions
    print("\n[RO-8] Owner Subscription:")
    r = session.get('http://127.0.0.1:8000/api/v1/subscriptions/subscription',
                    headers=headers, timeout=10)
    print(f"  Status: {r.status_code}")
    if r.status_code == 200:
        sub = r.json()
        if sub:
            print(f"  Plan ID: {sub.get('plan_id', 'N/A')}")
            print(f"  Status: {sub.get('status', 'N/A')}")
            print(f"  Trial ends: {sub.get('trial_ends_at', 'N/A')}")
        else:
            print(f"  No active subscription")
    
    # Test orders
    print("\n[RO-4] Orders (Waiter QR Ordering):")
    r = session.get('http://127.0.0.1:8000/api/v1/orders',
                    headers=headers, timeout=10)
    if r.status_code == 200:
        orders = r.json() if isinstance(r.json(), list) else r.json().get('items', [])
        print(f"  Total orders: {len(orders)}")
    
    # Test service calls
    print("\n[RO-14] Service Calls:")
    r = session.get('http://127.0.0.1:8000/api/v1/service-calls',
                    headers=headers, timeout=10)
    if r.status_code == 200:
        calls = r.json() if isinstance(r.json(), list) else r.json().get('items', [])
        print(f"  Total service calls: {len(calls)}")
    
    # Test kitchen tickets
    print("\n[RO-5] Kitchen Tickets:")
    r = session.get('http://127.0.0.1:8000/api/v1/kitchen/tickets',
                    headers=headers, timeout=10)
    if r.status_code == 200:
        tickets = r.json() if isinstance(r.json(), list) else r.json().get('items', [])
        print(f"  Total kitchen tickets: {len(tickets)}")
    
    # Test payment methods
    print("\n[RO-6] Payment Methods:")
    r = session.get('http://127.0.0.1:8000/api/v1/payment-methods',
                    headers=headers, timeout=10)
    if r.status_code == 200:
        methods = r.json() if isinstance(r.json(), list) else r.json().get('items', [])
        print(f"  Payment methods: {len(methods)}")
    
    # Test menu items
    print("\n[Menu Items]:")
    r = session.get('http://127.0.0.1:8000/api/v1/menu/items',
                    headers=headers, timeout=10)
    if r.status_code == 200:
        items = r.json() if isinstance(r.json(), list) else r.json().get('items', [])
        print(f"  Total menu items: {len(items)}")
    elif r.status_code == 405:
        print(f"  GET not allowed (405)")
    
    # Test tables
    print("\n[Tables]:")
    r = session.get('http://127.0.0.1:8000/api/v1/tables',
                    headers=headers, timeout=10)
    if r.status_code == 200:
        tables = r.json() if isinstance(r.json(), list) else r.json().get('items', [])
        print(f"  Total tables: {len(tables)}")
    
    # Test branches
    print("\n[Branches]:")
    r = session.get('http://127.0.0.1:8000/api/v1/branches',
                    headers=headers, timeout=10)
    if r.status_code == 200:
        branches = r.json() if isinstance(r.json(), list) else r.json().get('items', [])
        print(f"  Total branches: {len(branches)}")
    
    print("\n" + "=" * 60)
    print("ALL WORKFLOW TESTS COMPLETE")
    print("=" * 60)
else:
    print(f'Login failed: {r.status_code}')