import requests
import json

# Check self-service registration endpoint
session = requests.Session()

# 1. List available plans first
print("=== 1. List available plans ===")
r = session.get('http://127.0.0.1:8000/api/platform/public/plans', 
                headers={'Origin': 'http://127.0.0.1:5173'},
                timeout=10)
print(f'Status: {r.status_code}')
if r.status_code == 200:
    plans = r.json()['items']
    for p in plans:
        print(f"  {p['code']}: {p['name']} (trial_days={p['trial_days']})")

# 2. Try registration with sagardhami84@gmail.com
print("\n=== 2. Try self-service registration ===")
reg_data = {
    "restaurant_name": "Test Restaurant",
    "restaurant_slug": "test-restaurant-84",
    "owner_email": "sagardhami84@gmail.com",
    "owner_name": "Sagar Dhami",
    "owner_phone": "9820243416",
    "plan_code": "growth",
    "contact_email": "sagardhami84@gmail.com",
    "contact_phone": "9820243416",
    "legal_name": "Sagar Dhami",
    "timezone": "Asia/Kathmandu",
    "currency_code": "NPR",
    "source": "self_service",
    "reason": "Test registration"
}

r = session.post('http://127.0.0.1:8000/api/platform/public/register', 
                 json=reg_data,
                 headers={'Origin': 'http://127.0.0.1:5173'},
                 timeout=10)
print(f'Status: {r.status_code}')
print(f'Response: {r.text[:500]}')

# 3. Check existing registrations
print("\n=== 3. Check existing registrations ===")
session2 = requests.Session()
r = session2.get('http://127.0.0.1:8000/api/platform/self-service/registrations', 
                 headers={'Origin': 'http://127.0.0.1:5173'},
                 timeout=10)
print(f'Status: {r.status_code}')
if r.status_code == 200:
    data = r.json()
    print(f'Total: {data.get("total", 0)}')
    for item in data.get('items', []):
        print(f'  ID: {item.get("id")[:8]}... Email: {item.get("owner_email")} Status: {item.get("status")}')
PYEOF