import requests
import json

# Approve registration via API
session = requests.Session()

# Try login first
print("Attempting platform admin login...")
payload = {'email': 'owner@harbor.example', 'password': 'PlatformOwner!1'}
r = session.post('http://127.0.0.1:8000/api/platform/auth/login', 
                 json=payload,
                 headers={'Origin': 'http://127.0.0.1:5173'},
                 timeout=10)
print(f'Login status: {r.status_code}')
print(f'Login response: {r.text[:200]}')

if r.status_code == 200:
    print("\n--- Now approving registration ---")
    reg_id = '6403e03c-ed54-4723-9d54-2e1b374490cd'
    approve_payload = {'confirm': True, 'reason': 'Self-service registration approval'}
    
    r = session.post(f'http://127.0.0.1:8000/api/platform/self-service/registrations/{reg_id}/approve',
                     json=approve_payload,
                     headers={'Origin': 'http://127.0.0.1:5173'},
                     timeout=10)
    print(f'Approval status: {r.status_code}')
    print(f'Approval response: {r.text[:500]}')
else:
    print("\n--- Trying API without session login ---")
    reg_id = '6403e03c-ed54-4723-9d54-2e1b374490cd'
    approve_payload = {'confirm': True, 'reason': 'Self-service registration approval'}
    
    r = session.post(f'http://127.0.0.1:8000/api/platform/self-service/registrations/{reg_id}/approve',
                     json=approve_payload,
                     headers={'Origin': 'http://127.0.0.1:5173', 'Content-Type': 'application/json'},
                     timeout=10)
    print(f'Status: {r.status_code}')
    print(f'Response: {r.text[:500]}')