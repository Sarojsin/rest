import requests

session = requests.Session()

reg_data = {
    "restaurant_name": "Sagar Test Restaurant",
    "restaurant_slug": "sagar-test-84",
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
print(f'Registration status: {r.status_code}')
print(f'Response: {r.text[:500]}')

if r.status_code == 201:
    data = r.json()
    reg_id = data.get('id')
    print(f'Registration ID: {reg_id}')
    print(f'Status: {data.get("status")}')
    print(f'Owner email: {data.get("owner_email")}')