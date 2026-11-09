import requests

session = requests.Session()
session.headers.update({'Origin': 'http://127.0.0.1:5173'})

# Try the onboarding API
r = session.get('http://127.0.0.1:8000/api/platform/onboarding', timeout=10)
print(f'Onboarding API status: {r.status_code}')
print(f'Response: {r.text[:500]}')