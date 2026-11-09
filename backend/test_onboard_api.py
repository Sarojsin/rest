import requests

session = requests.Session()
session.headers.update({'Origin': 'http://127.0.0.1:5173'})

# Try the onboarding API (no auth)
r = requests.get('http://127.0.0.1:8000/api/platform/onboarding', timeout=10)
print(f'Onboarding API (no auth): {r.status_code}')
print(f'Response: {r.text[:200]}')

# Try with auth header
r2 = requests.get('http://127.0.0.1:8000/api/platform/onboarding', 
                  headers={'Authorization': 'Bearer test'}, timeout=10)
print(f'\\nOnboarding API (with auth header): {r2.status_code}')
print(f'Response: {r2.text[:200]}')