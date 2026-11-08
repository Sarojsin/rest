import requests
import json

# Register a new restaurant via self-service API
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
    "reason": "End-to-end onboarding test"
}

print("=== Step 1: Self-service registration ===")
r = session.post('http://127.0.0.1:8000/api/platform/public/register', 
                 json=reg_data,
                 headers={'Origin': 'http://127.0.0.1:5173'},
                 timeout=10)
print(f'Status: {r.status_code}')
print(f'Response: {r.text[:500]}')

if r.status_code == 201:
    data = r.json()
    reg_id = data.get('id')
    print(f'\nRegistration ID: {reg_id}')
    print(f'Status: {data.get("status")}')
    
    print(f'\n=== Step 2: Approve registration via database ===')
    print(f'Registration ID: {reg_id}')
    print(f'Owner email: sagardhami84@gmail.com')
    print(f'Next: Need to approve via database to generate invitation token')
else:
    print(f'Registration failed')